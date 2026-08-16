path = r"C:\dev\modernization-of-legacy-java-applications\agents\orchestrator.py"
with open(path, encoding="utf-8") as f:
    lines = f.readlines()

start = next(i for i, l in enumerate(lines) if l.lstrip().startswith("def apply_known_migration_fixes"))
end = next(i for i in range(start + 1, len(lines)) if lines[i].startswith("EVAL_DIR"))

new_code = '''def apply_generic_migration_fixes(legacy_app_dir):
    """
    Fixes that apply broadly to Spring Boot 2->3 Maven migrations using
    OpenAPI Generator. Not specific to any one legacy codebase - these
    should apply to most similarly-structured projects.
    """
    fixes_applied = []
    pom_path = os.path.join(legacy_app_dir, "pom.xml")
    with open(pom_path, "r", encoding="utf-8") as f:
        pom = f.read()

    if "<openapi-generator-maven-plugin.version>5.2.1</openapi-generator-maven-plugin.version>" in pom:
        pom = pom.replace(
            "<openapi-generator-maven-plugin.version>5.2.1</openapi-generator-maven-plugin.version>",
            "<openapi-generator-maven-plugin.version>7.9.0</openapi-generator-maven-plugin.version>"
        )
        fixes_applied.append("[generic] Bumped openapi-generator-maven-plugin to 7.9.0")

    if "<serializationLibrary>jackson</serializationLibrary>" in pom and "<useSpringBoot3>" not in pom:
        pom = pom.replace(
            "<serializationLibrary>jackson</serializationLibrary>",
            "<serializationLibrary>jackson</serializationLibrary>\\n                                <useSpringBoot3>true</useSpringBoot3>"
        )
        fixes_applied.append("[generic] Added useSpringBoot3=true to generator config")

    if "<groupId>io.swagger.core.v3</groupId>" not in pom:
        insert_point = pom.find("<dependencies>")
        if insert_point != -1:
            insert_point += len("<dependencies>")
            swagger_dep = (
                "\\n        <dependency>\\n"
                "            <groupId>io.swagger.core.v3</groupId>\\n"
                "            <artifactId>swagger-annotations</artifactId>\\n"
                "            <version>2.2.21</version>\\n"
                "        </dependency>\\n"
            )
            pom = pom[:insert_point] + swagger_dep + pom[insert_point:]
            fixes_applied.append("[generic] Pinned swagger-annotations to 2.2.21")

    if "<groupId>jakarta.validation</groupId>" not in pom:
        insert_point = pom.find("<dependencies>")
        if insert_point != -1:
            insert_point += len("<dependencies>")
            validation_dep = (
                "\\n        <dependency>\\n"
                "            <groupId>jakarta.validation</groupId>\\n"
                "            <artifactId>jakarta.validation-api</artifactId>\\n"
                "            <version>3.0.2</version>\\n"
                "        </dependency>\\n"
            )
            pom = pom[:insert_point] + validation_dep + pom[insert_point:]
            fixes_applied.append("[generic] Pinned jakarta.validation-api to 3.0.2")

    # Single write, after ALL pom edits above (previously this wrote too
    # early and silently discarded the validation-api pin - now fixed)
    with open(pom_path, "w", encoding="utf-8") as f:
        f.write(pom)

    return fixes_applied


def apply_project_specific_fixes(legacy_app_dir):
    """
    Fixes tied to this specific codebase (spring-petclinic-rest)'s file
    structure and pre-existing defects. Will NOT generalize automatically
    to a different legacy application - a different codebase would need
    its own equivalent fixes, discovered the same way (from failing build
    output), documented here as a known limitation of the framework.
    """
    fixes_applied = []

    dead_file = os.path.join(
        legacy_app_dir, "src/main/java/org/springframework/samples/petclinic/util/ApplicationSwaggerConfig.java"
    )
    if os.path.exists(dead_file):
        os.remove(dead_file)
        fixes_applied.append("[project-specific] Removed dead ApplicationSwaggerConfig.java")

    jpql_fixes = [
        ("repository/jpa/JpaPetRepositoryImpl.java", "WHERE pet_id=", "WHERE visit.pet.id="),
        ("repository/springdatajpa/SpringDataPetRepositoryImpl.java", "WHERE pet_id=", "WHERE visit.pet.id="),
        ("repository/jpa/JpaPetTypeRepositoryImpl.java", "WHERE type_id=", "WHERE pet.type.id="),
        ("repository/springdatajpa/SpringDataPetTypeRepositoryImpl.java", "WHERE type_id=", "WHERE pet.type.id="),
    ]
    for rel_path, old, new in jpql_fixes:
        full_path = os.path.join(legacy_app_dir, "src/main/java/org/springframework/samples/petclinic", rel_path)
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                src = f.read()
            if old in src:
                src = src.replace(old, new)
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(src)
                fixes_applied.append(f"[project-specific] Fixed JPQL column reference in {rel_path}")

    spec_path = os.path.join(legacy_app_dir, "src/main/resources/api-docs.yml")
    if os.path.exists(spec_path):
        with open(spec_path, "r", encoding="utf-8") as f:
            spec = f.read()
        old_required = "      required:\\n        - id\\n    User:"
        new_required = "      required:\\n        - id\\n        - name\\n    User:"
        if old_required in spec:
            spec = spec.replace(old_required, new_required)
            with open(spec_path, "w", encoding="utf-8") as f:
                f.write(spec)
            fixes_applied.append("[project-specific] Added missing 'name' to PetType required fields")

    return fixes_applied


def apply_known_migration_fixes(legacy_app_dir):
    """
    Combined entry point: generic fixes first, then project-specific ones.
    Kept so existing callers don't need to change.
    """
    return apply_generic_migration_fixes(legacy_app_dir) + apply_project_specific_fixes(legacy_app_dir)


'''

new_lines = lines[:start] + [new_code] + lines[end:]
with open(path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Done. Replaced lines", start+1, "to", end)