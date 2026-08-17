path = r"C:\dev\modernization-of-legacy-java-applications\agents\orchestrator.py"
with open(path, "rb") as f:
    raw = f.read()

content = raw.decode("utf-8")
lines = content.splitlines(keepends=True)

# Find the "def stage_migration" line
start = next(i for i, l in enumerate(lines) if l.lstrip().startswith("def stage_migration"))
# Find the next "def " after it (end of this function)
end = next(i for i in range(start + 1, len(lines)) if lines[i].startswith("def "))

print("--- Current function ---")
for l in lines[start:end]:
    print(repr(l))

# Rebuild the function with the verification restored
new_function = (
    'def stage_migration():\n'
    '    print("\\n=== STAGE 1: Migration (OpenRewrite) ===")\n'
    '    success, output = run_mvn([\n'
    '        "org.openrewrite.maven:rewrite-maven-plugin:run",\n'
    '        "-Drewrite.recipeArtifactCoordinates=org.openrewrite.recipe:rewrite-spring:RELEASE",\n'
    '        "-Drewrite.activeRecipes=org.openrewrite.java.spring.boot3.UpgradeSpringBoot_3_0"\n'
    '    ])\n'
    '    log_stage("Migration (OpenRewrite)", success, output)\n'
    '\n'
    '    print("\\n--- Applying known fix patterns (learned from prior migration analysis) ---")\n'
    '    fixes = apply_known_migration_fixes(LEGACY_APP_DIR)\n'
    '    log_stage("Known migration fixes applied", True, "\\n".join(fixes) if fixes else "No known fixes needed")\n'
    '\n'
    '    print("\\n--- Verifying build after migration ---")\n'
    '    success, output = run_mvn(["clean", "test"])\n'
    '    log_stage("Build verification after migration", success, output)\n'
    '    return success\n'
    '\n'
    '\n'
)

new_lines = lines[:start] + [new_function] + lines[end:]
new_content = "".join(new_lines)

with open(path, "w", encoding="utf-8", newline="") as f:
    f.write(new_content)

print("\nDone - function replaced.")