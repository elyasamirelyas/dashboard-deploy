# Modernization of Legacy Java Applications

MSc Project — Information Technology, IT Project 3154658A, University of Glasgow (2025).

A multi-agent LLM pipeline that automates the modernization of legacy Java/Spring Boot applications: framework migration, vulnerability remediation, and test generation, with build-verification gates between every stage and automatic rollback on failure.

## What the pipeline does

Given a target Spring Boot application, the pipeline runs through the following stages end-to-end:

1. **Baseline capture** — runs a dependency-check vulnerability scan and the existing test suite to record the "before" state.
2. **Migration** — upgrades the app via [OpenRewrite](https://docs.openrewrite.org/) (Spring Boot 2 → 3 / Java 8 → 17), followed by a small set of generic and project-specific fixes for issues OpenRewrite doesn't catch, then a build-verification gate.
3. **Vulnerability remediation** — an LLM agent reads the dependency-check scan, prioritizes vulnerable dependencies by severity and fix confidence, proposes and applies version overrides, and verifies the build (and full test suite) still passes before keeping each fix. Failed fixes are automatically rolled back.
4. **Test generation** — a coverage-driven agent parses JaCoCo XML reports, ranks under-covered classes, and generates new JUnit 5 tests via an LLM. Generated tests are discarded if they don't pass verification (the same verify-before-commit pattern used across all agents).
5. **Final verification** — full test suite + coverage run, results written out for evaluation.

Results for each run go into `evaluation/<app_id>/` (vulnerability scans, coverage XML) and a stage-by-stage JSON report is written to `agents/reports/pipeline_report_<app_id>.json`.

## Repository structure

```
agents/                  Pipeline source (Python)
  orchestrator.py         Runs the full pipeline end-to-end against one target app
  remediation_agent.py    Vulnerability remediation agent
  test_generation_agent.py  Coverage-driven test generation agent
  run_batch.py             Clones and runs the pipeline across a batch of target apps
  verify_apps.py           Checks each app's pipeline report for dissertation-evidence-clean status
  generate_evaluation_report.py  Builds a markdown before/after summary from scan + report data
  app.py                   Flask backend for the web dashboard
  reports/                 Per-app pipeline_report_<id>.json snapshots
  templates/                Dashboard HTML

target-apps/              Cloned target applications used for the multi-app validation round
legacy-app/                Reference target application: spring-petclinic-rest
legacy-app-baseline/       Untouched baseline copy of legacy-app, kept for comparison
legacy-app-fresh-run/      Clean re-run of the pipeline against an untouched baseline clone
legacy-app-demo-run/       Run used for the dashboard demo

evaluation/                Before/after vulnerability scans, coverage reports, and evaluation summaries per app
  reference-run/            The reference evaluation run (legacy-app) used as dissertation evidence

dev-history/               Archived scratch scripts / notes from development
docs/                       (reserved for project documentation)
```

## Setup

Requires Java (Maven-based target apps), Python 3.11+, and an OpenAI/LLM API key.

```
cd agents
python -m venv venv          # if not already created
venv\Scripts\activate         # Windows
pip install -r requirements.txt   # see note below
```

> Note: this repo doesn't yet have a pinned `requirements.txt` — dependencies were installed directly into `agents/venv`. Worth generating one (`pip freeze > requirements.txt` from inside the activated venv) before submission so the environment is reproducible.

Create a `.env` file inside `agents/` with:

```
NVD_API_KEY=<your NVD API key>
```

(An `OPENAI_API_KEY` or equivalent LLM credential is also required by the agents — check `orchestrator.py` / `remediation_agent.py` for the exact variable name expected.)

## Usage

Run the full pipeline against the default reference app (`legacy-app`):

```
python orchestrator.py
```

Run against a specific target app:

```
python orchestrator.py ../target-apps/app7-h2crud
```

or via environment variable:

```
set TARGET_APP_DIR=../target-apps/app7-h2crud
python orchestrator.py
```

Run the pipeline across the full batch of target apps (app7–app13):

```
python run_batch.py
```

Check which apps have a clean, dissertation-evidence-ready pipeline run:

```
python verify_apps.py
```

Generate a markdown before/after evaluation summary:

```
python generate_evaluation_report.py
```

Launch the results dashboard:

```
python app.py
```

## Evaluation results

### Reference run — `legacy-app` (spring-petclinic-rest)

**Vulnerability remediation**

| Metric | Before | After |
|---|---|---|
| Vulnerable dependencies | 13 | 12 |
| Total CVEs | 203 | 136 |
| Critical severity | 30 | 27 |
| High severity | 63 | 45 |
| Medium severity | 93 | 52 |
| Low severity | 17 | 12 |

**Test suite**

| Metric | Before | After |
|---|---|---|
| Total tests | 171 | 171 |
| Failing tests | 0 | 0 |

**Code coverage (JaCoCo)**

| Metric | Before | After |
|---|---|---|
| Line coverage | 88.4% (1273/1440) | 88.4% (1253/1417) |
| Branch coverage | 71.1% (270/380) | 70.9% (265/374) |
| Instruction coverage | 88.9% (5308/5969) | 89.0% (5117/5751) |

### Multi-app validation round

The pipeline was additionally run against seven public GitHub tutorial Spring Boot apps (`app7`–`app13`) to test generalization beyond the reference app, with per-app before/after vulnerability scans and coverage reports in `evaluation/`. Baseline-only scans are also recorded for `app2` (spring-petclinic), `app3` (bank application backend), and `app4` (Contrast Security's intentionally vulnerable Spring Boot app).

## Roadmap

Known gaps and next steps, based on the current state of the repo:

- Pin dependencies with a `requirements.txt` (currently installed ad hoc into `agents/venv`).
- Run `app2` (spring-petclinic), `app3` (bank application backend), and `app4` (Contrast Security vulnerable app) through the full pipeline — currently only baseline vulnerability scans exist for these; no migration/remediation/test-generation pass has been recorded yet.
- Populate `docs/` with project documentation (currently empty).
- Write up final dissertation evidence from the multi-app validation round.

## Status

Actively developed as part of an ongoing MSc dissertation. See `dev-history` in the git log for the full development timeline from initial baseline scan (2026-07-18) through the multi-app generalization round (2026-08-16/17).

## Support

This is a solo MSc dissertation project. For questions about the project, contact the author directly at `3154658a@student.gla.ac.uk`, or open an issue on the [GitLab repo](https://stgit.dcs.gla.ac.uk/msc-project-for-information-technology/2025/it-project-3154658a/modernization-of-legacy-java-applications/-/issues).

## Contributing

This repository is submitted coursework for an individual MSc dissertation and is not open for external contributions. If you're the module supervisor or a marker reviewing this work, see the `dev-history` git log for the full development timeline, and `evaluation/` for the underlying before/after data behind the results reported above.

## Authors and acknowledgment

**Elyas Amiri** — `3154658a@student.gla.ac.uk`
MSc Information Technology, University of Glasgow — IT Project 3154658A (2025)

## License

This is an academic dissertation project submitted to the University of Glasgow; no open-source license has been applied. Usage and distribution are subject to the University's academic policies on student work. If you'd like the code released under an open-source license (e.g. MIT, Apache 2.0), add a `LICENSE` file and note it here — check with your supervisor first, since IP terms for dissertation code can be governed by university policy.

