with open("orchestrator.py", "r", encoding="utf-8") as f:
    src = f.read()

anchor = '    schema_sql_path = os.path.join(legacy_app_dir, "src", "main", "resources", "schema.sql")'
if anchor not in src:
    print("ANCHOR NOT FOUND - STOPPED, NO CHANGES MADE")
    raise SystemExit(1)

if "thymeleaf-spring5" in src and "Removed stale javax thymeleaf-spring5" in src:
    print("ALREADY PATCHED - NO CHANGES MADE")
    raise SystemExit(0)

insert = '''    with open(pom_path, "r", encoding="utf-8") as f:
        pom = f.read()
    if "thymeleaf-spring6" in pom and "thymeleaf-spring5" in pom:
        _cleaned = re.sub(
            r"<dependency>(?:(?!</dependency>).)*?<artifactId>thymeleaf-spring5</artifactId>(?:(?!</dependency>).)*?</dependency>\\s*",
            "", pom, flags=re.DOTALL
        )
        if _cleaned != pom:
            pom = _cleaned
            fixes_applied.append("Removed stale javax thymeleaf-spring5 override (conflicts with jakarta thymeleaf-spring6 after Boot3 migration)")
            with open(pom_path, "w", encoding="utf-8") as f:
                f.write(pom)

'''

src = src.replace(anchor, insert + anchor, 1)
with open("orchestrator.py", "w", encoding="utf-8") as f:
    f.write(src)
print("PATCHED OK")