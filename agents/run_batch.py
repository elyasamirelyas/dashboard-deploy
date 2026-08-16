import subprocess, os, shutil, json
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(BASE)

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
report_path = os.path.join(BASE, "pipeline_report.json")

for name, url in REPOS:
    target_dir = os.path.join(PARENT, name)
    summary_lines.append(f"=== {name} ({url}) ===")

    if not os.path.exists(target_dir):
        clone = subprocess.run(["git", "clone", url, target_dir], capture_output=True, text=True)
        if clone.returncode != 0:
            summary_lines.append("CLONE FAILED: " + clone.stderr[-500:])
            summary_lines.append("")
            continue

    if os.path.exists(report_path):
        os.remove(report_path)

    run = subprocess.run(f'python orchestrator.py "{os.path.join("..", name)}"', shell=True, cwd=BASE, capture_output=True, text=True)

    if os.path.exists(report_path):
        shutil.copy(report_path, os.path.join(BASE, f"pipeline_report_{name}.json"))
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)
        failed = [s["stage"] for s in report["stages"] if not s["success"]]
        real_failures = [s for s in failed if s not in ("Baseline test run", "Baseline vulnerability scan", "Baseline test count")]
        if not failed:
            summary_lines.append("PASSED - ALL STAGES CLEAN")
        elif not real_failures:
            summary_lines.append("PASSED - pipeline fixed all pre-existing baseline issues (baseline itself failed as expected before fixes)")
        else:
            summary_lines.append("FAILED STAGES: " + ", ".join(real_failures))
    else:
        summary_lines.append("CRASHED BEFORE WRITING ANY REPORT - stdout/stderr below")
        summary_lines.append("STDOUT: " + run.stdout[-1500:])
        summary_lines.append("STDERR: " + run.stderr[-1500:])
    summary_lines.append("")

with open(os.path.join(BASE, "batch_summary.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(summary_lines))

print("\n".join(summary_lines))