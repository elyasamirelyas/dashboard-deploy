import os
import subprocess
import json
import sys
from dotenv import load_dotenv

load_dotenv()

LEGACY_APP_DIR = os.path.abspath("../legacy-app")
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

def stage_migration():
    print("\n=== STAGE 1: Migration (OpenRewrite) ===")
    success, output = run_mvn([
        "-U", "org.openrewrite.maven:rewrite-maven-plugin:run",
        "-Drewrite.recipeArtifactCoordinates=org.openrewrite.recipe:rewrite-spring:RELEASE",
        "-Drewrite.activeRecipes=org.openrewrite.java.spring.boot3.UpgradeSpringBoot_3_0"
    ])
    log_stage("Migration (OpenRewrite)", success, output)

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

    findings = load_vulnerabilities()
    top = pick_top_priority(findings)
    if not top:
        log_stage("Remediation", True, "No suitable high-confidence target found. Skipping.")
        return True

    print(f"Top priority target: {top['dependency']} | {top['cve']} | {top['severity']}")
    fix = ask_llm_for_fix(top)
    print(f"Proposed fix: {fix['group_id']}:{fix['artifact_id']} -> {fix['fixed_version']}")

    apply_version_override(POM_PATH, fix["group_id"], fix["artifact_id"], fix["fixed_version"])
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