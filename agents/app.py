import os
import subprocess
import threading
import json
from flask import Flask, jsonify, render_template

app = Flask(__name__)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.join(SCRIPT_DIR, "..")
TARGET_DIR = os.path.join(PARENT_DIR, "legacy-app-demo-run")
PIPELINE_REPORT_PATH = os.path.join(SCRIPT_DIR, "pipeline_report.json")
EVAL_SUMMARY_PATH = os.path.join(PARENT_DIR, "evaluation", "reference-run", "EVALUATION_SUMMARY.md")

run_lock = threading.Lock()
is_running = False


def prepare_fresh_checkout():
    if os.path.exists(TARGET_DIR):
        subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", TARGET_DIR], shell=True)
    subprocess.run(
        ["git", "clone", "https://github.com/spring-petclinic/spring-petclinic-rest.git", TARGET_DIR],
        check=True
    )
    subprocess.run(["git", "checkout", "v2.6.2"], cwd=TARGET_DIR, check=True)
    git_dir = os.path.join(TARGET_DIR, ".git")
    subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", git_dir], shell=True)


def run_pipeline_background():
    global is_running
    try:
        prepare_fresh_checkout()
        subprocess.run(
            ["python", "orchestrator.py", TARGET_DIR],
            cwd=SCRIPT_DIR, check=False
        )
    finally:
        is_running = False


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/run", methods=["POST"])
def run_pipeline():
    global is_running
    with run_lock:
        if is_running:
            return jsonify({"error": "A run is already in progress"}), 409
        is_running = True
        thread = threading.Thread(target=run_pipeline_background, daemon=True)
        thread.start()
    return jsonify({"status": "started"})


@app.route("/status")
def status():
    if not os.path.exists(PIPELINE_REPORT_PATH):
        return jsonify({"status": "idle", "stages": []})
    with open(PIPELINE_REPORT_PATH, "r", encoding="utf-8") as f:
        report = json.load(f)
    return jsonify(report)


@app.route("/report")
def report():
    if not os.path.exists(EVAL_SUMMARY_PATH):
        return jsonify({"available": False})
    with open(EVAL_SUMMARY_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    return jsonify({"available": True, "markdown": content})


if __name__ == "__main__":
    app.run(debug=True, port=5000)