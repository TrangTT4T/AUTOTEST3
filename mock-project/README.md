# Swag Labs mock project (ATEST03 Unit 5)

An integrated test-automation project for the demo shop **Swag Labs**
(https://www.saucedemo.com): risk-based strategy, BDD scenarios automated with Playwright,
a container image, a CI pipeline with quality gates, evidence, performance budgets with a
bottleneck analysis, and a written design defense. No cloud account is needed.

| Document | Content |
|---|---|
| [docs/01-strategy.md](docs/01-strategy.md) | scope, risk register, testability, approach, LO mapping |
| [docs/02-architecture.md](docs/02-architecture.md) | layers, scenario life cycle, ADRs, network control, synchronisation |
| [docs/03-findings.md](docs/03-findings.md) | the 13 registered defects with reproduction steps |
| [docs/04-execution-and-evidence.md](docs/04-execution-and-evidence.md) | containers, CI, evidence, performance analysis, cloud mapping |
| [docs/05-defense.md](docs/05-defense.md) | security, reliability, scalability, cost, panel questions |

## Quick start

Requires **Python 3.12**: the version in `.python-version` (PyCharm, VS Code, pyenv and uv pick it up), the same as CI and the Docker image of Units 3–5.

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
playwright install --with-deps chromium
```

```bash
pytest -n 4                                  # every scenario as standard_user, Chromium
pytest -n 4 --persona problem_user           # the same scenarios as a faulty persona
pytest -n 4 -m smoke --browser firefox       # smoke scenarios on Firefox
pytest -n 4 --device "Pixel 7"               # phone emulation
pytest tests/unit --cov                      # framework tests only (no browser)
pytest --collect-only -q --fail-on-uncovered # requirement and finding coverage gate
```

In the container (no local Python or browsers needed):

```bash
docker compose -f docker/compose.yaml build
docker compose -f docker/compose.yaml run --rm tests
SWAGLABS_PERSONA=error_user docker compose -f docker/compose.yaml run --rm tests
```

Results are in `reports/`: `traceability.md`, `perf.md`, `run.json`, JSON logs, failure
evidence and Playwright traces, all fingerprinted in `manifest.json`
(`python -m swaglabs.evidence reports` verifies them).

## Configuration

| Option | Environment variable | Default |
|---|---|---|
| `--persona` | `SWAGLABS_PERSONA` | `standard_user` |
| `--ui-timeout` (ms) | `SWAGLABS_UI_TIMEOUT_MS` | `10000` |
| `--base-url` | `SWAGLABS_BASE_URL` | `https://www.saucedemo.com` |
| — | `SWAGLABS_PASSWORD` | the public demo password shown on the login page |
| `--browser`, `--device`, `--headed`, `--tracing` … | — | pytest-playwright's options |

## Layout

```
features/            Gherkin: 9 feature files, 46 scenarios/examples, tagged @REQ-SL-xx @risk-* @smoke|@regression @area-*
tests/steps/         step definitions (talk only to the SwagLabs facade)
tests/test_scenarios.py   binds every feature file
tests/unit/          framework tests: domain, rules, reports, plugins (pytester), architecture
swaglabs/            the framework
  domain.py          Money, Catalogue, Cart, OrderSummary, SortOrder (oracles)
  app.py             SwagLabs facade, PerfRecorder
  pages/             page objects - selectors at the bottom of each class
  network.py         allow-list, request timings, console errors, dialogs
  waiting.py         eventually(): retry a read with back-off
  perf.py            budgets, percentiles, network/client split
  evidence.py        JSON logs with masking, run record, SHA-256 manifest
  requirements.py, findings.py, traceability.py, matrix.py
  plugins/           pytest glue: registry, findings, browser, reporting
requirements.toml    requirement registry (id, title, risk)
findings.toml        defects per persona and area -> strict expected failures
perf-budgets.toml    response-time budgets (ms)
docker/              Dockerfile (pinned Playwright image), compose.yaml
```

The CI pipeline is `../.github/workflows/mock-project.yml`.

## Rules of the house

- A scenario needs a requirement, exactly one risk tag equal to the registry's, and exactly one
  of `@smoke`/`@regression`; areas must be declared. Broken rules stop the run at collection.
- Selectors live in the `# --- Locators ---` section at the bottom of each page class.
- Steps never touch Playwright; no fixed sleeps; no password in features or docs.
- A defect is registered once (`findings.toml`) and documented once (`docs/03-findings.md`);
  tests fail if either is missing.
- Never put load on Swag Labs: it is someone else's system.
