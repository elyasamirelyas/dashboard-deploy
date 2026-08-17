with open("orchestrator.py", "r", encoding="utf-8") as f:
    src = f.read()

anchor = '    schema_sql_path = os.path.join(legacy_app_dir, "src", "main", "resources", "schema.sql")'
if anchor not in src:
    print("ANCHOR NOT FOUND - STOPPED, NO CHANGES MADE")
    raise SystemExit(1)

if "Converted file-based H2 datasource" in src:
    print("ALREADY PATCHED - NO CHANGES MADE")
    raise SystemExit(0)

insert = '''    for props_rel_path in ["src/main/resources/application.properties", "src/test/resources/application.properties"]:
        props_path = os.path.join(legacy_app_dir, props_rel_path)
        if not os.path.exists(props_path):
            continue
        with open(props_path, "r", encoding="utf-8") as f:
            props = f.read()
        _file_h2_match = re.search(r"spring\\.datasource\\.url=jdbc:h2:file:[^\\s;]+(;[^\\s]*)?", props)
        if _file_h2_match:
            _suffix = _file_h2_match.group(1) or ""
            _new_url_line = "spring.datasource.url=jdbc:h2:mem:testdb" + _suffix
            props = props.replace(_file_h2_match.group(0), _new_url_line)
            with open(props_path, "w", encoding="utf-8") as f:
                f.write(props)
            fixes_applied.append("Converted file-based H2 datasource (" + props_rel_path + ") to in-memory (avoids Windows file-lock/OneDrive sync flakiness)")

'''

src = src.replace(anchor, insert + anchor, 1)
with open("orchestrator.py", "w", encoding="utf-8") as f:
    f.write(src)
print("PATCHED OK")