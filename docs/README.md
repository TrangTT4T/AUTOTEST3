# Course guides — ATEST03 (Fast Track)

One guide per day. Every guide climbs from 🟢 Foundation through 🟡 Practitioner to
🔴 Senior, and ends with a self-check (answers hidden) and, for labs, a verification log
that says what was really run and what was not.

| Unit | Days | Learning outcomes | Guides |
|---|---|---|---|
| 1 — BDD automation design and framework practices | 1–4 | LO1, LO2 | [Day 1](unit1/Day1.md) · [Day 2](unit1/Day2.md) · [Day 3](unit1/Day3.md) · [Day 4](unit1/Day4.md) |
| 2 — Playwright end-to-end automation | 5–8 | LO3 | [Day 5](unit2/Day5.md) · [Day 6](unit2/Day6.md) · [Day 7](unit2/Day7.md) · [Day 8](unit2/Day8.md) |
| 3 — Mobile (Appium) and asynchronous systems | 9–12 | LO5, LO6 | [Day 9](unit3/Day9.md) · [Day 10](unit3/Day10.md) · [Day 11](unit3/Day11.md) · [Day 12](unit3/Day12.md) |
| 4 — AWS cloud execution, performance, CI/CD | 13–18 | LO7, LO8, LO9 | [Day 13](unit4/Day13.md) · [Day 14](unit4/Day14.md) · [Day 15](unit4/Day15.md) · [Day 16](unit4/Day16.md) · [Day 17](unit4/Day17.md) · [Day 18](unit4/Day18.md) |
| 5 — Mock project design and implementation (no AWS) | 19–22 | LO1–LO9 | [Day 19](unit5/Day19.md) · [Day 20](unit5/Day20.md) · [Day 21](unit5/Day21.md) · [Day 22](unit5/Day22.md) — code: [`mock-project/`](../mock-project/README.md) |

## Reading code excerpts

The repository root holds the **final** code (after Day 18). A guide quotes the code **as it was
that day**; later days improve it on purpose, and each change is explained where it happens.

| Excerpt in | Changed later in | What changed and why |
|---|---|---|
| Day 3: steps with `parsers.parse("…{name}…")` | Day 4 | Greedy placeholders made steps ambiguous: `{name:Quoted}` and `parsed()` |
| Day 3: `store` fixture builds `FakeStore.from_snapshot()` | Day 11 | The snapshot depends on the platform (web or app catalogue) |
| Day 7: e2e tests skipped offline | Day 11 | Platform selection deselects instead of skipping (NOT RUN is not MANUAL) |
| Day 11: platform selection inside the mobile plugin | Day 12 | Moved to `framework/plugins/selection.py`, a pure function |

Excerpts that describe the final design (for example the Locators sections of page and screen
objects) match the root code line for line. Test counts in verification logs are those of the day.

## Engineering standards the repository enforces

| Standard | Enforced by |
|---|---|
| Lint, format, strict types; security, exception-handling, complexity, and `assert`-free framework code | `ruff` (rule families in `pyproject.toml`), `mypy --strict` |
| Selectors declared at the bottom of every page, component, and screen class | Architecture tests (`tests/unit/test_architecture.py`) |
| Layer rules: steps use the port only; lookups only in page and screen objects; no fixed sleeps; the sandbox is a black box | Architecture tests |
| Every requirement has a scenario; outcomes reported as PASS / FAIL / KNOWN DEFECT / BLOCKED / MANUAL / NOT RUN | `--fail-on-uncovered`, the traceability matrix |
| ≥ 90 % code coverage of the offline-reachable framework (a ratchet) | `pytest --cov` (`[tool.coverage]`) |
| Known defects are strict, registered tripwires that fail when the defect disappears | `xfail(strict=True, raises=AssertionError)`, `framework/events/findings.py` |
| Defect tests pass on the fixed build (oracle validation) | `--sandbox-build fixed` in CI |
| Cloud configuration and workflows: no high-severity findings | `cfn-lint`, `actionlint` + shellcheck, `python -m framework.cloud.audit` |
| Performance objectives, failing closed on missing evidence; judged on the steady state | `python -m framework.perf.gate` (`[steady_state.*]` in `perf/sla.toml`) |
| The load-profile script implements the planned load profile (ISTQB CT-PT 4.2.7) | `tests/unit/test_jmeter_plans.py` against `perf/workload.toml` |
| JMeter plans: bounded, property-driven, every request asserted, explicit timeouts, polite to third-party sites (with a setUp guard); results format pinned | `tests/unit/test_jmeter_plans.py`, `-q perf/jmeter.properties` |
| Playwright: one place for page and `expect` timeouts, aligned with `--ui-timeout` | `configure_page`, `_expect_timeout`, an architecture test |
| A hung test fails on its own (90 s per test) instead of stalling CI; no retries; `.env` files never committed | `pytest-timeout` (`timeout` in `pyproject.toml`), `.gitignore` |
| UI checks use web-first, auto-retrying assertions (`expect(...)`), never `assert` on a one-off page read | Architecture tests (`test_ui_checks_use_web_first_assertions`, and the mock project's steps rule) |
| Every skip and xfail says why; an xfail is strict and names `raises=`; no imperative `pytest.xfail()` (Python has no `test.fixme`: a known bug is a strict xfail, never a skip) | `test_every_skip_and_xfail_says_why` in both projects, `xfail_strict = true` |
| `reports/` holds one run's evidence only: the controller removes the suite's outputs of an earlier run once, before any xdist worker starts (a global setup; pytest-playwright's per-worker clean-up is switched off) | `reset_run_outputs` / `reset_folder`, `tests/unit/test_run_outputs.py`, the mock project's `test_reports_hold_exactly_one_run` |
| One locator means one element: no `.first` to pick among several matches (strict mode reports duplicates); a cart line is changed only when it is the product's only line, in every adapter alike | `CartRows.the_only_one`, `AmbiguousTargetError` (never an `AssertionError`), `test_set_quantity_needs_exactly_one_line`, `test_a_cart_line_is_addressed_only_when_it_is_unique` |
| Reporting: a human view (terminal, job summary from `traceability.md`) and machine views (`traceability.json`, `junit.xml`); artifacts uploaded with `if: !cancelled()` (also for green runs) and a retention of 14 days (30 for the merged matrix); trace and screenshot on failure only, no video | `addopts` in `pyproject.toml`, the workflows, `framework.cloud.audit` |
| Page objects: one class per file; its selectors in a `# --- Locators ---` section at the bottom of the class, never at module level or inline | Architecture tests in both projects |
| A failed scenario's trace is readable: every Gherkin step is a named group of its browser actions (Playwright's `test.step`) | `plugins/trace_steps.py` in both projects, `tests/unit/test_trace_steps.py` |
