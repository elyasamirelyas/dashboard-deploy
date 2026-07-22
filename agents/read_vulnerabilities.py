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