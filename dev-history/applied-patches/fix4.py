# fix4.py - archived one-off patch script, inert now (points at an old
# dev path, C:\dev\..., that no longer exists). This is the patch that
# introduced the "clear stale target/ before verifying" step - OpenRewrite
# would sometimes leave old, half-migrated build output behind, which made
# the post-migration test run fail for reasons that had nothing to do with
# the migration itself. Deleting target/ first (with a few retries, since
# Windows can briefly lock files that were just written) fixed that. This
# retry-delete-then-verify block is still exactly what orchestrator.py's
# migration() function does today.

path = r"C:\dev\modernization-of-legacy-java-applications\agents\orchestrator.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

old = '''    print("\\n--- Verifying build after migration ---")
    success, output = run_mvn(["clean", "test"])
    log_stage("Build verification after migration", success, output)
    return success'''

new = '''    print("\\n--- Forcibly clearing stale build artifacts before verification ---")
    import shutil
    target_dir = os.path.join(LEGACY_APP_DIR, "target")
    for attempt in range(3):
        try:
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir)
            break
        except Exception as e:
            print(f"  target/ deletion attempt {attempt + 1} failed ({e}), waiting...")
            time.sleep(3)

    print("\\n--- Verifying build after migration ---")
    success, output = run_mvn(["test"])
    log_stage("Build verification after migration", success, output)
    return success'''

print("Found match:", old in content)
content = content.replace(old, new)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("Done.")