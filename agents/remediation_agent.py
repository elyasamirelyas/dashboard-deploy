# remediation_agent.py - handles the "which CVEs do we fix, and how"
# part of the pipeline. It reads the OWASP dependency-check report,
# works out which vulnerabilities are worth fixing, asks the LLM to
# propose a fixed version for each one, and applies that fix to pom.xml.
#
# Can also be run directly (python remediation_agent.py) for a quick
# one-off manual test against the top single vulnerability, with a
# yes/no prompt before it actually touches the pom.

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

# Priority ranking - lower number = higher priority.
# We only care about CRITICAL and HIGH for now.
SEVERITY_RANK = {"CRITICAL": 0, "HIGH": 1}

# Confidence levels from the scanner - we trust HIGHEST/HIGH more.
CONFIDENCE_RANK = {"HIGHEST": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "UNKNOWN": 4}

# For anything not in the dicts above, fallback is 99.
# Means unknown severities/confidences get sorted to the bottom.


# ------------------------------------------------------------------
# Reading the dependency-check report and picking what to fix
# ------------------------------------------------------------------

def load_vulnerabilities(report_path=None, min_severity=("HIGH", "CRITICAL")):
    """
    Parses the OWASP dependency-check JSON report and returns a flat list
    of findings (one per vulnerability). Only includes vulnerabilities with
    severities in min_severity (default: HIGH, CRITICAL).
    
    Also extracts Maven coordinates (groupId, artifactId, current_version)
    from the package purl field - this is used later for applying fixes.
    """
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

        # Extract Maven coordinates from the package purl.
        # Format: "pkg:maven/groupId/artifactId@version"
        group_id, artifact_id, current_version = None, None, None
        packages = dependency.get("packages", [])
        if packages:
            purl = packages[0].get("id", "")
            # FIXME: This regex assumes purl format is consistent.
            # Some packages might have different structures.
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
                    "description": vuln.get("description", "")[:800],  # Trim to avoid huge prompts
                })
    return findings


def pick_top_priority(findings):
    """
    Finds the single highest-priority vulnerability from the list.
    Used for manual testing only (when running this file directly).
    
    Sorts by severity first (CRITICAL > HIGH), then by confidence.
    Returns None if no suitable candidates (missing group_id/artifact_id).
    """
    # Only consider findings with valid Maven coordinates
    candidates = [f for f in findings if f["group_id"] and f["artifact_id"]]
    candidates.sort(key=lambda f: (
        SEVERITY_RANK.get(f["severity"], 99),
        CONFIDENCE_RANK.get(f["confidence"].upper(), 99)
    ))
    return candidates[0] if candidates else None


def get_prioritized_targets(findings, max_targets=5):
    """
    Returns the highest-priority vulnerabilities to fix, limited to max_targets.
    This is what the main pipeline uses (not the manual run).
    
    Removes duplicate dependencies - if the same dependency appears with
    multiple CVEs, we only keep the first (highest priority) one.
    """
    candidates = [f for f in findings if f["group_id"] and f["artifact_id"]]
    # Sort worst first
    candidates.sort(key=lambda f: (
        SEVERITY_RANK.get(f["severity"], 99),
        CONFIDENCE_RANK.get(f["confidence"].upper(), 99)
    ))

    # Deduplicate by (group_id, artifact_id) - keep the first occurrence
    seen = set()
    unique_targets = []
    for f in candidates:
        key = (f["group_id"], f["artifact_id"])
        if key not in seen:
            seen.add(key)
            unique_targets.append(f)

    return unique_targets[:max_targets]


# ------------------------------------------------------------------
# Asking the LLM what version actually fixes a given vulnerability
# ------------------------------------------------------------------

def ask_llm_for_fix(vuln):
    """
    Send a vulnerability to the LLM and get back a suggested fixed version.
    
    We use a cached completion to avoid repeated API calls during development.
    The prompt asks for a structured JSON response (see prompt below).
    
    TODO: Maybe add some retry logic here? Sometimes the LLM returns invalid JSON.
    """
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
    
    # Sometimes the LLM wraps the JSON in markdown code blocks - strip them.
    raw = re.sub(r"^```(json)?|```$", "", raw, flags=re.MULTILINE).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        # This happens occasionally, usually when the LLM adds extra text.
        # We raise a clear error so the pipeline fails gracefully.
        raise ValueError(
            f"LLM did not return valid JSON ({e}). Raw response:\n{raw[:500]}"
        ) from e


# ------------------------------------------------------------------
# Writing the fixed version into pom.xml
# ------------------------------------------------------------------

def apply_version_override(pom_path, group_id, artifact_id, new_version):
    """
    Updates a dependency version in pom.xml, or adds a new explicit entry.
    
    If the dependency is already declared in the pom, we update its <version>.
    If it's missing (likely a transitive dependency), we add a new <dependency>
    entry to force Maven to use the fixed version.
    
    The regex is a bit fragile - it assumes the dependency block is formatted
    with groupId and artifactId on separate lines.
    """
    with open(pom_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Pattern to find existing dependency block
    pattern = re.compile(
        r"(<dependency>\s*"
        rf"<groupId>{re.escape(group_id)}</groupId>\s*"
        rf"<artifactId>{re.escape(artifact_id)}</artifactId>\s*)"
        r"(<version>.*?</version>\s*)?"  # Version might be missing
        r"(.*?</dependency>)",
        re.DOTALL
    )

    match = pattern.search(content)

    if match:
        # Found it - update the version
        before, existing_version_tag, after = match.groups()
        new_version_tag = f"<version>{new_version}</version>\n            "
        new_block = before + new_version_tag + after
        new_content = content[:match.start()] + new_block + content[match.end():]
        action = "Updated"
    else:
        # Not found - add a new dependency block
        # TODO: This inserts after <dependencies> tag. Might break if dependencies
        # are managed by a parent pom or use dependencyManagement.
        new_dependency_block = (
            f"        <dependency>\n"
            f"            <groupId>{group_id}</groupId>\n"
            f"            <artifactId>{artifact_id}</artifactId>\n"
            f"            <version>{new_version}</version>\n"
            f"        </dependency>\n"
        )
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


# ------------------------------------------------------------------
# Manual/interactive run - not used by the pipeline, just handy for
# testing a single fix by hand: python remediation_agent.py
# ------------------------------------------------------------------

if __name__ == "__main__":
    findings = load_vulnerabilities()
    print(f"Loaded {len(findings)} high/critical vulnerabilities.\n")

    top = pick_top_priority(findings)
    if not top:
        print("No suitable candidate found.")
        exit()

    # Show the worst vulnerability we found
    print(f"Top priority target: {top['dependency']} | {top['cve']} | "
          f"{top['severity']} | confidence={top['confidence']}\n")

    # Ask the LLM for a fix
    fix = ask_llm_for_fix(top)
    print("--- LLM Proposed Fix (structured) ---")
    print(json.dumps(fix, indent=2))
    print()

    # Interactive confirmation before modifying pom.xml
    confirm = input(f"Apply {fix['group_id']}:{fix['artifact_id']} -> "
                     f"{fix['fixed_version']} to pom.xml? [y/N] ")
    if confirm.lower() == "y":
        apply_version_override(
            POM_PATH, fix["group_id"], fix["artifact_id"], fix["fixed_version"]
        )
    else:
        print("Skipped applying the fix.")