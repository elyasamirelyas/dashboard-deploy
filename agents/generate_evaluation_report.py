import os
import re
import json
import xml.etree.ElementTree as ET

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EVAL_DIR = os.path.join(SCRIPT_DIR, "..", "evaluation", "reference-run")
PIPELINE_REPORT_PATH = os.path.join(SCRIPT_DIR, "pipeline_report.json")


def count_vulnerabilities(json_path):
    if not os.path.exists(json_path):
        return None
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    vulnerable_deps = 0
    total_cves = 0
    by_severity = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}

    for dep in data.get("dependencies", []):
        vulns = dep.get("vulnerabilities", [])
        if vulns:
            vulnerable_deps += 1
        for v in vulns:
            total_cves += 1
            sev = v.get("severity", "").upper()
            if sev in by_severity:
                by_severity[sev] += 1

    return {
        "vulnerable_dependencies": vulnerable_deps,
        "total_cves": total_cves,
        "by_severity": by_severity,
    }


def get_jacoco_totals(xml_path):
    if not os.path.exists(xml_path):
        return None
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Top-level <counter> elements (direct children of <report>) give overall totals
    totals = {}
    for counter in root.findall("counter"):
        ctype = counter.get("type")
        missed = int(counter.get("missed"))
        covered = int(counter.get("covered"))
        total = missed + covered
        ratio = (covered / total * 100) if total > 0 else 0
        totals[ctype] = {"missed": missed, "covered": covered, "total": total, "ratio": ratio}

    return totals


def get_stage_detail(stage_name):
    if not os.path.exists(PIPELINE_REPORT_PATH):
        return None
    with open(PIPELINE_REPORT_PATH, "r", encoding="utf-8") as f:
        report = json.load(f)
    for stage in report.get("stages", []):
        if stage["stage"] == stage_name:
            return stage["details"]
    return None


def parse_test_count(detail_str):
    if not detail_str:
        return None, None
    m = re.search(r"Tests:\s*(\d+),\s*Failures:\s*(\d+)", detail_str)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None


def main():
    vulns_before = count_vulnerabilities(os.path.join(EVAL_DIR, "vulnerabilities_before.json"))
    vulns_after = count_vulnerabilities(os.path.join(EVAL_DIR, "vulnerabilities_after.json"))
    cov_before = get_jacoco_totals(os.path.join(EVAL_DIR, "coverage_before.xml"))
    cov_after = get_jacoco_totals(os.path.join(EVAL_DIR, "coverage_after.xml"))

    tests_before, fail_before = parse_test_count(get_stage_detail("Baseline test count"))
    tests_after, fail_after = parse_test_count(get_stage_detail("Final test count"))

    lines = []
    lines.append("# Evaluation Summary: Multi-Agent Modernization Pipeline\n")
    lines.append("## Vulnerability Remediation\n")
    lines.append("| Metric | Before | After |")
    lines.append("|---|---|---|")
    if vulns_before and vulns_after:
        lines.append(f"| Vulnerable dependencies | {vulns_before['vulnerable_dependencies']} | {vulns_after['vulnerable_dependencies']} |")
        lines.append(f"| Total CVEs | {vulns_before['total_cves']} | {vulns_after['total_cves']} |")
        for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            lines.append(f"| {sev.title()} severity CVEs | {vulns_before['by_severity'][sev]} | {vulns_after['by_severity'][sev]} |")
    else:
        lines.append("| (data not available - run the pipeline first) | - | - |")

    lines.append("\n## Test Suite\n")
    lines.append("| Metric | Before | After |")
    lines.append("|---|---|---|")
    lines.append(f"| Total tests | {tests_before if tests_before is not None else '-'} | {tests_after if tests_after is not None else '-'} |")
    lines.append(f"| Failing tests | {fail_before if fail_before is not None else '-'} | {fail_after if fail_after is not None else '-'} |")

    lines.append("\n## Code Coverage (JaCoCo)\n")
    lines.append("| Metric | Before | After |")
    lines.append("|---|---|---|")
    if cov_before and cov_after:
        for ctype in ["LINE", "BRANCH", "INSTRUCTION"]:
            if ctype in cov_before and ctype in cov_after:
                lines.append(
                    f"| {ctype.title()} coverage | "
                    f"{cov_before[ctype]['ratio']:.1f}% ({cov_before[ctype]['covered']}/{cov_before[ctype]['total']}) | "
                    f"{cov_after[ctype]['ratio']:.1f}% ({cov_after[ctype]['covered']}/{cov_after[ctype]['total']}) |"
                )
    else:
        lines.append("| (data not available - run the pipeline first) | - | - |")

    lines.append("\n## Pipeline Execution\n")
    if os.path.exists(PIPELINE_REPORT_PATH):
        with open(PIPELINE_REPORT_PATH, "r", encoding="utf-8") as f:
            report = json.load(f)
        for stage in report.get("stages", []):
            status = "✅" if stage["success"] else "❌"
            lines.append(f"- {status} {stage['stage']}")

    output = "\n".join(lines)
    output_path = os.path.join(EVAL_DIR, "EVALUATION_SUMMARY.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output)

    print(output)
    print(f"\n\nSaved to {output_path}")


if __name__ == "__main__":
    main()