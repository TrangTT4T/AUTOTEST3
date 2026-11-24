# Design defense — Swag Labs mock project (LO9)

How the solution holds up against **security, reliability, scalability and cost**, which
trade-offs were made on purpose, and the questions a review panel is likely to ask.

## 1. Security

| Threat | Control | Evidence |
|---|---|---|
| Credentials leak through code, logs or reports | Password only from the environment (or the public demo value); `repr=False`; masked in JSON logs (formatter + filter) and in saved HTML; feature files use `(valid)` | `tests/unit/test_config.py`, `test_reports.py::TestEvidence`, `test_architecture.py::test_no_password_in_feature_files_or_docs` |
| Pipeline token misuse | `permissions: contents: read`; no cloud credentials exist | `mock-project.yml` |
| Expression injection in CI | matrix values pass through `env:`; no `${{ }}` inside `run:` scripts | `mock-project.yml`, actionlint |
| Supply chain | base image pinned by digest; Python packages pinned; actions on current majors | `docker/Dockerfile`, `requirements*.txt` |
| A test escaping its sandbox | non-root user, read-only root, tmpfs, fresh container per job | `docker run` flags |
| Data sent to third parties | network allow-list; the error tracker is blocked and counted | `swaglabs/network.py`, `blocked_hosts` in evidence |
| Tampered or partial evidence | SHA-256 manifest written last, verified in CI | `python -m swaglabs.evidence reports` |
| Abuse of someone else's system | single-user timings only, ≤ 32 browsers for ~2 min, no load tests | `01-strategy.md` scope |

Residual risk: GitHub-hosted runners are shared infrastructure; acceptable because no secret
and no private data exist in this project. With real secrets: environment secrets with required
reviewers, OIDC instead of long-lived keys, and a self-hosted runner in a private network.

## 2. Reliability (flakiness is a defect of the suite)

- **No fixed waits.** State-based waits only; enforced by an architecture test.
- **Isolation.** Fresh browser context per test; arrange through state (cookie, localStorage),
  so no scenario depends on another or on order — which is what makes `-n 4` safe.
- **Deterministic oracles.** Sorting is checked by name order (visual_user's random prices
  cannot flip it); the slider by an invariant and a history, not one snapshot; lazy loading by
  tile-number continuity.
- **Strict register.** A known defect is an expected *AssertionError*. A timeout, a crash or a
  fix all turn the run red; a different failure is never hidden behind a known one.
- **Unreproducible observations are not registered** (SL-13): a flaky finding would teach the
  team to ignore red.
- **Verified instruments.** The performance monitor was cross-checked against an independent
  timeline and corrected (see 04).
- **Diagnosability.** Every failed step leaves screenshot, HTML, trace, console errors and
  dialogs; `run.json` says exactly what ran.

Accepted weakness: the system under test is a public site we do not control. A Sauce Labs
deployment can change behaviour overnight; the nightly run detects it, and the strict register
makes such a change visible instead of silently passing.

## 3. Scalability

| Dimension | Today | Scales by |
|---|---|---|
| Tests per job | `-n 4` workers | more workers (CPU-bound); xdist handles distribution |
| Targets | 8 matrix jobs | adding a line to the matrix; artifacts and the merged matrix pick it up automatically |
| Scenarios | 46 per run | features + steps; tags keep selection cheap (`-m smoke`) |
| Personas / findings | data files | new persona = one enum value + matrix line; new defect = one TOML entry |
| Run time | ~30 s (standard) to ~100 s (glitch) per job | the slowest job bounds the pipeline: split by feature file if it grows |

Limits: GitHub's concurrent-job quota per account; beyond that a cloud grid (Fargate tasks or a
Selenium/Playwright grid) is the next step — the container image moves unchanged.

## 4. Cost

| Item | Cost driver | Decision |
|---|---|---|
| CI minutes | 8 jobs × ~3 min per push + nightly | path filter (`mock-project/**`), `concurrency` cancels superseded runs; smoke-only on PRs is the next lever if minutes run short |
| Image build | ~1 min per job (base image pull) | acceptable at this size; next lever: build once, push to a registry, pull by digest in the matrix |
| Storage | reports with traces ≈ a few MB per job | 14-day retention; 30 days for the release view |
| People | flaky tests and unclear failures | the reliability rules above are the biggest saving |

Public repositories get these minutes free; for a private repository the same pipeline costs
roughly 8 × 3 = 24 runner-minutes per push.

## 5. Trade-offs we chose

| Choice | Benefit | Price |
|---|---|---|
| Personas as a run dimension (ADR-2) | scenarios stay about behaviour | the release view needs the merged matrix |
| Cookie/localStorage shortcuts (ADR-4) | fast, isolated, independent of broken buttons | depends on internals — guarded by a contract scenario |
| Recorded reference catalogue (ADR-5) | a real oracle | must be updated when the catalogue changes |
| Emulation instead of devices | free, fast, in every run | no real device quirks (touch latency, mobile Safari engine on iOS) |
| No visual testing | no baseline maintenance | visual regressions found by hand (REQ-SL-16 is MANUAL) |

## 6. Questions a panel will ask

**Why not just use plain Playwright tests?** Requirements, risk and known defects must be
traceable and readable by non-programmers; Gherkin + tags give that, and the plugins turn the
tags into gates and reports. Below the step layer it *is* plain Playwright.

**How do you know a passing run means something?** The plugin tests prove the gates work
(a fixed defect turns the run red, an unexpected exception is not hidden, uncovered requirements
fail the build); the personas prove the scenarios can fail — 13 registered defects are caught by
the same scenarios that pass for `standard_user`.

**Why is sorting checked by names and not by prices?** Because visual_user shows random prices;
the order of names is deterministic and is what the sort actually changes.

**Why strict xfail and not skip?** A skip hides the defect and never notices the fix. A strict
xfail reports KNOWN DEFECT in the matrix and goes red when the defect disappears.

**Where is the bottleneck of performance_glitch_user?** In the browser: ~5.1 s with the network
idle > 90 % of the time and no request at all during sorting; other interactions are normal.

**What happens when Swag Labs changes?** The nightly run fails; the evidence shows whether it is
a new defect (register it), a fixed one (update the register) or a legitimate change (update the
reference catalogue or a page object — one place each).

**How would you move this to AWS?** Push the same image to ECR; run each matrix entry as a
Fargate task with the same read-only/non-root settings; write `reports/` to S3 with a lifecycle
rule; ship `log-*.jsonl` and `perf.json` to CloudWatch for cross-run dashboards and alarms; add
Device Farm only for real devices. Nothing in the test code changes.
