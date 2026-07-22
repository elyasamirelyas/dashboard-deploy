import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

REPORT_PATH = "../legacy-app/target/dependency-check-report.json"

def load_vulnerabilities(min_severity=("HIGH", "CRITICAL")):
    with open(REPORT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    findings = []
    for dependency in data.get("dependencies", []):
        vulns = dependency.get("vulnerabilities", [])
        if not vulns:
            continue

        # Confidence is per-dependency, taken from vulnerabilityIds
        vuln_ids = dependency.get("vulnerabilityIds", [])
        confidence = vuln_ids[0]["confidence"] if vuln_ids else "UNKNOWN"

        for vuln in vulns:
            severity = vuln.get("severity", "").upper()
            if severity in min_severity:
                findings.append({
                    "dependency": dependency.get("fileName"),
                    "cve": vuln.get("name"),
                    "severity": severity,
                    "confidence": confidence,
                    "description": vuln.get("description", "")[:800],
                })
    return findings

def pick_top_priority(findings):
    # Prioritize CRITICAL/HIGH + HIGHEST/HIGH confidence first
    severity_rank = {"CRITICAL": 0, "HIGH": 1}
    confidence_rank = {"HIGHEST": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    findings.sort(key=lambda f: (
        severity_rank.get(f["severity"], 99),
        confidence_rank.get(f["confidence"].upper(), 99)
    ))
    return findings[0] if findings else None

def generate_fix(vuln):
    prompt = f"""
You are a security remediation agent for a Java Maven project.
Given the following vulnerability, suggest the exact change needed to fix it
in the project's pom.xml, and briefly explain why it works.

Dependency: {vuln['dependency']}
CVE: {vuln['cve']}
Severity: {vuln['severity']}
Confidence: {vuln['confidence']}
Description: {vuln['description']}
"""
    response = client.chat.completions.create(
        model="anthropic/claude-sonnet-4.5",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

if __name__ == "__main__":
    findings = load_vulnerabilities()
    print(f"Loaded {len(findings)} high/critical vulnerabilities.\n")

    top = pick_top_priority(findings)
    print(f"Top priority target: {top['dependency']} | {top['cve']} | {top['severity']} | confidence={top['confidence']}\n")

    fix = generate_fix(top)
    print("--- Suggested Fix ---\n")
    print(fix)