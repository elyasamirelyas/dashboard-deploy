with open("orchestrator.py", "r", encoding="utf-8") as f:
    src = f.read()

anchor = '    schema_sql_path = os.path.join(legacy_app_dir, "src", "main", "resources", "schema.sql")'
if anchor not in src:
    print("ANCHOR NOT FOUND - STOPPED, NO CHANGES MADE")
    raise SystemExit(1)

if "Pinned \" + _sibling" in src or "NON_KEYWORDS=USER" in src:
    print("ALREADY PATCHED - NO CHANGES MADE")
    raise SystemExit(0)

insert = '''    with open(pom_path, "r", encoding="utf-8") as f:
        pom = f.read()
    _bare_tl_match = re.search(
        r"<dependency>\\s*<groupId>org\\.thymeleaf</groupId>\\s*<artifactId>thymeleaf</artifactId>\\s*<version>([^<]+)</version>\\s*</dependency>",
        pom
    )
    if _bare_tl_match:
        _bare_version = _bare_tl_match.group(1)
        for _sibling in ("thymeleaf-spring5", "thymeleaf-spring6"):
            _sibling_pattern = (
                r"<dependency>\\s*<groupId>org\\.thymeleaf</groupId>\\s*<artifactId>"
                + _sibling + r"</artifactId>\\s*</dependency>"
            )
            _sibling_match = re.search(_sibling_pattern, pom)
            if _sibling_match:
                _new_block = (
                    "<dependency>\\n            <groupId>org.thymeleaf</groupId>\\n            <artifactId>"
                    + _sibling + "</artifactId>\\n            <version>" + _bare_version + "</version>\\n        </dependency>"
                )
                pom = pom[:_sibling_match.start()] + _new_block + pom[_sibling_match.end():]
                fixes_applied.append("Pinned " + _sibling + " to " + _bare_version + " to match explicitly-overridden thymeleaf core version (fixes NoSuchMethodError from version skew)")
                with open(pom_path, "w", encoding="utf-8") as f:
                    f.write(pom)

    with open(pom_path, "r", encoding="utf-8") as f:
        _pom_for_h2check = f.read()
    if "com.h2database" in _pom_for_h2check:
        for props_rel_path in ["src/main/resources/application.properties", "src/test/resources/application.properties"]:
            props_path = os.path.join(legacy_app_dir, props_rel_path)
            if not os.path.exists(props_path):
                continue
            with open(props_path, "r", encoding="utf-8") as f:
                props = f.read()
            if "NON_KEYWORDS" in props:
                continue
            url_match = re.search(r"^spring\\.datasource\\.url=(.+)$", props, re.MULTILINE)
            if url_match:
                old_line = url_match.group(0)
                old_url = url_match.group(1).strip()
                new_line = "spring.datasource.url=" + old_url + ";NON_KEYWORDS=USER"
                props = props.replace(old_line, new_line)
            else:
                props = props.rstrip("\\n") + "\\nspring.datasource.url=jdbc:h2:mem:testdb;NON_KEYWORDS=USER;DB_CLOSE_ON_EXIT=FALSE\\n"
            with open(props_path, "w", encoding="utf-8") as f:
                f.write(props)
            fixes_applied.append("Added H2 NON_KEYWORDS=USER to datasource URL in " + props_rel_path + " (H2 2.x reserves USER as a keyword)")

'''

src = src.replace(anchor, insert + anchor, 1)
with open("orchestrator.py", "w", encoding="utf-8") as f:
    f.write(src)
print("PATCHED OK")