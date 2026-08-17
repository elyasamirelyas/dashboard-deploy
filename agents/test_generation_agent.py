# test_generation_agent.py - the "write a test for the worst-covered
# class" part of the pipeline. Reads the JaCoCo coverage report to find
# a good target, pulls in its source (and its superclass, if it has one),
# and asks the LLM to write a JUnit 5 test for it.

import os
import re
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

# Classes with any of these annotations need a Spring context to run.
# We skip them because they're not suitable for plain JUnit unit tests.
SPRING_STEREOTYPES = [
    "@RestController", "@Controller", "@Service", "@Repository",
    "@Configuration", "@Aspect", "@Component", "@SpringBootApplication"
]


def read_file(path):
    """Simple file reader - just returns the contents as a string."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def find_lowest_coverage_class(jacoco_xml_path, src_main_java_dir):
    """
    Find the class with the worst line coverage that we can safely test.
    
    We skip:
      - Inner/anonymous classes (hard to test in isolation)
      - Classes with Spring stereotypes (need a live context)
      - Classes with zero lines (not useful)
      - Classes where the source file doesn't exist (shouldn't happen)
    
    Returns None if no suitable candidate is found.
    """
    tree = ET.parse(jacoco_xml_path)
    root = tree.getroot()

    candidates = []
    for package in root.findall("package"):
        for cls in package.findall("class"):
            class_name = cls.get("name")  # e.g. org/springframework/.../EntityUtils
            
            # Skip inner classes - they're usually tied to their parent
            if "$" in class_name:
                continue

            # Find the LINE counter for this class
            line_counter = None
            for counter in cls.findall("counter"):
                if counter.get("type") == "LINE":
                    line_counter = counter
                    break
            if line_counter is None:
                continue

            missed = int(line_counter.get("missed"))
            covered = int(line_counter.get("covered"))
            total = missed + covered
            if total == 0:
                continue

            ratio = covered / total
            
            # Check if source file exists
            source_path = os.path.join(src_main_java_dir, class_name + ".java")
            if not os.path.exists(source_path):
                continue

            # Check for Spring annotations - skip if it needs a context
            source = read_file(source_path)
            if any(stereo in source for stereo in SPRING_STEREOTYPES):
                continue

            candidates.append({
                "class_name": class_name,
                "ratio": ratio,
                "missed": missed,
                "total": total,
                "source_path": source_path,
            })

    if not candidates:
        return None

    # Sort by worst coverage first. If tie, pick the one with more missed lines
    # (bigger potential coverage gain).
    candidates.sort(key=lambda c: (c["ratio"], -c["missed"]))
    return candidates[0]


def guess_local_dependency_source(target_source, src_main_java_dir):
    """
    Try to find the source of a superclass the target class extends.
    
    This is best-effort - we look for "class X extends Y" and try to find
    Y.java in the project. If found, we return it; otherwise None.
    
    TODO: This only handles direct superclasses, not interfaces or generics.
    Might need to extend this if we see weird inheritance patterns.
    """
    match = re.search(r"class\s+\w+\s+extends\s+(\w+)", target_source)
    if not match:
        return None
    superclass_name = match.group(1)

    # Walk the source directory looking for the superclass file
    for root, _, files in os.walk(src_main_java_dir):
        for f in files:
            if f == f"{superclass_name}.java":
                return read_file(os.path.join(root, f))
    return None


def generate_test(target_source, target_class_simple_name, target_package, dependency_source=None):
    """
    Generate a JUnit 5 test class using the LLM.
    
    Returns the raw Java source code as a string (without markdown fences).
    
    The prompt is quite detailed because early versions of this produced
    tests that used Mockito or tried to spin up Spring contexts - both
    of which we don't want for this pipeline.
    """
    dep_block = f"\nIts likely dependency (for context):\n```java\n{dependency_source}\n```\n" if dependency_source else ""

    prompt = f"""
You are a test generation agent for a Java Spring project using JUnit 5.

Write a complete, compilable JUnit 5 test class for the class below.
Requirements:
- Package must be: {target_package}
- Class name must be: {target_class_simple_name}Tests
- Cover the main logic paths, including at least one success case and one
  edge/error case if applicable.
- If the class or its dependency uses generics or is abstract in a way that
  requires a concrete type for testing, create a small local concrete
  subclass inside the test file (e.g. a private static nested class).
- Use only JUnit 5 (org.junit.jupiter.api) and plain Java. No Mockito, no
  Spring context, no @SpringBootTest - this must run as a plain unit test.
- Respond with ONLY the raw Java source code for the file. No markdown code
  fences, no explanation before or after.

Class to test:
```java
{target_source}
```
{dep_block}
"""
    from llm_cache import cached_chat_completion
    raw = cached_chat_completion(
        client, "anthropic/claude-sonnet-4.5", [{"role": "user", "content": prompt}]
    ).strip()
    raw = re.sub(r"^```(java)?|```$", "", raw, flags=re.MULTILINE).strip()
    return raw