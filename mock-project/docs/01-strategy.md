# Test strategy — Swag Labs mock project

| | |
|---|---|
| Product | Swag Labs, https://www.saucedemo.com — a demo web shop (React single-page app) |
| Owner of the product | Sauce Labs (third party: we do **not** own it) |
| Test approach | Risk-based; BDD scenarios automated with Playwright; one run per persona and browser |
| Covers | LO1 (risk and testability), with links to how LO2–LO9 are met |

## 1. Product and context

Swag Labs is a small shop: log in → browse six products → cart → three-step checkout. It is
built for testing practice, which gives it two properties that shape this strategy:

1. **Personas with built-in faults.** Six demo accounts share one password (printed on the login
   page). `standard_user` behaves; the others inject faults — `problem_user` (broken images,
   sorting, buttons, form fields), `error_user` (JavaScript errors), `visual_user` (wrong prices
   and images), `performance_glitch_user` (5-second delays), `locked_out_user` (cannot log in).
   We treat them as a **fault-injection matrix**: the same suite runs once per persona, and a
   register (`findings.toml`) states which scenarios each persona must break.
2. **We do not own it.** No server access, no logs, no database, no load testing. Everything we
   learn comes from the browser. That limits telemetry to client-side measurements and forbids
   anything heavier than a handful of real users would generate.

## 2. Scope

**In scope** (requirements REQ-SL-01 … REQ-SL-15 in `requirements.toml`)

- Login, logout, sessions and protected pages (REQ-SL-01…03)
- Catalogue content, sorting, product pages (REQ-SL-04…06)
- Cart: add, remove, persistence, two tabs, double clicks (REQ-SL-07, 08)
- Checkout: validation, totals with 8 % tax, completion (REQ-SL-09…11)
- Reset App State (REQ-SL-12)
- Asynchronous content: spinner, lazy loading, auto-rotating slider (REQ-SL-13)
- Response-time budgets of key interactions, single user (REQ-SL-14)
- Phone-sized touch screen (REQ-SL-15)

**Out of scope, and why**

| Item | Reason | Where it is handled instead |
|---|---|---|
| Visual layout (REQ-SL-16) | Pixel comparison needs approved baselines per browser × viewport and a review workflow; without them it only produces noise | `@manual` scenario; checked by hand |
| Load and stress tests | Not our system: load on a third party is abuse. Stress tests run only on systems we own | Unit 4 (JMeter on our own sandbox) |
| Payment | Swag Labs has no real payment; real payment data is never entered anywhere | — |
| Native mobile apps | Swag Labs is a web app; its mobile story is the responsive site | Phone-sized browser context (REQ-SL-15); native Appium in Unit 3 |
| Security testing (scanning, injection) | Not authorised on a third-party site | Security review of OUR pipeline in [05-defense.md](05-defense.md) |
| About page, social links | Leave the product (saucelabs.com, social sites) | — |

## 3. Risk register

Score = likelihood (1–5) × impact (1–5). Bands: **high** 15–25, **medium** 8–14, **low** 1–7.
The band of each requirement is in `requirements.toml`, and every scenario's `@risk-*` tag must
equal the highest band of its requirements (enforced at collection time).

| Risk | L | I | Score | Requirement | Mitigation in the suite |
|---|---|---|---|---|---|
| Customer cannot log in, or the wrong person can | 3 | 5 | 15 high | SL-01, SL-02 | Login per persona; refused-credentials outline; error message and field state checked |
| Pages reachable without a session | 3 | 5 | 15 high | SL-03 | Direct navigation to 3 protected pages; logout then revisit; Back after logout |
| Wrong items or amounts in the cart | 4 | 5 | 20 high | SL-07 | Add/remove on both pages, every product, double click, badge vs stored state |
| Order with wrong/missing customer data | 4 | 4 | 16 high | SL-09 | Each missing field; every typed value verified in the field |
| Wrong amount charged | 3 | 5 | 15 high | SL-10 | Overview totals vs an independent oracle (Decimal, half-up rounding) |
| Order not placed / cart not emptied | 3 | 5 | 15 high | SL-11 | Finish → confirmation; badge and stored cart empty |
| Wrong price or picture shown | 4 | 3 | 12 medium | SL-04, SL-06 | Every card vs the reference catalogue; card vs product page |
| Sorting broken | 3 | 3 | 9 medium | SL-05 | Every order compared by NAME order (deterministic) |
| Cart lost between pages or tabs | 3 | 3 | 9 medium | SL-08 | Navigation + reload; second tab; eventual consistency check |
| Async content shows stale/partial data | 3 | 3 | 9 medium | SL-13 | State-based waits; tile-number continuity; slider history |
| Slow interactions lose customers | 3 | 4 | 12 medium | SL-14 | Budgets per interaction; network/client split |
| Unusable on a phone | 3 | 3 | 9 medium | SL-15 | Touch + narrow viewport; Pixel 7 emulation job |
| Reset leaves stale state | 2 | 2 | 4 low | SL-12 | Reset scenarios |
| Layout regressions | 2 | 3 | 6 low | SL-16 | Manual |

### Testability assessment

| Aspect | Finding | Consequence for the design |
|---|---|---|
| Locators | Almost every element has a stable `data-test` attribute | Page objects use `data-test` first; roles where they add meaning (menu buttons, spinner `role=status`) |
| State | Session = one cookie (`session-username`); cart = `localStorage["cart-contents"]` | Fast, honest set-up: log in by cookie, seed the cart in storage — guarded by a contract scenario |
| Oracles | No API to ask for truth | A recorded reference catalogue (`swaglabs/data/catalogue.json`) and a computed order summary |
| Determinism | visual_user prices are random; the slider rotates by itself; lazy tiles load when on screen | Assert on deterministic properties (name order, history, invariants), never on one racy snapshot |
| Observability | Only the browser | Network listener, console errors, dialogs, client-side timings, screenshots, traces |
| Third parties | Error reports go to an external tracker; fonts from Google | Allow-list network policy: the shop and its fonts only |

### Severity scale

| Severity | Meaning |
|---|---|
| critical | A purchase is blocked, or the customer is charged/shown wrong money; no workaround |
| major | A main function fails, but there is a workaround, or it hurts many users |
| minor | Cosmetic or rare; the journey still completes |

## 4. Approach

**Cross-platform.** One suite, many targets: personas × browsers × device emulation. The CI
matrix runs all five usable personas on Chromium, `standard_user` on Firefox and WebKit, and a
Pixel 7 emulation; every scenario also runs in a phone-sized touch context when tagged `@phone`.

**Levels.** Unit and plugin tests (no browser) guard the framework itself; BDD scenarios in a
real browser test the product; the CI matrix and the merged quality matrix give the release view.

**Selection.** `@smoke` = 9 critical scenarios for every change; `@regression` = everything;
`@persona-independent` scenarios (they log in with their own explicit users) run only in the
`standard_user` job.

**Known defects.** A defect is registered once in `findings.toml`, linked to a requirement and
an area. Scenarios with that area become **strict** expected failures for the affected personas.
The matrix reports them as KNOWN DEFECT (never as passed), and a fix turns the run red until the
register is updated — the register cannot silently rot.

**Entry criteria.** Lint, strict types, unit/plugin tests with ≥ 90 % branch coverage, and the
coverage gate (every requirement and every finding has a scenario) are green.

**Exit criteria (release view).** In the merged quality matrix: no FAIL in any run; every high-risk
requirement PASS for `standard_user` on all three browsers; every KNOWN DEFECT has an owner and a
decision (fix or accept) — see the quality matrix artifact of the CI run.

## 5. How the learning outcomes are met (no AWS)

| LO | Where |
|---|---|
| LO1 risk, testability, cross-platform strategy | This document |
| LO2 BDD: steps, hooks, tags, reporting, evidence | `features/`, `tests/steps/`, `swaglabs/plugins/`, [02-architecture.md](02-architecture.md) |
| LO3 reliable Playwright: fixtures, isolation, tracing, network control, parallel | `swaglabs/plugins/browser.py`, `swaglabs/network.py`, `-n 4`, traces on failure |
| LO4 containers | `docker/Dockerfile`, `docker/compose.yaml`, [04-execution-and-evidence.md](04-execution-and-evidence.md) |
| LO5 mobile with synchronisation | `@phone` scenarios, Pixel 7 job, touch actions; native Appium: Unit 3 |
| LO6 async: retries, duplicates, ordering, eventual consistency | `features/dynamic_catalogue.feature`, cart two-tab and double-click scenarios, `swaglabs/waiting.py` |
| LO7 distributed execution with retained artifacts (instead of ECS/Fargate + Device Farm) | GitHub Actions matrix of containers; artifacts kept 14/30 days |
| LO8 performance evidence and bottlenecks (instead of CloudWatch) | `perf-budgets.toml`, `swaglabs/perf.py`, `reports/perf.md` |
| LO9 defend the solution | [05-defense.md](05-defense.md) |
