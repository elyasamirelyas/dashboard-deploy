import os

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "orchestrator.py")
with open(path, "rb") as f:
    raw = f.read()

uses_crlf = b"\r\n" in raw
text = raw.decode("utf-8")
lines = text.splitlines()

blocks = [
    {"H": 93,  "E": 115, "T": 122, "strategy": "dedup_last_ours_line"},
    {"H": 397, "E": 398, "T": 409, "strategy": "keep_ours"},
    {"H": 449, "E": 459, "T": 474, "strategy": "keep_ours"},
    {"H": 674, "E": 703, "T": 719, "strategy": "keep_ours"},
]

for b in blocks:
    H, E, T = b["H"], b["E"], b["T"]
    assert lines[H-1].strip() == "<<<<<<< HEAD", f"line {H} is not a HEAD marker: {lines[H-1]!r}"
    assert lines[E-1].strip() == "=======", f"line {E} is not an equals marker: {lines[E-1]!r}"
    assert lines[T-1].strip() == ">>>>>>> origin/main", f"line {T} is not a theirs marker: {lines[T-1]!r}"
print("All marker positions verified correct.")

new_lines = []
i = 0
block_idx = 0
n = len(lines)
while i < n:
    if block_idx < len(blocks) and (i + 1) == blocks[block_idx]["H"]:
        b = blocks[block_idx]
        H, E, T = b["H"], b["E"], b["T"]
        ours = lines[H:E-1]
        theirs = lines[E:T-1]
        if b["strategy"] == "dedup_last_ours_line":
            resolved = ours[:-1] + theirs
        else:
            resolved = ours
        new_lines.extend(resolved)
        print(f"Resolved block at line {H}: ours had {len(ours)} lines, theirs had {len(theirs)} lines, kept {len(resolved)} lines")
        i = T
        block_idx += 1
    else:
        new_lines.append(lines[i])
        i += 1

remaining = sum(1 for l in new_lines if l.strip() in ("=======",) or l.strip().startswith("<<<<<<<") or l.strip().startswith(">>>>>>>"))
print(f"\nBlocks resolved: {block_idx}/4")
print(f"Remaining marker-like lines: {remaining}")

sep = "\r\n" if uses_crlf else "\n"
new_text = sep.join(new_lines) + sep
with open(path, "w", encoding="utf-8", newline="") as f:
    f.write(new_text)

print("File written.")