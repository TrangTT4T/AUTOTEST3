# Architecture — Swag Labs mock project

## Layers

```
features/*.feature            WHAT is tested, in business language (Gherkin + tags)
        │  bound by tests/test_scenarios.py (scenarios("."))
tests/steps/*_steps.py        HOW a sentence maps to actions - talks only to SwagLabs
        │
swaglabs/app.py  SwagLabs     one facade: page objects, session/cart shortcuts, timing, waiting
        │
swaglabs/pages/*.py           one class per page: selectors at the BOTTOM, methods return domain values
        │
Playwright (browser)          driven only from pages/ and app.py

swaglabs/domain.py            Money, Catalogue, Cart, OrderSummary, SortOrder  (the oracles)
swaglabs/{requirements,findings,traceability,perf,evidence,waiting,matrix}.py
                              pure logic, no pytest, no browser - unit-tested to ≥ 90 % branches
swaglabs/plugins/*.py         thin pytest glue: registry, findings, browser, reporting
```

Rules that keep the layers honest are **tests**, not conventions (`tests/unit/test_architecture.py`):
selectors live in the `# --- Locators ---` section at the bottom of each page class and are never
written inline; steps never import Playwright or touch `.page`; nobody sleeps for a fixed time
(except the retry helper's back-off and the slider's sampling cadence); no password in feature
files or docs.

## A scenario's life

1. **Collection.** `registry` loads `requirements.toml` and `findings.toml`, registers every
   `REQ-*` and `area-*` tag as a marker, and checks the tag rules of every scenario (requirement
   exists, risk tag matches the registry, exactly one of smoke/regression, areas known). A broken
   rule stops the run before any browser starts.
2. **Persona rules.** `findings` deselects `@persona-independent` scenarios unless the persona is
   `standard_user`, and marks every scenario whose areas match a finding for this persona as
   `xfail(strict=True, raises=AssertionError)` plus `known_defect(<id>)`.
3. **Set-up.** pytest-playwright gives a **fresh browser context** per test (own cookies, own
   localStorage); `browser.shop` attaches the network monitor and the performance recorder.
4. **Steps run.** `pytest_bdd_before_step` logs each step (JSON lines, secrets masked). A failing
   step triggers `pytest_bdd_step_error`: screenshot, page HTML, URL, console errors, dialogs and
   blocked hosts are saved under `reports/evidence/<test>/`; Playwright keeps the trace.
5. **Teardown.** The test's measurements travel to the xdist controller inside the report.
6. **Session end** (controller only). `reporting` writes the traceability matrix (md + json),
   timings (`perf.md`, `perf.json`), the run record (`run.json`), and **last** the manifest with
   the SHA-256 of every file.

## Architecture decision records

### ADR-1 BDD with pytest-bdd on top of Playwright, not plain Playwright tests
*Context:* the course requires traceable, reviewable specifications. *Decision:* Gherkin features
with tags that carry requirement, risk, suite and area. *Consequences:* product people can read
and review scenarios; tags drive selection, expected failures and the traceability matrix.
Cost: a step layer to maintain — kept small by talking to one facade.

### ADR-2 Personas as a run dimension (`--persona`), not as scenario parameters
*Context:* six accounts, same shop, different faults. Writing every scenario as an outline over
personas would multiply each scenario's examples and mix "what must work" with "what is broken
for whom". *Decision:* one persona per run; the findings register decides expectations.
*Consequences:* scenarios stay about behaviour; the CI matrix runs personas in parallel; the
merged quality matrix shows requirement × persona.

### ADR-3 Strict expected failures with `raises=AssertionError`
*Alternatives:* skip known defects (hides them), let them fail (the build is always red, people
stop looking), non-strict xfail (a fix goes unnoticed). *Decision:* strict, and only an
`AssertionError` counts as the expected failure. *Consequences:* a fix turns the run red until
the register is updated; a timeout or a bug in our own code is still a failure.

### ADR-4 Arrange through state, act through the UI
*Context:* logging in through the form in every scenario costs time and couples unrelated
scenarios to the login page (and to performance_glitch_user's 5-second login). *Decision:*
scenarios that are not about logging in set the session cookie; cart scenarios seed
`localStorage`. The behaviour under test is always driven through the UI. *Guard:* the contract
scenario *The quick-login shortcut creates the same session as the login form*.

### ADR-5 A reference catalogue as the oracle
*Context:* no API. Comparing the page with itself proves nothing. *Decision:* a recorded
catalogue (`swaglabs/data/catalogue.json`) and computed expectations (sort orders, 8 % tax with
`Decimal` half-up rounding). *Consequence:* a legitimate catalogue change needs one data-file
update, reviewed like code.

### ADR-6 Container image based on Microsoft's Playwright image, pinned by digest
*Decision:* `mcr.microsoft.com/playwright/python:v1.63.0-noble@sha256:…`, `pip install` of the
pinned requirements, non-root `pwuser`, read-only root file system at run time. *Why:* the
browsers and their system libraries match `playwright==1.63.0` exactly; a digest cannot move.

### ADR-7 GitHub Actions instead of a cloud test grid
*Context:* the course's reference design uses AWS (ECS/Fargate, Device Farm, S3, CloudWatch);
this project must not depend on AWS. *Decision:* a GitHub Actions matrix of containers;
artifacts with retention as the evidence store; JSON logs, run records and timing reports as
telemetry. The mapping is in [04-execution-and-evidence.md](04-execution-and-evidence.md#cloud-mapping).

## Network control

`swaglabs/network.py` attaches to every browser context:

- **Allow-list.** Only `www.saucedemo.com` and Google Fonts are reachable. Everything else is
  aborted and counted — today that is the shop's error tracker (`*.backtrace.io`). Reasons: our
  fault personas would flood a vendor's tracker with deliberate errors; a slow third party would
  make our timings flaky; and a test must not depend on services outside its scope.
- **Telemetry.** Start and end of every request feed the network-busy time of each timed
  interaction.
- **Dialogs.** An unexpected `alert()` is recorded and dismissed, so the page never hangs; the
  step decides whether it is a failure.
- **Console errors** (except our own blocked requests) go into the failure evidence.

## Synchronisation patterns (LO5, LO6)

| Situation | Pattern | Where |
|---|---|---|
| Element appears/changes | `expect(...)` auto-retrying assertions | page objects |
| A page replaced in a single-page app | wait for an element that only the NEW page has | `ProductPage.wait_until_loaded` |
| State that is not on screen (storage, cookies) | `eventually(probe, predicate)` with back-off, last value in the failure | `swaglabs/waiting.py`, `SwagLabs.eventually` |
| Two sources of truth (badge vs storage) | wait until they agree | *the cart badge agrees with the stored cart* |
| Content that keeps changing (slider) | record a history in the page (MutationObserver), assert on the history; read related values in ONE evaluate call | `SliderCatalogPage` |
| Content that loads when visible (lazy tiles) | scroll like a reader, one screen at a time; check tile-number continuity (no duplicates, no gaps) | lazy-load scenario |
| Input that may be dropped | type, then verify the field holds the value (short timeout) | `BasePage.fill_verified` |
| Retrying | retry READS, never actions (a retried click can act twice) — the one exception is scrolling, which is idempotent | `eventually` |
