# fix3.py - archived one-off patch script. Points at an old dev machine's
# path (C:\dev\...), so it's inert now - can't actually run against a
# path that no longer exists. This is the patch that fixed a subtle bug:
# `def run_mvn(args, cwd=LEGACY_APP_DIR, ...)` used LEGACY_APP_DIR as a
# default argument, which Python evaluates once, at function-definition
# time - not on every call. That's already fine here since LEGACY_APP_DIR
# never changes after startup, but it's a common trap, so this patch
# swapped it for the safer `cwd=None` + "default it inside the function"
# pattern. That's the version orchestrator.py still uses today.

path = r"C:\dev\modernization-of-legacy-java-applications\agents\orchestrator.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

old = "def run_mvn(args, cwd=LEGACY_APP_DIR, retries=2, delay=3):"
new = "def run_mvn(args, cwd=None, retries=2, delay=3):\n    if cwd is None:\n        cwd = LEGACY_APP_DIR"

print("Found match:", old in content)
content = content.replace(old, new)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Done.")