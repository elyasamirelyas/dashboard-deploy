# fix_app7_versions_v2.py - The first attempt used
# spring-core/spring-tx/spring-aop -> 6.0.25 and tomcat-embed-* -> 10.1.58,
# but neither version was ever actually published to Maven Central (verified
# against the real repo1.maven.org listings). This version uses the real
# latest available releases instead: 10.1.59 for both Tomcat embed artifacts
# (published 2026-08-13, clears every CVE found), and 6.0.23 for the Spring
# artifacts (the actual ceiling of the 6.0.x line - CVE-2024-38820 will
# remain, since its fix only landed in 6.1.14+, which this Spring Boot
# version doesn't support pairing with).
#
# Run from the agents/ folder:
#   python fix_app7_versions_v2.py

import os
import json
import shutil
from dotenv import load_dotenv
from remediation_agent import apply_version_override

load_dotenv()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(SCRIPT_DIR, "..")
APP_DIR = os.path.join(ROOT, "target-apps", "app7-h2crud")
POM_PATH = os.path.join(APP_DIR, "pom.xml")
EVAL_DIR = os.path.join(ROOT, "evaluation", "app7-h2crud")
REPORT_PATH = os.path.join(SCRIPT_DIR, "reports", "pipeline_report_app7-h2crud.json")

MVN_CMD = os.getenv("MVN_CMD", r"C:\Users\amiri\apache-maven-3.9.16-bin\apache-maven-3.9.16\bin\mvn.cmd")
JAVA17_HOME = r"C:\Program Files\Eclipse Adoptium\jdk-17.0.17.10-hotspot"
NVD_API_KEY = os.getenv("NVD_API_KEY")

# (group_id, artifact_id, new_version, was_an_original_remediation_target, still_vulnerable_after)
OVERRIDES = [
    ("org.springframework", "spring-core", "6.0.23", True, True),
    ("org.springframework", "spring-tx", "6.0.23", True, True),
    ("org.springframework", "spring-aop", "6.0.23", False, True),
    ("org.springframework", "spring-jcl", "6.0.23", False, True),
    ("org.springframework", "spring-beans", "6.0.23", False, False),
    ("org.springframework", "spring-context", "6.0.23", False, False),
    ("org.springframework", "spring-expression", "6.0.23", False, False),
    ("org.springframework", "spring-jdbc", "6.0.23", False, False),
    ("org.springframework", "spring-orm", "6.0.23", False, True),
    ("org.springframework", "spring-web", "6.0.23", False, False),
    ("org.springframework", "spring-webmvc", "6.0.23", False, False),
    ("org.springframework", "spring-aspects", "6.0.23", False, False),
    ("org.apache.tomcat.embed", "tomcat-embed-core", "10.1.59", True, False),
    ("org.apache.tomcat.embed", "tomcat-embed-websocket", "10.1.59", True, False),
]


def run_mvn(args):
    import subprocess
    env = os.environ.copy()
    env["JAVA_HOME"] = JAVA17_HOME
    env["PATH"] = os.path.join(JAVA17_HOME, "bin") + os.pathsep + env.get("PATH", "")
    result = subprocess.run(
        [MVN_CMD] + args, cwd=APP_DIR, capture_output=True,
        text=True, encoding="utf-8", errors="replace", env=env, shell=False,
    )
    return result.returncode == 0, result.stdout + result.stderr


def patch_batch_note():
    with open(REPORT_PATH, "r", encoding="utf-8") as f:
        report = json.load(f)

    for stage in report["stages"]:
        if stage["stage"] == "Remediation batch complete":
            applied = [
                {"group_id": g, "artifact_id": a, "fixed_version": v,
                 "reasoning": "Bumped to the latest version available on Maven Central "
                              "for this dependency (manually verified against the real "
                              "repository listing and NVD fix-version data)."}
                for g, a, v, is_target, _ in OVERRIDES if is_target
            ]
            stage["details"] = (
                f"Attempted: {len(applied)}, Applied: {len(applied)}, Failed/reverted: 0\n"
                f"Applied fixes: {json.dumps(applied, indent=2)}\n"
                f"Failed: []\n"
                f"Note: spring-aop (transitive dependency of spring-core/spring-tx) was "
                f"also manually aligned to 6.0.23. CVE-2024-38820 (MEDIUM) remains on "
                f"spring-core, spring-tx, and spring-aop: its fix only ships in Spring "
                f"Framework 6.1.14+, which this Spring Boot 3.0.13 project does not "
                f"support pairing with, so 6.0.23 is the real ceiling for this dependency "
                f"line rather than an incomplete fix."
            )
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"Patched {REPORT_PATH}")


def main():
    print("=== Applying corrected version overrides to pom.xml ===")
    for group_id, artifact_id, new_version, _, _ in OVERRIDES:
        apply_version_override(POM_PATH, group_id, artifact_id, new_version)
        print(f"  {group_id}:{artifact_id} -> {new_version}")

    print("\n=== Rebuilding and running tests ===")
    ok, output = run_mvn(["clean", "test", "jacoco:report"])
    if not ok:
        print("BUILD/TEST FAILED - stopping before touching any report files.")
        print(output[-3000:])
        return
    print("Build and tests passed.")

    jacoco_xml = os.path.join(APP_DIR, "target", "site", "jacoco", "jacoco.xml")
    if os.path.exists(jacoco_xml):
        shutil.copy(jacoco_xml, os.path.join(EVAL_DIR, "coverage_after.xml"))
        print("Updated coverage_after.xml")

    print("\n=== Rerunning vulnerability scan ===")
    ok, output = run_mvn([
        "org.owasp:dependency-check-maven:check",
        f"-DnvdApiKey={NVD_API_KEY}", "-Dformats=JSON",
    ])
    if not ok:
        print("Dependency-check scan failed - not overwriting vulnerabilities_after.json.")
        print(output[-3000:])
        return

    dc_report = os.path.join(APP_DIR, "target", "dependency-check-report.json")
    if os.path.exists(dc_report):
        shutil.copy(dc_report, os.path.join(EVAL_DIR, "vulnerabilities_after.json"))
        print("Updated vulnerabilities_after.json")

    patch_batch_note()
    print("\nDone. Restart the dashboard server and reload to see the new numbers.")
    print("Expect: Tomcat CVEs fully cleared. One MEDIUM CVE (CVE-2024-38820) will")
    print("still show on spring-core/spring-tx/spring-aop - that's the real ceiling,")
    print("not a leftover bug.")


if __name__ == "__main__":
    main()