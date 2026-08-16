with open("orchestrator.py", "r", encoding="utf-8") as f:
    src = f.read()

old1 = '            build_ok, build_output = run_mvn(["clean", "compile"])'
new1 = '            build_ok, build_output = run_mvn(["clean", "test"])'

old2 = '''    print("\\n--- Final build verification after all remediation ---")
    success, output = run_mvn(["clean", "compile"])
    log_stage("Build verification after remediation batch", success, output)'''
new2 = '''    print("\\n--- Final build verification after all remediation ---")
    success, output = run_mvn(["clean", "test"])
    log_stage("Build verification after remediation batch", success, output)'''

if old1 not in src or old2 not in src:
    print("ANCHOR NOT FOUND - STOPPED, NO CHANGES MADE")
    raise SystemExit(1)

if new1 in src.replace(old1, "", 1) and False:
    pass

src2 = src.replace(old1, new1, 1)
src2 = src2.replace(old2, new2, 1)

if src2 == src:
    print("ALREADY PATCHED OR NO CHANGE - CHECK MANUALLY")
    raise SystemExit(1)

with open("orchestrator.py", "w", encoding="utf-8") as f:
    f.write(src2)
print("PATCHED OK")