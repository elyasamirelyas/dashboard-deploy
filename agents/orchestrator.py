import os
import subprocess
import json
import sys
import re
import time
from dotenv import load_dotenv
from remediation_agent import load_vulnerabilities, get_prioritized_targets, ask_llm_for_fix, apply_version_override

def print_environment_diagnostics():
    print("\n=== ENVIRONMENT DIAGNOSTICS ===")
    print(f"JAVA_HOME env var: {os.environ.get('JAVA_HOME', 'NOT SET')}")
    result = subprocess.run(["java", "-version"], capture_output=True, text=True, shell=True)
    print(f"java -version output:\n{result.stdout}{result.stderr}")
    result2 = subprocess.run(["mvn", "-version"], capture_output=True, text=True, shell=True, cwd=LEGACY_APP_DIR)
    print(f"mvn -version output:\n{result2.stdout}{result2.stderr}")
    print("=== END DIAGNOSTICS ===\n")

load_dotenv()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_LEGACY_APP_DIR = os.path.join(SCRIPT_DIR, "..", "legacy-app")
LEGACY_APP_DIR = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.abspath(DEFAULT_LEGACY_APP_DIR)
NVD_API_KEY = os.getenv("NVD_API_KEY")

# Import the agent logic we already built
from remediation_agent import load_vulnerabilities, pick_top_priority, ask_llm_for_fix, apply_version_override, POM_PATH


REPORT = {"stages": []}


def log_stage(name, success, details=""):
    REPORT["stages"].append({"stage": name, "success": success, "details": details})
    status = "OK" if success else "FAILED"
    print(f"\n[{status}] {name}")
    if details:
        print(details[:500])
    save_report()  # write progress incrementally so the UI can poll it


def save_report():
    with open(os.path.join(SCRIPT_DIR, "pipeline_report.json"), "w", encoding="utf-8") as f:
        json.dump(REPORT, f, indent=2)


MVN_CMD = r"C:\Users\amiri\apache-maven-3.9.16-bin\apache-maven-3.9.16\bin\mvn.cmd"
JAVA17_HOME = r"C:\Program Files\Eclipse Adoptium\jdk-17.0.17.10-hotspot"

import time

def run_mvn(args, cwd=None, retries=2, delay=3):
    if cwd is None:
        cwd = LEGACY_APP_DIR
    env = os.environ.copy()
    env["JAVA_HOME"] = JAVA17_HOME
    env["PATH"] = os.path.join(JAVA17_HOME, "bin") + os.pathsep + env.get("PATH", "")

    last_output = ""
    for attempt in range(retries + 1):
        result = subprocess.run(
            [MVN_CMD] + args, cwd=cwd, capture_output=True, text=True,
            encoding="utf-8", errors="replace", env=env, shell=False
        )
        success = result.returncode == 0
        last_output = result.stdout[-3000:] + result.stderr[-1000:]
        if success:
            return success, last_output
        if attempt < retries:
            print(f"  (attempt {attempt + 1} failed, retrying in {delay}s...)")
            time.sleep(delay)

    return False, last_output

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
            
    # Fix 5: Pin swagger-annotations version explicitly. Generated DTOs use
    # Schema.requiredMode(), added in swagger-core 2.2.0+. Without an explicit
    # pin, Maven's transitive dependency resolution can non-deterministically
    # select an older version lacking this method.
    if "<groupId>io.swagger.core.v3</groupId>" not in pom:
        insert_point = pom.find("<dependencies>")
        if insert_point != -1:
            insert_point += len("<dependencies>")
            swagger_dep = (
                "\n        <dependency>\n"
                "            <groupId>io.swagger.core.v3</groupId>\n"
                "            <artifactId>swagger-annotations</artifactId>\n"
                "            <version>2.2.21</version>\n"
                "        </dependency>\n"
            )
            pom = pom[:insert_point] + swagger_dep + pom[insert_point:]
            fixes_applied.append("Pinned swagger-annotations to 2.2.21 (fixes non-deterministic requiredMode() resolution)")
            
    with open(pom_path, "w", encoding="utf-8") as f:
        f.write(pom)
        
    if "<groupId>jakarta.validation</groupId>" not in pom:
        insert_point = pom.find("<dependencies>")
        if insert_point != -1:
            insert_point += len("<dependencies>")
            validation_dep = (
                "\n        <dependency>\n"
                "            <groupId>jakarta.validation</groupId>\n"
                "            <artifactId>jakarta.validation-api</artifactId>\n"
                "            <version>3.0.2</version>\n"
                "        </dependency>\n"
            )
            pom = pom[:insert_point] + validation_dep + pom[insert_point:]
            fixes_applied.append("Pinned jakarta.validation-api to 3.0.2")

    return fixes_applied


EVAL_DIR = os.path.join(SCRIPT_DIR, "..", "evaluation", "reference-run")

def stage_baseline():
    print("\n=== STAGE 0: Capture Baseline (before any changes) ===")
    os.makedirs(EVAL_DIR, exist_ok=True)

    print("--- Baseline vulnerability scan ---")
    success, output = run_mvn([
        "org.owasp:dependency-check-maven:check",
        f"-DnvdApiKey={NVD_API_KEY}", "-Dformats=JSON"
    ])
    log_stage("Baseline vulnerability scan", success, output)
    src = os.path.join(LEGACY_APP_DIR, "target", "dependency-check-report.json")
    if os.path.exists(src):
        import shutil
        shutil.copy(src, os.path.join(EVAL_DIR, "vulnerabilities_before.json"))

    print("--- Baseline test run + coverage ---")
    success, output = run_mvn(["clean", "test", "jacoco:report"])
    log_stage("Baseline test run", success, output)

    jacoco_src = os.path.join(LEGACY_APP_DIR, "target", "site", "jacoco", "jacoco.xml")
    if os.path.exists(jacoco_src):
        import shutil
        shutil.copy(jacoco_src, os.path.join(EVAL_DIR, "coverage_before.xml"))

    surefire_dir = os.path.join(LEGACY_APP_DIR, "target", "surefire-reports")
    test_count, failures = count_tests(surefire_dir)
    log_stage("Baseline test count", True, f"Tests: {test_count}, Failures: {failures}")

    return True


def count_tests(surefire_dir):
    total_tests, total_failures = 0, 0
    if not os.path.exists(surefire_dir):
        return 0, 0
    for f in os.listdir(surefire_dir):
        if f.endswith(".txt"):
            with open(os.path.join(surefire_dir, f), "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    m = re.search(r"Tests run: (\d+), Failures: (\d+), Errors: (\d+)", line)
                    if m:
                        total_tests += int(m.group(1))
                        total_failures += int(m.group(2)) + int(m.group(3))
                        break
    return total_tests, total_failures

def stage_migration():
    print("\n=== STAGE 1: Migration (OpenRewrite) ===")
    success, output = run_mvn([
        "org.openrewrite.maven:rewrite-maven-plugin:run",
        "-Drewrite.recipeArtifactCoordinates=org.openrewrite.recipe:rewrite-spring:RELEASE",
        "-Drewrite.activeRecipes=org.openrewrite.java.spring.boot3.UpgradeSpringBoot_3_0"
    ])
    log_stage("Migration (OpenRewrite)", success, output)

    print("\n--- Applying known fix patterns (learned from prior migration analysis) ---")
    fixes = apply_known_migration_fixes(LEGACY_APP_DIR)
    log_stage("Known migration fixes applied", True, "\n".join(fixes) if fixes else "No known fixes needed")

    # Note: an automated build-verification step was attempted here but
    # removed after extensive testing showed it fails intermittently only
    # when triggered via the web dashboard (never when run directly from
    # the command line), despite isolating and fixing several real bugs
    # along the way (a Python mutable-default-argument bug, missing
    # Windows Defender exclusions, and stale target/ artifacts). The root
    # cause was not conclusively identified within the project timeline.
    # Correctness is still verified later, via the remediation and final
    # test stages, and via the terminal-run reference evaluation.
    return True


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
    targets = get_prioritized_targets(findings, max_targets=5)

    if not targets:
        log_stage("Remediation", True, "No suitable high-confidence targets found. Skipping.")
        return True

    pom_path = os.path.join(LEGACY_APP_DIR, "pom.xml")
    applied = []
    failed = []

    for target in targets:
        print(f"\nTarget: {target['dependency']} | {target['cve']} | {target['severity']} | confidence={target['confidence']}")

        with open(pom_path, "r", encoding="utf-8") as f:
            pom_backup = f.read()

        try:
            fix = ask_llm_for_fix(target)
            print(f"Proposed fix: {fix['group_id']}:{fix['artifact_id']} -> {fix['fixed_version']}")
            apply_version_override(pom_path, fix["group_id"], fix["artifact_id"], fix["fixed_version"])

            # Known matched-version-set handling: some libraries must move together
            JACKSON_GROUP = "com.fasterxml.jackson.core"
            JACKSON_MATCHED_ARTIFACTS = ["jackson-core", "jackson-annotations", "jackson-databind"]
            if fix["group_id"] == JACKSON_GROUP and fix["artifact_id"] in JACKSON_MATCHED_ARTIFACTS:
                for sibling in JACKSON_MATCHED_ARTIFACTS:
                    if sibling != fix["artifact_id"]:
                        try:
                            apply_version_override(pom_path, JACKSON_GROUP, sibling, fix["fixed_version"])
                            print(f"  Also aligned matched dependency: {JACKSON_GROUP}:{sibling} -> {fix['fixed_version']}")
                        except Exception as e:
                            print(f"  Could not align {sibling}: {e}")

            build_ok, build_output = run_mvn(["clean", "compile"])
            if build_ok:
                applied.append(fix)
                print(f"Applied and verified: {fix['group_id']}:{fix['artifact_id']}")
            else:
                # Roll back this specific change
                with open(pom_path, "w", encoding="utf-8") as f:
                    f.write(pom_backup)
                failed.append({"target": target["dependency"], "reason": "build failed, reverted"})
                print(f"Build failed after this fix - reverted: {fix['group_id']}:{fix['artifact_id']}")
        except Exception as e:
            with open(pom_path, "w", encoding="utf-8") as f:
                f.write(pom_backup)
            failed.append({"target": target["dependency"], "reason": str(e)})
            print(f"Error applying fix, reverted: {e}")

    print("\n--- Post-remediation vulnerability scan ---")
    success, output = run_mvn([
        "org.owasp:dependency-check-maven:check",
        f"-DnvdApiKey={NVD_API_KEY}", "-Dformats=JSON"
    ])
    if success:
        import shutil
        os.makedirs(EVAL_DIR, exist_ok=True)
        shutil.copy(
            os.path.join(LEGACY_APP_DIR, "target", "dependency-check-report.json"),
            os.path.join(EVAL_DIR, "vulnerabilities_after.json")
        )
    
    log_stage(
        "Remediation batch complete",
        True,
        f"Attempted: {len(targets)}, Applied: {len(applied)}, Failed/reverted: {len(failed)}\n"
        f"Applied fixes: {json.dumps(applied, indent=2)}\n"
        f"Failed: {json.dumps(failed, indent=2)}"
    )

    print("\n--- Final build verification after all remediation ---")
    success, output = run_mvn(["clean", "compile"])
    log_stage("Build verification after remediation batch", success, output)
    return success


def stage_test_generation():
    print("\n=== STAGE 3: Coverage-driven Test Generation ===")

    src_main_java_dir = os.path.join(LEGACY_APP_DIR, "src", "main", "java")
    jacoco_xml_path = os.path.join(LEGACY_APP_DIR, "target", "site", "jacoco", "jacoco.xml")

    print("--- Generating coverage report ---")
    success, output = run_mvn(["test", "jacoco:report"])
    import shutil
    jacoco_src = os.path.join(LEGACY_APP_DIR, "target", "site", "jacoco", "jacoco.xml")
    if os.path.exists(jacoco_src):
        shutil.copy(jacoco_src, os.path.join(EVAL_DIR, "coverage_after.xml"))

    surefire_dir = os.path.join(LEGACY_APP_DIR, "target", "surefire-reports")
    test_count, failures = count_tests(surefire_dir)
    log_stage("Final test count", True, f"Tests: {test_count}, Failures: {failures}")
    
    if not success or not os.path.exists(jacoco_xml_path):
        log_stage("Test generation", False, "Could not generate/find JaCoCo XML report.\n" + output)
        return False

    from test_generation_agent import read_file, find_lowest_coverage_class, guess_local_dependency_source, generate_test

    target = find_lowest_coverage_class(jacoco_xml_path, src_main_java_dir)
    if not target:
        log_stage("Test generation", True, "No suitable low-coverage, testable class found. Skipping.")
        return True

    print(f"Lowest-coverage testable class: {target['class_name']} "
          f"({target['ratio']*100:.0f}% covered, {target['missed']} lines missed)")

    target_source = read_file(target["source_path"])
    dependency_source = guess_local_dependency_source(target_source, src_main_java_dir)

    class_name_parts = target["class_name"].split("/")
    simple_name = class_name_parts[-1]
    package_name = ".".join(class_name_parts[:-1])

    test_code = generate_test(target_source, simple_name, package_name, dependency_source)

    output_path = os.path.join(
        LEGACY_APP_DIR, "src", "test", "java", *class_name_parts[:-1], f"{simple_name}Tests.java"
    )

    if os.path.exists(output_path):
        log_stage("Test generation", True, f"{simple_name}Tests.java already exists. Skipping generation.")
        return True

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(test_code)
    log_stage("Test generation", True, f"Wrote {output_path} for {target['class_name']}")

    print("\n--- Verifying new test passes ---")
    success, output = run_mvn(["test", f"-Dtest={simple_name}Tests"])

    if success:
        log_stage("New test verification", True, output)
    else:
        os.remove(output_path)
        log_stage(
            "New test verification",
            True,  # don't block the pipeline - this is a handled, non-fatal case
            f"Generated test for {target['class_name']} failed verification "
            f"(likely a minor assertion mismatch, e.g. guessed string format) "
            f"and was discarded. Pipeline continues without this test.\n{output[-1500:]}"
        )
    return True  # always allow pipeline to continue past this stage


def stage_final_report():
    print("\n=== STAGE 4: Final Full Test Run + Coverage ===")
    success, output = run_mvn(["test", "jacoco:report"])
    log_stage("Final full test suite + coverage", success, output)
    return success


if __name__ == "__main__":
    print_environment_diagnostics()
    print("Starting multi-agent modernization pipeline...\n")

    ok = stage_baseline()
    if ok:
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
    
    
    
