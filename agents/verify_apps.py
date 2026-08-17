# verify_apps.py - reads each app's pipeline_report.json (checking both the
# evaluation/<app_id>/ location and the agents/reports/pipeline_report_<id>.json
# fallback, same two spots app.py's dashboard checks) and reports whether that
# app is dissertation-evidence-clean: every stage EXCEPT a baseline stage must
# have succeeded. Baseline failures are expected (the pre-fix "before" state)
# and don't disqualify an app - anything else that failed does.
#
# Run from the agents/ folder:
#   python verify_apps.py

import os
import re
import json
import glob

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EVAL_ROOT = os.path.join(SCRIPT_DIR, "..", "evaluation")
REPORTS_DIR = os.path.join(SCRIPT_DIR, "reports")
SHOWCASE_PATH = os.path.join(SCRIPT_DIR, "reports", "showcase_report.json")

# Stage names allowed to fail without disqualifying the run.
BASELINE_STAGE_HINTS = ("baseline",)


def is_baseline_stage(stage_name):
    name = (stage_name or "").lower()
    return any(hint in name for hint in BASELINE_STAGE_HINTS)


def discover_app_ids():
    ids = set()
    if os.path.isdir(EVAL_ROOT):
        for name in os.listdir(EVAL_ROOT):
            if os.path.isdir(os.path.join(EVAL_ROOT, name)):
                ids.add(name)
    for path in glob.glob(os.path.join(REPORTS_DIR, "pipeline_report_app*.json")):
        m = re.search(r"pipeline_report_(app[\w-]+)\.json$", os.path.basename(path))
        if m:
            ids.add(m.group(1))
    return sorted(ids)


def report_path_for(app_id):
    candidates = [
        os.path.join(EVAL_ROOT, app_id, "pipeline_report.json"),
        os.path.join(REPORTS_DIR, f"pipeline_report_{app_id}.json"),
    ]
    if app_id == "reference-run":
        candidates.append(SHOWCASE_PATH)
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def check_app(report_path):
    with open(report_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    stages = data.get("stages", [])

    if not stages:
        return "NO STAGES", []

    bad_stages = []
    for s in stages:
        name = s.get("stage", "")
        if not s.get("success") and not is_baseline_stage(name):
            bad_stages.append(name)

    if bad_stages:
        return "FAIL", bad_stages

    last_stage = stages[-1].get("stage", "").lower()
    if "final" not in last_stage or "coverage" not in last_stage:
        return "INCOMPLETE", [f"last stage was '{stages[-1].get('stage')}', not the final stage"]

    return "CLEAN", []


def main():
    app_ids = discover_app_ids()
    if not app_ids:
        print("No apps found under evaluation/ or agents/reports/")
        return

    results = []
    for app_id in app_ids:
        report_path = report_path_for(app_id)
        if not report_path:
            results.append((app_id, "NO REPORT", []))
            continue
        try:
            status, details = check_app(report_path)
        except (OSError, json.JSONDecodeError) as e:
            status, details = "UNREADABLE", [str(e)]
        results.append((app_id, status, details))

    print(f"{'APP':<25} STATUS")
    print("-" * 50)
    for app_id, status, details in results:
        print(f"{app_id:<25} {status}")
        for d in details:
            print(f"    -> {d}")

    clean = [r for r in results if r[1] == "CLEAN"]
    print()
    print(f"{len(clean)}/{len(results)} apps are dissertation-evidence-clean.")


if __name__ == "__main__":
    main()