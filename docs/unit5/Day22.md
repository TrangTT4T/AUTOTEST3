# Unit 5 · Day 22 — Topic Revision (LO1–LO9), then the Mock Project Defense

| | |
|---|---|
| **Course** | Advanced Automation Test Engineering (ATEST03) — Fast Track |
| **Unit** | Unit 5 — Mock Project Design and Implementation |
| **Session A** | **Topic Revision** · Guides/Review · **240 min** · **LO1–LO9** |
| **Session B** | Assignment/Lab, part 4 of 4 · **120 min** · evidence pack and design defense (**LO9**) |
| **Code** | `mock-project/` (final), `.github/workflows/mock-project.yml` |
| **Output** | Revision answers · an evidence pack · a 10-minute defense with answers to the panel |

---

# Session A — Topic Revision (LO1–LO9) · 240 min

| Time | Block |
|---|---|
| 0–25 | A.0 The map: nine outcomes, one project |
| 25–200 | A.1–A.9 One block per LO (≈ 20 min each): key ideas → traps → quiz → "show it in the project" |
| 200–240 | A.10 Mixed scenario questions (exam style) |

## A.0 The map

| LO | Bloom | One sentence | Unit where you learned it | Where it lives in the mock project |
|---|---|---|---|---|
| LO1 | B5 Evaluate | judge risk and testability, choose a cross-platform strategy | 1 | `docs/01-strategy.md`, `requirements.toml` |
| LO2 | B3 Apply | BDD with maintainable steps, hooks, tags, reports, evidence | 1 | `features/`, `tests/steps/`, `swaglabs/plugins/` |
| LO3 | B3 Apply | reliable Playwright: fixtures, isolation, tracing, network, parallel | 2 | `swaglabs/plugins/browser.py`, `network.py`, `-n 4` |
| LO4 | B3 Apply | containerised, reproducible, isolated, recoverable runs | 4 | `docker/` |
| LO5 | B3 Apply | mobile automation with synchronisation | 3 | `@phone`, Pixel 7 job (native Appium: Unit 3) |
| LO6 | B4 Analyse | async systems: retries, duplicates, ordering, eventual consistency | 3 | `dynamic_catalogue.feature`, `waiting.py`, two-tab/double-click |
| LO7 | B3 Apply | distributed execution with retained artifacts | 4 | CI matrix, artifacts, manifest |
| LO8 | B4 Analyse | performance evidence → bottlenecks | 4 | `perf-budgets.toml`, `perf.py`, `perf.md` |
| LO9 | B5 Evaluate | defend a solution: security, reliability, scalability, cost | 4 | `docs/05-defense.md` |

The Bloom level tells you what an answer must contain. **B3 Apply**: you can do it and explain
the steps. **B4 Analyse**: you can take evidence apart and say *why*. **B5 Evaluate**: you can
compare options against criteria and defend a choice — including what you gave up.

---

## A.1 LO1 — Risk and testability (B5)

**Key ideas.** Risk = likelihood × impact, scored with evidence. Requirements written *after*
exploration are sharper ("any product", not "a product"). Testability = control, observation,
oracles, determinism, isolation — each weakness gets a design decision. Scope includes what is
not tested, with reasons. The strategy must be executable (risk tags checked at collection).

**Traps.** Scoring by gut feeling; "test everything" (no prioritisation); oracles that compare
the page with itself; registering a defect you cannot reproduce.

**Quiz.**
1. Two risks score 12 each: wrong price shown (L4 × I3) and slow login (L3 × I4). Same score —
   are they handled the same way?
2. What makes `visual_user`'s random prices a testability problem, and what is the answer?
3. Name one item you put out of scope and the reason you would give a product owner.

<details><summary>Answers</summary>

1. Same band (medium), so both get regression coverage, but the *kind* of test differs: a content oracle check (every card vs the reference catalogue) vs a timing budget with a bottleneck split. The score sets priority, not technique.
2. The output is non-deterministic, so "the list is sorted by the displayed price" can pass or fail by chance. Assert a deterministic property instead: the order of **names** (the app sorts by the real price), and check displayed prices separately against the oracle — where they fail every time (SL-09).
3. Load testing Swag Labs: it is a third party's system; load on it is abuse, and its results would not describe our system anyway. (Or visual pixel comparison: needs baselines per browser × viewport and a review workflow → manual.)
</details>

**Show it:** `docs/01-strategy.md` §3; `tests/unit/test_registers.py::test_feature_files_follow_the_tag_rules`.

---

## A.2 LO2 — BDD that stays maintainable (B3)

**Key ideas.** Features say *what* in business language; steps say *how* and talk to one facade.
Tags carry requirement, risk, suite, area — and are validated. Hooks log steps and save evidence
on failure. Reports: traceability with honest statuses (FAIL > KNOWN DEFECT > PASS > MANUAL).
Data tables and outlines for data; area tags on **Examples** where only some rows are affected.

**Traps.** UI words in Gherkin ("click the button with id…"); one step per click; steps that
import Playwright; counting xfail as skipped/manual; greedy placeholders (`{name}` matching
across quotes); empty Examples cells with `parse` (use a regex parser).

**Quiz.**
1. Why is `Then I see the login error "<error>"` better than `Then the element [data-test=error] has text "<error>"`?
2. A scenario is tagged `@REQ-SL-07 @REQ-SL-14 @risk-medium @regression`. What happens, and why?
3. What does the matrix show for a requirement with 5 passing scenarios and 1 known defect?

<details><summary>Answers</summary>

1. It states the behaviour; the selector belongs to the page object. When the selector changes, the feature (the specification) does not.
2. Collection stops with "Tag rules broken": REQ-SL-07 is high risk, so the scenario must be `@risk-high`. The risk analysis is executable.
3. KNOWN DEFECT — the worst outcome decides. The requirement is not met for that persona, however many other scenarios pass.
</details>

**Show it:** `features/checkout.feature` (Examples-level areas), `swaglabs/plugins/registry.py`, `reports/traceability.md`.

---

## A.3 LO3 — Reliable Playwright (B3)

**Key ideas.** A fresh browser context per test (isolation) makes parallel runs safe. Web-first
assertions (`expect`) retry; `eventually` for everything else. One `evaluate_all` for a
consistent snapshot. Wait for an element only the new page has (SPA navigation). Network
control: allow-list, count what is blocked. Traces and screenshots on failure. `expect`'s
timeout aligned with the action timeout.

**Traps.** `wait_for_timeout(2000)` as synchronisation; shared logged-in state between tests;
reading the old page after an SPA URL change; letting third-party calls into timing; retrying
actions.

**Quiz.**
1. A test passes alone and fails with `-n 4`. Three likely causes?
2. Why block the error tracker instead of just ignoring it?
3. Where do you look first when a CI-only failure happens?

<details><summary>Answers</summary>

1. Shared state between tests (same account data, same storage), order dependence (a test relies on an earlier one), resource contention making a too-tight timeout or a fixed wait fail.
2. Our fault personas would send deliberate errors to a vendor's tracker (pollution), and a slow third party would add noise to our timings. Blocking and counting keeps the test inside its scope and documents what was blocked.
3. The evidence of that run: the step's JSON (URL, console errors, dialogs, blocked hosts), screenshot and HTML, then the Playwright trace (`playwright show-trace`), then `run.json` to compare versions and settings with your local run.
</details>

**Show it:** `swaglabs/plugins/browser.py::shop`, `swaglabs/network.py`, `reports/evidence/`.

---

## A.4 LO4 — Containers (B3)

**Key ideas.** Reproducible = pinned base by digest + pinned packages. Isolated = read-only
root, tmpfs for scratch, a volume only for evidence, non-root user. Recoverable = `--init`,
evidence on a volume, refuse to start without a writable `reports/`. The same image locally and
in CI.

**Traps.** `:latest` tags; running as root; writing reports inside the container's filesystem
(lost on exit); a 64 MB `/dev/shm` for Chromium; secrets in `ENV` or in a layer.

**Quiz.**
1. Why `HOME=/tmp` in the image?
2. What does `--init` give you that a plain `docker run` does not?
3. The proxy CA is needed to build behind a company proxy. How do you use it without leaking it into the image?

<details><summary>Answers</summary>

1. Browsers write profiles and caches under `$HOME`. With a read-only root file system, `$HOME` must point at a writable tmpfs.
2. A real PID 1 that forwards signals (Ctrl-C, `docker stop`) to pytest, so it can finish and write reports, and that reaps zombie browser processes.
3. A BuildKit secret mount (`RUN --mount=type=secret,id=proxy_ca …`): available during that `RUN` only, never stored in a layer.
</details>

**Show it:** `docker/Dockerfile`, `docker/compose.yaml`, the "cannot write evidence" refusal.

---

## A.5 LO5 — Mobile with synchronisation (B3)

**Key ideas.** In this project mobile = the responsive site: a phone-sized touch context
(`@phone`: viewport 412 × 915, `has_touch`) on every browser, plus a Pixel 7 emulation job
(device descriptor: user agent, scale factor, `is_mobile`). Touch actions (`tap`). Layout checks
(no sideways scrolling). Content that loads **when visible** behaves differently on narrow
screens — the lazy-load story. Native apps: Appium with explicit waits on accessibility ids
(Unit 3) — the same rule, *wait for a state*.

**Traps.** `is_mobile` on Firefox (unsupported — that is why `@phone` omits it); assuming a test
that passes on desktop passes on a phone; jumping to the end of a lazy list.

**Quiz.**
1. Why did the lazy-load test pass on desktop and fail on Pixel 7?
2. What does emulation not tell you that a real device does?

<details><summary>Answers</summary>

1. Tiles load only when on screen. On desktop (three columns) every tile was on screen at some point; on a phone (one column) jumping to the sentinel skipped the middle tiles, which stayed placeholders. The fix scrolls one screen at a time and checks only tiles that were on screen.
2. Real rendering engines on the device (e.g. Safari on iOS hardware), touch latency, memory and CPU limits, real mobile networks, OS dialogs and permissions.
</details>

**Show it:** `features/mobile.feature`, `PHONE_CONTEXT` in `swaglabs/plugins/registry.py`, the Pixel 7 CI job.

---

## A.6 LO6 — Asynchronous behaviour (B4)

**Key ideas.** Retries with back-off on **reads**; the failure reports the last value. Duplicates
and ordering: tile numbering 0..n-1 catches both. Eventual consistency: two sources of truth
(badge, storage) must *eventually* agree; a second tab converges after reload. Changing content:
assert an invariant (dot names the shown product) and a history (MutationObserver), not one
snapshot. Idempotency: a double click must never produce duplicates.

**Traps.** Retrying an action ("click until it works"); `sleep` instead of a state; a single
snapshot of a moving UI; asserting a transient state (the spinner is visible).

**Quiz.**
1. Explain why "click dot 5, then the shown name is dot 5's product" is flaky, and give the robust version.
2. What exactly does `eventually` report when it gives up, and why does that matter?
3. In Unit 3 you tested exactly-once processing of order events. Which check in this project plays the same role?

<details><summary>Answers</summary>

1. The slider rotates on its own; it can move on between the click and the read. Robust: record a history of shown products (observer installed before the click) and assert the product appears in it; separately, assert the invariant that the active dot always names the shown product, reading both in one call.
2. The description, the timeout, the number of tries and the last observed value. It turns "timed out" into evidence of what the system actually did.
3. The double-click scenario: the stored cart must hold the product at most once (no duplicate effect from a repeated command), and the badge must agree with the store.
</details>

**Show it:** `swaglabs/waiting.py`, `features/dynamic_catalogue.feature`, `features/cart.feature`.

---

## A.7 LO7 — Distributed execution with retained artifacts (B3)

**Key ideas.** Shard by an independent dimension (persona/browser) — each shard a fresh container
on a fresh VM; `fail-fast: false`; artifacts uploaded `if: always()` with retention; a manifest
to verify integrity; a merge job that produces the release view and gates on it. In AWS terms:
Fargate task per shard, S3 with lifecycle, Device Farm for real devices — same image.

**Traps.** Uploading artifacts only on success; one shard's failure cancelling the others;
unbounded retention (cost) or none (no audit trail); merged reports that silently skip missing
shards.

**Quiz.**
1. Why `fail-fast: false` here?
2. What does the manifest protect against?
3. How would the matrix map onto ECS/Fargate?

<details><summary>Answers</summary>

1. Each persona's result is independent information. A failure in one must not cancel the others, or the release view is incomplete exactly when it matters.
2. Partial or altered evidence: a missing screenshot, an edited `run.json`, a file added later. `python -m swaglabs.evidence reports` re-hashes every file.
3. One task definition (the same image, read-only root, non-root user, a writable volume for reports); one `RunTask` per matrix entry with `SWAGLABS_PERSONA` and pytest arguments as overrides; reports synced to S3 under a run prefix; a final step merges the traceability files.
</details>

**Show it:** `.github/workflows/mock-project.yml`, `python -m swaglabs.matrix`.

---

## A.8 LO8 — Performance evidence → bottlenecks (B4)

**Key ideas.** Budgets per interaction, measured from action to visible result; p50/p95/max
(nearest rank). Split the time: network-busy (union of request intervals in the window) vs
client. Validate the instrument against an independent measurement. In Unit 4 (our own system):
load, Little's law, saturation, telemetry correlation — never on a third-party site.

**Traps.** Averages instead of percentiles; timing only the click (not the result); counting
parallel requests twice; trusting an instrument you never checked; load-testing someone else's site.

**Quiz.**
1. Four requests of 100 ms run in parallel during a 500 ms interaction. Network-busy? Verdict?
2. Why did the first monitor say "network-bound" with zero requests?
3. Write the bottleneck statement for `performance_glitch_user`.

<details><summary>Answers</summary>

1. 100 ms (union, not sum) → 20 % of 500 ms → **client**-bound.
2. Two instrument bugs: unfinished requests from before the window were counted as busy until "now", and request times were stamped when Python *received* the events, which arrive late while page JavaScript spins. Fixed with `window_activity` and the browser's own `request.timing`.
3. Login and sorting take ~5.1 s (p95 5.3/5.1 s vs budgets 2.5/2 s); the network is idle > 90 % of that time and sorting sends no request, so the delay is client-side JavaScript in those two actions; other interactions match standard_user. Fix the client code; re-measure with the same scenarios.
</details>

**Show it:** `reports/perf.md` of the glitch job, `swaglabs/perf.py`, `tests/unit/test_reports.py::TestPerf`.

---

## A.9 LO9 — Defend the solution (B5)

**Key ideas.** Four criteria: **security** (secrets, least privilege, supply chain, data sent
out), **reliability** (no flakiness, isolation, strict register, diagnosability), **scalability**
(what grows, what saturates first, the next step), **cost** (minutes, storage, people's time).
Every decision has a price; name it. Evidence beats adjectives.

**Traps.** Claiming "secure/reliable" without a control and an evidence pointer; hiding
trade-offs; "we would use AWS" without saying what it adds.

**Quiz.**
1. A panel member: "Your cookie shortcut means you never test login." Answer.
2. "Why not retry failed tests three times?"
3. "When would you move to a cloud grid?"

<details><summary>Answers</summary>

1. Login is tested where it is the subject: REQ-SL-01/02 scenarios use the form for every persona, and the contract scenario proves the form sets exactly the cookie the shortcut sets. Elsewhere the shortcut removes an unrelated dependency (and glitch_user's 5 s) from 40 scenarios.
2. Retries hide intermittent defects and make flakiness invisible. We remove flakiness at the source (state-based waits, isolation, deterministic oracles) and register real defects as strict expected failures. A retry policy, if ever needed, must be limited to classified environment errors and reported.
3. When we need real devices, more parallelism than the runner quota, or test data that must stay inside a private network. The image moves unchanged; see `docs/05-defense.md`.
</details>

---

## A.10 Mixed scenario questions (exam style, 40 min)

Answer in 5–8 lines each, naming evidence.

1. **The nightly run is red.** `problem_user-chromium` reports `XPASS(strict)` on *Every product
   can be added from the catalogue*. Walk through your next 30 minutes.
2. **A new persona** `accessibility_user` appears on the login page. What changes, file by file?
3. **The tax rate changes to 10 %.** What fails, and what do you change?
4. **Your manager** wants the whole matrix on every pull request, and the bill doubled. Propose a
   cheaper plan that keeps the risk coverage.
5. **A developer** says the slider test is "flaky, just add a sleep". Respond.

<details><summary>Guidance</summary>

1. Open the job's evidence: was the scenario run as problem_user (run.json)? Re-run locally as problem_user to confirm. If the defect is gone: confirm all six products add correctly; update `findings.toml` (remove problem_user from SL-04, or close SL-04) and `docs/03-findings.md`; check whether error_user still shows it. If it is not gone: the test lost its teeth (e.g. it no longer adds all products) — fix the test. Either way the strict register did its job.
2. `Persona` enum value; CI matrix line; exploration charter; findings entries for what it breaks (new areas if needed, with scenarios that use them — the coverage gate enforces this); docs. No scenario text changes.
3. *The overview adds 8 % tax…* fails for standard_user (FAIL, not KNOWN DEFECT). If the change is intended: update `tax_rate` in `catalogue.json` and the requirement title; the oracle recomputes everything. If not: it is a defect — register it.
4. The project already does the first step: pull requests run `-m smoke` on the 8 targets, `main`/nightly/manual runs the full suite (`SUITE` in `mock-project.yml`). Next levers, in order: build the image once and pull it by digest (35 s per job today); on PRs run `standard_user` on Chromium plus the scenarios of changed features, and the persona matrix nightly. Measure first: the slowest job (performance_glitch_user, ~140 s) sets the pipeline's wall time. High-risk requirements stay covered on every change.
5. A sleep only makes the race rarer and the suite slower. The robust test asserts the invariant (dot names the shown product, read in one call) and uses a recorded history for "was shown after my choice". Show the two scenarios and their history-based assertions.
</details>

---

# Session B — Evidence pack and design defense (LO9) · 120 min

| Time | Activity |
|---|---|
| 0–40 | B1 Assemble the evidence pack |
| 40–70 | B2 Prepare the 10-minute defense |
| 70–110 | B3 Defense rehearsal in pairs (10 min talk + 10 min questions, then swap) |
| 110–120 | B4 Self-assessment against the rubric |

## B1 — The evidence pack

| # | Item | Source |
|---|---|---|
| 1 | Strategy, risk register, testability assessment | `docs/01-strategy.md` |
| 2 | Architecture and ADRs | `docs/02-architecture.md` |
| 3 | Findings report (13 defects, reproduction steps, 1 retired observation) | `docs/03-findings.md` |
| 4 | Quality gates: lint, types, unit/plugin tests, coverage ≥ 90 %, coverage gate | `quality` job log (or local commands) |
| 5 | The quality matrix (requirement × run) | `quality-matrix` artifact |
| 6 | Per-run evidence: traceability, perf, run record, logs, traces, manifest | `reports-*` artifacts |
| 7 | Performance analysis with the bottleneck statement | `docs/04-execution-and-evidence.md` + glitch `perf.md` |
| 8 | Proof the tests can fail | a strict-register run where a defect is removed from `findings.toml` (XPASS → red) and one where a finding is added for a working behaviour (FAIL → red) |
| 9 | Design defense | `docs/05-defense.md` |

Without GitHub, produce items 4–6 locally:

```bash
ruff check . && ruff format --check . && mypy
pytest tests/unit --cov
pytest --collect-only -q --fail-on-uncovered
for p in standard_user problem_user error_user visual_user performance_glitch_user; do
  pytest tests/test_scenarios.py -n 4 --persona "$p" && cp -r reports "reports-$p-chromium"
done
python -m swaglabs.matrix reports-*/traceability.json > quality-matrix.md
```

## B2 — The 10-minute defense

| Minute | Slide | Content |
|---|---|---|
| 0–1 | Context | product, what we own and do not own, constraints (no load, no AWS) |
| 1–3 | Risk and strategy | top risks, the persona matrix idea, scope "no"s |
| 3–5 | Architecture | layers, ADR-2 (personas), ADR-3 (strict xfail), ADR-4 (state set-up) |
| 5–7 | Results | the quality matrix; 13 defects; SL-14 found by the suite; SL-13 not registered |
| 7–8 | Performance | glitch bottleneck: client-side; the instrument story |
| 8–10 | Evaluation | security, reliability, scalability, cost — one control and one evidence pointer each; what you would do next |

## B3 — Panel questions to rehearse

1. How do you know your tests can fail?
2. Why are known defects not simply skipped?
3. What is your flake rate, and how would you measure it?
4. What does your solution cost per month, and what would you cut first?
5. Which decision would you change with hindsight?
6. What breaks first if the suite grows to 500 scenarios?
7. What evidence would convince you the performance verdict is right?
8. How would you add real devices?

(Model answers: `docs/05-defense.md` §6, and A.1–A.9 above.)

## B4 — Rubric (self-assessment)

| Criterion | Weight | Excellent (5) | Adequate (3) | Weak (1) |
|---|---:|---|---|---|
| Risk & testability (LO1) | 15 | scored with evidence; every weakness has a decision; scope "no"s argued | register present; some decisions | list of features, no risk |
| BDD & framework (LO2, LO3) | 20 | tags enforced; layered; isolated; evidence on failure; traceability honest | works; some layer leaks | brittle, selectors in steps |
| Async & mobile (LO5, LO6) | 15 | invariants/histories; no fixed waits; phone context; eventual consistency | state waits; some snapshots | sleeps |
| Containers & CI (LO4, LO7) | 15 | pinned, read-only, non-root; matrix; retained, verified evidence; merged gate | image + pipeline | manual runs only |
| Performance (LO8) | 15 | budgets, percentiles, split, validated instrument, bottleneck statement | timings reported | one stopwatch number |
| Defense (LO9) | 20 | four criteria with controls + evidence; trade-offs named; good answers under questions | criteria covered | adjectives without evidence |

---

## After Unit 5: what the mock project delivered

| Day | Output | Where |
|---|---|---|
| 19 | exploration notes, requirements, risk register, findings draft, ADRs, strategy | `docs/01-strategy.md`, `requirements.toml`, `findings.toml` |
| 20 | framework, 46 scenarios/examples, strict register, evidence, traceability | `swaglabs/`, `features/`, `tests/` |
| 21 | async scenarios, budgets with bottleneck verdicts, container image, CI matrix | `perf-budgets.toml`, `docker/`, `.github/workflows/mock-project.yml` |
| 22 | revision, evidence pack, defense | `docs/04…05`, your presentation |

---

## Verification log

| Check | Result |
|---|---|
| Revision answers | Checked against the project code and the runs of 2026-11-24 |
| Commands in B1 | Run locally (Chromium, 4 workers): every persona exit 0; `python -m swaglabs.matrix` merges the five files; no FAIL |
| Numbers quoted (13 defects, 46 tests, 98 % coverage, glitch timings) | Taken from `findings.toml`, `pytest --collect-only`, `pytest tests/unit --cov`, and `reports/perf.md` of the glitch run |
| CI matrix | The workflow passes `actionlint` and the repository's policy audit; it has not been run on GitHub from this environment |
