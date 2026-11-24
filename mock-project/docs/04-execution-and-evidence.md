# Execution, evidence and performance

## Where the suite runs

| Where | Command | Isolation |
|---|---|---|
| Laptop | `pytest -n 4 --persona problem_user` | fresh browser context per test |
| Container (local) | `docker compose -f docker/compose.yaml run --rm tests` | + fresh container per run, read-only root, non-root user |
| CI | `.github/workflows/mock-project.yml` | + fresh virtual machine per matrix job |

The same image runs locally and in CI — "works on my machine" is answered by "it ran in the
image whose digest is in the Dockerfile".

### Container design (LO4)

| Property | How | Why |
|---|---|---|
| Reproducible | Base image pinned by digest; Python packages pinned in `requirements.txt` | Same bytes on every build |
| Isolated | `--read-only` root, writes only to `/tmp` (tmpfs) and `/work/reports` (volume) | A test cannot change the code or leave state for the next run |
| Least privilege | `USER pwuser` (uid 1001) | A compromised page cannot write outside its tmpfs |
| Recoverable | `--init` (real PID 1: signals reach pytest, zombie browsers are reaped); evidence on a volume | A cancelled run still leaves its reports |
| Fail fast | `reporting` refuses to start if `reports/` is not writable | No run without evidence |
| Chromium shared memory | `--ipc=host` | Docker's 64 MB `/dev/shm` crashes Chromium on large pages |
| Offline proof | `compose run unit` uses `network_mode: none` | The unit suite really needs no network |

### CI pipeline (LO7 without AWS)

```
quality ──► e2e matrix (8 containers in parallel) ──► quality-matrix
  lint            standard/problem/glitch/error/visual × chromium       merge traceability.json
  mypy strict     standard × firefox, webkit                            of every run; exit 1 on
  unit+plugins    standard × Pixel 7 emulation                          any unexpected FAIL
  coverage ≥90 %  each: build image, run, verify manifest,
  req/finding gate      job summary, upload reports (14 days)
  actionlint
```

- `fail-fast: false`: one persona's result never cancels another's.
- Pull requests run `@smoke` only (9 critical scenarios) on all 8 targets — fast feedback; `main`,
  the nightly run and manual runs execute the full suite. The whole suite was built to run in
  parallel from the start (fresh browser context per test, state seeded per test, no shared
  accounts on the server side), so speed comes from parallelism, not from skipping checks.
- `concurrency` cancels superseded runs of the same branch (no wasted minutes).
- Nightly `schedule`: the site can change without any commit of ours — drift is found the next
  morning, not at the next unrelated change.
- `permissions: contents: read`; matrix values reach shell scripts through `env:`, never through
  `${{ }}` inside a script (no expression injection).
- Light load by design: 8 jobs × 4 workers = at most 32 browsers for ~2 minutes against a static
  site served by a CDN. No load test is ever pointed at it.

## Evidence (instead of S3)

Every job uploads `reports/` as an artifact named after its persona and browser, retained 14
days; the merged `quality-matrix` is retained 30 days.

`reports/` is the evidence of exactly one run. The controller empties it once, before any xdist
worker starts — a *global setup*: a session fixture would run once per worker, and a late worker
would delete what faster ones already wrote (which is why pytest-playwright's own per-worker
clean-up of `reports/artifacts` is switched off). Without it, a second local run appended to the
old `log-*.jsonl` files and kept old `evidence/` folders, and the manifest signed them as this
run's. In CI every job starts from an empty folder anyway; the reset makes local runs match.

| File | Content | Used for |
|---|---|---|
| `traceability.md/.json` | requirement → scenarios → outcomes → status | release decision, merged matrix |
| `perf.md/.json` | every timed interaction, budget verdict, bottleneck | performance trend, SL-11 |
| `run.json` | persona, browser, device, versions, commit, run id, outcome counts, duration | reproducing a run |
| `log-<worker>.jsonl` | one JSON object per log line, password masked | searching what happened |
| `evidence/<test>/` | screenshot, page HTML, JSON (step, error, URL, console errors, dialogs, blocked hosts) | debugging a failed step |
| `artifacts/<test>/trace.zip` | Playwright trace (DOM, network, actions) of failed tests | time-travel debugging (`playwright show-trace`) |
| `manifest.json` | SHA-256 and size of every file above | `python -m swaglabs.evidence reports` proves nothing was changed or lost |

**Secrets.** The password comes from `SWAGLABS_PASSWORD` (or the public demo value), is
`repr=False` in `Settings`, is replaced by `***` in every log line and in saved page HTML, and
never appears in feature files (they say `(valid)`). A unit test fails if it appears in docs or
features.

## Performance evidence

Single-user timings, measured in the browser on every run (`perf-budgets.toml`). Each
measurement covers the action **and** the visible result (e.g. click *Login* → products list
visible), so it is what a user waits for.

**Where this sits in ISTQB CT-PT.** These are **user-based objectives** (4.1.1) checked by
single-user **transactions** (4.2.2) — each timed from the user's action to its visible result,
with no think time inside. They are *not* a load test: there is no operational or load profile,
no concurrency and no throughput objective, because Swag Labs is someone else's system. The full
chapter-4 cycle (PTP, operational → load profile, ramp-up/steady/ramp-down, abort criteria,
steady-state analysis) is done on a system we own: Unit 4, `perf/performance-test-plan.md` and
Day 16 B7. Combining the two is exactly what CT-PT 4.3 recommends — run GUI scripts during a load
test to measure the real user experience under load.

**Network vs client split.** While an interaction runs, the browser monitor collects the
browser's own start/end time of every request (`request.timing`). The union of those intervals
inside the window is *network-busy time*; the rest is *client time* (JavaScript, rendering,
deliberate delays). The slowest sample of each action is labelled *client*, *network* or *mixed*.

**Result for `performance_glitch_user` (Chromium, 4 workers):**

| Action | p50 ms | p95 ms | Budget | Network busy (typical) | Requests | Bound by |
|---|---:|---:|---:|---:|---:|---|
| login | 5199 | 5270 | 2500 | 120–170 ms | 6 (images after the page appears) | client |
| sort | 5070 | 5089 | 2000 | 10–370 ms | 0 | client |
| add-to-cart | 64 | 91 | 1000 | — | — | network |
| open-cart | 77 | 133 | 2000 | — | — | mixed |

**Bottleneck analysis.** Login and sorting take ~5.1 s while the network is idle for more than
90 % of the time, and sorting sends **no request at all**: the delay is in the browser's
JavaScript, not on a server. Every other interaction of the same persona is as fast as for
`standard_user` — the slowness is specific to two actions, so the fix belongs in their client
code. An independent check (a request timeline recorded during one login) showed the first
request 5.05 s after the click — the same conclusion from a different instrument.

**Lesson about instruments.** The first version of the monitor time-stamped requests when Python
*received* the event. While the page's JavaScript spins, Playwright delivers events late, so a
request from before the click looked as if it lasted 5 s and sorting was labelled
*network-bound*. Cross-checking against a second measurement exposed it; the monitor now uses
the browser's own timestamps and ignores unfinished requests that started before the window
(both covered by unit tests). Never trust a number from an instrument you have not checked.

## Cloud mapping

The course's reference design, and what replaces each part here:

| Reference (AWS) | This project | Kept property | Given up |
|---|---|---|---|
| ECR + ECS/Fargate tasks | Docker image built per job, run on GitHub-hosted runners | isolated, disposable, parallel containers | autoscaling beyond the runner limit, private VPC |
| Device Farm | Chromium, Firefox, WebKit + Pixel 7 emulation | cross-browser and mobile viewport coverage | real devices, real mobile networks |
| S3 evidence bucket with lifecycle | Actions artifacts with `retention-days` + SHA-256 manifest | retention, integrity check | object lock, cross-account access |
| CloudWatch logs/metrics/alarms | JSON-lines logs, `perf.json`, job summaries, failing gates | searchable logs, per-run metrics | dashboards across runs, alarms (trend over time) |
| IAM roles | `permissions: contents: read`, no cloud credentials at all | least privilege | — |

What would make us move to a cloud grid: real devices (native app, mobile Safari on hardware),
more parallelism than the runner plan allows, or test data that must stay inside a private
network. See [05-defense.md](05-defense.md).
