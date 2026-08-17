# read_vulnerabilities.py - archived early draft of what became
# load_vulnerabilities() in remediation_agent.py. This version is much
# simpler: it only pulls out dependency name, CVE id, severity, and
# description - no groupId/artifactId/version parsing from the maven purl,
# and no confidence field. Those got added later once the pipeline needed
# to actually apply a fix, not just list what's wrong. Not called from
# anywhere else - just a quick standalone script for eyeballing the scan
# results, from before remediation_agent.py existed.

import json

REPORT_PATH = "../legacy-app/target/dependency-check-report.json"

def load_vulnerabilities(min_severity=("HIGH", "CRITICAL")):
    with open(REPORT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    findings = []
    for dependency in data.get("dependencies", []):
        vulns = dependency.get("vulnerabilities", [])
        if not vulns:
            continue
        for vuln in vulns:
            severity = vuln.get("severity", "").upper()
            if severity in min_severity:
                findings.append({
                    "dependency": dependency.get("fileName"),
                    "cve": vuln.get("name"),
                    "severity": severity,
                    "description": vuln.get("description", "")[:800],  # trim long text
                })
    return findings

if __name__ == "__main__":
    results = load_vulnerabilities()
    print(f"Found {len(results)} high/critical vulnerabilities:\n")
    for r in results:
        print(f"- {r['dependency']} | {r['cve']} | {r['severity']}")