# ATEST03 — Advanced Automation Test Engineering (Fast Track): course guides and code

Learning guides (one per day, newbie → senior) and the project built through the course, in Python.

| Unit | Days | Topic | Guides |
|---|---|---|---|
| 1 | 1–4 | BDD automation design and framework practices | [docs/unit1](docs/unit1) — index: [docs/README.md](docs/README.md) |
| 2 | 5–8 | Playwright end-to-end automation | [docs/unit2](docs/unit2) |
| 3 | 9–12 | Mobile (Appium) and asynchronous-system testing | [docs/unit3](docs/unit3) |
| 4 | 13–18 | AWS cloud execution, performance (JMeter), and CI/CD | [docs/unit4](docs/unit4) |
| 5 | 19–22 | Mock project: Swag Labs, end to end, without AWS | [docs/unit5](docs/unit5) — code: [mock-project/](mock-project/README.md) |

The code at the root of this repository is the **final state** after Unit 4: it contains every
earlier day's work. Unit 5's mock project is a separate, self-contained project in
[`mock-project/`](mock-project/README.md) (own dependencies, image and workflow
`.github/workflows/mock-project.yml`). The guides mention per-day packages such as `Unit2/day7-code/shop-bdd.zip`;
in this repository, all of them are this one project.

Systems used: the Shopify demo store `sauce-demo.myshopify.com` (web), Sauce Labs My Demo App
(Android), a local order-events sandbox (`sandbox/`), BlazeDemo for light load tests only, and
Swag Labs (`www.saucedemo.com`, Unit 5 — single-user timings only, never load).

---

# shop-bdd — BDD automation for sauce-demo.myshopify.com

Executable specifications (Gherkin + pytest-bdd) for a Shopify demo store, run either
in a real browser (Playwright) or fully offline against a recorded catalogue — plus the
mobile app (Appium, Unit 3 Day 11), an asynchronous order-events system (Unit 3 Day 12), and
container, performance, cloud, and CI/CD work (Unit 4). This one project is the code of Units 1–4.

## Quick start

```bash
python -m venv .venv
```

```bash
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

```bash
pip install -r requirements-dev.txt
```

```bash
playwright install chromium
```

| Goal | Command |
|---|---|
| Everything local, in parallel: unit tests, offline BDD, events sandbox | `pytest --store fake -n auto` |
| Asynchronous-system tests only (local sandbox) | `pytest --store fake tests/events tests/test_order_events.py` |
| The same against the fixed sandbox build (all must pass) | `... --sandbox-build fixed` |
| Smoke on the live store | `pytest tests/test_*.py -m smoke` |
| Page-object tests (live) | `pytest tests/pages` |
| End-to-end workflows, priority 1 (live) | `pytest tests/e2e -m p1` |
| All end-to-end workflows (live) | `pytest tests/e2e` |
| A workflow with a full trace | `pytest tests/e2e -m p1 --tracing on` then `playwright show-trace reports/artifacts/<test>/trace.zip` |
| Everything automated, live (serial) | `pytest tests/test_*.py -m "not manual"` |
| One requirement | `pytest -m REQ-05` |
| Watch the browser | `pytest -m smoke --headed --slowmo 300` |
| Fail if a requirement has no scenario | `pytest --store fake --fail-on-uncovered` |
| Code coverage gate (≥ 90 % of offline-reachable code; see `[tool.coverage]`) | `pytest --store fake -n auto --cov` |
| Mobile: BDD `@mobile` scenarios + `tests/mobile` (needs Appium and a device) | `pytest --store mobile` |
| Container: build, then run the offline suite read-only | `docker build -f docker/Dockerfile -t shop-bdd-tests:local .` then see "Unit 4" below |
| Performance: local sandbox load + SLA gate | see "Unit 4" below (JMeter 5.6.3, Java 17+) |
| Cloud configuration audit (policy as code) | `python -m framework.cloud.audit cloud .github/workflows --fail-on high` |
| Quality gate (as CI) | `ruff check . && ruff format --check . && mypy && python -m framework.review --strict` |
| BDD review report (step usage, ambiguity, smells) | `python -m framework.review` → `reports/bdd-review.md` |
| Architecture fitness tests | `pytest tests/unit/test_architecture.py` |

Options also read environment variables: `SHOP_STORE=fake`, `SHOP_UI_TIMEOUT_MS=20000`,
`SHOP_SANDBOX_BUILD=fixed`, `SHOP_SANDBOX_URL=http://127.0.0.1:8765`.

## Architecture

```
features/*.feature            WHAT: business behaviour, tagged with requirement + risk
        │
tests/steps/*.py              GLUE: thin, typed steps; call the Store port only
        │
framework/ports.py            Store protocol  ◀── the only API steps may use
        │
        ├── framework/adapters/fake.py          in-memory, fed by tests/data/catalogue_snapshot.json
        └── framework/adapters/web/
              store.py        orchestration + cross-layer consistency check
              api.py          shop JSON endpoints, called inside the page (same cookies)
              guard.py        bot-check / outage detection
              diagnostics.py  console errors + failed shop requests, kept for failures
              shop.py         Shop facade: one entry point to every page object (+ API)
              components/     header, main menu, mini-cart, product grid, breadcrumb
              pages/          page objects: the ONLY place with selectors and waits
        │
framework/domain.py           Money, Catalogue, Product, Cart, OrderSummary, ...: immutable typed values
framework/testdata.py         builders: unique_email(), new_customer()
framework/plugins/            pytest plugins: fixtures, tag rules, evidence, traceability
requirements.toml             requirement registry: ids, titles, risk (single source of truth)
```

### Layer rules (checked in review)

1. Feature files contain no selectors, URLs, or clicks.
2. Steps call only `Store` methods and assert on domain objects. No Playwright imports.
3. Selectors and waits live only in `framework/adapters/web/pages/`.
4. Every wait waits for proof (a server response, a URL, a visible element). No `sleep`.
5. Money is `Money` (Decimal). Never float.
6. Volatile data (prices, sold-out products) is read at runtime, never hard-coded.
7. Logic in plugins lives in pure functions (`framework/requirements.py`,
   `framework/traceability.py`, `framework/review.py`) with unit tests; hooks only adapt.
8. Step patterns are built with `parsed(...)` and every quoted placeholder is typed
   `"{x:Quoted}"` (`framework/step_types.py`). A plain `"{x}"` also matches text containing
   quotes, which makes two definitions match one Gherkin line; pytest-bdd then picks one
   silently.

Rules 2, 3, and 4 are enforced by `tests/unit/test_architecture.py`; rule 8 and the Gherkin
rules by `python -m framework.review --strict`.

## Page-object library (for plain Playwright tests)

`Shop` gives every page object; the `shop` fixture provides one per test
(fresh browser context, live catalogue loaded once per run):

```python
def test_catalogue_labels_sold_out_products(shop: Shop) -> None:
    cards = shop.catalog().open().products()
    assert {c.name for c in cards if c.sold_out} == {i.name for i in shop.catalogue.sold_out()}
```

| `shop.` | Page object | Main methods |
|---|---|---|
| `home()` | `HomePage` | `open()`, `featured_products()` |
| `catalog()` | `CatalogPage` | `open()`, `products()`, `open_product(name)` |
| `open_product(name)` / `product()` | `ProductPage` | `read()`, `option_names()`, `select_variant(v)`, `add_to_cart(n)`, `is_sold_out()` |
| `cart()` | `CartPage` | `open()`, `read()`, `is_empty()`, `set_quantity()`, `remove_all()`, `continue_shopping()`, `check_out()` |
| `mini_cart()` | `MiniCart` | `open()`, `read()`, `remove(name)` |
| `search()` | `SearchResultsPage` | `open_for(keyword)`, `results()`, `titles()`, `has_no_results()` |
| `checkout()` | `CheckoutPage` | `wait_until_loaded()`, `order_summary()` (read-only) |
| `content()` | `ContentPage` | `open_page(handle)`, `heading_text()` |
| `blog()` / `article()` | `BlogPage` / `ArticlePage` | `article_list()`, `open_article(title)`, `heading_text()`, `author()` |
| `login()` | `LoginPage` | `fill_credentials()`, `sign_in()`, `errors()`, `show_password_recovery()` |
| `register()` | `RegisterPage` | `fill_form(customer)`, `register(customer)` |
| `not_found()` | `NotFoundPage` | `open_missing(path)`, `is_shown()` |
| `api` | `StoreApi` | `add_lines(...)`, `cart()` — fast setup and data-layer checks |

Every page object also has `header` (search, cart count, account links),
`menu` (main menu), `breadcrumb`, `last_status` (HTTP status of the last
`open`), and `page_title()`.

**Never exercised against the public demo shop:** `LoginPage.sign_in` with real
accounts, `request_password_reset`, and `RegisterPage.register` (CAPTCHA, real
e-mail, real accounts). They are ready for an owned test environment.

## End-to-end workflow tests (Unit 2)

`tests/e2e/` automates the prioritised workflows with plain Playwright tests:

| Priority | Workflow | File |
|---|---|---|
| P1 | Purchase journey: catalogue → variant → search → cart → quantity change → checkout summary | `test_purchase_journey.py` |
| P1 | The selected variant is what the server receives (request observed, nothing mocked) | `test_network_control.py` |
| P2 | Search → product details; sold-out protection; two shoppers' carts are separate | `test_find_and_protect.py` |
| P2 | Add to Cart fails (HTTP 500/503): cart unchanged; customer can retry (strict xfail: shop defect) | `test_network_control.py` |
| P2 | The shop works with third-party telemetry silenced | `test_network_control.py` |

Building blocks:

- `business_step(page, "...")` (`framework/adapters/web/steps.py`): logs the step and groups
  its actions under that title in the Playwright trace.
- `silence_third_parties(context)` and `simulate_failure(page, url, status)`
  (`framework/adapters/web/network.py`). Every e2e test silences third parties automatically.
- `@covers("REQ-03", ...)` (`framework/requirements_marks.py`): e2e results count in the
  traceability matrix next to the BDD scenarios.

## Mobile (Unit 3): My Demo App on Android with Appium

The same Store port has a third adapter, `MobileStore` (`framework/adapters/mobile/`), built
from screen objects. `features/mobile_cart.feature` reuses the Unit 1 cart steps unchanged with
the app's products; `tests/mobile/` holds plain Appium workflow tests (checkout, login rules).

Prerequisites on your machine: Android Studio with an emulator (or a phone with USB debugging),
Node.js 22.22.2+ / 24.15+, Appium 4 and its UiAutomator2 driver, and the app's APK
(release 2.3.0 of `saucelabs/my-demo-app-android`).

```bash
npm install -g appium
```

```bash
appium driver install uiautomator2
```

```bash
appium
```

then, in a second terminal:

```bash
SHOP_ANDROID_APP=/path/to/my-demo-app.apk SHOP_ANDROID_AVD=Pixel_8 pytest --store mobile
```

| Option | Environment variable | Default |
|---|---|---|
| `--appium-url` | `SHOP_APPIUM_URL` | `http://127.0.0.1:4723` |
| `--android-app` | `SHOP_ANDROID_APP` | — (app already installed) |
| `--android-device` | `SHOP_ANDROID_DEVICE` | `Android Emulator` |
| `--android-avd` | `SHOP_ANDROID_AVD` | — (Appium starts this emulator) |

**Platform selection** — each run deselects what its platform cannot run (a summary line says how many and why):

| `--store` | BDD `@web` | BDD `@mobile` | `tests/e2e`, `tests/pages` | `tests/mobile` |
|---|---|---|---|---|
| `fake` | run (web catalogue) | run (app catalogue) | — | — |
| `web` | run | — | run | — |
| `mobile` | — | run | — | run |

**No device?** `pytest --store mobile` reports every mobile test **BLOCKED** with the reason
("no Appium server at …", or "mobile environment not ready: Neither ANDROID_HOME …"),
and tries to start the session only once.

**App data without a device.** `tests/data/mobile_catalogue.json` (24 products, USD) and
`tests/data/mobile_ui_inventory.json` (every id and content description per layout) were
extracted from the app's source with `tools/`; `tests/unit/test_mobile.py` checks every
locator against the inventory. Refresh after an app update:

```bash
git clone --depth 1 https://github.com/saucelabs/my-demo-app-android.git /tmp/mda
```

```bash
python -m tools.extract_mobile_catalogue /tmp/mda tests/data/mobile_catalogue.json
```

```bash
python -m tools.extract_ui_inventory /tmp/mda tests/data/mobile_ui_inventory.json
```

**Evidence on failure** (`reports/mobile/<test>/`): `screenshot.png`, `page_source.xml`,
`logcat.txt`, `device_info.json`, `capabilities.json` (secrets masked), `recording.mp4`.

**App behaviour noted from its source:** any non-empty password is accepted except for
`alice@example.com` (locked out) — recorded as a strict xfail; delivery adds $5.99 at review.

## Asynchronous systems (Unit 3): the order-events sandbox

`sandbox/` is a small order-fulfilment back end and the **system under test** of Day 12:
`POST /orders` answers `202 Accepted`; payment, packing and shipping happen later through an
in-memory broker with at-least-once delivery (acks, visibility timeout 0.6 s, retries with
backoff 0.2 s / 0.4 s, 3 attempts, dead-letter queue); a projector builds the read model and
pushes status frames over WebSocket (`/ws?correlation_id=…&since=…`). Faults are injected per
correlation id (`POST /admin/faults`): `duplicate`, `lose_ack`, `deliver_after`, `delay`,
`gateway_fail`, `gateway_slow`, `drop_connection`.

The tests treat it as a black box (an architecture test forbids importing it):
`framework/events` talks HTTP + WebSocket, and each test gets an `OrderFlow` with its own
correlation id that follows the live status **before** acting. Every pytest-xdist worker
starts its own sandbox on a free port. Run one by hand to explore it:

```bash
python -m sandbox --port 8765 --build release
```

| Where | What |
|---|---|
| `features/order_events.feature` | The business rules (REQ-10…13), same tag rules as every feature |
| `tests/events/` | Fault-injection tests: duplicates, lost acks, resubmits, timeouts, ordering, DLQ, redrive, reconnect, worker outage |
| `framework/events/findings.py` | Known defects D-12-01…03 and the builds they are in |
| `reports/events/evidence.md` | Execution evidence for every events test (Day 10 template), written each run |
| `reports/events/<test>/` | On failure or known defect: deliveries, events, frames, payments, DLQ, faults, log excerpt |

**Known defects in build `release`** (strict xfail, `raises=AssertionError`):

| Id | Severity | Finding | Requirement |
|---|---|---|---|
| D-12-01 | Critical | A payment retried after a gateway timeout charges the customer twice | REQ-10 |
| D-12-02 | High | A late "packed" update overwrites "shipped": the status goes backwards | REQ-11 |
| D-12-03 | Medium | After a reconnect, the live status skips one update | REQ-13 |

`--sandbox-build fixed` runs the same tests against the corrected build: all 20 must pass,
which proves that each defect test fails **only** because of its defect.

## Unit 4: containers, performance, cloud, CI/CD

| Folder | What | Runs here? |
|---|---|---|
| `docker/Dockerfile` | Test-runner image: digest-pinned base, non-root (UID 10001), works with a read-only root | Yes: `docker build`, `docker run` |
| `framework/cloud/run_suite.py` | Container entry point: JSON log lines, SIGTERM → clean stop, reports + manifest stored, honest exit code | Yes |
| `framework/cloud/artifacts.py` | Artifact store: a folder or S3 (SSE, run-id metadata, manifest last) | Yes (S3 tested with moto) |
| `framework/cloud/audit.py` | Static audit of IAM, ECS, CloudFormation, and workflows | Yes |
| `perf/*.jmx`, `perf/sla.toml` | JMeter plans: BlazeDemo journey (light load only) and the local sandbox (stress) | Yes, with JMeter |
| `framework/perf/` | JTL statistics, SLA gate, telemetry sampler, load-vs-telemetry bottleneck report | Yes |
| `cloud/cloudformation/*.yaml` | Reference AWS design: ECR, S3, CloudWatch, ECS/Fargate, IAM, GitHub OIDC, budget; Device Farm project | Linted only (`cfn-lint`) |
| `cloud/devicefarm/` | Device Farm test spec and test-package builder (wheels for the Amazon Linux 2 host) | Package builds here; the run needs AWS |
| `.github/workflows/cloud.yml` | Reference cloud pipeline (OIDC, Fargate, Device Farm, gates, cleanup); skipped without AWS variables | Linted only (`actionlint`) |
| `exam/audit-case/` | Day 18 exam material: a deliberately flawed setup to audit | Yes (the audit finds the mechanical flaws) |

**Run the suite in the container the way Fargate would** (read-only root, non-root, no network):

```bash
docker build -f docker/Dockerfile -t shop-bdd-tests:local .
```

```bash
mkdir -p archive && chmod 777 archive
```

```bash
docker run --rm --read-only --tmpfs /tmp --tmpfs /app/reports:uid=10001 --network none -v "$PWD/archive:/archive" shop-bdd-tests:local --suite offline --artifacts /archive
```

**Performance on the local sandbox** (three terminals, or `&`):

```bash
python -m sandbox --port 8765 --gateway-latency 0.05
```

```bash
python -m framework.perf.telemetry http://127.0.0.1:8765 --out reports/perf/telemetry.csv --duration 70
```

```bash
jmeter -n -t perf/orders_sandbox.jmx -q perf/jmeter.properties -l reports/perf/orders.jtl -e -o reports/perf/orders-html -Jusers=40 -Jduration=60
```

```bash
python -m framework.perf.correlate reports/perf/orders.jtl reports/perf/telemetry.csv
```

```bash
python -m framework.perf.gate reports/perf/orders.jtl --profile sandbox
```

`--concurrency fulfilment=4` (repeatable, any subscription) gives a worker more parallel consumers:
the corrective action of Day 16. **BlazeDemo** is someone else's site: at most 10 users and 5 minutes
(`perf/blazedemo_purchase.jmx` defaults to 5 users, 2 minutes, 1–3 s think time, and a setUp
guard refuses to start above 10 users or 5 minutes). Always pass `-q perf/jmeter.properties`: it pins
the results columns the analysis reads. `tests/unit/test_jmeter_plans.py` checks every plan: bounded,
property-driven, every request asserted, explicit timeouts, polite to third-party targets.

## Browser context defaults

Every browser context defaults to `locale="en-GB"` and `timezone_id="Europe/London"`
(`browser_context_args` in `framework/plugins/fixtures.py`); override per test with
`@pytest.mark.browser_context_args(...)`. `new_shop()` creates extra isolated shoppers.

## Known shop defects (found by this suite)

| Defect | Evidence | Handled by |
|---|---|---|
| Failed Add to Cart: no message; after HTTP 500 the button turns into a disabled "Sold Out", after a network failure it stays disabled — the customer cannot retry | `tests/e2e/test_network_control.py::test_customer_can_retry_after_a_failed_add_to_cart` (`xfail(strict=True)`) | Cart is unchanged (checked by a passing test); report to the shop |
| Mini-cart not refreshed after an AJAX add | `tests/pages/test_cart_pages.py::test_mini_cart_updates_without_a_page_load` (`xfail(strict=True)`) | Read the mini-cart after a page load |
| Hidden mini-cart duplicates cart rows and element ids | Strict-mode violation on `#updates_<id>` | Cart locators scoped to `#cart` |
| Cart quantity box has no label; remove link named "x" | Accessibility snapshot | Row located by product link, input searched inside it |
| Registration labels not linked; duplicated ids (`div#first_name` wraps `input#first_name`) | Strict-mode violation | Inputs located by `name` |
| Password-recovery e-mail field has no label | Accessibility snapshot | Located by id |

A strict `xfail` turns a known defect into a tripwire: when the shop fixes it,
the test passes unexpectedly, fails the run, and tells you to remove the marker.

## Tags and the requirement registry

Every scenario needs:

| Tag | Rule |
|---|---|
| `@REQ-xx` | ≥ 1, each listed in `requirements.toml` |
| `@risk-high/medium/low` | exactly 1, equal to the highest risk of its requirements |
| `@smoke` / `@regression` | exactly 1 |
| `@web` / `@api` / `@mobile` | ≥ 1 (usually on the `Feature`) |
| `@manual` | optional; then risk and suite tags are not required, and the scenario is skipped |

Broken rules stop the run at collection time with a list of every problem.

To add a requirement: add it to `requirements.toml`, then write scenarios.
`--fail-on-uncovered` (on in CI) fails the run while it has none.

## Outcome classes

| Outcome | Raised by | Meaning |
|---|---|---|
| **FAIL** | `AssertionError`, `CartInconsistencyError` | Product defect |
| **KNOWN DEFECT** | strict xfail (a registered defect) | Requirement not met, documented; turns FAIL if the defect disappears unannounced |
| **BLOCKED** | `EnvironmentBlockedError` | Bot protection / outage. Not a defect: rerun later, with less load |
| **MANUAL** | `@manual` | Known, documented automation gap |
| **NOT COVERED** | — | Registered requirement without any scenario |
| **NOT RUN** | — | Has scenarios, but none selected in this run |

The traceability matrix is printed after every run and written to
`reports/traceability.csv` and `reports/traceability.md`.

## Evidence on failure

| Where | What |
|---|---|
| Terminal "Captured log" | Every scenario and step, plus what the store adapter did |
| `reports/evidence/<test>/<step>.png` | Full-page screenshot at the failing **business step** |
| `reports/evidence/<test>/<step>.json` | Step, error, URL, browser console errors, failed shop requests |
| `reports/artifacts/<test>/trace.zip` | Playwright trace: `playwright show-trace <file>` |

## Working with a live third-party site

- Run live suites **serially**. Parallel browsers look like a bot attack.
- Setup goes through the JSON API; checks go through the UI.
- The catalogue is loaded once per run; each scenario gets a new browser context
  (and so a new, empty cart) with no clean-up requests.
- Never try to bypass bot protection. A BLOCKED run is information, not a failure to hide.

## CI

`.github/workflows/ci.yml`

- **quality** (every push / PR): ruff, format check, mypy (strict), BDD review (strict), cfn-lint, actionlint, the cloud audit,
  unit and architecture tests, offline BDD and the events sandbox in parallel with the
  coverage gate, then the events tests against the fixed build (oracle validation).
- **container**: builds the image and runs the offline suite read-only, as Fargate would.
- **performance**: JMeter 5.6.3 (SHA-512 verified) against the local sandbox, telemetry,
  bottleneck report, SLA gate; the light BlazeDemo journey only on manual runs.
- **cloud** (`cloud.yml`, manual, reviewer approval): OIDC → ECR → Fargate → Device Farm → gates → cleanup.
  Skipped unless the AWS repository variables exist.
- **live** (main, nightly, or manual): smoke on push; nightly the full BDD regression
  plus the page-object tests; serial; reports uploaded as artifacts.

## Refreshing the offline catalogue

`tests/data/catalogue_snapshot.json` is a trimmed copy of the live `/products.json`.
If the live store changes, re-record it and run `pytest tests/unit` — the snapshot tests
state the store facts the scenarios rely on.
