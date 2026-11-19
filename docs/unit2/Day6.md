# Unit 2 · Day 6 — Tracing, Network Interception, Authentication State, Parallel Execution, Reporting

| | |
|---|---|
| **Course** | Advanced Automation Test Engineering (ATEST03) — Fast Track |
| **Unit** | Unit 2 — Playwright End-to-End Automation |
| **Learning outcome** | **LO3** — Build reliable Playwright suites using fixtures, isolation, tracing, network control, and parallel execution (Bloom **B3: Apply**) |
| **Format** | Concept/Lecture · Virtual · 120 minutes · no code to produce (short illustrations only) |
| **System used in examples** | https://sauce-demo.myshopify.com/ and the Unit 1 framework |
| **Output of the day** | Part 2 of your **Playwright test design notes** (end of this document) |

> **How the facts here were checked.** Every behaviour described was confirmed with Playwright 1.63, pytest-playwright 0.10, pytest-xdist 3.8, pytest-html 4.2, and pytest-rerunfailures 16.7 while preparing the course — on a local test page, and with two short runs against the live shop for the analytics example. Part 6 lists the results that surprised us.

---

## How to use this lecture

Day 5 was about one test running correctly. Day 6 is about **many tests, run often, by a team**: how you see what happened (tracing, reporting), how you control what the application receives (network), how you avoid repeating slow setup (authentication state), and how you finish in minutes (parallel execution).

| Badge | Level | After this level you can… |
|---|---|---|
| 🟢 | **Foundation** | Open a trace and explain a failure; say what a route, a mock, and storage state are |
| 🟡 | **Practitioner** | Choose a network pattern for a test, configure evidence and reports, run in parallel safely |
| 🔴 | **Senior** | Decide what to mock and what never to mock, design auth and data for parallel runs, and make flakiness visible instead of hidden |

### Lecture plan (120 min)

| Time | Part |
|---|---|
| 0–10 | Part 0 — Why these five topics belong together |
| 10–35 | Part 1 — Tracing and evidence |
| 35–65 | Part 2 — Network interception |
| 65–85 | Part 3 — Authentication state |
| 85–105 | Part 4 — Parallel execution |
| 105–115 | Part 5 — Reporting patterns |
| 115–120 | Part 6 — Lessons and checklist |

---

## Glossary

| Term | Meaning | Vietnamese |
|---|---|---|
| Trace | A recording of a test: actions, page snapshots, network, console, source | Bản ghi vết |
| Trace Viewer | The tool that opens a trace (`playwright show-trace`) | Trình xem vết |
| Artifact | A file a run produces: trace, screenshot, video, report | Tệp sản phẩm của lần chạy |
| Route | A rule that intercepts matching requests before they reach the network | Tuyến chặn |
| Mock / fulfill | Answer a request with a made-up response | Giả lập phản hồi |
| Abort | Make a request fail as if the network broke | Hủy request |
| HAR | HTTP Archive: a JSON file of recorded requests and responses, replayable | Tệp lưu trữ HTTP |
| Storage state | Saved cookies and storage, to start a context already logged in | Trạng thái lưu trữ |
| Worker | One parallel process running a share of the tests (`gw0`, `gw1`, …) | Tiến trình chạy song song |
| Sharding | Splitting a suite across several machines | Chia nhỏ bộ test |
| Rerun / retry | Running a failed test again automatically | Chạy lại |
| JUnit XML | A standard test-result file that CI systems read | Báo cáo JUnit XML |
| Flake rate | How often tests fail and then pass without a code change | Tỉ lệ chập chờn |

---

## Part 0 — Why these five topics belong together 🟢

A suite of 300 browser tests run on every change meets five problems, and each topic answers one:

| Problem at scale | Answer |
|---|---|
| "It failed in CI and passes on my laptop. What happened?" | **Tracing** and evidence |
| "We cannot make the server return an error to test the error message." / "A third-party script breaks our tests." | **Network interception** |
| "Every test spends 10 seconds logging in, and the login has a CAPTCHA." | **Authentication state** |
| "The suite takes 40 minutes." | **Parallel execution** |
| "Nobody reads the results; flaky tests are retried until green." | **Reporting patterns** |

---

## Part 1 — Tracing and evidence 🟢 → 🔴

### 1.1 🟢 A flight recorder for tests

A trace records, for every action: what was called, a **snapshot of the page before and after**, screenshots, every network request and response, console messages, and the line of test code. You can replay a failure that happened on a CI machine hours ago, without rerunning anything.

Inside the `trace.zip` file (checked): `trace.trace` (actions), `trace.network` (requests), `trace.stacks` (source positions), a `screencast/` folder of screenshots, and a `src/` folder with your test source.

### 1.2 🟡 Recording evidence with pytest-playwright

| Option | Values | Recommended in CI |
|---|---|---|
| `--tracing` | `on`, `off`, `retain-on-failure` | `retain-on-failure` |
| `--screenshot` | `on`, `off`, `only-on-failure` | `only-on-failure` |
| `--video` | `on`, `off`, `retain-on-failure` | `retain-on-failure` (when visual timing matters) |
| `--output` | folder | e.g. `reports/artifacts` — one sub-folder per test |

`retain-on-failure` records every test but **keeps files only for failures** (checked: in a run of four tests with one failure, only the failing test's `video.webm` remained). The Unit 1 framework already sets tracing and screenshots this way.

Outside pytest, the same recorder is three calls:

```python
context.tracing.start(screenshots=True, snapshots=True, sources=True)
# ... the test ...
context.tracing.stop(path="trace.zip")
```

### 1.3 🟡 Opening a trace

```bash
playwright show-trace reports/artifacts/<test-folder>/trace.zip
```

| Panel | Answers |
|---|---|
| Action list / timeline | Which action failed, and how long each took |
| Before / After snapshots | What the page looked like at that moment — inspect it like a live page |
| Call log | Which actionability check failed (Day 5, Part 4) |
| Network | Which requests were sent, their status, timing, and bodies |
| Console | JavaScript errors from the page |
| Source | The test line that ran |

### 1.4 🔴 A diagnosis routine for a CI failure

1. Download the run's artifacts (CI keeps them for failures only).
2. Open the trace at the failing action; read the **call log** first.
3. Compare the **before** snapshot with what the test expected: wrong page, overlay, missing data?
4. Check the **network** panel for a failed or slow request just before the failure.
5. Decide: **product defect**, **test defect** (wrong locator or wait), or **environment** (bot check, outage) — the Unit 1 `BLOCKED` classification is the automated version of this step.

### 1.5 🔴 Tracing with structure, and with care

- **Group actions into business steps.** `context.tracing.group("Add Grey jacket to cart")` … `group_end()` (available in 1.63) makes the trace read like the scenario. A BDD hook can open one group per Gherkin step.
- **Long sessions** can be split into chunks (`start_chunk` / `stop_chunk`), one trace per logical part.
- **Traces are sensitive.** They contain everything the page showed and every request body — including typed passwords and tokens. Store them like logs with personal data: limited retention (the course CI keeps 14 days), limited access, never attached to public tickets.
- **Tracing every test has a cost** (time and disk). Use `on` while debugging locally, `retain-on-failure` in CI.

> **Checkpoint 1.** A test failed with "Timeout waiting for Add to Cart". Which two panels of the trace do you open first, and why?

---

## Part 2 — Network interception 🟢 → 🔴

### 2.1 🟢 A toll booth between the page and the internet

A **route** is a rule: "every request matching this pattern stops at my booth first". For each request, the handler decides one of four things:

```
                     ┌─ continue_()  → let it go to the network (optionally changed)
page ── request ──▶  │─ fulfill()    → answer it myself (a mock)
                     │─ abort()      → make it fail like a broken network
                     └─ fallback()   → let the next (earlier) route decide
```

Why testers want this:

| Need | Example on the shop |
|---|---|
| Test states that are hard to create | The server answering "500" to Add to Cart |
| Remove unstable outside dependencies | Analytics and social scripts (Part 2.5) |
| Make data deterministic | A fixed product list instead of a live one |
| Speed | Skip images and fonts in pure-logic tests |

### 2.2 🟡 The patterns (all checked)

**Mock a JSON answer:**

```python
page.route("**/cart.js", lambda route: route.fulfill(status=200, json={"item_count": 3, "items": []}))
```

**Simulate a failure** — a server error, or no network at all:

```python
page.route("**/cart/add.js", lambda route: route.fulfill(status=500, body="Server error"))
page.route("**/cart/add.js", lambda route: route.abort())
```

An aborted `fetch()` is rejected ("Failed to fetch") and the page's `requestfailed` event reports `net::ERR_FAILED`.

**Patch a real response** — go to the server, change one thing, return the rest untouched:

```python
def patch(route):
    response = route.fetch()
    route.fulfill(response=response, body=response.text().replace("£55.00", "£0.00"))
```

**Add a header** to outgoing requests:

```python
page.route("**/*", lambda route: route.continue_(headers={**route.request.headers, "x-test-run": "nightly"}))
```

For every request of a context, the simpler option is the context setting `extra_http_headers={"X-Test-Run": "nightly"}` (Day 5).

**Block by type or by host:**

```python
page.route("**/*", lambda route: route.abort() if route.request.resource_type in {"image", "font"} else route.continue_())
```

**Scope:** `page.route(...)` affects one page; `context.route(...)` affects every page of the context, including pages opened later. Remove routes with `page.unroute_all()`.

### 2.3 🟡 Observing without interfering

You do not need a route just to **watch** traffic:

| Need | Tool |
|---|---|
| Wait for the response to *this* action | `with page.expect_response("**/cart/add.js"):` (used throughout Unit 1) |
| Wait for a request to be sent | `with page.expect_request(...)` |
| Log everything | `page.on("request")`, `page.on("response")`, `page.on("requestfailed")` |
| Collect the shop's own failed requests for evidence | The Unit 1 `BrowserDiagnostics` (Day 3, Part 7) |

### 2.4 🔴 Rules that decide which route runs

Checked behaviour:

| Rule | Consequence |
|---|---|
| The route registered **last** runs **first** | A test can override a general route from a fixture by adding a specific one |
| `route.fallback()` passes the request to the **previously** registered route | Layer routes: "log everything" + "mock this one" |
| `route.continue_()` sends the request to the network immediately | No other route sees it |
| Headers changed with `continue_()` **are sent** (the server received them) but `page.on("request")` still shows the **original** headers | To see what was really sent, use `response.request.all_headers()` |

### 2.5 🔴 A real measurement: blocking the shop's analytics

Every shop page sends dozens of tracking requests (Shopify's "monorail" telemetry, `/api/collect`, a Facebook script, OpenTelemetry). Two short runs against the live shop, opening a product and adding it to the cart (one run each, so treat the numbers as an observation, not a statistic):

| Strategy | Add to Cart worked | Requests seen | Intercepted | Time |
|---|---|---|---|---|
| No interception | yes | 65 | — | 3.5 s |
| `route.abort()` the analytics | yes | **74** | 25 | 3.2 s |
| `route.fulfill(status=204)` the analytics | yes | 66 | 16 | 3.3 s |

What the numbers teach:

- **Aborting made *more* requests.** The telemetry script treats a failed request as "try again"; monorail was attempted 18 times. Answering with an empty `204` ("received, nothing to say") stopped the retry storm.
- **Speed barely changed** here. The real benefits are elsewhere: tests no longer depend on third-party services being up, and the shop owner's analytics are not polluted by robot traffic.
- **Measure before you claim.** "Blocking analytics makes tests faster" sounded obvious; on this shop it was not true.

### 2.6 🔴 HAR: record once, replay without the server

```python
context = browser.new_context(record_har_path="cart.har", record_har_url_filter="**/cart*.js")
# ...browse, close the context: the HAR file is written...
page.route_from_har("cart.har", url="**/cart*.js", not_found="abort")
```

Checked: a page replayed from a HAR file loaded correctly **after the server had been shut down**.

| Option | Meaning |
|---|---|
| `not_found="abort"` | A request missing from the HAR fails — strict, deterministic |
| `not_found="fallback"` | A missing request goes to the network |
| `update=True` | Re-record the HAR from the live server (refresh stale recordings) |

Use HAR to freeze an unstable dependency or to run UI tests offline. Its danger: a recording **ages**. Keep a live smoke test that would notice when reality has moved on.

### 2.7 🔴 What to mock — and what never to mock

| Mock it | Never mock it |
|---|---|
| Third-party services (analytics, social, payment sandboxes) | **The behaviour under test** — a test of "Add to Cart" that mocks `/cart/add.js` proves only the mock |
| Error states that are hard to trigger (500, timeout, empty list) | The contract between your own frontend and backend in your **only** end-to-end test of it |
| Slow, non-essential resources (images, fonts) in logic tests | Anything you cannot keep in sync — a mock that drifted from reality passes forever |

Two senior safeguards:

1. **Mocks need a twin that is not mocked.** For every mocked flow, keep at least one live test of the same flow (the Unit 1 BDD suite plays that role for the cart).
2. **Service workers can bypass routes.** If an application uses one, create the context with `service_workers="block"`, or some requests never reach your route.

> **Checkpoint 2.** You want to test the shop's message when Add to Cart fails. Which pattern do you use, and which request do you intercept? What must stay unmocked elsewhere in the suite?

---

## Part 3 — Authentication state 🟡 → 🔴

### 3.1 🟢 Why not log in in every test?

A UI login costs seconds, can hit a CAPTCHA (the shop's login does), triggers rate limits, and makes every test fail when only the login is broken. Log in **once**, test the login flow **separately**.

### 3.2 🟡 Storage state

`context.storage_state(path="state.json")` saves cookies and localStorage. Since Playwright 1.51, `indexed_db=True` also saves IndexedDB, where some applications keep their tokens (the 1.63 signature: `path`, `indexed_db`, `opfs`, `credentials`). A new context created with `storage_state="state.json"` starts in the saved state — Day 5 showed a shop cart surviving this way.

### 3.3 🟡 The standard pattern

```python
@pytest.fixture(scope="session")
def customer_state(browser, tmp_path_factory) -> Path:
    path = tmp_path_factory.mktemp("auth") / "customer.json"
    context = browser.new_context()
    log_in(context.new_page(), os.environ["SHOP_CUSTOMER_EMAIL"], os.environ["SHOP_CUSTOMER_PASSWORD"])
    context.storage_state(path=path)
    context.close()
    return path
```

Every test then asks for `new_context(storage_state=customer_state)`. *Illustration only:* this shop's login cannot be automated (CAPTCHA — Day 4, F-08); the pattern needs an environment with test accounts.

### 3.4 🔴 Design decisions

| Decision | Senior answer |
|---|---|
| Log in through the UI or an API? | API (or a token endpoint) when the application offers one: faster and no CAPTCHA. Keep **one** UI login test |
| Where do credentials come from? | Environment variables / CI secrets. Never in code, never printed, never in reports |
| Commit `state.json`? | Never: it *is* a live session. Generate per run into a temporary folder; add `*.json` auth folders to `.gitignore` |
| Sessions expire | Generate state at the start of each run (session fixture), not once a week |
| Several roles | One state file per role: `customer.json`, `admin.json` |
| Parallel workers | **One test account per worker** (§4.4): two workers sharing one account share its server-side data (addresses, orders, wish lists) |

> **Checkpoint 3.** Storage state isolates browser data. Why can two parallel tests that use the *same* account still interfere?

---

## Part 4 — Parallel execution 🟡 → 🔴

### 4.1 🟢 Workers

```bash
pytest -n auto
```

`pytest-xdist` starts several **worker processes** (named `gw0`, `gw1`, … — checked; without xdist the `worker_id` fixture is `master`). Each worker has its own Python process and its own browser, so session-scoped fixtures run **once per worker**: the Unit 1 catalogue is loaded once in each worker, not once in total.

### 4.2 🟡 Distribution modes

| `--dist` | Tests are grouped… | Use when |
|---|---|---|
| `load` (default) | Not at all: any free worker takes the next test | Tests are fully isolated |
| `loadscope` | By module / class | Tests in a class share an expensive class fixture |
| `loadfile` | By file | Same, per file |
| `loadgroup` | By `@pytest.mark.xdist_group("name")` | A few tests must run in the same worker (e.g., they share one test account) |
| `worksteal` | Dynamic rebalancing | Test durations vary a lot |

### 4.3 🟡 Preconditions — Day 5's isolation, now mandatory

| Shared thing | Parallel-safe version |
|---|---|
| Browser state | A context per test |
| Files | `tmp_path` per test, never a fixed path |
| Ports | Port `0` (any free port) |
| Test data | Created by the test, or unique per run/worker (`testrun_uid`, `worker_id`, `unique_email()`) |
| Reports and plugins | Written by the main process from test reports — the Day 3 traceability bug (an empty matrix under xdist) is exactly what happens otherwise |
| Artifacts | One folder per test (pytest-playwright already does this) |

### 4.4 🔴 The limits of parallelism

- **Shared external systems.** Four browsers hitting a third-party shop look like an attack: this course's live runs met Cloudflare checks and an HTTP 429 "Too Many Requests". Parallel runs are for **owned** environments; against someone else's site, run serially.
- **Shared accounts.** Partition: worker `gw0` uses account 0, `gw1` account 1, …; or group the tests that need the same account with `xdist_group`.
- **Machine resources.** Every worker runs a browser. More workers than the machine can feed makes every test slower and timing-sensitive. Measure `-n 2`, `-n 4`, `-n auto` and keep the fastest **stable** setting.
- **Across machines (sharding).** CI can split a suite over several machines (a job matrix, or plugins such as `pytest-split`); each machine then runs xdist inside. Merge the reports afterwards.

### 4.5 🔴 Parallelism reveals hidden coupling

A suite that passes serially and fails in parallel was already broken: tests depended on each other's leftovers. Treat the first parallel run as a **test of the suite's isolation** — the same three proofs as Day 5: repeated, parallel, random order.

---

## Part 5 — Reporting patterns 🟡 → 🔴

### 5.1 🟢 Different readers, different reports

| Reader | Needs | Report |
|---|---|---|
| Developer fixing a failure | What happened, step by step | Trace, screenshot, logs, evidence folder |
| CI system | Pass/fail per test, to block a merge | JUnit XML (`--junitxml`) |
| Team lead / stakeholder | Overall health, trends | HTML report, dashboard |
| Auditor / product owner | Which requirements are proven | Traceability matrix (Unit 1) |

### 5.2 🟡 The tools

| Tool | Command | Notes |
|---|---|---|
| Terminal summary | `-ra` | Lists every non-passing outcome with its reason |
| JUnit XML | `--junitxml=reports/junit.xml` | Built into pytest; read by every CI system |
| pytest-html | `--html=reports/report.html --self-contained-html` | One file (≈ 34 KB for a small run, checked); easy to attach |
| Allure | `allure-pytest` plugin + Allure CLI | Rich: steps, attachments, history, trends. Needs its own server or CLI to view; not set up in this course |
| Playwright artifacts | `--tracing`, `--screenshot`, `--video` | Per-test folders |
| Unit 1 additions | Traceability matrix (`.csv`, `.md`), BDD review report, evidence JSON | Requirement view and business-step evidence |

### 5.3 🔴 Five patterns that make reports trustworthy

1. **Classify outcomes, do not just count them.** Passed / failed / **blocked** (environment) / **xfail** (known defect) / **manual** — Unit 1's matrix. "37 failed" tells nothing; "35 blocked by HTTP 429, 2 product defects" is a decision.
2. **Make retries visible.** Checked with `pytest-rerunfailures`: a test that failed once and then passed is reported as "1 passed, 1 rerun" in the terminal and in the HTML report — but the **JUnit XML that CI reads shows a plain pass**. If you allow retries, publish the rerun count separately and treat every rerun as a defect to fix; otherwise flakiness becomes invisible.
3. **Link evidence to results.** A failure line should point to its trace, screenshot, and evidence folder; nobody searches artifact folders by hand.
4. **Keep evidence on purpose.** Failures only (`retain-on-failure`), a retention period, and access control (§1.5).
5. **Watch trends, not just runs.** Flake rate per test, duration per test, blocked runs per week. A test that is slowly getting slower or flakier is a defect report in advance.

> **Checkpoint 5.** Your CI dashboard (built from JUnit XML) shows 100 % green for a month, but developers say "the suite is flaky". How can both be true, and what do you change?

---

## Part 6 — Lessons and checklist 🔴

### 6.1 Surprises from preparing this lecture

| What happened | Lesson |
|---|---|
| Aborting analytics requests produced *more* requests (74 vs 65) | Scripts retry failures; answer with `fulfill(status=204)` instead. Measure before you claim a benefit |
| Blocking analytics did not make the shop noticeably faster | The value was independence and clean analytics, not speed |
| A header added with `continue_()` reached the server but not `page.on("request")` | Events show the original request; use `response.request.all_headers()` to see what was sent |
| JUnit XML showed a rerun test as a simple pass | Retries hide flakiness unless reported separately |
| A HAR replay worked with the server shut down | HAR is a real tool for offline, deterministic UI tests — with a live twin to catch drift |

### 6.2 Checklist additions (continue Day 5's list)

| # | Check |
|---|---|
| 11 | CI records traces and screenshots `retain-on-failure`; artifacts have a retention period |
| 12 | Every mocked flow has a live, unmocked twin somewhere in the suite |
| 13 | Routes are scoped (page vs context) and removed when no longer needed |
| 14 | No credentials in code, reports, or committed state files; auth state generated per run |
| 15 | Parallel runs use unique data and accounts per worker; never parallel against a third-party site |
| 16 | Reports classify outcomes and show reruns; evidence is linked from each failure |

---

## Your output: Playwright test design notes, part 2

Add to the page you started on Day 5:

| Topic | Your decision and the reason |
|---|---|
| Evidence settings for local runs and for CI | |
| Which requests your Day 7 tests will mock, and their live twins | |
| Third-party requests to block or answer, and how | |
| Authentication strategy (for an application with login) | |
| Parallel settings, and where you will **not** run in parallel | |
| Reports: who reads which, and how reruns are shown | |

---

## Self-check (answers below — try first)

1. What does a trace contain that a screenshot does not?
2. Why is `--tracing retain-on-failure` the usual CI setting rather than `on`?
3. Name the four things a route handler can do with a request.
4. Two routes match the same URL. Which runs first, and how can it hand the request to the other?
5. Why did aborting the shop's analytics requests increase the number of requests?
6. Give one thing you should mock and one you must never mock in an end-to-end test of Add to Cart.
7. Why must `state.json` never be committed?
8. Why does the Unit 1 catalogue load once per worker instead of once per run?
9. Why is a third-party shop the wrong place for `-n 8`?
10. How can a CI dashboard stay green while the suite is flaky?

<details>
<summary><b>Answer guide</b></summary>

1. Every action with before/after page snapshots you can inspect, the network requests and responses, console messages, the call log, and the source line — the whole story, not one picture.
2. Recording costs time and disk on every test; `retain-on-failure` records everything but keeps files only when they are needed.
3. `continue_()` (optionally changed), `fulfill()` (mock), `abort()` (fail), `fallback()` (let an earlier route decide).
4. The one registered last; it calls `route.fallback()` to pass the request to the previously registered route.
5. The telemetry script retries failed requests; aborting made it try again (monorail 18 times). An empty `204` answer is accepted and ends the retries.
6. Mock: third-party analytics, or a 500 error to test the error message. Never mock `/cart/add.js` in the test whose purpose is to prove adding to the cart works.
7. It is a live session (cookies, tokens): anyone with the file is logged in. It also expires, so it must be generated per run anyway.
8. Each xdist worker is a separate process with its own session; session-scoped fixtures run once per worker.
9. Many parallel browsers look like an attack to bot protection and rate limits (this course met Cloudflare checks and HTTP 429), and the load falls on someone else's system.
10. Retries turn first-time failures into passes, and JUnit XML records only the final pass. Publish rerun counts (terminal/HTML show them), track flake rate, and treat each rerun as a defect.
</details>

## Next: Day 7 — the lab

Automate prioritised end-to-end workflows on the shop with fixtures, tracing, and network control: the first day of Unit 2 where you write the code.
