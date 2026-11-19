# Unit 4 · Day 16 — Topic Revision (LO7), then the Device Farm and Performance Lab

| | |
|---|---|
| **Course** | Advanced Automation Test Engineering (ATEST03) — Fast Track |
| **Unit** | Unit 4 — AWS Cloud Execution, Performance, and CI/CD |
| **Session A** | Topic Revision · Guides/Review · Virtual · **60 min** · **LO7** |
| **Session B** | AWS Device Farm and performance lab: execute Appium tests, correlate CloudWatch evidence, and identify bottlenecks · Assignment/Lab · Hybrid · **150 min** · **LO5, LO7, LO8** |
| **Code** | `Unit4/unit4-code/shop-bdd.zip`: `perf/`, `framework/perf/`, `cloud/devicefarm/`, `sandbox/` |
| **Tools** | Apache JMeter **5.6.3** (Java 17 or newer), Python 3.12 |
| **Output of the day** | A: quiz and drill answers. B: a BlazeDemo load report, a **bottleneck analysis with before/after evidence**, a Device Farm run plan, and findings in Day 4 format |

> **How this lab was checked.**
> - **Run for real**, with JMeter 5.6.3 (downloaded from the Apache archive and checked against its SHA-512):
>   - the BlazeDemo plan, at light load: 5 users, 2 minutes;
>   - the sandbox plan, at 40 users for 60 s, four times (before the fix and three corrective variants), with telemetry sampled every second.
>
>   All numbers below are from those runs.
> - **Theory only:** the Device Farm part has no AWS account behind it. The test package was built and installed offline in a clean container, but no device run happened.
> - **CloudWatch:** taught by mapping the sandbox's local telemetry to the CloudWatch metrics you would read on AWS.

---

# Session A — Topic Revision: Cloud Execution (LO7) · 60 min

| Time | Activity |
|---|---|
| 0–10 | A.1 One-page map |
| 10–30 | A.2 Quiz (10 questions) |
| 30–50 | A.3 Evidence drill: what happened to these runs? |
| 50–60 | A.4 Peer review of your Day 15 cloud run record |

## A.1 One-page map

| Concern | Decision in the reference design | Proof you have seen |
|---|---|---|
| Identity | 3 roles; CI through OIDC restricted to one repository and one environment; PassRole limited to 2 roles | `cfn-lint` clean; audit: 0 high |
| Network | Public subnet + public IP, **no inbound rules**, HTTPS out; no NAT | Template |
| Image | Digest-pinned base, non-root 10001, read-only root, immutable tags, scan on push | Local read-only run: 260 passed |
| Stop | SIGTERM → clean interrupt → evidence kept → exit 2 | Stop drill: 0.4 s |
| Artifacts | `runs/<id>/` + manifest last; encrypted; private; 30 days | moto test |
| Telemetry | JSON lines → CloudWatch Logs (14 days); Container Insights | Logs Insights queries |
| Devices | us-west-2; 2-device pool; 20-minute job timeout; wheels for glibc ≤ 2.26 | Offline install of the package |
| Cost | Tasks not services; budget $10; one cloud run at a time | Price table |

## A.2 Quiz (answers below — try first)

1. Which role pulls the image, and which role writes the artifacts?
2. What is wrong with a GitHub OIDC trust policy that only checks `aud`?
3. Why is a Fargate *service* the wrong way to run a test suite?
4. A run's last log line says `"exit_code": 75`. What happened, and is the run green?
5. Name two settings that stop S3 test reports from becoming public.
6. Why is `--read-only` worth testing locally before you deploy?
7. Where does Device Farm run, and what happens if you lint its template for us-east-1?
8. Why build the Device Farm wheelhouse with `--platform … --python-version 3.12` instead of a plain `pip wheel`?
9. Which costs dominate a cloud test platform: containers, devices, or idle infrastructure?
10. What does `manifest.json` add that a plain upload does not?

<details>
<summary><b>Answer guide</b></summary>

1. The task **execution** role pulls the image (and writes the logs); the **task** role writes the artifacts.
2. Any repository's workflow can present a token with that audience. Without a `sub` condition, every GitHub repository can assume the role.
3. A service restarts tasks that end, so the suite loops forever, costs money around the clock, and gives no single exit code.
4. The tests passed, but the evidence was not stored. It is **not** green: treat it as an infrastructure failure.
5. Any two of: Block Public Access (all four flags), no `Allow` to `Principal: "*"`, `BucketOwnerEnforced` (no ACLs), the audit rules S3-001 and S3-004 in CI.
6. It reproduces Fargate's filesystem rule in seconds. This lab found a manifest written to the read-only image before any cloud run.
7. In us-west-2. Linting for us-east-1 fails: `Resource type 'AWS::DeviceFarm::Project' does not exist in 'us-east-1'`.
8. The wheels must match the *device host* (Linux x86_64, Python 3.12, glibc 2.26), not your laptop. The script also rejects wheels that need a newer glibc.
9. Devices, and anything left running (services, NAT gateways, hung device runs). A container run costs well under a cent.
10. Proof that the upload finished, plus a size and SHA-256 for every file, so missing or corrupted evidence can be detected.
</details>

## A.3 Evidence drill

Each row is an excerpt from a run (examples in the real formats). Classify each as product, test, environment, or infrastructure, and say the next step.

| # | Evidence |
|---|---|
| 1 | `{"event": "run.end", "pytest_exit_code": 0, "exit_code": 75, …}` and before it `{"event": "artifacts.failed", "error": "ClientError('… AccessDenied … PutObject')"}` |
| 2 | `stopCode: TaskFailedToStart`, `stoppedReason: CannotPullContainerError: … manifest unknown` |
| 3 | `{"event": "run.signal", "signal": "SIGTERM"}`, `"interrupted": true`, `stopCode: UserInitiated` |
| 4 | `run.end` with `pytest_exit_code: 1`; `runs/<id>/traceability.md` shows REQ-04 **FAIL** |
| 5 | Device Farm run `result: ERRORED`; the Appium log ends at `Could not find a connected Android device` |

<details>
<summary><b>Answer guide</b></summary>

1. **Infrastructure (IAM).** The task role lacks `s3:PutObject` on the prefix. The tests passed, but the run is not green. Fix the policy and rerun.
2. **Infrastructure (image).** The tag does not exist in ECR (a wrong tag, or the push failed). Check the pipeline's push step.
3. **Environment (stopped).** Someone or a cancellation stopped it; partial evidence was kept. Rerun it; there is no product signal.
4. **Product or test.** Open the stored reports for REQ-04 and diagnose as in Unit 1.
5. **Environment (device)** on Device Farm's side. It is BLOCKED, not FAIL. Rerun; if it repeats, pick another device or pool.
</details>

## A.4 Peer review

Swap your Day 15 **cloud run record** with a partner. Check that:
- every field has evidence;
- the exit code is interpreted correctly;
- the stop drill shows `interrupted: true` **and** stored evidence;
- the cost estimate gives its unit prices.

---

# Session B — Device Farm and Performance Lab (LO5, LO7, LO8) · 150 min

## Lab plan

| Time | Part |
|---|---|
| 0–10 | B0 — Setup: JMeter, the sandbox, the rules of engagement |
| 10–40 | B1 — A realistic journey: BlazeDemo at light load |
| 40–90 | B2 — Find the bottleneck: load + telemetry on the sandbox |
| 90–110 | B3 — Corrective actions, verified |
| 110–125 | B4 — From local telemetry to CloudWatch evidence |
| 125–145 | B5 — Appium on Device Farm (walkthrough) and correlating mobile evidence |
| 145–150 | B6 — Deliverables |

## B0 — Setup 🟢

1. Install **Java 17+** (for example Eclipse Temurin 21).
2. Download **Apache JMeter 5.6.3** from the Apache archive, and **check its checksum**. CI does the same, so a tampered download never runs.

```bash
curl -sSfLO https://archive.apache.org/dist/jmeter/binaries/apache-jmeter-5.6.3.tgz
```

```bash
echo "5978a1a35edb5a7d428e270564ff49d2b1b257a65e17a759d259a9283fc17093e522fe46f474a043864aea6910683486340706d745fcdf3db1505fd71e689083  apache-jmeter-5.6.3.tgz" | sha512sum -c -
```

```bash
tar xzf apache-jmeter-5.6.3.tgz && export PATH="$PWD/apache-jmeter-5.6.3/bin:$PATH"
```

On Windows, download the `.zip` and check it with `certutil -hashfile apache-jmeter-5.6.3.zip SHA512` against the `.sha512` file next to it.

**Rules of engagement:**

| Target | Allowed load | Why |
|---|---|---|
| **BlazeDemo** (`blazedemo.com`, BlazeMeter's public practice site) | **≤ 10 users, ≤ 5 minutes**, think time on, no embedded resources | It is someone else's service; practice traffic must stay light. The plan identifies itself with the User-Agent `ATEST03-course-lab JMeter/5.6.3 (training load test)`, and its setUp guard **refuses** heavier runs |
| **The local order-events sandbox** (Unit 3) | Anything: stress, spike, soak | You own it and run it on your machine |
| The Unit 1 Shopify demo shop | **No load tests** | Not agreed; it has bot protection; Units 1–2 already run there serially |

---

## B1 — A realistic journey: BlazeDemo at light load 🟢 → 🟡

### B1.1 The plan (`perf/blazedemo_purchase.jmx`)

```
setUp Thread Group "Guard"  JSR223: users ≤ max_users (10) and duration ≤ max_duration (300 s), else stop the test
Thread Group "Travellers"   users=${__P(users,5)}  ramp-up 20 s  duration 120 s
  Uniform Random Timer      think time 1–3 s (before every request)
  01 Home           GET  /                      assert "Welcome to the Simple Travel Agency!"
  02 Find flights   POST /reserve.php           assert "Flights from ${fromPort} to ${toPort}:"
                    Regex Extractor (random match): flight number, price, airline → flight_g1..g3
  03 Choose flight  POST /purchase.php (the chosen flight's fields)   assert "Please submit the form below…"
  04 Purchase       POST /confirmation.php      assert "Thank you for your purchase today!"
                    Regex Extractor: confirmation id; assertion on the variable: \d+
CSV Data Set: perf/data/blazedemo_routes.csv (route + passenger per iteration)
Cookie Manager (cleared per iteration) · HTTP Defaults (https, timeouts) · User-Agent header
```

**The guard, tested.** Asked for 20 users, the plan stops before any traffic. The results file holds a single failed sample, `guard: users and duration within the agreed limits,400,REFUSED: 20 users / 30 s exceeds 10 users / 300 s on a third-party site`, and **0** requests to blazedemo.com. A rule in a document can be ignored; a rule in the plan cannot.

**Correlation** (as in Unit 1) is the core skill here. The flight form's hidden fields are *extracted from the response* and sent back, never hard-coded. A random match spreads the requests over flights, as real users would.

### B1.2 Run it

```bash
jmeter -n -t perf/blazedemo_purchase.jmx -q perf/jmeter.properties -l reports/perf/blazedemo.jtl -e -o reports/perf/blazedemo-html
```

```bash
python -m framework.perf.gate reports/perf/blazedemo.jtl --profile blazedemo
```

Real result (5 users, 120 s, 18 November 2026):

```
summary =    249 in 00:02:00 =    2.1/s Avg:   182 Min:   116 Max:   787 Err:     0 (0.00%)
perf gate blazedemo: PASSED -> reports/perf/gate-blazedemo.md
```

| Transaction | Samples | Errors % | p50 ms | p90 | p95 | p99 | Max |
|---|---|---|---|---|---|---|---|
| 01 Home | 64 | 0.00 | 171 | 392 | 518 | 787 | 787 |
| 02 Find flights | 64 | 0.00 | 157 | 195 | 206 | 576 | 576 |
| 03 Choose flight | 64 | 0.00 | 165 | 193 | 211 | 423 | 423 |
| 04 Purchase | 62 | 0.00 | 168 | 209 | 242 | 456 | 456 |

Open `reports/perf/blazedemo-html/index.html` (JMeter's dashboard) for the graphs over time.

### B1.3 🔴 Read it like a senior

- **The home page has the slowest tail** (p95 518, p99 787) while the other pages are about 200 ms. With only 64 samples, p99 is close to the single maximum. Collect more samples before you call it a finding.
- **62 vs 64:** the test stopped while some users were mid-journey, so the last steps have fewer samples (and "04 Purchase" has 3 more samples than its own request). Analyse the steady state, and treat the edges carefully (Day 14, §3.5).
- **The first smoke run (2 users, 25 s) FAILED the gate** with `samples: expected >= 10, actual 6`. That is correct: too little evidence is not a pass.
- **A 200 with the wrong content.** Checked by hand with the same requests: `purchase.php` always shows *"Your flight from TLV to SFO has been reserved"*, airline *United*, price *400*, whatever flight was chosen. The confirmation's amount is always *555 USD*. These are BlazeDemo's demo behaviours: functional findings, **not** performance errors. If they were real defects, a status-only assertion would report a perfect, fast, wrong system.

> **Your turn (🟡).** Add an assertion to "03 Choose flight" that the page shows the chosen airline (`${flight_g3}`). Run **one** user for one iteration (`-Jusers=1 -Jduration=10`). What happens, and how do you report it: as a performance failure or as a functional finding? Then remove it from the load plan, and keep it as a separate functional check.

---

## B2 — Find the bottleneck: load + telemetry on the sandbox 🟡 → 🔴

### B2.1 The system and the plan

The Unit 3 order-events sandbox: an order is accepted (`POST /orders`, 202), then **payments** charges it (gateway latency 0.05 s in this lab), **fulfilment** packs and ships it (2 × 0.05 s), and the **projector** updates the read model.

`perf/orders_sandbox.jmx`: each virtual user places an order, then **polls** `GET /orders/{id}` every 100 ms until it shows `shipped` (a bounded While Controller), then a check confirms it shipped. The transaction **"TX order completed"** is the end-to-end time of an asynchronous flow. That is what REQ-13 promises: shipped within 2 s.

### B2.2 Run with telemetry (three terminals)

```bash
python -m sandbox --port 8765 --gateway-latency 0.05
```

```bash
python -m framework.perf.telemetry http://127.0.0.1:8765 --out reports/perf/telemetry.csv --duration 70
```

```bash
jmeter -n -t perf/orders_sandbox.jmx -q perf/jmeter.properties -l reports/perf/orders.jtl -Jusers=40 -Jrampup=10 -Jduration=60
```

Then line up the client side with the server side, and apply the gate:

```bash
python -m framework.perf.correlate reports/perf/orders.jtl reports/perf/telemetry.csv
```

```bash
python -m framework.perf.gate reports/perf/orders.jtl --profile sandbox
```

### B2.3 🔴 Form a hypothesis first

Before you look at the results, write down where you expect the bottleneck. *This lab's author predicted **payments**: it calls an external gateway, and gateways are slow.*

### B2.4 The evidence (real run, before any fix)

`reports/perf/bottleneck.md`, excerpt:

| Window (s) | Users | TX order completed /s | p95 ms | fulfilment queued | payments queued | projector queued | fulfilment /s | payments /s | projector /s |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 20 | 8.6 | 1424 | 8.6 | 0.0 | 0.0 | 8.0 | 11.6 | 39.4 |
| 5 | 40 | 9.8 | 2829 | 28.4 | 0.0 | 0.0 | 9.8 | 13.8 | 47.4 |
| 10 | 40 | 9.8 | 4145 | 37.8 | 0.2 | 0.0 | 9.8 | 10.0 | 39.4 |
| 30 | 40 | 10.0 | 4159 | 38.0 | 0.0 | 0.0 | 9.8 | 10.0 | 39.4 |
| 55 | 40 | 9.8 | 4164 | 37.8 | 0.0 | 0.0 | 9.8 | 9.6 | 39.0 |

```
Bottleneck: fulfilment, capacity about 9.8/s
- at full load (40 users, 11 windows): mean queue fulfilment 37.1; payments 0.1, projector 0.0
- processing rates: fulfilment 9.8/s, payments 10.2/s, projector 40.0/s
- client side: 9.8 completed/s, p95 4023 ms
FAIL  TX order completed  p95 ms  expected <= 2000  actual 4154
```

**The hypothesis was wrong.** Payments' queue is empty; **fulfilment's** queue holds almost every order (about 38 of the 40 users), while it completes a flat 9.8 per second. Each fulfilment takes 2 × 0.05 s, so one worker can do at most 10 per second. The payments gateway (0.05 s) allows 20 per second: it waits for fulfilment, not the other way round.

How to read the table:
1. **Users doubled (20 → 40); throughput stayed at about 9.8; p95 tripled.** By Little's law, this is a saturated resource (Day 14, §3.3).
2. **The queue that grows, with a flat processing rate, is the bottleneck.** The others' rates are capped by it: payments processes 10/s because only 10/s complete.
3. **`POST /orders` stayed at p95 2 ms the whole time.** The front door accepts instantly while the work queues behind it, the classic asynchronous trap from Unit 3. A test that only measured the POST would report "excellent performance".

### B2.5 The cost of polling

JMeter's summary for this run: **22,982 samples in 60 s** (383/s), for only **583** completed orders. Most samples are `GET /orders/{id}` polls, about 36 per order at 100 ms. In production, that is load on the read model created only by the *way* clients wait. Unit 3's answer applies here too: subscribe to pushed status (WebSocket) instead of polling, or poll with backoff.

---

## B3 — Corrective actions, verified 🔴

The sandbox can run more consumers per subscription (`--concurrency name=N`), the local equivalent of scaling the consumer service. Each change was run with the **same** load (40 users, 60 s):

| Run | Change | Completed/s | TX p95 ms | Queue at full load | Gate |
|---|---|---|---|---|---|
| 1 | none | 9.72 | 4154 | fulfilment ≈ 37 | **FAIL** |
| 2 | `--concurrency payments=4` (the wrong guess) | 9.72 | 4153 | fulfilment ≈ 37 | **FAIL**, and nothing changed |
| 3 | `--concurrency fulfilment=4` | 19.32 | 2121 | **payments ≈ 36** | **FAIL** (just over 2,000) |
| 4 | `fulfilment=4` + `payments=4` | 38.64 | 1028 | fulfilment ≈ 31 | **PASS** |

What these runs teach:

1. **Fixing the wrong component changes nothing** (run 2). Always fix what the evidence points at, and **verify** by re-running the same load.
2. **The bottleneck moves** (run 3). Fulfilment ×4 can do about 40/s, so payments (about 20/s with one worker) becomes the limit. Its queue now holds the users.
3. **In a closed test, something always queues** (run 4). With 40 users and no think time, the slowest stage still holds the waiting users. The question is not "is there a queue?" but "**is the objective met at the load we must support?**" Run 4 meets REQ-13 (p95 1,028 ms ≤ 2,000).
4. **Little's law holds in every run:** X × mean R ≈ 35–36 (Day 14, §3.3).

### B3.1 Recommendation, in Day 4 format

| Field | Finding P-16-01 |
|---|---|
| Title | Fulfilment throughput caps order completion at about 10 per second |
| Severity | High: REQ-13 (shipped within 2 s) fails above about 20 concurrent customers |
| Evidence | `bottleneck.md` (queue ≈ 37 at a flat 9.8/s), gate p95 4,154 ms; JTL and telemetry attached |
| Cause | One fulfilment consumer; 0.1 s of work per order |
| Corrective action | Scale fulfilment consumers to 4 **and** payments to 4 (one alone moves the bottleneck); add an alarm on fulfilment queue depth |
| Verification | The same load: p95 1,028 ms, 38.6 completed/s, gate PASS |
| Follow-up | Replace client polling with pushed status (~36 GETs per order); load test with an **open** model at the expected arrival rate |

---

## B4 — From local telemetry to CloudWatch evidence 🟡 → 🔴

On AWS, the same analysis uses CloudWatch. The method is identical: one time axis, client-side numbers next to server-side numbers.

| Sandbox `/metrics` (local) | CloudWatch on AWS (SQS consumers on ECS) | Meaning |
|---|---|---|
| `queued` | SQS `ApproximateNumberOfMessagesVisible` | Work waiting |
| (age of the oldest) | SQS `ApproximateAgeOfOldestMessage` | How late the oldest work is: often the best alarm |
| `in_flight` | SQS `ApproximateNumberOfMessagesNotVisible` | Work being processed |
| `processed` per second | SQS `NumberOfMessagesDeleted` per period | Consumer throughput |
| `workers` | ECS service `RunningTaskCount` (Container Insights) | Consumer capacity |
| (CPU of a worker) | ECS `CpuUtilized` / `CPUUtilization` | Is a consumer CPU-bound or waiting? |
| JMeter JTL | Your load test results, plus the load balancer's `TargetResponseTime` | The customer's view |

**What changes on AWS:**

| Difference | Consequence |
|---|---|
| Standard metrics have **1-minute** resolution; some SQS metrics are published every 5 minutes *(AWS docs)* | A 60-s test shows one or two points. Hold the steady state for **≥ 10 minutes**, and compare minutes, not seconds |
| Clocks: JMeter writes epoch milliseconds; CloudWatch stores UTC | Record the test's start and end in UTC, and query exactly that window |
| Many tasks | Use metric math (`SUM`, `AVG` by service), or Container Insights per task |
| Evidence must be kept | Export the queries' results (CSV or a dashboard snapshot) into `runs/<id>/` next to the JTL |

A CloudWatch Logs Insights query that lines up the runner's events with a load window:

```
fields @timestamp, event, run_id, duration_s
| filter run_id = "perf-2026-11-18-1"
| stats count(*) by bin(1m), event
```

---

## B5 — Appium on Device Farm (walkthrough) and correlating mobile evidence 🟡 → 🔴

> ⚠️ **Not executed** (no AWS account). The package build and the offline install **were** run.

### B5.1 Build the test package

```bash
bash cloud/devicefarm/build_test_package.sh build/devicefarm
```

Real output from this lab:

```
wheel platform check: all wheels run on glibc 2.26
build/devicefarm/test_package.zip (94M)
```

60 wheels for Linux x86_64 / Python 3.12. Installed with `--no-index` in a clean container **with no network**: pytest collected the 10 mobile tests.

> 🔴 **Design debt to note:** the mobile package carries Playwright, aiohttp, and boto3, because the framework imports every adapter at start-up. It works, but it is 94 MB for 10 mobile tests. Lazy imports per platform would make it much smaller. Day 18 asks you to weigh this kind of debt.

### B5.2 Upload, schedule, wait, collect

This is the same sequence as `.github/workflows/cloud.yml`, job `device-farm`, in region **us-west-2**:

1. `create-upload` three times: the app as `ANDROID_APP`, the package as `APPIUM_PYTHON_TEST_PACKAGE`, and `cloud/devicefarm/testspec.yml` as `APPIUM_PYTHON_TEST_SPEC`. For each, PUT the file to the returned pre-signed URL and wait until the upload's status is `SUCCEEDED`.
2. `schedule-run` with the device pool (2 Android phones, OS ≥ 13) and `jobTimeoutMinutes=20`.
3. Poll `get-run` until the status is `COMPLETED` (bounded); gate on `result = PASSED`.
4. `list-artifacts` for `FILE`, `LOG`, and `SCREENSHOT`: video, device log, Appium log, and our own `shop-bdd-reports/` (copied in `post_test`).
5. Cleanup, always: `stop-run` if it is unfinished, and `delete-upload` for all three uploads.

### B5.3 🔴 Correlating mobile evidence

A device run produces three timelines. Line them up:

| Source | Example evidence | Answers |
|---|---|---|
| Our framework (`shop.mobile` log, `mobile_step`) | `STEP Open Sauce Labs Backpack and add two` at 12:01:07.4 | Which business step was slow or failed |
| Appium server log | `POST /session/…/element` taking 9 s; `NoSuchElement` | Was it the locator, the app, or the driver? |
| Device Farm job data | Video; device log (logcat); per-job device performance data (CPU, memory) *(AWS docs)* | Was the device or the app under strain at that moment? |

**Exercise** (example data, not from a run):

| Device | Checkout test | Slowest step | Device CPU at that step |
|---|---|---|---|
| Pixel 8 (Android 15) | 38 s, PASS | Payment screen 3.1 s | 35 % |
| Galaxy A14 (Android 13) | 71 s, FAIL (timeout 15 s at "Review: items and total") | Review screen 16.2 s | 98 % |

1. Product, test, or environment?
2. What evidence would you attach?
3. What would you change: in the test, and what would you recommend to the app team?

<details>
<summary><b>Guide</b></summary>

1. Most likely **product performance on a low-end device**: the same step takes 5× longer, with the CPU saturated, and only on that device. It is not a locator problem; the step eventually renders.
2. The video segment, the CPU graph around the step, the Appium log lines with their timings, and our step log with timestamps.
3. **Do not** just raise the timeout to make it pass: that hides the defect. Record the finding, with the device class. Run the low-end device in the pool on purpose. Recommend profiling the review screen's rendering. Separately, define a performance objective per device class, so the test can decide what "too slow" means.
</details>

---

## B6 — Deliverables

- [ ] BlazeDemo: the gate report and the HTML dashboard from your run (≤ 10 users), plus your answer to the "Your turn" in B1.3
- [ ] Sandbox: your hypothesis written **before** the run; `bottleneck.md` and the gate report for runs 1, 3, and 4
- [ ] Finding P-16-01 (or your own, if your numbers differ), with the corrective action **verified**
- [ ] The B4 mapping table, filled with the CloudWatch queries you would run for your own system
- [ ] A Device Farm run plan: the pool, the timeout, the uploads, the gates, the cleanup, and the cost estimate (2 devices × your suite's minutes × $0.17)
- [ ] The B5.3 exercise answered

---

## Common errors

| Error | Meaning | Fix |
|---|---|---|
| `java: command not found` / `Unsupported class file` | No Java, or one that is too old | Install Java 17+ |
| JTL with `Non HTTP response code: java.net.UnknownHostException` | DNS or a proxy | Behind a proxy: `jmeter … -H proxy.host -P 3128` |
| `perf gate …: FAILED` with `samples` | The run was too short, or the script broke early | Look at the JTL errors first, then run longer |
| Everything 0 ms and `NOT_FOUND` in the URLs | `POST /orders` failed, so `order_id` was never extracted | Is the sandbox running? Check the port (`-Jport=`) |
| `bottleneck: none` | No queue at this load | Increase the users, or check that the telemetry covered the run (same machine clock) |
| BlazeDemo 429 or 5xx | You are too heavy, or the site is down | Stop. Lower the load. Never retry harder |

---

## Self-check (answers below — try first)

1. Why were the authors' hypothesis and the evidence different, and what does that teach?
2. Which column of the bottleneck table proves fulfilment, not payments, was the limit?
3. Why did `--concurrency payments=4` change nothing?
4. Run 4 still shows a queue at fulfilment. Is that a problem?
5. What does `POST /orders` p95 = 2 ms tell you about the system?
6. Why must a CloudWatch-based analysis use longer tests than this local one?
7. How do you tell a functional defect from a performance failure in a load test?
8. What is the minimum evidence for a Device Farm finding on one device class?

<details>
<summary><b>Answer guide</b></summary>

1. The gateway "looked" slow, but each fulfilment takes twice as long. Measure; don't guess. Write the hypothesis down so that you notice when the evidence disagrees.
2. The queue columns: fulfilment ≈ 37–38 at a flat 9.8/s, while payments' queue is ≈ 0.
3. Payments was not saturated. Adding capacity where nothing waits does not change the throughput of the stage that limits it.
4. Not by itself. A closed test with 40 users and no think time always queues somewhere. What matters is that the objective (p95 ≤ 2 s) holds at the required load, and that the queue does not grow without bound.
5. Only that the front door accepts quickly. The work behind it queues, so you must measure completion, not acceptance.
6. Standard metrics have 1-minute resolution (some SQS metrics 5 minutes). A 60-s test gives one or two data points, so hold the steady state for 10 minutes or more.
7. Assert content in the load test. A wrong page that returns 200 is a functional finding; report it separately and keep correctness checks out of the throughput statistics.
8. The video segment, device performance data around the step, the Appium log timings, our step log, the device model and OS, and a comparison with a faster device on the same build.
</details>

## Next: Day 17

Topic revision of LO5, LO7, and LO8, then the CI/CD integration lab: one pipeline with the container, Device Farm, and performance stages, quality gates, reports, and cleanup.

---

## Verification log

| Check | Result |
|---|---|
| BlazeDemo setUp guard (`-Jusers=20`) | Refused: 1 failed guard sample, 0 requests to blazedemo.com |
| BlazeDemo with `-q perf/jmeter.properties` (2 users, 20 s) | 0 errors; results columns as pinned (incl. `allThreads`, `failureMessage`) |
| `tests/unit/test_jmeter_plans.py` | Pass; three deliberate plan mutations each caught |
| JMeter 5.6.3 download | SHA-512 matched the Apache archive's published value |
| BlazeDemo, 5 users, 120 s (`perf/blazedemo_purchase.jmx`) | 249 samples, 0 errors, gate PASSED; table above |
| BlazeDemo smoke, 2 users, 25 s | Gate FAILED on `samples` (6 < 10), as designed |
| BlazeDemo content behaviours (purchase page, amount) | Observed with direct requests (`curl`) on 18 November 2026 |
| Sandbox, 40 users, 60 s, gateway latency 0.05 s: 4 runs | Tables above (correlate + gate outputs) |
| `framework/perf` unit tests | Pass (percentiles, CSV with commas, gate fail-closed, diagnosis) |
| CI performance job replayed locally (5 users, 30 s, default latency) | Gate PASSED; TX p95 520 ms; already shows a fulfilment queue of 2.8 |
| Device Farm package | 94 MB, 60 wheels, glibc ≤ 2.26; offline install + 10 tests collected |
| **Device Farm run / CloudWatch on AWS** | **Not executed**: no AWS account; CloudWatch metric names from AWS documentation |
