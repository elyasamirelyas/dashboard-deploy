# patch_final_test_counts.py - one-off helper: re-runs the final test suite
# for each already-completed app and patches the "Final full test suite +
# coverage" stage's details in its existing pipeline_report.json with the
# correct post-test-generation count. Does NOT redo migration, remediation,
# or test generation - those already happened and their results are already
# on disk; this only reruns `mvn test jacoco:report` once, same as stage 4
# already does, and fixes the logged count to match.

import os
import re
import json
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(SCRIPT_DIR, "..")
MVN_CMD = os.getenv("MVN_CMD", r"C:\Users\amiri\apache-maven-3.9.16-bin\apache-maven-3.9.16\bin\mvn.cmd")
JAVA17_HOME = r"C:\Program Files\Eclipse Adoptium\jdk-17.0.17.10-hotspot"

# app_id -> (app directory, pipeline_report.json path)
APPS = {
    "reference-run": (
        os.path.join(ROOT, "legacy-app"),
        os.path.join(ROOT, "evaluation", "reference-run", "pipeline_report.json"),
    ),
    "app7-h2crud": (
        os.path.join(ROOT, "target-apps", "app7-h2crud"),
        os.path.join(SCRIPT_DIR, "reports", "pipeline_report_app7-h2crud.json"),
    ),
    "app8-restdemo": (
        os.path.join(ROOT, "target-apps", "app8-restdemo"),
        os.path.join(SCRIPT_DIR, "reports", "pipeline_report_app8-restdemo.json"),
    ),
    "app9-crudh2": (
        os.path.join(ROOT, "target-apps", "app9-crudh2"),
        os.path.join(SCRIPT_DIR, "reports", "pipeline_report_app9-crudh2.json"),
    ),
    "app10-example": (
        os.path.join(ROOT, "target-apps", "app10-example"),
        os.path.join(SCRIPT_DIR, "reports", "pipeline_report_app10-example.json"),
    ),
    "app12-rafsan": (
        os.path.join(ROOT, "target-apps", "app12-rafsan"),
        os.path.join(SCRIPT_DIR, "reports", "pipeline_report_app12-rafsan.json"),
    ),
    "app13-vicky": (
        os.path.join(ROOT, "target-apps", "app13-vicky"),
        os.path.join(SCRIPT_DIR, "reports", "pipeline_report_app13-vicky.json"),
    ),
}


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


def run_mvn(app_dir):
    env = os.environ.copy()
    env["JAVA_HOME"] = JAVA17_HOME
    env["PATH"] = os.path.join(JAVA17_HOME, "bin") + os.pathsep + env.get("PATH", "")
    result = subprocess.run(
    [MVN_CMD, "clean", "test", "jacoco:report"], cwd=app_dir, capture_output=True,
    text=True, encoding="utf-8", errors="replace", env=env, shell=False,
    )
    return result.returncode == 0


def patch_report(report_path, test_count, failures):
    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)
    patched = False
    for stage in report["stages"]:
        if stage["stage"] == "Final full test suite + coverage":
            tail = stage["details"].split("\n", 1)
            rest = tail[1] if len(tail) > 1 else ""
            stage["details"] = f"Tests: {test_count}, Failures: {failures}\n{rest}".rstrip()
            patched = True
    if not patched:
        print(f"  WARNING: no 'Final full test suite + coverage' stage in {report_path}")
        return
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


if __name__ == "__main__":
    for app_id, (app_dir, report_path) in APPS.items():
        print(f"=== {app_id} ===")
        if not os.path.exists(app_dir):
            print(f"  SKIP: {app_dir} not found")
            continue
        if not os.path.exists(report_path):
            print(f"  SKIP: {report_path} not found")
            continue
        ok = run_mvn(app_dir)
        surefire_dir = os.path.join(app_dir, "target", "surefire-reports")
        test_count, failures = count_tests(surefire_dir)
        print(f"  mvn test: {'OK' if ok else 'FAILED'} | Tests: {test_count}, Failures: {failures}")
        patch_report(report_path, test_count, failures)
        print(f"  Patched {report_path}")
    print("\nDone. Now run: python generate_evaluation_report.py")