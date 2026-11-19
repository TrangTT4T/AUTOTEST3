# Unit 2 · Day 8 — Topic Revision, then Reliability and Maintainability Patterns

| | |
|---|---|
| **Course** | Advanced Automation Test Engineering (ATEST03) — Fast Track |
| **Unit** | Unit 2 — Playwright End-to-End Automation |
| **Learning outcome** | **LO3** — Build reliable Playwright suites using fixtures, isolation, tracing, network control, and parallel execution (Bloom **B3: Apply**) |
| **Session A** | Topic Revision · Guides/Review · Virtual · **60 min** |
| **Session B** | Reliability and maintainability patterns: failure analysis, flaky-test control, tracing diagnostics, stability improvement, maintainability criteria · Concept/Lecture · Virtual · **120 min** |
| **Code** | None to produce. Short illustrations only |
| **Output of the day** | Session A: quiz answers and a peer review of your Day 7 tests. Session B: your team's **reliability policy** (one page, end of this document) |

> **About the examples.** The syllabus asks for "sample failure traces" and "flaky-test examples". Every one used here **really happened** while this course was built on the live shop — with the evidence that diagnosed it. Real failures teach better than invented ones.

---

# Session A — Topic Revision (60 min)

## A.1 Plan

| Time | Activity |
|---|---|
| 0–15 | The Unit 2 map and the ten rules |
| 15–25 | Myths and facts |
| 25–40 | Quiz (15 questions) |
| 40–60 | Peer review of Day 7 tests with the checklist |

## A.2 The Unit 2 map

```
Day 5  WHAT Playwright is            Day 6  HOW to run it at scale         Day 7  DOING it on the shop
────────────────────────            ──────────────────────────           ─────────────────────────
architecture (3 processes)           tracing & evidence                    prioritised workflows (P1/P2)
browser → context → page             network: observe / mock / fail        business_step → trace groups
locators (role, name, strict)        authentication state                  request contract (variant id)
actions & auto-wait                  parallel execution (xdist)            failure simulation → defect D-01
expect vs assert                     reporting patterns                    third-party isolation (204)
fixtures & scopes                                                          @covers → traceability
isolation
```

## A.3 The ten rules of Unit 2

| # | Rule | Day |
|---|---|---|
| 1 | One browser per session, **one context per test** | 5 |
| 2 | Locate by **role and accessible name**; CSS only inside a page object, tightly scoped | 5 |
| 3 | Page facts through **`expect`**; plain `assert` only for values already read | 5 |
| 4 | After an action that changes server state, **wait for its evidence** (response, URL, visible outcome) — never sleep | 5, 7 |
| 5 | Never `force=True` without a written reason | 5 |
| 6 | CI keeps traces and screenshots **on failure**; traces are sensitive | 6 |
| 7 | Mock only boundaries and failures; every mocked flow has a **live twin** | 6, 7 |
| 8 | Log in once, save **storage state**, start each test in a **new** context from it | 6 |
| 9 | Parallel only where the tests and the environment allow it — **never** against a third-party site | 6 |
| 10 | Reports **classify** outcomes and **show reruns** | 6 |

## A.4 Myths and facts

| Myth | Fact |
|---|---|
| "Playwright waits automatically, so I never need to wait." | It waits for **elements** to be actionable, not for the **server** to finish (Day 3: Add to Cart, `networkidle`). |
| "`networkidle` means the page is ready." | It is a load state, reached once; after that it returns at once. |
| "A green CI means a stable suite." | JUnit XML shows a rerun test as a simple pass (Day 6, checked). |
| "Blocking analytics makes tests faster." | On this shop, aborting made the scripts retry (74 vs 65 requests); speed barely changed. |
| "A test that passes alone is correct." | It may depend on leftovers; prove isolation with repeated, parallel, and random-order runs. |
| "Mocking makes tests reliable." | It makes them deterministic — and possibly wrong, if the mock drifts from reality. |
| "More retries = more stability." | Retries hide instability; they do not remove it. |
| "Emulating an iPhone tests the iPhone." | It tests layout in a desktop engine with a phone's size and user agent. |

## A.5 Quiz

1. Name the three processes involved in a Playwright click.
2. Why is `page` function-scoped?
3. `get_by_role("button", name="Add")` matches 3 elements. Name two ways to make it match one.
4. What does "strict mode violation" protect you from?
5. Which actionability check fails when a loading overlay covers a button?
6. What is wrong with `assert not locator.is_visible()`?
7. Two routes match a URL. Which runs first?
8. Why answer telemetry with `204` instead of `abort()`?
9. Why must `state.json` never be committed?
10. What is a worker's `worker_id` without xdist? With xdist?
11. Which outcome classes should a report distinguish?
12. In the Day 7 retry test, why `xfail(strict=True)` and not `skip`?
13. What did `test_selected_variant_is_what_the_server_receives` read, and what did it mock?
14. Why is the Day 7 journey test P1 but the 404 check not in the e2e suite at all?
15. What made the business steps visible in the Day 7 trace?

<details>
<summary><b>Answers</b></summary>

1. Python test → Playwright driver (Node.js) → browser.
2. A page lives in a context that holds cookies and storage; sharing it leaks state between tests.
3. `exact=True`; a longer/unique name; scope it inside its card with `filter(has=...)` and chaining.
4. Acting on the wrong one of several matching elements (for example a hidden duplicate).
5. "Receives events" — the log says "`<div id=overlay>` intercepts pointer events".
6. It reads once; the element might appear a moment later. Use `expect(locator).to_be_hidden()`.
7. The one registered last; `fallback()` hands over to the earlier one.
8. Aborted requests were retried by the telemetry script; an empty `204` is accepted and ends the retries.
9. It is a live session (anyone with the file is logged in) and it expires.
10. `master`; `gw0`, `gw1`, …
11. Passed, failed (product defect), blocked (environment), xfail (known defect), skipped/manual — and reruns shown separately.
12. `strict` makes the run fail when the defect is fixed (XPASS), so the test is updated; `skip` would hide the change forever.
13. It read the `POST /cart/add.js` body (`id=<variant id>`). Nothing was mocked.
14. The journey covers High-risk money and cart behaviour across pages; REQ-09 is Low risk and already covered by BDD and page tests.
15. `business_step(...)`, which calls `context.tracing.group(title)` / `group_end()`.
</details>

## A.6 Peer review of Day 7 tests (20 min)

In pairs, swap your new Day 7 test and review it with the **Day 5 + Day 6 checklist**:

| # | Check | ✔ / ✘ / evidence |
|---|---|---|
| 1 | Role/label locators; CSS only inside page objects | |
| 2 | No `.nth()` / `.first` unless order is the behaviour | |
| 3 | Page facts through `expect` | |
| 4 | Server-changing actions wait for evidence | |
| 5 | No `sleep`, `wait_for_timeout`, `force=True`, raised global timeouts | |
| 6 | Own data and context; no order dependence | |
| 7 | Volatile data read at runtime or checked as a rule | |
| 8 | Extra contexts from `new_context` / `new_shop` | |
| 9 | Locale / time zone / viewport explicit | |
| 10 | Passes repeated, in parallel (offline), and in random order | |
| 11 | Traces and screenshots kept on failure | |
| 12 | Mocked flows have a live twin | |
| 13 | Routes scoped and removed when no longer needed | |
| 14 | No credentials in code, reports, or committed state | |
| 15 | Unique data/accounts per worker; serial against third parties | |
| 16 | Outcomes classified; reruns visible; evidence linked | |

Write each ✘ as a finding in Day 4's format (observation, evidence, impact, recommendation, severity, effort).

---

# Session B — Reliability and Maintainability Patterns (120 min)

## B.0 Plan and levels

| Time | Part |
|---|---|
| 0–10 | B.1 — A vocabulary for failures |
| 10–35 | B.2 — Failure analysis: the course's real failure casebook |
| 35–60 | B.3 — Flaky-test control |
| 60–80 | B.4 — Tracing diagnostics |
| 80–100 | B.5 — Stability improvement patterns |
| 100–115 | B.6 — Maintainability criteria |
| 115–120 | B.7 — Your reliability policy |

| Badge | After this level you can… |
|---|---|
| 🟢 | Classify a failure and name its likely cause |
| 🟡 | Diagnose a failure from its evidence and choose the right fix pattern |
| 🔴 | Set a team policy for flaky tests, retries, quarantine, and maintainability — and measure it |

### Glossary

| Term | Meaning | Vietnamese |
|---|---|---|
| Failure analysis | Finding the real cause of a failed test | Phân tích lỗi |
| Root cause | The cause that, once removed, stops the failure | Nguyên nhân gốc |
| Flaky test | Passes and fails without any code change | Test chập chờn |
| Flake rate | Share of runs in which a test failed and then passed on retry or rerun | Tỉ lệ chập chờn |
| Quarantine | Moving a known-flaky test out of the blocking suite, with an owner and a deadline | Cách ly test |
| Retry | Running a failed test again automatically | Chạy lại |
| Determinism | Same input, same result, every time | Tính tất định |
| Stability budget | The flake rate a team accepts, and acts on when exceeded | Ngân sách ổn định |
| Maintainability | How cheaply tests can be changed when the product changes | Khả năng bảo trì |

---

## B.1 A vocabulary for failures 🟢

Every failed test has one of four owners. Naming the owner first prevents the most expensive mistake: "fixing" the test when the product is broken, or filing a product bug when the test is wrong.

| Class | Meaning | Who acts | Example from this course |
|---|---|---|---|
| **Product defect** | The application does the wrong thing | Developers | Failed Add to Cart shown as "Sold Out" (Day 7, D-01) |
| **Test defect** | The test's locator, wait, data, or assertion is wrong | Test author | A hard-coded tax amount of £18.33 (Day 5) |
| **Environment** | Network, bot protection, outages, rate limits | Ops / rerun later | Cloudflare check; HTTP 429 (Days 3, 4) |
| **Framework / tooling** | The test infrastructure itself is wrong | Framework owner | Tag validator that checked nothing (Day 3) |

A **flaky** test is not a fifth class: it is a test whose failures come and go, and its root cause still belongs to one of the four.

---

## B.2 Failure analysis: the course's casebook 🟡 → 🔴

Each case: **symptom** (what you saw) → **evidence** (what proved the cause) → **root cause** → **fix pattern**.

### Case 1 — "The cart has 1 item, but I added 2" (test defect, timing)

| | |
|---|---|
| Symptom | After clicking Add to Cart twice, the cart showed 1 — sometimes |
| Evidence | Waiting on `wait_for_load_state("networkidle")` returned **immediately**; the second `POST /cart/add.js` had not finished |
| Root cause | A load state is reached once per page load; it cannot wait for later AJAX work |
| Fix pattern | **Wait for the evidence of the action**: `expect_response("/cart/add")` around each click |

### Case 2 — "Every test fails with a timeout" (environment)

| | |
|---|---|
| Symptom | 8 scenarios passed, then every following test timed out on ordinary elements |
| Evidence | The failure screenshot showed Cloudflare's *"Your connection needs to be verified"* page |
| Root cause | Bot protection after a burst of automated traffic |
| Fix pattern | **Detect and classify** (`EnvironmentBlockedError` → `BLOCKED`), **reduce load** (catalogue once, API setup, serial runs). Never try to bypass it |

### Case 3 — "Three scenarios blocked, but the ones between them pass" (framework)

| | |
|---|---|
| Symptom | Only the scenarios using API setup were reported `BLOCKED` |
| Evidence | The real responses: `/cart.js` and `/cart/add.js` return valid JSON labelled `text/javascript` |
| Root cause | The blocked-page detector judged the `Content-Type` header, not the body |
| Fix pattern | **Judge the content, not the label**; suspect the detector when its "blocked" results do not cluster in time |

### Case 4 — "Green with broken tags" (framework, silent)

| | |
|---|---|
| Symptom | Nothing — the run stayed green |
| Evidence | A deliberate negative test (break a tag, expect a failure) did not fail |
| Root cause | pytest-bdd 9 no longer sets the attribute the validator relied on, so it checked zero scenarios |
| Fix pattern | **Every guard gets a test that proves it can fail**; add a fail-loud check when the guard finds nothing to check |

### Case 5 — "A rename broke a different scenario" (test defect, maintainability)

| | |
|---|---|
| Symptom | Renaming `{name}` to `{product}` in one step made another scenario fail with `quantity_of('Noir jacket" in variant "L / Red')` |
| Evidence | Review tool: one Gherkin line matched two definitions; pytest-bdd's source picks the last registered |
| Root cause | A greedy `"{name}"` placeholder also matched text containing quotes |
| Fix pattern | **Remove ambiguity by construction** (`{name:Quoted}`) and **enforce it** (`framework.review --strict` in CI) |

### Case 6 — "strict mode violation: resolved to 2 elements" (test defect, locator)

| | |
|---|---|
| Symptom | Filling the cart's quantity box failed |
| Evidence | The error listed two elements with the same id: the visible cart and a **hidden mini-cart** |
| Root cause | Duplicate markup (a testability defect of the shop) and a CSS locator that saw hidden elements |
| Fix pattern | **Scope** locators to the visible region; prefer role locators (they ignore hidden elements) |

### Case 7 — "My Cart (0) right after adding" (test defect, timing)

| | |
|---|---|
| Symptom | Reading the header right after the server confirmed the add showed the old number |
| Evidence | The response had arrived; the header text changed a moment later |
| Root cause | The UI updates **after** the server answers |
| Fix pattern | Read UI facts with **`expect`** (`expect_cart_count(n)`), not a one-off read |

### Case 8 — "The tax line disappeared" (test defect, volatile data)

| | |
|---|---|
| Symptom | `included_tax` was `None` instead of £18.33 |
| Evidence | Same failure with locale en-GB and en-US; the checkout showed an empty "Taxes" row |
| Root cause | Shopify's checkout content varies between sessions; the test hard-coded a value nobody required |
| Fix pattern | Check volatile data **only when present** and **as a rule** (VAT = total ÷ 6) |

### Case 9 — "An empty traceability table in parallel" (framework, parallel)

| | |
|---|---|
| Symptom | `pytest -n 2` printed the matrix header with no rows |
| Evidence | Tags were collected inside the workers; the summary ran in the main process |
| Root cause | Plugin state kept in the wrong process |
| Fix pattern | Carry data **inside test reports** (`report.keywords`, `user_properties`), which workers send to the main process |

### Case 10 — "A different time zone name" and "a 980-pixel phone" (test defect, assumptions)

| | |
|---|---|
| Symptom | `Asia/Saigon` instead of `Asia/Ho_Chi_Minh`; `innerWidth` 980 instead of 390 |
| Evidence | Chromium reports ICU canonical names; the page had no `<meta name="viewport">` |
| Root cause | The test checked a spelling and assumed responsive markup |
| Fix pattern | **Assert effects, not representations** (UTC offset); treat surprising emulation results as possible product findings |

### What the casebook says

| Class | Cases |
|---|---|
| Test defect | 1, 5, 6, 7, 8, 10 |
| Framework / tooling | 3, 4, 9 |
| Environment | 2 |
| Product defect | Found separately by tests that worked (mini-cart, D-01) |

Most failures were **test or framework defects**, and most were found **because the framework made them visible**. That is the normal picture — and the reason the next three parts exist.

> **Checkpoint B.2.** For case 7, what would a team that "fixes" it with `time.sleep(1)` have gained and lost?

---

## B.3 Flaky-test control 🟡 → 🔴

### B.3.1 🟢 Where flakiness comes from

| Cause | Typical sign | Course example |
|---|---|---|
| Timing / asynchronous UI | Fails more on slow machines or CI | Cases 1, 7 |
| Shared state / order | Passes alone, fails in the suite (or vice versa) | Day 5 shared-context demonstration |
| Volatile data | Fails after the site's content changed | Case 8 |
| External dependencies | Fails in bursts, for many tests at once | Case 2 |
| Resource contention | Fails only with high `-n` | (Avoided: serial against the shop) |
| Test infrastructure | Odd patterns that do not match product behaviour | Cases 3, 9 |

### B.3.2 🟡 Detect before users of the suite lose trust

| Method | How |
|---|---|
| Repeat | `pytest-repeat --count N` on new or changed tests |
| Random order | `pytest-randomly` with a few seeds |
| Parallel | `-n 4` on offline/owned environments |
| History | Record per-test outcomes from CI; a test that both failed and passed on the same code is flaky |
| Rerun counts | If retries exist, report them (Day 6: JUnit XML hides them) |

### B.3.3 🔴 Retries: a tool with a price

`pytest-rerunfailures` can retry; it can also be **narrow**:

```bash
pytest --reruns 1 --only-rerun "EnvironmentBlockedError"
```

| Policy | Senior position |
|---|---|
| Blanket `--reruns 3` on everything | No: turns a 1-in-5 failure into "green" and hides timing bugs |
| Retry only **classified environment** errors (`--only-rerun`), once, with a delay | Acceptable: the cause is known and outside the product |
| Retry assertion failures | No: an assertion failure is information |
| Any retry | Must be **visible** in the report and counted in the flake rate |

The per-test marker exists too (`@pytest.mark.flaky(reruns=1)`); treat it like `force=True` — a review finding unless the reason is written next to it.

### B.3.4 🔴 Quarantine: isolate, own, fix

When a test is flaky and the fix is not immediate:

```python
@pytest.mark.quarantine(owner="qa-team", issue="QA-123", until="2026-12-01")
```

| Rule | Why |
|---|---|
| Quarantined tests still **run** (separate job, non-blocking) | You keep evidence and notice when they recover |
| Every quarantine has an **owner**, an **issue**, and an **expiry** | Otherwise quarantine becomes a graveyard |
| A quarantined High-risk test is a **release risk**, reported as such | The behaviour it protects is now unprotected |
| Expired quarantine fails the build | Forces a decision: fix or delete |

(A `quarantine` marker would be registered like any other; the expiry check is a small collection hook — the same technique as the tag rules in Unit 1.)

### B.3.5 🔴 A stability budget

Set a number and act on it, for example:

| Metric | Budget | When exceeded |
|---|---|---|
| Flake rate of the blocking suite | < 1 % of test runs per week | Stop adding tests; fix the top offenders |
| Quarantined tests | ≤ 3, none older than 2 weeks | Fix or delete |
| `BLOCKED` runs | Reported weekly | Escalate the environment (owned staging, allow-list) |

---

## B.4 Tracing diagnostics 🟡 → 🔴

### B.4.1 🟡 One routine for every failure

1. **Classify the symptom** from the error type and message (call log line, `EnvironmentBlockedError`, `CartInconsistencyError`, plain `AssertionError`).
2. **Open the evidence at the failing step**: the business-step group in the trace (Day 7), the step screenshot and JSON (Unit 1).
3. **Look before and after**: the DOM snapshot before the failing action shows what the test saw.
4. **Check the network around it**: a failed, slow, or unexpected request just before the failure.
5. **Check the console**: JavaScript errors from the page.
6. **Name the owner** (B.1) and write the finding with its evidence.

### B.4.2 🟡 Where each failure class shows itself

| Class | Strongest evidence | What you see |
|---|---|---|
| Timing | Call log + network timing | The action happened before the response it depended on |
| Locator | Call log | "strict mode violation …", "waiting for get_by_role(...)" and the element absent in the snapshot |
| Data | Snapshot + assertion message | The page shows a different (valid) value than the test expected |
| Environment | Screenshot / snapshot | A page that is not the application (bot check, error page), HTTP 403/429/503 |
| Product defect | Snapshot + network + console | The application did the wrong thing after a correct request |
| Framework | Patterns across tests | Results that do not cluster like real failures (case 3), or no failures where some are expected (case 4) |

### B.4.3 🔴 Make traces easy to read before you need them

| Practice | Benefit |
|---|---|
| `business_step` groups | The trace reads like the workflow |
| Assertion messages with the whole state (`cart.describe()`) | Often no trace needed at all |
| Business-step evidence (Unit 1 `step_error` hook) | Screenshot of the exact step, plus browser console and failed requests |
| `retain-on-failure` | Traces exist exactly when needed (one Day 7 trace: 9.8 MB) |
| Unique, readable test names | The artifact folder name says which test it is |

---

## B.5 Stability improvement patterns 🟡 → 🔴

| Pattern | Removes | Course implementation |
|---|---|---|
| Wait for evidence, not time | Timing flakiness | `expect_response`, `wait_for_url`, `expect(...)` |
| Fresh context per test | Shared state | pytest-playwright `context`/`page`; `new_shop` |
| Setup through the API | Slow, fragile UI setup | `StoreApi.add_lines` |
| Data read at runtime / rules instead of values | Volatile data | Catalogue prices; VAT = total ÷ 6; "any sold-out product" |
| Pinned context options | Machine-dependent results | `locale="en-GB"`, `timezone_id="Europe/London"` |
| Isolate from third parties | External flakiness | `silence_third_parties` (204) |
| Detect and classify the environment | False product failures | `EnvironmentBlockedError` → `BLOCKED` |
| Cross-layer checks | Silent wrong data | Cart page vs cart JSON vs header |
| Push checks down the pyramid | Too many slow e2e tests | Day 7 decisions: REQ-09 not duplicated at e2e |
| Low load on shared systems | Rate limits | Catalogue once, cart snapshot cache, serial live runs |
| Guards with negative tests | Silent framework bugs | Architecture tests, review tool tests |

And three anti-patterns to remove on sight: `sleep` / `wait_for_timeout`; `force=True`; global timeouts raised "to be safe".

---

## B.6 Maintainability criteria 🟡 → 🔴

### B.6.1 🟢 The real measure

> **When the product changes, how many files must change, and how fast do you know which?**

A theme rename of "Add to Cart" should change **one** page-object line, and the failure should name that locator. In this framework it does.

### B.6.2 🟡 Criteria and how to check them

| Criterion | Good sign | How to check |
|---|---|---|
| Single place per knowledge | A locator, URL, or rule exists once | Architecture tests (selectors only in pages/components); pylint duplicate-code |
| Layering | Tests → page objects → Playwright; steps → port | Architecture tests; imports |
| Readability | A test reads as its workflow | Business steps; names; no technical noise in Gherkin |
| Small, typed units | Short functions, typed values (`Money`, `Cart`) | `mypy --strict`; complexity ≤ 10 |
| Explicit configuration | Options in one place, overridable | `Settings`, `browser_context_args`, `pyproject.toml` |
| Test data builders | No hand-built records in tests | `new_customer()`, `unique_email()` |
| Self-checking framework | Guards fail when broken | Unit tests for tools; negative tests |
| Documented decisions | Why a test is `xfail`, skipped, or manual | Reasons in markers and feature files; README defect table |

### B.6.3 🔴 Page objects: what belongs inside

| Inside a page object | Outside (in the test) |
|---|---|
| Locators and readiness waits (`wait_until_loaded`) | Business assertions ("the total is correct") |
| Actions with their evidence waits (`add_to_cart`) | Test data choices |
| Reading the page into domain objects (`read() → Cart`) | Network mocking for a specific test |
| Knowledge of the page's quirks (hidden duplicates, unlabeled fields), with a comment | Cross-page journeys |

Page objects in this course return **domain objects**, not raw strings, so tests compare `Money` with `Money` and never parse text.

### B.6.4 🔴 A code-review checklist for Playwright code

| Ask | Red flag |
|---|---|
| Would a theme change touch more than one file? | Selector in a test |
| Does the test read like the workflow? | Twenty raw actions without steps |
| Is every wait tied to evidence? | A sleep, a raised timeout |
| Is every `xfail`/`skip`/`flaky`/`force` explained? | A marker without a reason |
| Can this run in any order, in parallel (offline)? | Module-scoped page, fixed file paths |
| Would a failure explain itself? | `assert a == b` with no message on a complex value |

---

## B.7 Your output: the team reliability policy (one page)

| Topic | Your policy |
|---|---|
| Failure classes and who acts on each | |
| Retry policy (what may be retried, how often, how it is reported) | |
| Quarantine rules (owner, issue, expiry, separate job) | |
| Stability budget and the action when it is exceeded | |
| Evidence policy (what is kept, how long, who can see it) | |
| Environment policy (where parallel runs are allowed; how `BLOCKED` is handled) | |
| Maintainability gates (lint, types, architecture tests, review tool) | |
| Review checklist used for every new Playwright test | |

---

## Self-check (answers below — try first)

1. Name the four failure owners and give one course example of each.
2. Which course failures were found only because a guard was tested by breaking things on purpose?
3. Why is "retry assertion failures" the wrong policy, while "retry classified environment errors once" can be acceptable?
4. What three things must every quarantined test have?
5. A test fails only with `-n 8`. Which cause class do you suspect first, and what do you check?
6. Where in a trace do you look first for a locator problem, and for an environment problem?
7. Why do this course's page objects return domain objects rather than strings?
8. What single question measures maintainability, and how does this framework answer it for a renamed button?

<details>
<summary><b>Answer guide</b></summary>

1. Product (D-01, failed Add to Cart shown as "Sold Out"); test (hard-coded £18.33 tax); environment (Cloudflare check / HTTP 429); framework (tag validator that checked nothing).
2. Case 4 (silent tag validator) and the architecture tests' proof; also the review tool's ambiguity (case 5), proven by a rename experiment.
3. An assertion failure means the product or the test is wrong — retrying hides information. A classified environment error has a known cause outside the product; one visible, delayed retry saves a rerun without hiding a defect.
4. An owner, an issue/ticket, and an expiry date — and it keeps running in a separate, non-blocking job.
5. Shared state or resource contention (or shared accounts/data). Check fixtures' scopes, fixed paths/ports, accounts per worker, and whether the environment rate-limits.
6. Locator: the call log of the failing action and the "before" snapshot. Environment: the screenshot/snapshot (is it the application at all?) and HTTP statuses in the network panel.
7. Tests compare typed values (`Money`, `Cart`) instead of parsing text in every test; parsing lives once, in the page object.
8. "When the product changes, how many files change, and how fast do you know which?" A renamed button changes one locator line in one page object, and the failing test's call log names that locator.
</details>

## Next

Unit 3 — Mobile and asynchronous-system testing (Day 9: Appium architecture, capabilities, locators, gestures, synchronization, and mobile evidence).
