import os
import json
import re
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

REPORT_PATH = "../legacy-app/target/dependency-check-report.json"
POM_PATH = "../legacy-app/pom.xml"


def load_vulnerabilities(min_severity=("HIGH", "CRITICAL")):
    with open(REPORT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    findings = []
    for dependency in data.get("dependencies", []):
        vulns = dependency.get("vulnerabilities", [])
        if not vulns:
            continue

        vuln_ids = dependency.get("vulnerabilityIds", [])
        confidence = vuln_ids[0]["confidence"] if vuln_ids else "UNKNOWN"

        # Extract groupId/artifactId/current version from the Maven "purl" package id,
        # e.g. "pkg:maven/mysql/mysql-connector-java@8.0.27"
        group_id, artifact_id, current_version = None, None, None
        packages = dependency.get("packages", [])
        if packages:
            purl = packages[0].get("id", "")
            match = re.match(r"pkg:maven/([^/]+)/([^@]+)@(.+)", purl)
            if match:
                group_id, artifact_id, current_version = match.groups()

        for vuln in vulns:
            severity = vuln.get("severity", "").upper()
            if severity in min_severity:
                findings.append({
                    "dependency": dependency.get("fileName"),
                    "group_id": group_id,
                    "artifact_id": artifact_id,
                    "current_version": current_version,
                    "cve": vuln.get("name"),
                    "severity": severity,
                    "confidence": confidence,
                    "description": vuln.get("description", "")[:800],
                })
    return findings


def pick_top_priority(findings):
    severity_rank = {"CRITICAL": 0, "HIGH": 1}
    confidence_rank = {"HIGHEST": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "UNKNOWN": 4}
    candidates = [f for f in findings if f["group_id"] and f["artifact_id"]]
    candidates.sort(key=lambda f: (
        severity_rank.get(f["severity"], 99),
        confidence_rank.get(f["confidence"].upper(), 99)
    ))
    return candidates[0] if candidates else None


def ask_llm_for_fix(vuln):
    prompt = f"""
You are a security remediation agent for a Java Maven project.
Given the vulnerability below, respond with ONLY a JSON object (no markdown, no
explanation outside the JSON) with exactly these fields:

{{
  "group_id": "...",
  "artifact_id": "...",
  "fixed_version": "...",
  "reasoning": "one or two sentence explanation of why this version fixes it"
}}

Vulnerability:
Dependency: {vuln['dependency']}
Group ID: {vuln['group_id']}
Artifact ID: {vuln['artifact_id']}
Current version: {vuln['current_version']}
CVE: {vuln['cve']}
Severity: {vuln['severity']}
Confidence: {vuln['confidence']}
Description: {vuln['description']}
"""
    response = client.chat.completions.create(
        model="anthropic/claude-sonnet-4.5",
        messages=[{"role": "user", "content": prompt}]
    )
    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```(json)?|```$", "", raw, flags=re.MULTILINE).strip()
    return json.loads(raw)


def apply_version_override(pom_path, group_id, artifact_id, new_version):
    with open(pom_path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(
        r"(<dependency>\s*"
        rf"<groupId>{re.escape(group_id)}</groupId>\s*"
        rf"<artifactId>{re.escape(artifact_id)}</artifactId>\s*)"
        r"(<version>.*?</version>\s*)?"
        r"(.*?</dependency>)",
        re.DOTALL
    )

    match = pattern.search(content)
    if not match:
        raise ValueError(f"Could not find dependency block for {group_id}:{artifact_id}")

    before, existing_version_tag, after = match.groups()
    new_version_tag = f"<version>{new_version}</version>\n            "

    new_block = before + new_version_tag + after
    new_content = content[:match.start()] + new_block + content[match.end():]

    with open(pom_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    action = "Updated" if existing_version_tag else "Inserted"
    print(f"{action} version for {group_id}:{artifact_id} -> {new_version}")


if __name__ == "__main__":
    findings = load_vulnerabilities()
    print(f"Loaded {len(findings)} high/critical vulnerabilities.\n")

    top = pick_top_priority(findings)
    if not top:
        print("No suitable candidate found.")
        exit()

    print(f"Top priority target: {top['dependency']} | {top['cve']} | "
          f"{top['severity']} | confidence={top['confidence']}\n")

    fix = ask_llm_for_fix(top)
    print("--- LLM Proposed Fix (structured) ---")
    print(json.dumps(fix, indent=2))
    print()

    confirm = input(f"Apply {fix['group_id']}:{fix['artifact_id']} -> "
                     f"{fix['fixed_version']} to pom.xml? [y/N] ")
    if confirm.lower() == "y":
        apply_version_override(
            POM_PATH, fix["group_id"], fix["artifact_id"], fix["fixed_version"]
        )
    else:
        print("Skipped applying the fix.")