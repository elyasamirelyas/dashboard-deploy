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