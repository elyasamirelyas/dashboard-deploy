# run_batch.py - clones each of the apps below (if not already cloned)
# and runs the full orchestrator.py pipeline against it, one app at a
# time. Writes a per-app pipeline_report_<name>.json snapshot plus a
# plain-text batch_summary.txt so all the results can be checked at a
# glance without opening every JSON file by hand.

import subprocess, os, shutil, json

BASE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(BASE)
TARGET_APPS_DIR = os.path.join(PARENT, "target-apps")
REPORTS_DIR = os.path.join(BASE, "reports")
os.makedirs(TARGET_APPS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

# the apps this batch run covers, as (folder name, git url) pairs
REPOS = [
    ("app7-h2crud", "https://github.com/bezkoder/spring-boot-h2-database-crud"),
    ("app8-restdemo", "https://github.com/snehal0087/SpringBootRestDemo"),
    ("app9-crudh2", "https://github.com/santhoshvernekar/sample-spring-boot-crud-example-with-h2"),
    ("app10-example", "https://github.com/cip-p/spring-boot-example"),
    ("app11-atomize", "https://github.com/atomize/springboot-h2-rest_api-example"),
    ("app12-rafsan", "https://github.com/rafsan-jany/spring-boot-rest-api-h2-database"),
    ("app13-vicky", "https://github.com/iamvickyav/spring-boot-data-H2-embedded"),
]

summary_lines = []
report_path = os.path.join(REPORTS_DIR, "pipeline_report.json")

for name, url in REPOS:
    target_dir = os.path.join(TARGET_APPS_DIR, name)
    summary_lines.append(f"=== {name} ({url}) ===")

    # only clone if we don't already have it - lets a batch run be
    # re-run without re-downloading every app from scratch each time
    if not os.path.exists(target_dir):
        clone = subprocess.run(["git", "clone", url, target_dir], capture_output=True, text=True)
        if clone.returncode != 0:
            summary_lines.append("CLONE FAILED: " + clone.stderr[-500:])
            summary_lines.append("")
            continue

    # clear out any report left over from the previous app before this
    # run, so we can tell a fresh report apart from a stale leftover one
    if os.path.exists(report_path):
        os.remove(report_path)

    run = subprocess.run(f'python orchestrator.py "{os.path.join("..", "target-apps", name)}"', shell=True, cwd=BASE, capture_output=True, text=True)

    if os.path.exists(report_path):
        # keep this app's report around under its own name, since the
        # next loop iteration is about to overwrite pipeline_report.json
        shutil.copy(report_path, os.path.join(REPORTS_DIR, f"pipeline_report_{name}.json"))
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)
        failed = [s["stage"] for s in report["stages"] if not s["success"]]
        # a failed baseline stage is expected - that's the "before" state,
        # from before any fixes were applied - so it doesn't count as a
        # real pipeline failure on its own
        real_failures = [s for s in failed if s not in ("Baseline test run", "Baseline vulnerability scan", "Baseline test count")]
        if not failed:
            summary_lines.append("PASSED - ALL STAGES CLEAN")
        elif not real_failures:
            summary_lines.append("PASSED - pipeline fixed all pre-existing baseline issues (baseline itself failed as expected before fixes)")
        else:
            summary_lines.append("FAILED STAGES: " + ", ".join(real_failures))
    else:
        # orchestrator.py never even got as far as writing a report -
        # something crashed early, so dump its raw output for debugging
        summary_lines.append("CRASHED BEFORE WRITING ANY REPORT - stdout/stderr below")
        summary_lines.append("STDOUT: " + run.stdout[-1500:])
        summary_lines.append("STDERR: " + run.stderr[-1500:])
    summary_lines.append("")

with open(os.path.join(BASE, "batch_summary.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(summary_lines))

print("\n".join(summary_lines))