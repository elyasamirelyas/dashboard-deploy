import os, re

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "orchestrator.py")
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

pattern = re.compile(r"<<<<<<< HEAD\r?\n(.*?)\r?\n=======\r?\n(.*?)\r?\n>>>>>>> origin/main", re.DOTALL)
blocks = list(pattern.finditer(content))
print(f"Found {len(blocks)} conflict block(s).\n")
for i, m in enumerate(blocks):
    print(f"===== BLOCK {i+1} =====")
    print("--- OURS ---")
    print(m.group(1))
    print("--- THEIRS ---")
    print(m.group(2))
    print()