import os
import sys
import json
from flask import Flask, jsonify, render_template

app = Flask(__name__)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.join(SCRIPT_DIR, "..")
SHOWCASE_PATH = os.path.join(SCRIPT_DIR, "showcase_report.json")

TARGET_REPO_URL = "https://github.com/spring-petclinic/spring-petclinic-rest.git"
TARGET_REPO_TAG = "v2.6.2"

sys.path.insert(0, SCRIPT_DIR)
from generate_evaluation_report import (
    count_vulnerabilities, get_jacoco_totals, get_stage_detail, parse_test_count,
    EVAL_DIR as REPORT_EVAL_DIR,
)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/status")
def status():
    with open(SHOWCASE_PATH, "r", encoding="utf-8") as f:
        return jsonify(json.load(f))


@app.route("/report")
def report():
    vulns_before = count_vulnerabilities(os.path.join(REPORT_EVAL_DIR, "vulnerabilities_before.json"))
    vulns_after = count_vulnerabilities(os.path.join(REPORT_EVAL_DIR, "vulnerabilities_after.json"))
    cov_before = get_jacoco_totals(os.path.join(REPORT_EVAL_DIR, "coverage_before.xml"))
    cov_after = get_jacoco_totals(os.path.join(REPORT_EVAL_DIR, "coverage_after.xml"))

    tests_before, fail_before = parse_test_count(get_stage_detail("Baseline test count"))
    tests_after, fail_after = parse_test_count(get_stage_detail("Final test count"))

    return jsonify({
        "available": True,
        "vulns_before": vulns_before, "vulns_after": vulns_after,
        "tests_before": tests_before, "fail_before": fail_before,
        "tests_after": tests_after, "fail_after": fail_after,
        "coverage_before": cov_before.get("LINE") if cov_before else None,
        "coverage_after": cov_after.get("LINE") if cov_after else None,
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000, use_reloader=False)