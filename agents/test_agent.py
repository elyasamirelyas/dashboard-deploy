import os
from dotenv import load_dotenv
from openai import OpenAI

# Load the API key from .env
load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

# The real CVE we found in our baseline scan
cve_description = """
Vulnerability: CVE-2026-54512
Library: jackson-databind 2.13.1
Severity: HIGH (CVSS 8.1)
Description: jackson-databind's PolymorphicTypeValidator (PTV) can be bypassed
when a type identifier contains generic parameters. An attacker can place a
denied class as a generic type parameter of an allowed container, bypassing
the allow-list and enabling deserialization of attacker-controlled classes.
Fixed in versions 2.18.8, 2.21.4, and 3.1.4.
"""

prompt = f"""
You are a security remediation agent for a Java Maven project.
Given the following vulnerability, suggest the exact change needed to fix it
in the project's pom.xml, and briefly explain why it works.

{cve_description}
"""

response = client.chat.completions.create(
    model="anthropic/claude-sonnet-4.5",
    messages=[{"role": "user", "content": prompt}]
)

print(response.choices[0].message.content)