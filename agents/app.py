# app.py - web backend for the Modernization Control Panel dashboard
#
# This is the server-side component that powers the dashboard UI. It's intentionally
# lightweight - no database, no ORM, just a Flask app that reads files from the
# filesystem and serves them up to the frontend. The pipeline runs (orchestrator.py)
# write their output to evaluation/<app_id>/ and this reads those results.
#
# The dashboard shows:
#   - Which apps have successfully completed a pipeline run
#   - The detailed stage-by-stage log for each app
#   - Before/after metrics: CVEs, test counts, and coverage percentages
#
# Routes:
#   /              - the dashboard HTML page
#   /apps          - JSON list of available apps (clean runs vs incomplete)
#   /status/<id>   - JSON pipeline stage log for a specific app
#   /report/<id>   - JSON before/after metrics for a specific app

import os
import re
import sys
import glob
import json
from flask import Flask, jsonify, render_template

app = Flask(__name__)

# ------------------------------------------------------------------
# Path configuration - everything is relative to where this file lives
# ------------------------------------------------------------------

# Get the directory containing this script - we use this as our base
# for constructing all other paths

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# The parent directory contains the evaluation/ folder where pipeline
# results are stored, plus other project components
PARENT_DIR = os.path.join(SCRIPT_DIR, "..")

# Each app gets its own subfolder under evaluation/ with all its results
EVAL_ROOT = os.path.join(PARENT_DIR, "evaluation")   # evaluation/<app_id>/...


# The original showcase report from App5 - kept as a fallback for the
# reference app in case the evaluation/ copy isn't available
SHOWCASE_PATH = os.path.join(SCRIPT_DIR, "reports", "showcase_report.json")  # original App5 snapshot

# We need functions from the evaluation report generator to parse
# vulnerability counts, coverage data, and test statistics
sys.path.insert(0, SCRIPT_DIR)
from generate_evaluation_report import count_vulnerabilities, get_jacoco_totals, parse_test_count

# -----------------------------------------------------------
# App display names - make the dropdown more user-friendly
# -----------------------------------------------------------

# Each app has an internal ID (like "app7-h2crud") that's used everywhere
# in the code, but we display friendlier names in the UI. If an app isn't
# in this dictionary, we just title-case its ID and use that instead.
APP_LABELS = {
    "reference-run": "App5 — crud-h2 (reference)",
    "app7-h2crud": "App7 — h2crud",
    "app9-crudh2": "App9 — crudh2",
    "app10-example": "App10 — example",
    "app12-rafsan": "App12 — rafsan",
    "app13-vicky": "App13 — vicky",
    "app11-atomize": "App11 — atomize",
    "app8-restdemo": "App8 — restdemo",
    "app4-vulnerable": "App4 — vulnerable",
    "app3-sample-rest": "App3 — sample-rest",
    "app2-petclinic-old": "App2 — petclinic-old",
}

# ------------------------------------------------------------------
# Pipeline completion criteria
# ------------------------------------------------------------------

# To consider a pipeline run "complete" and successful, the last stage
# logged must contain both of these strings. This ensures we only show
# runs that actually made it through the entire pipeline, not ones that
# crashed or were interrupted midway.
#
# Currently the final stage is named "Final full test suite + coverage"
# so this matches both "final" and "coverage". If the stage name ever
# changes, we'll need to update these hints.
TERMINAL_STAGE_HINTS = ("final", "coverage")

# OpenRewrite sometimes outputs a line like "Estimated time saved: 7h 49m"
# during the migration phase. We extract this to display in the dashboard
# as an interesting metric, but it's optional - not every run has it.
TIME_SAVED_RE = re.compile(r"stimate[d]?\s+time\s+saved:\s*((?:\d+h\s*)?\d+m)", re.IGNORECASE)


# ------------------------------------------------------------------
# Helper functions - these do the actual file reading and data parsing
# ------------------------------------------------------------------

def _extract_time_saved(stages):
     # OpenRewrite sometimes logs how much time it estimates it saved.
    # We look for that in the migration stage details. Not every run has
    # this, so we just return None if we can't find it rather than guessing.
    for s in stages or []:
        m = TIME_SAVED_RE.search(s.get("details") or "")
        if m:
            return m.group(1).strip()
    return None


def _stages_report_path(app_id):
    # Figure out which pipeline_report.json to use for this app.
    # We prefer the per-run copy under evaluation/, then fall back to the
    # snapshot in agents/reports/. For the reference app only, we also
    # check the original showcase file. Returns None if nothing exists yet.
    candidates = [
        os.path.join(EVAL_ROOT, app_id, "pipeline_report.json"),
        os.path.join(SCRIPT_DIR, "reports", f"pipeline_report_{app_id}.json"),
    ]
    if app_id == "reference-run":
        candidates.append(SHOWCASE_PATH)
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def _load_stages(app_id):
    # Reads the pipeline stages for one app. Returns None if there's no
    # report yet (normal - just means this app hasn't been run), or if the
    # file is broken or half-written. We don't want a bad file to crash
    # the dashboard, so we treat any read error as "no data".
    path = _stages_report_path(app_id)
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("stages", [])
    except (OSError, json.JSONDecodeError) as e:
        print(f"[app.py] Could not read {path}: {e}")
        return None


def _is_clean(stages):
    # A run is clean only if every stage succeeded AND the pipeline made
    # it all the way to the end. If any stage failed or the run stopped
    # early, we don't consider it complete enough to show in the dashboard.
    if not stages:
        return False
    if not all(s.get("success") for s in stages):
        return False
    last = stages[-1].get("stage", "").lower()
    return all(hint in last for hint in TERMINAL_STAGE_HINTS)


def _discover_app_ids():
    # Find every app that we have data for by looking at folder names
    # under evaluation/ and any pipeline_report_<app>.json snapshots in
    # agents/reports/. Returns a sorted list of app ID strings.
    ids = set()
    if os.path.isdir(EVAL_ROOT):
        for name in os.listdir(EVAL_ROOT):
            if os.path.isdir(os.path.join(EVAL_ROOT, name)):
                ids.add(name)
    for path in glob.glob(os.path.join(SCRIPT_DIR, "reports", "pipeline_report_app*.json")):
        m = re.search(r"pipeline_report_(app[\w-]+)\.json$", os.path.basename(path))
        if m:
            ids.add(m.group(1))
    return sorted(ids)


def _label_for(app_id):
    # Convert an app ID like "app7-h2crud" into something nicer for the
    # dropdown. Use the mapping from APP_LABELS if available, otherwise
    # clean up the ID and title-case it.
    return APP_LABELS.get(app_id, app_id.replace("-", " ").replace("_", " ").title())


def _get_stage_detail_from(stages, stage_name):
    # Find a stage by its exact name and return its detail text.
    # Returns None if that stage wasn't reached in this run.
    for s in stages or []:
        if s.get("stage") == stage_name:
            return s.get("details")
    return None


def _get_stage_detail_from(stages, stage_name):
    # Find a stage by its exact name and return its detail text.
    # Returns None if that stage wasn't reached in this run.
    for s in stages or []:
        if s.get("stage") == stage_name:
            return s.get("details")
    return None


def _validate_app_id(app_id):
    """Reject any app_id not in the known set, closing off path traversal
    via crafted URLs like /status/../../../../etc."""
    if app_id != "reference-run" and app_id not in _discover_app_ids():
        return False
    return True


# ------------------------------------------------------------------
# Flask routes - the actual web endpoints
# ------------------------------------------------------------------

@app.route("/")
def index():
    # just serves the dashboard page itself
    return render_template("index.html")


@app.route("/apps")
def apps():
    # Build the list of apps for the dropdown. Apps only count as
    # "included" if their most recent run was a full, clean pass.
    # Anything else (no data, failed run, incomplete run) goes into
    # "excluded" so the UI doesn't show broken results.
    included, excluded = [], []
    for app_id in _discover_app_ids():
        stages = _load_stages(app_id)
        if stages is None:
            excluded.append({"id": app_id, "reason": "no pipeline report found"})
            continue
        if _is_clean(stages):
            included.append({"id": app_id, "label": _label_for(app_id)})
        else:
            excluded.append({"id": app_id, "reason": "last recorded run is not a clean pass"})
    # Put the reference app first (it's the showcase), then sort the rest alphabetically
    included.sort(key=lambda a: (a["id"] != "reference-run", a["id"]))
    return jsonify({"apps": included, "excluded": excluded})


@app.route("/status/<app_id>")
def status(app_id):
   # Return the stage-by-stage log for one app. The UI uses this to
    # animate the pipeline schematic. If no report exists, return a 404
    # with empty stages so the UI can show a friendly "no data" state.
    if not _validate_app_id(app_id):
        return jsonify({"status": "unavailable", "stages": []}), 404
    stages = _load_stages(app_id)
    if stages is None:
        return jsonify({"status": "unavailable", "stages": []}), 404
    return jsonify({"status": "done", "stages": stages})


@app.route("/report/<app_id>")
def report(app_id):
    # Return the before/after headline numbers for one app: CVE counts,
    # test counts, and coverage. This pulls from several separate files,
    # so if one of them is missing or broken we still return whatever
    # we have rather than crashing the whole response.
    if not _validate_app_id(app_id):
        return jsonify({"available": False, "error": "unknown app_id"}), 404
    eval_dir = os.path.join(EVAL_ROOT, app_id)
    try:
        stages = _load_stages(app_id) or []

        vulns_before = count_vulnerabilities(os.path.join(eval_dir, "vulnerabilities_before.json"))
        vulns_after = count_vulnerabilities(os.path.join(eval_dir, "vulnerabilities_after.json"))
        cov_before = get_jacoco_totals(os.path.join(eval_dir, "coverage_before.xml"))
        cov_after = get_jacoco_totals(os.path.join(eval_dir, "coverage_after.xml"))

        tests_before, fail_before = parse_test_count(_get_stage_detail_from(stages, "Baseline test count"))
        tests_after, fail_after = parse_test_count(_get_stage_detail_from(stages, "Final test count"))
        time_saved = _extract_time_saved(stages)

        return jsonify({
            "available": True,
            "vulns_before": vulns_before, "vulns_after": vulns_after,
            "tests_before": tests_before, "fail_before": fail_before,
            "tests_after": tests_after, "fail_after": fail_after,
            "time_saved": time_saved,
            "coverage_before": cov_before.get("LINE") if cov_before else None,
            "coverage_after": cov_after.get("LINE") if cov_after else None,
        })
    except (OSError, json.JSONDecodeError) as e:
       # A data file for this app exists but couldn't be read - maybe it
        # was only half-written, or got corrupted somehow. Tell the UI
        # clearly what happened instead of letting it hit a raw Flask error page.
        print(f"[app.py] /report/{app_id} failed: {e}")
        return jsonify({"available": False, "error": str(e)}), 500


# Old routes with no app ID in the URL - kept around so nothing that
# links to them breaks. They just point at the reference app (App5).
@app.route("/status")
def status_default():
    return status("reference-run")


@app.route("/report")
def report_default():
    return report("reference-run")


if __name__ == "__main__":
    app.run(debug=False, port=5001, use_reloader=False)