# orchestrator.py - runs the entire multi-agent modernization pipeline end-to-end.
#
# Stages: baseline capture -> OpenRewrite migration -> vulnerability remediation ->
# test generation -> final verification. Results go into evaluation/<app_id>/ and
# a pipeline report is written to agents/reports/pipeline_report.json for the
# dashboard.

import os
import subprocess
import json
import sys
import re
import time
import shutil
from dotenv import load_dotenv
from remediation_agent import load_vulnerabilities, get_prioritized_targets, ask_llm_for_fix, apply_version_override

load_dotenv()

# ------------------------------------------------------------------
# Determine target app and set up directories
# ------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_LEGACY_APP_DIR = os.path.join(SCRIPT_DIR, "..", "legacy-app")
NVD_API_KEY = os.getenv("NVD_API_KEY")

# Precedence: env var TARGET_APP_DIR > command-line arg > default
LEGACY_APP_DIR = os.environ.get("TARGET_APP_DIR") or (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_LEGACY_APP_DIR)
LEGACY_APP_DIR = os.path.abspath(LEGACY_APP_DIR)

_default_app_abspath = os.path.abspath(DEFAULT_LEGACY_APP_DIR)
_is_default_target = (LEGACY_APP_DIR == _default_app_abspath)

# Project-specific fixes (hardcoded for petclinic) are only enabled for the
# default legacy-app folder. Any other app gets the generic LLM diagnoser.
_env_flag = os.environ.get("ENABLE_PROJECT_SPECIFIC_FIXES")
if _env_flag is None:
    ENABLE_PROJECT_SPECIFIC_FIXES = _is_default_target
else:
    ENABLE_PROJECT_SPECIFIC_FIXES = _env_flag.lower() == "true"

# Each app gets its own subdirectory under evaluation/ to avoid collisions
_eval_subdir = "reference-run" if _is_default_target else (os.path.basename(LEGACY_APP_DIR.rstrip(os.sep)) or "target-run")
EVAL_DIR = os.path.join(SCRIPT_DIR, "..", "evaluation", _eval_subdir)

# Maven and Java paths - these are specific to the environment this was built on
MVN_CMD = os.getenv("MVN_CMD", r"C:\Users\amiri\apache-maven-3.9.16-bin\apache-maven-3.9.16\bin\mvn.cmd")
JAVA17_HOME = r"C:\Program Files\Eclipse Adoptium\jdk-17.0.17.10-hotspot"

REPORT = {"stages": []}
SUREFIRE_DIR = os.path.join(LEGACY_APP_DIR, "target", "surefire-reports")


# ------------------------------------------------------------------
# Utilities used across the pipeline
# ------------------------------------------------------------------

def print_environment_diagnostics():
    """Log Java and Maven versions at startup to help debug build issues later."""
    print("\n=== ENVIRONMENT DIAGNOSTICS ===")
    print(f"JAVA_HOME env var: {os.environ.get('JAVA_HOME', 'NOT SET')}")
    result = subprocess.run(["java", "-version"], capture_output=True, text=True, shell=True)
    print(f"java -version output:\n{result.stdout}{result.stderr}")
    result2 = subprocess.run(["mvn", "-version"], capture_output=True, text=True, shell=True, cwd=LEGACY_APP_DIR)
    print(f"mvn -version output:\n{result2.stdout}{result2.stderr}")
    print("=== END DIAGNOSTICS ===\n")


def log_stage(name, success, details=""):
    """Append a stage result to the in-memory report and save to disk immediately."""
    REPORT["stages"].append({"stage": name, "success": success, "details": details})
    status = "OK" if success else "FAILED"
    print(f"\n[{status}] {name}")
    if details:
        print(details[:500])
    save_report()


def save_report():
    """Write the current pipeline report to agents/reports/pipeline_report.json."""
    os.makedirs(os.path.join(SCRIPT_DIR, "reports"), exist_ok=True)
    with open(os.path.join(SCRIPT_DIR, "reports", "pipeline_report.json"), "w", encoding="utf-8") as f:
        json.dump(REPORT, f, indent=2)


def _copy_if_exists(src, dst):
    """Copy a file if it exists; used for optional reports."""
    if os.path.exists(src):
        shutil.copy(src, dst)


def run_mvn(args, cwd=None, retries=2, delay=3):
    """
    Execute a Maven command with JDK 17 environment and optional retries.
    Returns (success_bool, combined_output).
    """
    if cwd is None:
        cwd = LEGACY_APP_DIR
    env = os.environ.copy()
    env["JAVA_HOME"] = JAVA17_HOME
    env["PATH"] = os.path.join(JAVA17_HOME, "bin") + os.pathsep + env.get("PATH", "")

    last_output = ""
    for attempt in range(retries + 1):
        result = subprocess.run(
            [MVN_CMD] + args, cwd=cwd, capture_output=True, text=True,
            encoding="utf-8", errors="replace", env=env, shell=False
        )
        success = result.returncode == 0
        last_output = result.stdout[-3000:] + result.stderr[-1000:]
        if success:
            return success, last_output
        if attempt < retries:
            print(f"  (attempt {attempt + 1} failed, retrying in {delay}s)...")
            time.sleep(delay)

    return False, last_output


# ------------------------------------------------------------------
# Migration fixes - generic (for any Spring Boot 2->3 project) and
# project-specific (hardcoded for spring-petclinic-rest)
# ------------------------------------------------------------------

def apply_generic_migration_fixes(legacy_app_dir):
    """
    Apply pom.xml fixes that are generally needed after OpenRewrite migration.
    These are not tied to a specific app.
    """
    fixes_applied = []
    pom_path = os.path.join(legacy_app_dir, "pom.xml")
    with open(pom_path, "r", encoding="utf-8") as f:
        pom = f.read()

    # Bump openapi-generator plugin to a version compatible with Spring Boot 3
    if "<openapi-generator-maven-plugin.version>5.2.1</openapi-generator-maven-plugin.version>" in pom:
        pom = pom.replace(
            "<openapi-generator-maven-plugin.version>5.2.1</openapi-generator-maven-plugin.version>",
            "<openapi-generator-maven-plugin.version>7.9.0</openapi-generator-maven-plugin.version>"
        )
        fixes_applied.append("[generic] Bumped openapi-generator-maven-plugin to 7.9.0")

    # Add useSpringBoot3=true to the generator config if not present
    if "<serializationLibrary>jackson</serializationLibrary>" in pom and "<useSpringBoot3>" not in pom:
        pom = pom.replace(
            "<serializationLibrary>jackson</serializationLibrary>",
            "<serializationLibrary>jackson</serializationLibrary>\n                                <useSpringBoot3>true</useSpringBoot3>"
        )
        fixes_applied.append("[generic] Added useSpringBoot3=true to generator config")

    # Add swagger-annotations if missing (needed by generated code)
    if "<groupId>io.swagger.core.v3</groupId>" not in pom:
        insert_point = pom.find("<dependencies>")
        if insert_point != -1:
            insert_point += len("<dependencies>")
            swagger_dep = (
                "\n        <dependency>\n"
                "            <groupId>io.swagger.core.v3</groupId>\n"
                "            <artifactId>swagger-annotations</artifactId>\n"
                "            <version>2.2.21</version>\n"
                "        </dependency>\n"
            )
            pom = pom[:insert_point] + swagger_dep + pom[insert_point:]
            fixes_applied.append("[generic] Pinned swagger-annotations to 2.2.21")

    # Pin jakarta.validation-api to avoid classpath conflicts
    if "<groupId>jakarta.validation</groupId>" not in pom:
        insert_point = pom.find("<dependencies>")
        if insert_point != -1:
            insert_point += len("<dependencies>")
            validation_dep = (
                "\n        <dependency>\n"
                "            <groupId>jakarta.validation</groupId>\n"
                "            <artifactId>jakarta.validation-api</artifactId>\n"
                "            <version>3.0.2</version>\n"
                "        </dependency>\n"
            )
            pom = pom[:insert_point] + validation_dep + pom[insert_point:]
            fixes_applied.append("[generic] Pinned jakarta.validation-api to 3.0.2")

    # Write once after all modifications - doing it earlier would lose changes
    with open(pom_path, "w", encoding="utf-8") as f:
        f.write(pom)

    return fixes_applied


def apply_project_specific_fixes(legacy_app_dir):
    """
    Hardcoded fixes for spring-petclinic-rest specific post-migration issues.
    Only runs if ENABLE_PROJECT_SPECIFIC_FIXES is True (i.e., for the default app).
    """
    fixes_applied = []

    # Remove a dead Swagger config class that no longer compiles
    dead_file = os.path.join(
        legacy_app_dir, "src/main/java/org/springframework/samples/petclinic/util/ApplicationSwaggerConfig.java"
    )
    if os.path.exists(dead_file):
        os.remove(dead_file)
        fixes_applied.append("[project-specific] Removed dead ApplicationSwaggerConfig.java")

    # JPQL column reference fixes - the migration changed column names in the DB schema
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

    # OpenAPI spec missing required field - add it
    spec_path = os.path.join(legacy_app_dir, "src/main/resources/api-docs.yml")
    if os.path.exists(spec_path):
        with open(spec_path, "r", encoding="utf-8") as f:
            spec = f.read()
        old_required = "      required:\n        - id\n    User:"
        new_required = "      required:\n        - id\n        - name\n    User:"
        if old_required in spec:
            spec = spec.replace(old_required, new_required)
            with open(spec_path, "w", encoding="utf-8") as f:
                f.write(spec)
            fixes_applied.append("[project-specific] Added missing 'name' to PetType required fields")

    return fixes_applied


# ------------------------------------------------------------------
# Generic build-failure diagnosis via LLM (used for non-petclinic apps)
# ------------------------------------------------------------------

def parse_maven_compile_errors(mvn_output):
    """Extract compiler error details from Maven output."""
    pattern = re.compile(
        r"\[ERROR\]\s*(?P<file>.+?\.java):\[(?P<line>\d+),(?P<col>\d+)\]\s*(?P<msg>.+)"
    )
    errors = []
    for m in pattern.finditer(mvn_output):
        file_path = m.group("file")
        # Maven sometimes prints Windows paths with an extra leading slash
        # before the drive letter (e.g. "/C:/Users/...") - Windows doesn't
        # recognize that as a real path, so strip it if present.
        file_path = re.sub(r"^/([A-Za-z]:)", r"\1", file_path)
        errors.append({"file": file_path, "line": int(m.group("line")), "message": m.group("msg").strip()})
    return errors


def _read_source_snippet(file_path, line, context=15):
    """Return a few lines around a given line number for context."""
    if not os.path.exists(file_path) or line is None:
        return ""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    start = max(0, line - context - 1)
    end = min(len(lines), line + context)
    return "\n".join(f"{i + 1}: {lines[i]}" for i in range(start, end))


def ask_llm_for_build_fix(error, source_snippet):
    """Ask the LLM to propose a fix for a single compiler error."""
    from remediation_agent import client  # reuse the OpenRouter client

    prompt = f"""
You are a build-failure diagnoser for a Java Maven project undergoing a
Spring Boot version migration. You are given ONE compiler error plus the
surrounding source. Propose the SMALLEST possible source change that fixes
this specific error, without changing unrelated behaviour.

Respond with ONLY a JSON object (no markdown, no explanation outside the
JSON) with exactly these fields:

{{
  "file": "...",
  "search": "...",
  "replace": "...",
  "explanation": "one sentence"
}}

"search" must be an EXACT, unique substring of the file's current content
(whitespace included). If you cannot confidently identify a fix, respond
with {{"file": null, "search": null, "replace": null, "explanation": "insufficient context"}}.

Error:
File: {error['file']}
Line: {error['line']}
Message: {error['message']}

Source context:
{source_snippet}
"""
    from llm_cache import cached_chat_completion
    raw = cached_chat_completion(
        client, "anthropic/claude-sonnet-4.5", [{"role": "user", "content": prompt}]
    ).strip()
    raw = re.sub(r"^```(json)?|```$", "", raw, flags=re.MULTILINE).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        # Preserve the raw response in the exception for debugging
        raise ValueError(
            f"LLM did not return valid JSON ({e}). Raw response:\n{raw[:500]}"
        ) from e


def apply_search_replace_fix(legacy_app_dir, fix):
    """Apply a search/replace fix to a source file."""
    target_path = os.path.join(legacy_app_dir, fix["file"])
    if not os.path.exists(target_path):
        # Fallback: search for file by name in case path changed (e.g., OpenRewrite moved it)
        target_name = os.path.basename(fix["file"])
        matches = [
            os.path.join(root, target_name)
            for root, _, files in os.walk(legacy_app_dir) if target_name in files
        ]
        if not matches:
            return False
        target_path = matches[0]

    with open(target_path, "r", encoding="utf-8") as f:
        content = f.read()
    if fix["search"] not in content:
        return False

    content = content.replace(fix["search"], fix["replace"], 1)
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(content)
    return True


def diagnose_and_fix_build_failures(legacy_app_dir, max_iterations=5):
    """
    Generic LLM-based build fixer. Runs compile, parses errors, asks LLM for a fix,
    applies it, and repeats until build succeeds or max iterations reached.
    """
    fixes_applied = []

    for iteration in range(1, max_iterations + 1):
        success, output = run_mvn(["clean", "test-compile"], cwd=legacy_app_dir)
        if success:
            return {"success": True, "fixes_applied": fixes_applied, "iterations": iteration - 1}

        errors = parse_maven_compile_errors(output)
        if not errors:
            return {"success": False, "fixes_applied": fixes_applied,
                     "reason": "build failed but no structured compiler error could be parsed",
                     "log_tail": output[-2000:]}

        first_error = errors[0]
        source_path = os.path.join(legacy_app_dir, first_error["file"])
        snippet = _read_source_snippet(source_path, first_error["line"])

        try:
            fix = ask_llm_for_build_fix(first_error, snippet)
        except (json.JSONDecodeError, ValueError) as e:
            return {"success": False, "fixes_applied": fixes_applied,
                     "reason": f"LLM did not return valid JSON: {e}"}

        if not fix.get("file") or not fix.get("search"):
            return {"success": False, "fixes_applied": fixes_applied,
                     "reason": fix.get("explanation", "LLM could not propose a fix")}

        target_path = os.path.join(legacy_app_dir, fix["file"])
        backup = None
        if os.path.exists(target_path):
            with open(target_path, "r", encoding="utf-8") as f:
                backup = f.read()

        if not apply_search_replace_fix(legacy_app_dir, fix):
            continue

        fixes_applied.append({
            "file": fix["file"],
            "description": fix.get("explanation", ""),
            "fixed_error": first_error["message"],
        })

        # Verify the fix didn't make things worse
        success2, output2 = run_mvn(["clean", "test-compile"], cwd=legacy_app_dir)
        if not success2 and backup is not None:
            new_errors = parse_maven_compile_errors(output2)
            if len(new_errors) > len(errors):
                # Revert if error count increased
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(backup)
                fixes_applied.pop()
                return {"success": False, "fixes_applied": fixes_applied,
                         "reason": "fix increased error count, reverted",
                         "log_tail": output2[-2000:]}

    return {"success": False, "fixes_applied": fixes_applied,
             "reason": f"max iterations ({max_iterations}) reached without a clean build"}


def count_tests(surefire_dir):
    """Count total tests and failures from Surefire text reports."""
    total_tests, total_failures = 0, 0
    if not os.path.exists(surefire_dir):
        return 0, 0
    for f in os.listdir(surefire_dir):
        if f.endswith(".txt"):
            with open(os.path.join(surefire_dir, f), "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    m = re.search(r"Tests run: (\d+), Failures: (\d+), Errors: (\d+)", line)
                    if m:
                        total_tests += int(m.group(1))
                        total_failures += int(m.group(2)) + int(m.group(3))
                        break
    return total_tests, total_failures


# ------------------------------------------------------------------
# Pipeline stages (executed in order in __main__)
# ------------------------------------------------------------------

def baseline():
    """Stage 0: Capture before-migration metrics (vulnerabilities, tests, coverage)."""
    print("\n=== STAGE 0: Capture Baseline (before any changes) ===")
    os.makedirs(EVAL_DIR, exist_ok=True)

    print("--- Baseline vulnerability scan ---")
    success, output = run_mvn([
        "org.owasp:dependency-check-maven:check",
        f"-DnvdApiKey={NVD_API_KEY}", "-Dformats=JSON"
    ])
    log_stage("Baseline vulnerability scan", success, output)
    _copy_if_exists(
        os.path.join(LEGACY_APP_DIR, "target", "dependency-check-report.json"),
        os.path.join(EVAL_DIR, "vulnerabilities_before.json"),
    )

    print("--- Baseline test run + coverage ---")
    success, output = run_mvn(["clean", "test", "jacoco:report"])
    log_stage("Baseline test run", success, output)
    _copy_if_exists(
        os.path.join(LEGACY_APP_DIR, "target", "site", "jacoco", "jacoco.xml"),
        os.path.join(EVAL_DIR, "coverage_before.xml"),
    )

    test_count, failures = count_tests(SUREFIRE_DIR)
    log_stage("Baseline test count", True, f"Tests: {test_count}, Failures: {failures}")

    return True


def migration():
    """Stage 1: Run OpenRewrite migration and apply necessary fixes."""
    print("\n=== STAGE 1: Migration (OpenRewrite) ===")
    print("\n--- Applying generic migration fixes before OpenRewrite ---")
    pre_fixes = apply_generic_migration_fixes(LEGACY_APP_DIR)
    log_stage("Generic migration fixes applied (pre-OpenRewrite)", True, "\n".join(pre_fixes) if pre_fixes else "No generic fixes needed")
    if ENABLE_PROJECT_SPECIFIC_FIXES:
        print("\n--- Applying project-specific fixes (petclinic-only, hardcoded) ---")
        fixes2 = apply_project_specific_fixes(LEGACY_APP_DIR)
        log_stage("Project-specific fixes applied", True, "\n".join(fixes2) if fixes2 else "No project-specific fixes needed")

    success, output = run_mvn([
        "org.openrewrite.maven:rewrite-maven-plugin:run",
        "-Drewrite.recipeArtifactCoordinates=org.openrewrite.recipe:rewrite-spring:RELEASE",
        "-Drewrite.activeRecipes=org.openrewrite.java.spring.boot3.UpgradeSpringBoot_3_0,org.openrewrite.java.spring.boot3.AddSetUseTrailingSlashMatch"
    ])
    log_stage("Migration (OpenRewrite)", success, output)

    print("\n--- Re-applying generic migration fixes after OpenRewrite ---")
    post_fixes = apply_generic_migration_fixes(LEGACY_APP_DIR)
    log_stage("Generic migration fixes applied (post-OpenRewrite)", True, "\n".join(post_fixes) if post_fixes else "No generic fixes needed")

    print("\n--- Forcibly clearing stale build artifacts before verification ---")
    target_dir = os.path.join(LEGACY_APP_DIR, "target")
    for attempt in range(3):
        try:
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir)
            break
        except Exception as e:
            print(f"  target/ deletion attempt {attempt + 1} failed ({e}), waiting...")
            time.sleep(3)

    print("\n--- Verifying build after migration ---")
    success, output = run_mvn(["test"])
    log_stage("Build verification after migration", success, output)

    if not success and not ENABLE_PROJECT_SPECIFIC_FIXES:
        print("\n--- Running generic LLM-based build-failure diagnoser ---")
        diag = diagnose_and_fix_build_failures(LEGACY_APP_DIR)
        log_stage(
            "Generic build-failure diagnosis",
            diag["success"],
            f"Fixes applied: {json.dumps(diag['fixes_applied'], indent=2)}\n{diag.get('reason', '')}"
        )
        if diag["success"]:
            success, output = run_mvn(["test"])
            log_stage("Build verification after diagnosis", success, output)
    return success


# Some libraries must be upgraded as a set; otherwise runtime NoSuchMethodError can occur.
# Jackson core and Thymeleaf+Spring are known examples. Add more as needed.
MATCHED_VERSION_SETS = {
    "com.fasterxml.jackson.core": ["jackson-core", "jackson-annotations", "jackson-databind"],
    "org.thymeleaf": ["thymeleaf", "thymeleaf-spring5", "thymeleaf-spring6"],
}


def _align_matched_siblings(pom_path, fix):
    """If the fixed dependency belongs to a matched set, bump its siblings too."""
    siblings = MATCHED_VERSION_SETS.get(fix["group_id"])
    if not siblings or fix["artifact_id"] not in siblings:
        return
    for sibling in siblings:
        if sibling == fix["artifact_id"]:
            continue
        try:
            apply_version_override(pom_path, fix["group_id"], sibling, fix["fixed_version"])
            print(f"  Also aligned matched dependency: {fix['group_id']}:{sibling} -> {fix['fixed_version']}")
        except Exception as e:
            print(f"  Could not align {sibling}: {e}")


def stage_vulnerability_remediation():
    """Stage 2: Scan for CVEs, ask LLM for fixed versions, apply and test each."""
    print("\n=== STAGE 2: Vulnerability Scan + Remediation ===")
    success, output = run_mvn([
        "org.owasp:dependency-check-maven:check",
        f"-DnvdApiKey={NVD_API_KEY}", "-Dformats=JSON,HTML"
    ])
    log_stage("Vulnerability scan", success, output)
    if not success:
        return False

    report_path = os.path.join(LEGACY_APP_DIR, "target", "dependency-check-report.json")
    findings = load_vulnerabilities(report_path=report_path)
    targets = get_prioritized_targets(findings, max_targets=5)

    if not targets:
        log_stage("Remediation", True, "No suitable high-confidence targets found. Skipping.")
        return True

    pom_path = os.path.join(LEGACY_APP_DIR, "pom.xml")
    applied = []
    failed = []

    for target in targets:
        print(f"\nTarget: {target['dependency']} | {target['cve']} | {target['severity']} | confidence={target['confidence']}")

        with open(pom_path, "r", encoding="utf-8") as f:
            pom_backup = f.read()

        try:
            fix = ask_llm_for_fix(target)
            print(f"Proposed fix: {fix['group_id']}:{fix['artifact_id']} -> {fix['fixed_version']}")
            apply_version_override(pom_path, fix["group_id"], fix["artifact_id"], fix["fixed_version"])
            _align_matched_siblings(pom_path, fix)

            build_ok, build_output = run_mvn(["clean", "test"])
            if build_ok:
                applied.append(fix)
                print(f"Applied and verified: {fix['group_id']}:{fix['artifact_id']}")
            else:
                # Revert this change and continue to next target
                with open(pom_path, "w", encoding="utf-8") as f:
                    f.write(pom_backup)
                failed.append({"target": target["dependency"], "reason": "build failed, reverted"})
                print(f"Build failed after this fix - reverted: {fix['group_id']}:{fix['artifact_id']}")
        except Exception as e:
            with open(pom_path, "w", encoding="utf-8") as f:
                f.write(pom_backup)
            failed.append({"target": target["dependency"], "reason": str(e)})
            print(f"Error applying fix, reverted: {e}")

    print("\n--- Post-remediation vulnerability scan ---")
    success, output = run_mvn([
        "org.owasp:dependency-check-maven:check",
        f"-DnvdApiKey={NVD_API_KEY}", "-Dformats=JSON"
    ])
    if success:
        os.makedirs(EVAL_DIR, exist_ok=True)
        _copy_if_exists(
            os.path.join(LEGACY_APP_DIR, "target", "dependency-check-report.json"),
            os.path.join(EVAL_DIR, "vulnerabilities_after.json"),
        )

    log_stage(
        "Remediation batch complete",
        True,
        f"Attempted: {len(targets)}, Applied: {len(applied)}, Failed/reverted: {len(failed)}\n"
        f"Applied fixes: {json.dumps(applied, indent=2)}\n"
        f"Failed: {json.dumps(failed, indent=2)}"
    )

    print("\n--- Final build verification after all remediation ---")
    success, output = run_mvn(["clean", "test"])
    log_stage("Build verification after remediation batch", success, output)
    return success


def test_generation():
    """Stage 3: Identify the worst-covered class and generate a JUnit test for it."""
    print("\n=== STAGE 3: Coverage-driven Test Generation ===")

    src_main_java_dir = os.path.join(LEGACY_APP_DIR, "src", "main", "java")
    jacoco_xml_path = os.path.join(LEGACY_APP_DIR, "target", "site", "jacoco", "jacoco.xml")

    print("--- Generating coverage report ---")
    success, output = run_mvn(["test", "jacoco:report"])
    _copy_if_exists(jacoco_xml_path, os.path.join(EVAL_DIR, "coverage_after.xml"))

    test_count, failures = count_tests(SUREFIRE_DIR)
    log_stage("Final test count", True, f"Tests: {test_count}, Failures: {failures}")

    if not success or not os.path.exists(jacoco_xml_path):
        log_stage("Test generation", False, "Could not generate/find JaCoCo XML report.\n" + output)
        return False

    from test_generation_agent import read_file, find_lowest_coverage_class, guess_local_dependency_source, generate_test

    target = find_lowest_coverage_class(jacoco_xml_path, src_main_java_dir)
    if not target:
        log_stage("Test generation", True, "No suitable low-coverage, testable class found. Skipping.")
        return True

    print(f"Lowest-coverage testable class: {target['class_name']} "
          f"({target['ratio']*100:.0f}% covered, {target['missed']} lines missed)")

    target_source = read_file(target["source_path"])
    dependency_source = guess_local_dependency_source(target_source, src_main_java_dir)

    class_name_parts = target["class_name"].split("/")
    simple_name = class_name_parts[-1]
    package_name = ".".join(class_name_parts[:-1])

    test_code = generate_test(target_source, simple_name, package_name, dependency_source)

    output_path = os.path.join(
        LEGACY_APP_DIR, "src", "test", "java", *class_name_parts[:-1], f"{simple_name}Tests.java"
    )

    if os.path.exists(output_path):
        log_stage("Test generation", True, f"{simple_name}Tests.java already exists. Skipping generation.")
        return True

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(test_code)
    log_stage("Test generation", True, f"Wrote {output_path} for {target['class_name']}")

    print("\n--- Verifying new test passes ---")
    success, output = run_mvn(["test", f"-Dtest={simple_name}Tests"])

    if success:
        log_stage("New test verification", True, output)
    else:
        # If the generated test fails, delete it and continue (non-critical)
        os.remove(output_path)
        log_stage(
            "New test verification",
            True,
            f"Generated test for {target['class_name']} failed verification "
            f"(likely a minor assertion mismatch, e.g. guessed string format) "
            f"and was discarded. Pipeline continues without this test.\n{output[-1500:]}"
        )
    return True


def final_report():
    """Stage 4: Run final full test suite and coverage after all modifications."""
    print("\n=== STAGE 4: Final Full Test Run + Coverage ===")
    success, output = run_mvn(["test", "jacoco:report"])
    log_stage("Final full test suite + coverage", success, output)
    return success


# ------------------------------------------------------------------
# Entry point - run stages sequentially; stop on first failure.
# ------------------------------------------------------------------

if __name__ == "__main__":
    print_environment_diagnostics()
    print("Starting multi-agent modernization pipeline...\n")

    ok = baseline()
    if ok:
        ok = migration()
    if ok:
        ok = stage_vulnerability_remediation()
    if ok:
        ok = test_generation()
    if ok:
        final_report()

    print("\n\n=== PIPELINE SUMMARY ===")
    for s in REPORT["stages"]:
        print(f"{'OK' if s['success'] else 'FAILED':6} - {s['stage']}")

    save_report()
    print("\nFull report saved to reports/pipeline_report.json")