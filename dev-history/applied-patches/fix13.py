with open("orchestrator.py", "r", encoding="utf-8") as f:
    src = f.read()

marker = "Removed trailing comma(s) before closing parenthesis"
if marker in src:
    print("ALREADY PATCHED - NO CHANGES MADE")
    raise SystemExit(0)

old = "    return fixes_applied"
if old not in src:
    print("ANCHOR NOT FOUND - STOPPED, NO CHANGES MADE")
    raise SystemExit(1)

insert = '''    _schema_path_trailing_comma = os.path.join(legacy_app_dir, "src", "main", "resources", "schema.sql")
    if os.path.exists(_schema_path_trailing_comma):
        with open(_schema_path_trailing_comma, "r", encoding="utf-8", errors="ignore") as f:
            _schema_content = f.read()
        _cleaned_schema = re.sub(r",(\\s*\\))", r"\\1", _schema_content)
        if _cleaned_schema != _schema_content:
            with open(_schema_path_trailing_comma, "w", encoding="utf-8") as f:
                f.write(_cleaned_schema)
            fixes_applied.append("Removed trailing comma(s) before closing parenthesis in schema.sql (H2 2.x rejects trailing commas that older H2/MySQL tolerated)")
    return fixes_applied'''

src2 = src.replace(old, insert, 1)
with open("orchestrator.py", "w", encoding="utf-8") as f:
    f.write(src2)
print("PATCHED OK")