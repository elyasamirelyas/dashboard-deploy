import json

with open("../legacy-app/target/dependency-check-report.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for dep in data["dependencies"]:
    if dep.get("vulnerabilities") and dep.get("fileName", "").startswith("hsqldb"):
        print(json.dumps(dep["vulnerabilityIds"], indent=2))
        break