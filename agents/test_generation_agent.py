import os
import re
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

TARGET_CLASS_PATH = "../legacy-app/src/main/java/org/springframework/samples/petclinic/util/EntityUtils.java"
BASE_ENTITY_PATH = "../legacy-app/src/main/java/org/springframework/samples/petclinic/model/BaseEntity.java"
OUTPUT_TEST_PATH = "../legacy-app/src/test/java/org/springframework/samples/petclinic/util/EntityUtilsTests.java"


def read_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def generate_test(target_source, dependency_source):
    prompt = f"""
You are a test generation agent for a Java Spring project using JUnit 5.

Write a complete, compilable JUnit 5 test class for the class below.
Requirements:
- Package must be: org.springframework.samples.petclinic.util
- Class name must be: EntityUtilsTests
- Cover: the successful lookup case, and the case where the entity is not
  found (should throw ObjectRetrievalFailureException).
- Since BaseEntity and getById() use generics with a real entity type needed
  for testing, create a small local concrete subclass of BaseEntity inside
  the test file (e.g. a private static nested class) to use in the tests.
- Use only JUnit 5 (org.junit.jupiter.api) and plain Java. No Mockito needed.
- Respond with ONLY the raw Java source code for the file. No markdown code
  fences, no explanation before or after.

Class to test:
```java
{target_source}
```

Its dependency (BaseEntity):
```java
{dependency_source}
```
"""
    response = client.chat.completions.create(
        model="anthropic/claude-sonnet-4.5",
        messages=[{"role": "user", "content": prompt}]
    )
    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```(java)?|```$", "", raw, flags=re.MULTILINE).strip()
    return raw


if __name__ == "__main__":
    target_source = read_file(TARGET_CLASS_PATH)
    dependency_source = read_file(BASE_ENTITY_PATH)

    print("Generating test for EntityUtils.java (lowest coverage: 19%)...\n")
    test_code = generate_test(target_source, dependency_source)

    print("--- Generated Test ---\n")
    print(test_code)
    print()

    confirm = input(f"Write this to {OUTPUT_TEST_PATH}? [y/N] ")
    if confirm.lower() == "y":
        os.makedirs(os.path.dirname(OUTPUT_TEST_PATH), exist_ok=True)
        with open(OUTPUT_TEST_PATH, "w", encoding="utf-8") as f:
            f.write(test_code)
        print(f"Test written to {OUTPUT_TEST_PATH}")
    else:
        print("Skipped writing the test.")