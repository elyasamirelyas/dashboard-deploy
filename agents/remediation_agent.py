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


def load_vulnerabilities(report_path=None, min_severity=("HIGH", "CRITICAL")):
    path = report_path or REPORT_PATH
    with open(path, "r", encoding="utf-8") as f:
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

def get_prioritized_targets(findings, max_targets=5):
    severity_rank = {"CRITICAL": 0, "HIGH": 1}
    confidence_rank = {"HIGHEST": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "UNKNOWN": 4}

    candidates = [f for f in findings if f["group_id"] and f["artifact_id"]]
    candidates.sort(key=lambda f: (
        severity_rank.get(f["severity"], 99),
        confidence_rank.get(f["confidence"].upper(), 99)
    ))

    # Dedupe by (group_id, artifact_id) - keep first (highest priority) occurrence
    seen = set()
    unique_targets = []
    for f in candidates:
        key = (f["group_id"], f["artifact_id"])
        if key not in seen:
            seen.add(key)
            unique_targets.append(f)

    return unique_targets[:max_targets]


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
    from llm_cache import cached_chat_completion
    raw = cached_chat_completion(
        client, "anthropic/claude-sonnet-4.5", [{"role": "user", "content": prompt}]
    ).strip()
    raw = re.sub(r"^```(json)?|```$", "", raw, flags=re.MULTILINE).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"LLM did not return valid JSON ({e}). Raw response:\n{raw[:500]}"
        ) from e


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

    if match:
        before, existing_version_tag, after = match.groups()
        new_version_tag = f"<version>{new_version}</version>\n            "
        new_block = before + new_version_tag + after
        new_content = content[:match.start()] + new_block + content[match.end():]
        action = "Updated"
    else:
        # Not a direct dependency (likely transitive) - add an explicit
        # override entry. Maven's "nearest declaration wins" rule means
        # this takes precedence over the transitive version.
        new_dependency_block = (
            f"        <dependency>\n"
            f"            <groupId>{group_id}</groupId>\n"
            f"            <artifactId>{artifact_id}</artifactId>\n"
            f"            <version>{new_version}</version>\n"
            f"        </dependency>\n"
        )
        # Insert right after the first <dependencies> tag
        insert_point = content.find("<dependencies>")
        if insert_point == -1:
            raise ValueError("Could not find <dependencies> section in pom.xml")
        insert_point += len("<dependencies>")
        new_content = (
            content[:insert_point] + "\n" + new_dependency_block + content[insert_point:]
        )
        action = "Added new explicit override for transitive dependency"

    with open(pom_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"{action}: {group_id}:{artifact_id} -> {new_version}")

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