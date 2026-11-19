# Unit 4 · Day 14 — Cloud CI/CD and Performance Concepts: Secure Parameters, Secrets, Quality Gates, Cleanup, Distributed Workload, Cost Controls

| | |
|---|---|
| **Course** | Advanced Automation Test Engineering (ATEST03) — Fast Track |
| **Unit** | Unit 4 — AWS Cloud Execution, Performance, and CI/CD |
| **Learning outcomes** | **LO7** — Execute containerized and mobile automation securely… (B3) · **LO8** — Analyze distributed performance and CloudWatch evidence to identify bottlenecks and recommend corrective actions (B4: Analyze) |
| **Format** | Concept/Lecture · Virtual · 120 minutes · no code to produce (short illustrations from the project) |
| **Tools** | GitHub Actions (recommended CI/CD), Apache JMeter 5.6.3 (performance), the project's gates |
| **Output of the day** | Your **pipeline and performance test design** (one page, end of this document) |

> **How the facts here were checked.**
> - **Run for real:** the gates, JMeter runs, and numbers below come from this project, on a local machine, in November 2026.
> - **Checked with `actionlint` but never run on GitHub:** the workflow files.
> - **From documentation:** AWS and GitHub behaviour is marked *(docs)*.

---

## How to use this lecture

Day 13 was about **where** tests run. Today is about **how a pipeline runs them safely and repeatably**, and **what "fast enough" means**. You need both on Day 16, where you diagnose a real bottleneck, and on Day 17, where you assemble the pipeline.

| Badge | Level | After this level you can… |
|---|---|---|
| 🟢 | **Foundation** | Tell configuration from secrets; name the performance-test types and metrics; read a JMeter plan |
| 🟡 | **Practitioner** | Design gates that fail for the right reasons; model a workload; plan cleanup and cost limits |
| 🔴 | **Senior** | Reason with Little's law and percentiles; spot misleading performance reports; distribute load without corrupting results |

### Lecture plan (120 min)

| Time | Part |
|---|---|
| 0–10 | Part 0 — Anatomy of a cloud test pipeline |
| 10–30 | Part 1 — Secure parameters and secrets |
| 30–45 | Part 2 — Quality gates |
| 45–80 | Part 3 — Performance-testing concepts (and JMeter) |
| 80–95 | Part 4 — Distributed workload |
| 95–105 | Part 5 — Cleanup |
| 105–120 | Part 6 — Cost controls |

---

## Glossary

| Term | Meaning | Vietnamese |
|---|---|---|
| Secret | A value that grants access (password, token, key) | Bí mật |
| Parameter | Configuration that may be read by anyone with access to the configuration | Tham số cấu hình |
| Quality gate | An automated check that stops the pipeline when a criterion is not met | Cổng chất lượng |
| Throughput | Completed operations per second | Thông lượng |
| Response time / latency | How long one operation takes | Thời gian phản hồi |
| Percentile (p95) | 95 % of operations were at least this fast | Phân vị |
| Concurrency | Operations in progress at the same moment | Mức đồng thời |
| Saturation | A resource is fully used; work starts to queue | Bão hòa |
| Bottleneck | The resource that limits throughput | Nút thắt cổ chai |
| SLO / SLA | An objective you aim for / a contractual promise | Mục tiêu / cam kết dịch vụ |
| Think time | The pause a real user takes between actions | Thời gian suy nghĩ |
| Ramp-up | Gradually adding users at the start of a test | Tăng tải dần |

---

## Part 0 — Anatomy of a cloud test pipeline 🟢

```
push / PR ─▶ quality (lint, types, unit, offline BDD, events, config audit)   ← minutes, every change
              ├─▶ container (build image, run suite read-only)                ← every change
              ├─▶ performance (local load + SLA gate)                          ← every change, small
              └─▶ live (real shop, serial, smoke)                              ← main / nightly
manual + approval ─▶ cloud (OIDC → ECR → Fargate → Device Farm → gates → cleanup) ← on demand, costs money
```

**Recommendation: GitHub Actions.**
- The repository is on GitHub, the project already has `ci.yml`, and it signs in to AWS through OIDC (Day 13).
- Its *environments* add required reviewers before any job that costs money.

Alternatives:
- **AWS CodeBuild/CodePipeline:** inside AWS; it can run in your VPC.
- **GitLab CI** and **Jenkins:** fine if your organisation already runs them.

The concepts below apply to all of them.

---

## Part 1 — Secure parameters and secrets 🟢 → 🔴

### 1.1 🟢 Is it a secret?

| Value | Kind | Where it belongs |
|---|---|---|
| `SUITE=offline`, `AWS_REGION=us-east-1`, a bucket name | Configuration | Repository **variables**, the task definition `environment` |
| A role ARN | Configuration, not a secret: it grants nothing without the trust conditions | Repository variable |
| A shop admin password, an API token, a webhook URL with a token | **Secret** | A secret store; injected at run time; never printed |
| AWS access keys | Avoid them entirely | Use OIDC (Day 13, §1.4) |

### 1.2 🟡 Where secrets live

| Store | Use |
|---|---|
| **AWS Secrets Manager** | Secrets with rotation (database passwords, third-party tokens) |
| **SSM Parameter Store** (`SecureString`) | Simpler secrets, encrypted with KMS |
| **GitHub secrets** (repository or environment) | What the *pipeline* itself needs. Environment secrets are only released to jobs in that environment |

ECS injects a stored secret as an environment variable **when the container starts**. The task definition holds only a *reference* *(AWS docs)*:

```json
"secrets": [
  { "name": "SHOP_API_TOKEN", "valueFrom": "arn:aws:ssm:us-east-1:111122223333:parameter/shop-bdd/api-token" }
]
```

The **execution role** needs `ssm:GetParameters` (or `secretsmanager:GetSecretValue`) on that one ARN, and `kms:Decrypt` if a customer-managed key encrypts it.

### 1.3 🔴 How secrets leak, and the rule that catches each

| Leak | Example | Guard |
|---|---|---|
| Plain text in a task definition | The exam case: `SHOP_ADMIN_PASSWORD=Summer2026!` | Audit rule **ECS-001**; use `secrets` |
| Baked into an image layer | `COPY .env .` or `ARG TOKEN` in a Dockerfile | `.dockerignore`; BuildKit secrets (our proxy CA) |
| Printed in logs | `echo $TOKEN`, or verbose HTTP logs | GitHub masks registered secrets *(docs)*; never log headers |
| Long-lived CI keys | `secrets.AWS_ACCESS_KEY_ID` | Audit rule **GHA-002**; OIDC |
| Untrusted code running with secrets | `pull_request_target` + checkout of the PR head | Audit rule **GHA-001** (critical) |
| In test reports | Screenshots of a page with a token; captured capabilities | Unit 3 masks capabilities (`safe_capabilities`) |

---

## Part 2 — Quality gates 🟡 → 🔴

### 2.1 The gates in this project

| Gate | Fails when | Where |
|---|---|---|
| Lint, format, types | Any finding. Beyond style, the rules include security (bandit `S`), blind `except` without a written reason (`BLE`), unused arguments, complexity > 10, and `assert` in framework code (removed by `python -O`) | `ruff`, `mypy --strict` |
| BDD review | Undefined, ambiguous, or unused steps; Gherkin smells | `python -m framework.review --strict` |
| Tests + requirement coverage | A failed test; a requirement with no scenario | `pytest --fail-on-uncovered` |
| Code coverage | Below **90 %** of the offline-reachable code (browser- and device-only adapters are excluded and covered by live runs) | `pytest --cov` (`fail_under` in `pyproject.toml`: a ratchet) |
| Oracle validation | A defect test does not pass on the fixed build | Unit 3, Day 12 |
| Template and workflow lint | Invalid CloudFormation or workflow syntax; shell bugs | `cfn-lint`, `actionlint` + shellcheck |
| Configuration audit | Any finding of severity **high** or above | `python -m framework.cloud.audit --fail-on high` |
| Image scan | Any CRITICAL vulnerability | ECR scan (cloud pipeline) |
| Container exit code | Not 0 (1 = tests, 75 = evidence lost) | Cloud pipeline |
| **Performance SLA** | A percentile, error rate, or **sample count** misses its objective | `python -m framework.perf.gate` |
| Device Farm result | Not `PASSED` | Cloud pipeline |

### 2.2 🔴 Rules for gates that mean something

1. **Fail closed.** A missing label, an empty results file, or too few samples is a **failure**, never a pass. Unit 3 found a test that passed before its fault had even happened; the performance gate has `min_samples` for the same reason. The first BlazeDemo smoke run in this lab had only 6 samples per step, and the gate failed it on purpose (`samples: expected >= 10, actual 6`).
2. **Percentiles, not averages.** Day 18's exam case reports "PASS, average 420 ms" while p95 is 9.8 s and 6.1 % of requests fail.
3. **Known exceptions are registered, not hidden.** Strict xfails list known defects in a register; the matrix shows **KNOWN DEFECT**, never "pass" or "manual".
4. **A gate's thresholds have a source.** `perf/sla.toml` comments where each number comes from, for example `p95_ms = 2000  # = REQ-13 consistency target`.
5. **Gate on evidence that is kept.** Every gate writes a report (Markdown + JSON) that the pipeline uploads.

The performance gate's objectives (`perf/sla.toml`, excerpt):

```toml
[defaults]
min_samples = 20      # fewer samples than this proves nothing: the gate FAILS
max_error_pct = 1.0

[sandbox."POST /orders"]
p95_ms = 200          # the front door only accepts: it must stay fast at any load
max_error_pct = 0.0

[sandbox."TX order completed"]
p95_ms = 2000         # = REQ-13 consistency target (2 s from order to "shipped")
max_error_pct = 0.0
```

---

## Part 3 — Performance-testing concepts 🟢 → 🔴

### 3.1 🟢 Types of performance test

| Type | Load shape | Question it answers |
|---|---|---|
| **Smoke / baseline** | A few users, briefly | Does the script work, and what is "normal"? |
| **Load** | The expected peak, held | Do we meet the objectives at the expected load? |
| **Stress** | Increase until something breaks | Where is the limit, and how does it fail? |
| **Spike** | A sudden jump | Does it survive bursts, and recover? |
| **Soak (endurance)** | Normal load for hours | Leaks, growth, slow degradation |
| **Capacity** | Steps of increasing load | How much traffic can it serve within the objectives? |

> **Whose system?** Stress, spike, and soak tests go only against systems **you own, or have written permission to load**. For practice, this course uses **BlazeDemo** (BlazeMeter's public practice site) at **light** load only: at most 10 users and 5 minutes, with think time. Everything heavier runs against the **local order-events sandbox** from Unit 3.

### 3.2 🟢 Metrics

| Metric | Read it as | Trap |
|---|---|---|
| Throughput (requests/s, transactions/s) | Work done | More requests can be *worse*: polling, retries |
| Response time **percentiles** (p50, p90, p95, p99) | The experience of most users, and of the unlucky ones | An average hides the slow tail |
| Error rate | Requests that failed, or **gave wrong content** | A 200 with an error page is still an error: assert content |
| Concurrency (active threads) | The load you applied | Not the same as users in a real system |
| Utilisation and saturation (CPU, queue depth, connections) | Why it is slow | High CPU on the **load generator** invalidates the test |

### 3.3 🔴 Little's law: the one formula

> **N = X × R** (in a steady state). N = items in the system, X = throughput, R = time each item spends in the system.

The real data from this unit's sandbox experiment (Day 16): 40 virtual users, each placing an order and waiting until it ships.

| Run | X (orders/s) | Mean R (s) | X × R |
|---|---|---|---|
| Before the fix | 9.72 | 3.647 | 35.4 |
| Fulfilment ×4 | 19.32 | 1.869 | 36.1 |
| Fulfilment ×4 + payments ×4 | 38.64 | 0.943 | 36.4 |

X × R stays at about 36 in every run. That is the 40 users, minus the time each user spends between orders and the 10 s ramp-up. **In a closed system, once something saturates, adding users does not add throughput; it adds waiting.** If someone's report shows rising users, flat throughput, and rising response times, Little's law tells you they hit a bottleneck before you look at any server metric.

### 3.4 🔴 Closed vs open workload

| Model | How load is generated | Real world | JMeter |
|---|---|---|---|
| **Closed** | N users loop: request → wait for the answer → think → repeat | Call-centre agents, batch jobs | Thread Group (our plans) |
| **Open** | Requests *arrive* at a rate, whether or not earlier ones finished | Public web traffic | Open Model Thread Group, or a Precise Throughput Timer |

In a closed test, a slow system makes the load generator **slow down too**. The arrival rate drops exactly when the system struggles, so the queue never grows as large as it would with real traffic. This is called **coordinated omission**. Use an open model when you must prove behaviour at a given *arrival rate*.

### 3.5 🟡 Making results trustworthy

| Practice | Why |
|---|---|
| Ramp up, and analyse the steady state | Start-up effects (empty caches, opening connections) distort the first seconds |
| Discard the edges | When the test's time is up, threads stop mid-journey. In the BlazeDemo run, "04 Purchase" has 62 samples but its request only 59: 3 journeys were cut off |
| Think time | Without it, 5 users behave like 50 |
| Watch the load generator | Above roughly 80 % CPU, *it* becomes the bottleneck (exam case: 97–100 %) |
| Repeat | One run is an anecdote: compare at least 3 runs |
| Correlate with server telemetry | Client numbers say *that* it is slow; server numbers say *why* (Day 16) |
| Assert content, not just status | A fast error page is not a fast purchase |

### 3.6 🟢 JMeter vocabulary (5.6.3)

| Element | Role | In `perf/blazedemo_purchase.jmx` |
|---|---|---|
| Test plan | The file (`.jmx`) | "BlazeDemo - flight purchase journey" |
| setUp thread group | Runs once, before the load | "Guard": a JSR223 check that **refuses** to start above 10 users or 5 minutes on a third-party site |
| Thread group | Virtual users, ramp-up, duration | "Travellers": `${__P(users,5)}` users, 20 s ramp-up, 120 s |
| Config elements | Shared settings | HTTP Request Defaults (https, blazedemo.com), Cookie Manager, a CSV Data Set of routes |
| Controllers | Structure | Transaction Controllers "01 Home" … "04 Purchase" |
| Samplers | Requests | `GET /`, `POST /reserve.php`, … |
| Timers | Think time | Uniform Random Timer, 1–3 s |
| Pre/post-processors | Correlation | A Regular Expression Extractor picks a random flight and its price and airline |
| Assertions | Correctness | "Flights from Paris to Buenos Aires:", "Thank you for your purchase today!", the confirmation id is a number |
| Listeners | Results | None in the plan: run **non-GUI** with `-l results.jtl -e -o html/` |

Properties make one plan serve every environment, for example `-Jusers=5 -Jduration=120 -Jhost=…`. **Never run load from the GUI**: it uses the load generator's CPU and distorts the results.

### 3.7 🔴 A test plan is code: review it like code

| Practice | In this project |
|---|---|
| **Pin the results format.** JMeter's defaults differ between installations; the analysis must not depend on them | `-q perf/jmeter.properties`: CSV, the exact columns, no response bodies in results, no hidden HTTP retries |
| **Fail closed on the evidence.** A results file without the needed columns is an error, not "0 samples" | `read_jtl` refuses it and names the missing columns |
| **Bound everything.** Users and duration come from properties; every loop has a maximum | `test_plan_is_bounded_and_property_driven` |
| **Assert every request.** Under load, a server returns fast error pages | `test_every_request_is_asserted` |
| **Be explicit about time.** Connect and response timeouts in HTTP Defaults | `test_plan_is_robust` |
| **Be polite to someone else's site.** Light defaults, think time, an identifying User-Agent, no embedded resources, and a guard that refuses heavier runs | `test_third_party_targets_get_polite_load` and the setUp guard |

`tests/unit/test_jmeter_plans.py` applies these rules to every `perf/*.jmx`. Each rule was checked by breaking a copy of the BlazeDemo plan on purpose: 50 users, no think time, and a request without an assertion each fail with a clear message (`assert 50 <= 10`, `think time`, `requests without an assertion: ['GET /']`).

---

## Part 4 — Distributed workload 🟡 → 🔴

### 4.1 When one machine is not enough

| Approach | How | Trade-off |
|---|---|---|
| **JMeter distributed mode** | One controller drives several JMeter servers over RMI *(JMeter docs)* | Needs open RMI ports between machines and identical plans and data on each; the controller can become a bottleneck |
| **Independent shards** (recommended for the cloud) | N identical Fargate tasks each run the plan with `users = total / N`, then the JTL files are merged | No inter-node networking; a failed shard is visible; easy to scale |
| **Test sharding** (functional suites) | `pytest -n` per task, or split by file across tasks | Results merged per test |
| **Device Farm** | One job per device in the pool, in parallel | Minutes × devices |

### 4.2 🔴 What breaks when you distribute

| Problem | Symptom | Fix |
|---|---|---|
| Shared test data | Two shards buy "the same" product, or use the same account | Per-shard data files, or ids that include the shard |
| Clock skew between generators | Merged timelines are wrong | NTP on the hosts (Fargate has it); align by run start; compare windows, not single seconds |
| Percentiles from shards | You **cannot average p95s** | Merge the raw samples (JTL), then compute percentiles. `framework.perf.jtl` does this |
| A silent dead shard | The total load is lower than planned | Each shard reports its sample count; the gate's `min_samples` and the active-threads column show it |
| The target's rate limits | 429 or "blocked" pages from one IP | Agree the test with the owner; spread the source IPs only with permission |

---

## Part 5 — Cleanup 🟡 → 🔴

| Leftover | Cost or risk | Cleanup |
|---|---|---|
| A running task (a hung test) | Fargate per second, possibly for hours | A pipeline step with `if: always()` that stops the task if it is still running |
| A Device Farm run | Device minutes until the job timeout | `stop-run` in `if: always()`, plus a **20-minute job timeout** on the project |
| Uploads (app, test package) | Clutter, storage | `delete-upload` after the run |
| Old images | ECR storage | Lifecycle policy: keep the last 10 |
| Old artifacts and logs | S3 and CloudWatch storage | Lifecycle 30 days; log retention 14 days |
| Test data in the system under test | Wrong data for the next run; real orders | Per-run correlation ids; cleanup **inside** the test, with its own assertion |

**Cleanup rules:**
- it runs **always**, also after a failure or a cancel;
- it is **idempotent**: deleting what is already gone is fine;
- it has a **bound**: a timeout;
- it **reports** what it removed.

A cleanup that fails silently is how the exam case ended up paying for three hung device runs.

---

## Part 6 — Cost controls 🟡 → 🔴

### 6.1 Know the price of a run

| Item | Unit price (approximate, us-east-1, November 2026) | One run of this project |
|---|---|---|
| Fargate | about $0.04048 per vCPU-hour, $0.004445 per GB-hour (x86) | 1 vCPU / 2 GB for 10 min ≈ **$0.008** |
| Device Farm | $0.17 per device minute (after the trial) | 2 devices × 8 min ≈ **$2.72** |
| CloudWatch Logs | Per GB ingested, plus storage | A few MB per run: cents |
| S3 | Per GB-month, plus requests | Cents, with a 30-day expiry |
| NAT gateway (avoided) | about $0.045 per hour + per GB | ~$33/month just to exist |

The surprise: **devices and anything left running cost far more than the containers**.

### 6.2 Guard rails

| Control | Implementation in this project |
|---|---|
| Budget with alerts | `AWS::Budgets::Budget`: email at 80 % of $10 actual, and 100 % forecast |
| Approval before spending | GitHub environment `aws-lab` with required reviewers |
| One cloud run at a time | `concurrency: group: cloud` in `cloud.yml` |
| Timeouts everywhere | `timeout-minutes` on every job (audit rule GHA-004); Device Farm job timeout 20 min; `stopTimeout` 30 s |
| Retention | S3 30 days, logs 14 days, ECR last 10 |
| Right-sizing | 1 vCPU / 2 GB, measured with Container Insights. The exam case uses 4 vCPU / 16 GB |
| Cheaper capacity | ARM64 (about 20 % less). Fargate Spot is possible for retryable shards, but it can be interrupted |
| Tags | `project: shop-bdd` on resources, to see the cost per project |
| No 24/7 test infrastructure | Tasks, not services; no NAT; schedules only for what needs them |

---

## Your output: pipeline and performance test design (one page)

| Topic | Your decision and the reason |
|---|---|
| CI/CD platform and how it authenticates to AWS | |
| Secrets: list, store, injection, who can read them | |
| Gates: list, thresholds, the source of each threshold, fail-closed rules | |
| Performance: test types, workload model (open or closed), users and think time, steady-state window, targets you may load | |
| Distributed load: approach, data separation, how results are merged | |
| Cleanup: what, when, how it is verified | |
| Cost: price per run, budget, limits | |

---

## Self-check (answers below — try first)

1. Is a role ARN a secret? Is a webhook URL?
2. Where does an ECS secret's value live, and which role reads it?
3. Why must a performance gate fail when it has too few samples?
4. A report says "average 420 ms — PASS". What do you ask for?
5. Users grew from 20 to 40; throughput stayed at 9.8/s; response time doubled. What happened?
6. Why can a closed-model test look better than reality?
7. Three shards report p95 values of 800, 900, and 1,000 ms. What is the overall p95?
8. What makes a cleanup step trustworthy?
9. Which costs more: a 10-minute Fargate run or a 10-minute Device Farm run on two phones?
10. Why not stress-test BlazeDemo?

<details>
<summary><b>Answer guide</b></summary>

1. A role ARN is configuration: it grants nothing without the trust conditions. A webhook URL that contains a token **is** a secret.
2. In Secrets Manager or SSM Parameter Store. The task definition holds only the reference, and the **execution role** reads the value when the container starts.
3. With few samples, percentiles are meaningless and a broken script (zero samples) would "pass". Failing closed turns missing evidence into a visible failure.
4. p95 and p99, the error rate, the sample count, the steady-state window, the load generator's CPU, and how many runs. The exam case hides p95 9.8 s and 6.1 % errors behind its average.
5. A bottleneck saturated at about 9.8/s. By Little's law, the extra users only queue: R ≈ N / X doubles when N doubles.
6. When the system slows down, the virtual users slow down too, so fewer requests arrive and queues stay shorter than real, independent arrivals would make them (coordinated omission).
7. It cannot be computed from those numbers. Merge the raw samples and compute the percentile from all of them.
8. It runs always (also after failures and cancels), is idempotent, has a timeout, and reports or verifies what it removed.
9. Device Farm: 2 × 10 min × $0.17 = $3.40, against under one cent for Fargate.
10. It is someone else's service. We have no agreement for heavy load, so the course keeps BlazeDemo to light, agreed-style load and does stress work on its own sandbox.
</details>

## Next: Day 15

The AWS execution lab: package the suite into an image, run it as Fargate would, keep the artifacts, and walk through the deployment to ECR/ECS.

---

## Verification log

| Check | Result |
|---|---|
| Little's law table | From the Day 16 runs (JMeter 5.6.3, 40 users, 60 s, local sandbox, gateway latency 0.05 s) |
| BlazeDemo edge effect (62 vs 59) | From the 5-user, 120-s BlazeDemo run (0 errors) |
| Gate failing on too few samples | First 2-user BlazeDemo smoke run: 6 samples per step → FAILED (min 10) |
| `perf/sla.toml` excerpts | Copied from the project |
| Workflows | `actionlint` + shellcheck clean; **not run on GitHub** |
| AWS secrets injection, OIDC, Budgets | From AWS and GitHub documentation; **not deployed** |
| Prices | Approximate, November 2026; check the AWS pricing pages |
