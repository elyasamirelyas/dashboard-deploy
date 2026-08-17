# apply_fix.py - a standalone one-off script, not called by anything else
# in the pipeline (confirmed - nothing in agents/ imports it). This was
# an early, manual version of the pom-version-bump logic; the pipeline's
# real version now lives in remediation_agent.py's apply_version_override,
# which also handles the transitive-dependency case this one doesn't (it
# just raises an error if the dependency isn't declared directly in the pom).
# Kept here as a record of a fix that was applied by hand at some point.

import re

def apply_version_override(pom_path, group_id, artifact_id, new_version):
    with open(pom_path, "r", encoding="utf-8") as f:
        content = f.read()

    # find the <dependency> block for this exact groupId + artifactId
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

# the one-off fix this script was actually written for: bumping the
# mysql connector to a version without the known CVEs
if __name__ == "__main__":
    apply_version_override(
        pom_path="../legacy-app/pom.xml",
        group_id="mysql",
        artifact_id="mysql-connector-java",
        new_version="8.0.33"
    )