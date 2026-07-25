import os
import subprocess
import json
import sys
from dotenv import load_dotenv

load_dotenv()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_LEGACY_APP_DIR = os.path.join(SCRIPT_DIR, "..", "legacy-app")
LEGACY_APP_DIR = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.abspath(DEFAULT_LEGACY_APP_DIR)
NVD_API_KEY = os.getenv("NVD_API_KEY")

# Import the agent logic we already built
from remediation_agent import load_vulnerabilities, pick_top_priority, ask_llm_for_fix, apply_version_override, POM_PATH
from test_generation_agent import read_file, generate_test

REPORT = {"stages": []}


def log_stage(name, success, details=""):
    REPORT["stages"].append({"stage": name, "success": success, "details": details})
    status = "OK" if success else "FAILED"
    print(f"\n[{status}] {name}")
    if details:
        print(details[:500])


def run_mvn(args, cwd=LEGACY_APP_DIR):
    result = subprocess.run(
        ["mvn"] + args, cwd=cwd, capture_output=True, text=True, shell=True,
        encoding="utf-8", errors="replace"
    )
    success = result.returncode == 0
    return success, result.stdout[-3000:] + result.stderr[-1000:]

def apply_known_migration_fixes(legacy_app_dir):
    """
    Applies fix patterns discovered during initial migration testing.
    These address gaps OpenRewrite's automated recipes don't cover:
    generator tooling config, dead code, Hibernate 6 JPQL strictness,
    and a pre-existing spec defect.
    """
    fixes_applied = []

    # Fix 1: OpenAPI generator plugin - bump version, add useSpringBoot3
    pom_path = os.path.join(legacy_app_dir, "pom.xml")
    with open(pom_path, "r", encoding="utf-8") as f:
        pom = f.read()

    if "<openapi-generator-maven-plugin.version>5.2.1</openapi-generator-maven-plugin.version>" in pom:
        pom = pom.replace(
            "<openapi-generator-maven-plugin.version>5.2.1</openapi-generator-maven-plugin.version>",
            "<openapi-generator-maven-plugin.version>7.9.0</openapi-generator-maven-plugin.version>"
        )
        fixes_applied.append("Bumped openapi-generator-maven-plugin to 7.9.0")

    if "<serializationLibrary>jackson</serializationLibrary>" in pom and "<useSpringBoot3>" not in pom:
        pom = pom.replace(
            "<serializationLibrary>jackson</serializationLibrary>",
            "<serializationLibrary>jackson</serializationLibrary>\n                                <useSpringBoot3>true</useSpringBoot3>"
        )
        fixes_applied.append("Added useSpringBoot3=true to generator config")

    with open(pom_path, "w", encoding="utf-8") as f:
        f.write(pom)

    # Fix 2: Remove dead Springfox workaround class
    dead_file = os.path.join(
        legacy_app_dir, "src/main/java/org/springframework/samples/petclinic/util/ApplicationSwaggerConfig.java"
    )
    if os.path.exists(dead_file):
        os.remove(dead_file)
        fixes_applied.append("Removed dead ApplicationSwaggerConfig.java (Springfox workaround)")

    # Fix 3: JPQL raw-column-name bugs (Hibernate 6 strictness)
    jpql_fixes = [
        ("repository/jpa/JpaPetRepositoryImpl.java", "WHERE pet_id=", "WHERE visit.pet.id="),
        ("repository/springdatajpa/SpringDataPetRepositoryImpl.java", "WHERE pet_id=", "WHERE visit.pet.id="),
        ("repository/jpa/JpaPetTypeRepositoryImpl.java", "WHERE type_id=", "WHERE pet.type.id="),
        ("repository/springdatajpa/SpringDataPetTypeRepositoryImpl.java", "WHERE type_id=", "WHERE pet.type.id="),
    ]
    for rel_path, old, new in jpql_fixes:
        full_path = os.path.join(legacy_app_dir, "src/main/java/org/springframework/samples/petclinic", rel_path)
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                src = f.read()
            if old in src:
                src = src.replace(old, new)
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(src)
                fixes_applied.append(f"Fixed JPQL column reference in {rel_path}")

    # Fix 4: Missing 'required' field in OpenAPI spec (pre-existing defect)
    spec_path = os.path.join(legacy_app_dir, "src/main/resources/api-docs.yml")
    if os.path.exists(spec_path):
        with open(spec_path, "r", encoding="utf-8") as f:
            spec = f.read()
        old_required = "      required:\n        - id\n    User:"
        new_required = "      required:\n        - id\n        - name\n    User:"
        if old_required in spec:
            spec = spec.replace(old_required, new_required)
            with open(spec_path, "w", encoding="utf-8") as f:
                f.write(spec)
            fixes_applied.append("Added missing 'name' to PetType required fields in api-docs.yml")

    return fixes_applied


def stage_migration():
    print("\n=== STAGE 1: Migration (OpenRewrite) ===")
    success, output = run_mvn([
        "-U", "org.openrewrite.maven:rewrite-maven-plugin:run",
        "-Drewrite.recipeArtifactCoordinates=org.openrewrite.recipe:rewrite-spring:RELEASE",
        "-Drewrite.activeRecipes=org.openrewrite.java.spring.boot3.UpgradeSpringBoot_3_0"
    ])
    log_stage("Migration (OpenRewrite)", success, output)

    print("\n--- Applying known fix patterns (learned from prior migration analysis) ---")
    fixes = apply_known_migration_fixes(LEGACY_APP_DIR)
    log_stage("Known migration fixes applied", True, "\n".join(fixes) if fixes else "No known fixes needed")

    print("\n--- Verifying build after migration ---")
    success, output = run_mvn(["clean", "compile"])
    log_stage("Build verification after migration", success, output)
    return success


def stage_vulnerability_remediation():
    print("\n=== STAGE 2: Vulnerability Scan + Remediation ===")
    success, output = run_mvn([
        "org.owasp:dependency-check-maven:check",
        f"-DnvdApiKey={NVD_API_KEY}", "-Dformats=JSON,HTML"
    ])
    log_stage("Vulnerability scan", success, output)
    if not success:
        return False

    report_path = os.path.join(LEGACY_APP_DIR, "target", "dependency-check-report.json")
    findings = load_vulnerabilities(report_path=report_path)
    top = pick_top_priority(findings)
    if not top:
        log_stage("Remediation", True, "No suitable high-confidence target found. Skipping.")
        return True

    print(f"Top priority target: {top['dependency']} | {top['cve']} | {top['severity']}")
    fix = ask_llm_for_fix(top)
    print(f"Proposed fix: {fix['group_id']}:{fix['artifact_id']} -> {fix['fixed_version']}")

    apply_version_override(os.path.join(LEGACY_APP_DIR, "pom.xml"), fix["group_id"], fix["artifact_id"], fix["fixed_version"])
    log_stage("Remediation applied", True, json.dumps(fix, indent=2))

    print("\n--- Verifying build after remediation ---")
    success, output = run_mvn(["clean", "compile"])
    log_stage("Build verification after remediation", success, output)
    return success


def stage_test_generation():
    print("\n=== STAGE 3: Coverage-driven Test Generation ===")
    target_path = os.path.join(
        LEGACY_APP_DIR, "src/main/java/org/springframework/samples/petclinic/util/EntityUtils.java"
    )
    dep_path = os.path.join(
        LEGACY_APP_DIR, "src/main/java/org/springframework/samples/petclinic/model/BaseEntity.java"
    )
    output_path = os.path.join(
        LEGACY_APP_DIR, "src/test/java/org/springframework/samples/petclinic/util/EntityUtilsTests.java"
    )

    if os.path.exists(output_path):
        log_stage("Test generation", True, "EntityUtilsTests.java already exists. Skipping generation.")
        return True

    target_source = read_file(target_path)
    dep_source = read_file(dep_path)
    test_code = generate_test(target_source, dep_source)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(test_code)
    log_stage("Test generation", True, f"Wrote {output_path}")

    print("\n--- Verifying new test passes ---")
    success, output = run_mvn(["test", "-Dtest=EntityUtilsTests"])
    log_stage("New test verification", success, output)
    return success


def stage_final_report():
    print("\n=== STAGE 4: Final Full Test Run + Coverage ===")
    success, output = run_mvn(["test", "jacoco:report"])
    log_stage("Final full test suite + coverage", success, output)
    return success


if __name__ == "__main__":
    print("Starting multi-agent modernization pipeline...\n")

    ok = stage_migration()
    if ok:
        ok = stage_vulnerability_remediation()
    if ok:
        ok = stage_test_generation()
    if ok:
        stage_final_report()

    print("\n\n=== PIPELINE SUMMARY ===")
    for s in REPORT["stages"]:
        print(f"{'OK' if s['success'] else 'FAILED':6} - {s['stage']}")

    with open("pipeline_report.json", "w", encoding="utf-8") as f:
        json.dump(REPORT, f, indent=2)
    print("\nFull report saved to pipeline_report.json")
    
    
    
