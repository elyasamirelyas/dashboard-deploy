"""
app.py - the web backend for the Modernization Control Panel dashboard.

This is a small Flask app with no database of its own: it just reads the
JSON/XML result files that orchestrator.py already writes when the pipeline
runs (per-app folders under evaluation/), and serves them to the browser UI
in templates/index.html.

Routes:
  /              - the dashboard page itself
  /apps          - which target apps have a clean, complete pipeline run
  /status/<id>   - the stage-by-stage pipeline log for one app
  /report/<id>   - the before/after numbers (CVEs, tests, coverage) for one app
"""
import os
import re
import sys
import glob
import json
from flask import Flask, jsonify, render_template

app = Flask(__name__)

# Where things live on disk, relative to this file.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.join(SCRIPT_DIR, "..")
EVAL_ROOT = os.path.join(PARENT_DIR, "evaluation")          # evaluation/<app_id>/...
SHOWCASE_PATH = os.path.join(SCRIPT_DIR, "reports", "showcase_report.json")  # original App5 snapshot

sys.path.insert(0, SCRIPT_DIR)
from generate_evaluation_report import count_vulnerabilities, get_jacoco_totals, parse_test_count

# Human-readable labels for known app slugs. Anything not listed here just
# gets titleized from its folder/file name, so new apps show up automatically.
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

# A pipeline run only counts as "finished properly" if its last stage name
# contains both these words (e.g. "Final full test suite + coverage").
TERMINAL_STAGE_HINTS = ("final", "coverage")

# Matches OpenRewrite's own "Estimated time saved: 7h 49m" line, if it logged one.
TIME_SAVED_RE = re.compile(r"stimate[d]?\s+time\s+saved:\s*((?:\d+h\s*)?\d+m)", re.IGNORECASE)


def _extract_time_saved(stages):
    """Pull OpenRewrite's own 'estimated time saved' figure out of the
    migration stage log, if it reported one. Not every run logs it, so
    this returns None rather than guessing."""
    for s in stages or []:
        m = TIME_SAVED_RE.search(s.get("details") or "")
        if m:
            return m.group(1).strip()
    return None


def _stages_report_path(app_id):
    """Work out which pipeline_report.json to use for this app.

    Prefer evaluation/<app_id>/pipeline_report.json (the stable, per-run
    copy); fall back to the per-app snapshot in agents/, then (for the
    reference app only) the original showcase file. Returns None if none
    of those exist yet.
    """
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
    """Read the pipeline's stage list for one app.

    Returns None if there's no report file yet (a normal, expected case -
    just means this app hasn't been run), or if the file exists but is
    empty/corrupted (not expected, but shouldn't take the whole dashboard
    down - we just treat it the same as "no data available").
    """
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
    """True only if every stage succeeded AND the run actually reached the
    end of the pipeline (not just stopped partway through)."""
    if not stages:
        return False
    if not all(s.get("success") for s in stages):
        return False
    last = stages[-1].get("stage", "").lower()
    return all(hint in last for hint in TERMINAL_STAGE_HINTS)


def _discover_app_ids():
    """Find every app we have any data for, by looking at folder names
    under evaluation/ and any pipeline_report_<app>.json snapshots in
    agents/. Returns a sorted list of app ids (folder-name-style slugs)."""
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
    """Turn an app id into a friendly display name for the dropdown."""
    return APP_LABELS.get(app_id, app_id.replace("-", " ").replace("_", " ").title())


def _get_stage_detail_from(stages, stage_name):
    """Find one stage by exact name in a stage list and return its logged
    detail text, or None if that stage isn't present."""
    for s in stages or []:
        if s.get("stage") == stage_name:
            return s.get("details")
    return None


@app.route("/")
def index():
    """Serve the dashboard page itself."""
    return render_template("index.html")


@app.route("/apps")
def apps():
    """List every app the dropdown should offer.

    An app only shows up in "included" if its most recent recorded run
    was a full, clean pass. Anything else (no data yet, or a run that
    failed partway through) goes into "excluded" instead - the UI never
    shows a failed run as if it were a result.
    """
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
    # Reference app first, then alphabetical.
    included.sort(key=lambda a: (a["id"] != "reference-run", a["id"]))
    return jsonify({"apps": included, "excluded": excluded})


@app.route("/status/<app_id>")
def status(app_id):
    """Return the stage-by-stage log for one app, used to animate the
    pipeline schematic in the UI."""
    stages = _load_stages(app_id)
    if stages is None:
        return jsonify({"status": "unavailable", "stages": []}), 404
    return jsonify({"status": "done", "stages": stages})


@app.route("/report/<app_id>")
def report(app_id):
    """Return the before/after headline numbers for one app: CVE counts,
    test counts, and coverage. This reads several separate files, so if
    any one of them is missing or unreadable we still want to return
    whatever we *do* have, rather than a raw error page."""
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
        # A data file for this app exists but couldn't be read (e.g. it was
        # only half-written, or got corrupted). Tell the UI clearly instead
        # of returning a raw Flask error page.
        print(f"[app.py] /report/{app_id} failed: {e}")
        return jsonify({"available": False, "error": str(e)}), 500


# Backward-compatible aliases -> reference app (App5).
@app.route("/status")
def status_default():
    return status("reference-run")


@app.route("/report")
def report_default():
    return report("reference-run")


if __name__ == "__main__":
    app.run(debug=False, port=5001, use_reloader=False)