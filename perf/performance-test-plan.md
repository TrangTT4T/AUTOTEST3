# Performance Test Plan (PTP) — order-events sandbox and BlazeDemo

Structured after ISTQB CT-PT, chapter 4 (Performance Testing Tasks). Each section names the
file that **implements** it, so the plan cannot drift from what actually runs: the load profile
is checked against the script by `tests/unit/test_jmeter_plans.py`, and the objectives are
checked against every run by `python -m framework.perf.gate`.

| | |
|---|---|
| Systems under test | **Order-events sandbox** (`sandbox/`, ours: any load allowed) · **BlazeDemo** (third party: light load only) |
| Tool | Apache JMeter 5.6.3, non-GUI; analysis in `framework/perf/` |
| Owner | the test team of this course project |
| Status | executed in CI on every push (smoke, load profile) and by hand (Day 16 capacity experiment) |

---

## 1. Objectives (CT-PT 4.1.1)

Objectives come from stakeholders, not from the tool. Two kinds, kept apart:

| Id | Kind | Objective | Source | Measured as | In |
|---|---|---|---|---|---|
| O1 | user-based | An order is shipped within 2 s for 95 % of customers | Requirement REQ-13 (consistency target) | p95 of `J1 Place order and track` ≤ 2000 ms | `sla.toml [sandbox_profile]` |
| O2 | user-based | The order button answers at once | UX guideline: < 0.2 s feels instant | p95 of `J1.1 Submit order` ≤ 200 ms | same |
| O3 | user-based | The status page answers at once | same | p95 of `J2 Check order status` ≤ 300 ms (think time excluded) | same |
| O4 | user-based | No failed journeys at the planned load | Business: a failed order is a lost sale | errors ≤ 1 % (J1), 0 % (J2) | same |
| O5 | technical | The system sustains the planned peak: 4 journeys/s (1.2 orders/s + 2.8 status checks/s) | Capacity plan (section 5) | throughput ≥ 75 % of plan per journey, in the steady state | same |
| O6 | technical | No message ends in the dead-letter queue | Operations: dead letters need manual work | `/metrics` `dead_letters` = 0 after the run | tearDown check |
| O7 | technical | Find the first saturated component and its limit | Architecture review (Day 16) | queue depth vs consumer rate (telemetry) | `framework/perf/correlate.py` |
| O8 | user-based | BlazeDemo journey steps answer within 1.5–2 s at 5 users | Practice target (third party) | p95 per step | `sla.toml [blazedemo]` |

## 2. System overview

```
customer ─HTTP/JSON─► POST /orders ─► broker ─► payments ─► fulfilment ─► projector ─► GET /orders/{id}
                                          │ (asynchronous, at-least-once, with a dead-letter queue)
                                          └─► /metrics (queue depth, processed, dead letters)
```

One process on the load generator's host (port 8765), started fresh for each run, so every run
begins from the same empty state. Protocols (CT-PT 4.2.1): **HTTP/1.1 with JSON (REST)** for the
sandbox, **HTTPS with HTML forms** for BlazeDemo. Other families you will meet elsewhere:
SOAP/XML web services, JDBC/ODBC directly against a database, WebSocket (the sandbox's live
status feed, not load-tested here), MQTT/CoAP for IoT devices.

## 3. Test types

| Test | Plan | Load | Purpose | When |
|---|---|---|---|---|
| Smoke / baseline | `orders_sandbox.jmx` | 5 users, 30 s | the script works; a baseline for comparison | every push |
| **Load (profile)** | `orders_sandbox_profile.jmx` | operational mix, ramp-up → steady → ramp-down | O1–O6 at the planned peak | every push (shortened) and by hand (full) |
| Capacity | `orders_sandbox.jmx` | 40 users, then fixes | O7: where is the limit, what saturates | Day 16, by hand |
| Light journey | `blazedemo_purchase.jmx` | ≤ 10 users, ≤ 300 s (enforced by a setUp guard) | O8; practising correlation on a real site | by hand only |
| Stress, spike, soak | — | — | only on systems we own and with an agreed window; not scheduled in this course | — |

## 4. Acceptance criteria

`perf/sla.toml` holds every number in section 1. The gate **fails closed**: too few samples, a
missing label, or a results file without the needed columns is a failure, never a pass. The load
profile is judged on its **steady state only** (`[steady_state.sandbox_profile]`); set-up and
verification checks are judged on the whole run (`window = "whole"`).

Baseline: the smoke run of every push is the baseline the load results are compared with; a
change of more than 20 % in p95 at the same load is investigated even when it is within the SLA.

## 5. Operational profile → load profile (CT-PT 4.2.3, 4.2.4, 4.2.5)

**Operational profile** (who does what at the peak hour) — `perf/workload.toml`:

| Journey | Share | What the user does | Think time |
|---|---:|---|---|
| J1 Place order and track | 30 % | submits an order, watches the status until "shipped" | none inside the journey |
| J2 Check order status | 70 % | opens the confirmation link from the e-mail | 1–3 s (reads the e-mail) |

The mix is an **assumption** for a small shop and is labelled as such; in a real project it comes
from access logs ("70 % of sessions only check an order").

**Load profile** — derived by `python -m framework.perf.model perf/workload.toml`:

| Journey | Rate /s at peak | R s | Z s | Concurrent users N = X(R+Z) |
|---|---:|---:|---:|---:|
| J1 Place order and track | 1.20 | 1 | 0 | 1.2 |
| J2 Check order status | 2.80 | 0.05 | 2 | 5.7 |
| **Total** | **4.00** | | | **6.9** |

Shape: **ramp-up 20 s → steady state 60 s at 4 journeys/s → ramp-down 20 s** (open workload:
journeys *arrive* at the rate, as on a public website; ~320 journeys per run).

Two laws, one meaning: **N = X × (R + Z)** (Little) and **X = N / (R + Z)** (interactive response
time). 500 users who each query once a minute produce 30 000 queries/hour; the same 500 users
querying once an hour produce 500 — concurrency alone says nothing about load. Check of the
model against a real run: predicted 6.9 concurrent users, **measured 7.0** (mean active threads
in the steady state).

## 6. Test data

| Data | How | Why |
|---|---|---|
| Orders for J2 | **seeded** by the setUp group (20 orders), checked "shipped" before the load starts | J2 needs existing orders; seeding makes every run start equal |
| Order ids | **correlated**: extracted from each response (`$.order_id`), never hard-coded | ids are generated by the system |
| Status-check targets | **parameterised**: a random seeded order per J2 journey | spreads reads; avoids one hot, cached record |
| Correlation ids | `PERF-<run>-…` | test traffic is recognisable in logs and can be cleaned up |
| BlazeDemo routes | `perf/data/blazedemo_routes.csv`, fictional passengers | no personal data, ever |
| Production data | never used | GDPR: test data must not identify real people |

## 7. Environment and configuration

| Item | Value | Consequence |
|---|---|---|
| SUT | sandbox, single process, in-memory | not production-sized: results show **relative** behaviour and bottlenecks, not production capacity |
| Load generator | the same host (CI runner / laptop) | watch its CPU: above ~80 % the generator becomes the bottleneck |
| Time | one host clock for JMeter, telemetry and the SUT | no clock skew between the tools (CT-PT 4.3: time synchronisation) |
| External services | the sandbox simulates payment and fulfilment (service virtualisation) | no real payment provider is ever called |

## 8. Scripts (CT-PT 4.2.2, 4.2.6, 4.2.7)

`perf/orders_sandbox_profile.jmx`:

| Script part (CT-PT) | JMeter element | Does |
|---|---|---|
| Initialisation (`vuser_init`) | setUp thread group "Prepare" (`stoptest` on error) | validates the environment (`GET /health`), seeds 20 orders, waits until they are visible |
| Main / action | Open Model Thread Group "Shoppers" | arrivals by the schedule; an If-controller mix of J1/J2 |
| Transactions | Transaction Controllers, **nested**: `J1` = `J1.1 Submit order` + `J1.2 Wait until shipped`; `J2` | per-step and end-to-end times; think time excluded where it is not response time |
| Timers | Uniform Random Timer 1–3 s (think time); Constant Timer (poll interval) | realistic pacing |
| Verification and error handling | Response/JSON assertions on **every** request; a check sampler "order shipped within the poll budget" | a fast error page is not a fast order |
| Synchronisation points | the While-controller poll waits for the asynchronous state | an async result is waited for, not assumed |
| Clean-up (`vuser_end`) | tearDown thread group "Verify" | dead-letter queue empty; records whether the run was aborted |

## 9. Execution (CT-PT 4.2.8, 4.3.1)

**Preparation checklist** — automated where possible:

1. Start the SUT fresh; wait for `/health` (CI step; the setUp group checks again).
2. Seed and verify the test data (setUp group).
3. Start telemetry sampling (`python -m framework.perf.telemetry`).
4. Validation run: the smoke test (5 users, 30 s) must pass its gate before the load test runs.
5. Results format pinned: `-q perf/jmeter.properties` (CSV columns, no bodies, no hidden retries).

**During the run** — real-time monitoring: JMeter's summariser prints throughput, errors and
active threads every 30 s; telemetry samples queue depths every second.

**Abort criteria** — a JSR223 listener stops the load when, after at least `abort_min_samples`
(50) load samples, the error rate exceeds `abort_error_pct` (10 %). Every later arrival then sends
nothing, and the tearDown group records `ABORTED: …` as a failed sample, so the gate fails and
the report says why. (Tested: forcing failures stopped the load after 51 samples at 11.8 %.)

## 10. Metrics

| Group | Metrics | Source |
|---|---|---|
| Virtual users | active threads over time | JTL `allThreads`, gate timeline |
| Response time | min / mean / p50 / p90 / p95 / p99 / max per transaction | gate statistics |
| Throughput | journeys/s, requests/s per label | gate statistics, JMeter dashboard |
| Errors | error %, HTTP response codes per label | gate, "Response codes" table |
| System | queue depth, processed/s per consumer, dead letters | telemetry, `/metrics` |

## 11. Analysis and reporting (CT-PT 4.4.1)

`python -m framework.perf.gate <jtl> --profile sandbox_profile --timeline-label "J2 Check order status"`
writes `reports/perf/gate-sandbox_profile.md`:

1. **Executive summary** — verdict, scope of the evidence (steady-state window, samples), first miss.
2. **Statistics** of the steady state, **objectives** with expected/actual/result.
3. **Response codes** for the whole run; **load over time** (ramp-up, steady state, ramp-down).

Pitfalls of raw results the analysis guards against: ramp-up/ramp-down samples mixed with the
steady state; journeys cut off when the test stops; averages hiding the tail; transaction
samples double-counting their children's failures; an overloaded load generator.

Recommendations follow the finding format of Unit 1 Day 4 (observation → evidence → impact →
recommendation → how to verify); Day 16 B3 is the worked example (consumers ×4 → throughput ×4).

## 12. Risks of the performance test itself

| Risk | Mitigation |
|---|---|
| The sandbox is not production-sized | report bottlenecks and ratios, never "production can take N users" |
| Load generator and SUT share a host | keep load light in CI; capacity experiments on a dedicated machine |
| Assumed operational profile | marked as assumed; replace with log analysis before any capacity decision |
| Load on a third party (BlazeDemo) | setUp guard refuses > 10 users or > 300 s; manual trigger only |

## 13. Communication (CT-PT 4.1.3)

**For business stakeholders** (one slide):
> At the planned peak (4 customer journeys per second), 95 % of orders are confirmed as shipped
> within 0.3 s against a 2 s promise, with no failed orders. The test cannot tell us the shop's
> real capacity — it runs on a small replica — but it shows where the limit will be: the
> payment and fulfilment workers (Day 16). Cost of the check: about one CI minute per change.

**For technical stakeholders** (one page): the open-model schedule and why (public traffic does
not slow down when the system does), the steady-state window, the nested transactions, the
abort rule, the seeded data, the telemetry correlation, and the repeatability: every number in
this plan is regenerated by the commands in sections 5 and 11.

---

## Coverage of the CT-PT chapter 4 learning objectives

| LO | Where in this project |
|---|---|
| 4.1.1 Derive objectives | section 1 (user-based vs technical, with sources) |
| 4.1.2 Outline a PTP | this document |
| 4.1.3 Communicate to stakeholders | section 13 |
| 4.2.1 Protocols | section 2 |
| 4.2.2 Transactions | section 8 (nested, think time excluded); `J1`/`J1.1`/`J1.2` |
| 4.2.3 Operational profiles | section 5; `perf/workload.toml` |
| 4.2.4 Load profiles | section 5; Open Model schedule; `framework/perf/model.py` |
| 4.2.5 Throughput and concurrency | section 5 (Little / interactive response-time law, verified 6.9 vs 7.0) |
| 4.2.6 Script structure | section 8 (init / action / end, timers, verification, synchronisation) |
| 4.2.7 Implement scripts consistent with the plan | the plan's defaults are tested against `workload.toml` |
| 4.2.8 Prepare for execution | section 9 checklist; setUp validation and seeding |
| 4.3.1 Run the tests | section 9: ramp-up/steady/ramp-down, monitoring, abort criteria, time synchronisation |
| 4.4.1 Analyse and report | section 11; the gate report |
