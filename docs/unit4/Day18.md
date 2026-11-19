# Unit 4 · Day 18 — Topic Revision (LO7, LO8), then the Cloud Execution Audit Exam

| | |
|---|---|
| **Course** | Advanced Automation Test Engineering (ATEST03) — Fast Track |
| **Unit** | Unit 4 — AWS Cloud Execution, Performance, and CI/CD |
| **Session A** | Topic Revision · Guides/Review · Virtual · **60 min** · **LO7, LO8** |
| **Session B** | **Exam** — Cloud execution audit: evaluate security, reliability, scalability, performance, cost, and corrective actions · Virtual · **420 min** · **LO7, LO8, LO9** |
| **LO9** | Evaluate and defend an advanced cloud-ready automation solution against security, reliability, scalability, and cost criteria (Bloom **B5: Evaluate**) |
| **Exam material** | `Unit4/unit4-code/shop-bdd.zip` → `exam/audit-case/` (the case) and `cloud/`, `.github/workflows/` (the reference design, for comparison) |
| **Output** | Session A: revision answers. Session B: **an audit report** and **a defence** of your corrective plan |

> **How the exam material was checked.**
> - **Fictional:** the case "QA Platform v1" is invented. Its configuration files are deliberately flawed, and its evidence files (JMeter summary, metrics, costs) are synthetic but internally consistent. The numbers in the model answer were recomputed from them.
> - **Audit run:** `python -m framework.cloud.audit` was run on the case. It reports **28 findings (12 high or critical)**. The case was built so that **many other flaws are not mechanical**; finding those is what the exam tests.
> - **Do not deploy** any file of the case.

---

# Session A — Topic Revision (LO7, LO8) · 60 min

| Time | Activity |
|---|---|
| 0–15 | A.1 The audit lens: five criteria, one finding format |
| 15–40 | A.2 Quiz (10 questions) |
| 40–60 | A.3 Warm-up audit: three small snippets |

## A.1 The audit lens

| Criterion | Questions you ask | Typical evidence |
|---|---|---|
| **Security** | Who can do what? Where are the secrets? What is exposed? | IAM policies, trust policies, security groups, bucket policies, workflow triggers |
| **Reliability** | Does a failure show up as a failure? Can you reproduce and diagnose a run? | Exit-code handling, logs, artifacts, retries, single points of failure, tags and digests |
| **Scalability** | What happens at 2× and 10× load? What saturates first? | Metrics over time, queue depth and age, connection pools, autoscaling settings |
| **Performance** | Is the test valid? What do the percentiles say? Where is the bottleneck? | JMeter results, the load generator's health, telemetry |
| **Cost** | What do we pay for, and what do we get for it? What runs while nobody needs it? | Cost breakdown, sizing, schedules, retention, timeouts |

**One finding format** (from Unit 1, Day 4), used for every finding:

| Field | Content |
|---|---|
| Id, title | `SEC-03 — The CI role trusts every GitHub repository` |
| Criterion, severity | Security · Critical / High / Medium / Low |
| Observation | What you saw, quoted exactly (file and line) |
| Evidence | The file, metric, or log, and how you checked it (tool output, calculation) |
| Impact | What can happen, to whom, how likely |
| Recommendation | The concrete change, with an example |
| Effort | S / M / L |
| Verification | How anyone can confirm the fix worked |

**Severity guide:**

| Severity | Meaning |
|---|---|
| Critical | Exploitable now, or money or data at direct risk |
| High | Likely to cause an incident, or hides failures |
| Medium | Raises risk or cost noticeably |
| Low | Hygiene |

## A.2 Quiz (answers below — try first)

1. What turns `iam:PassRole` from harmless into an escalation path?
2. A team says: "Our tasks are in private subnets, so they are secure." What do you ask next?
3. Why is `latest` a reliability problem, not only a security one?
4. A report gives the average response time only. Name three numbers you need before you accept a conclusion.
5. Why can a saturated load generator make a system look *faster* than it is?
6. What does a rising `ApproximateAgeOfOldestMessage` tell you that queue depth alone does not?
7. How do you compute the monthly cost of a Fargate service with 4 vCPU and 16 GB that runs 24/7?
8. Which cleanup failures cost money, and which corrupt test results?
9. What is the difference between "the audit tool found no high findings" and "the platform is secure"?
10. What makes a corrective action *verifiable*?

<details>
<summary><b>Answer guide</b></summary>

1. `Resource: "*"`: the holder can hand any role, including an administrator role, to a service it controls.
2. How do they reach AWS APIs and the internet (a NAT gateway: its cost and single AZ)? What can the tasks themselves do (task role)? What is inbound-reachable (security groups)? Who can change the image they run?
3. The same tag can point to different images over time, so you cannot reproduce or attribute a run. A service running `latest` can silently pick up an untested image.
4. Any three of: p95 and p99, the error rate, the sample count and steady-state duration, the load generator's CPU, the number of runs, the workload model and think time.
5. Its threads wait for CPU instead of sending requests, so the real arrival rate drops below the plan, and the system sees less load (coordinated omission). The timings it measures also include its own delays, so its numbers cannot be trusted either way.
6. That the oldest work is getting later and later: consumers are falling behind *relative to arrivals*, whatever the traffic level. Depth can be high simply because traffic is high.
7. (vCPU × vCPU-hour price + GB × GB-hour price) × 730 h ≈ (4 × 0.04048 + 16 × 0.004445) × 730 ≈ **$170** in us-east-1.
8. Money: running tasks, hung device runs, NAT gateways, logs and artifacts with no expiry. Results: test data left in the system, shared accounts, and data used by the next run.
9. A tool checks known mechanical patterns. Security also depends on design (who can push images, which data tests touch), process (keys on laptops), and data flows that no rule sees.
10. A measurable signal that anyone can re-check, for example "the audit reports 0 high", "the next Cost Explorer month shows NAT $0", or "p95 ≤ 2 s at 40 users in the same test".
</details>

## A.3 Warm-up audit (10 min each pair, then compare)

```json
{"Effect": "Allow", "Principal": {"Federated": "arn:aws:iam::111122223333:oidc-provider/token.actions.githubusercontent.com"},
 "Action": "sts:AssumeRoleWithWebIdentity",
 "Condition": {"StringLike": {"token.actions.githubusercontent.com:sub": "repo:acme/*"}}}
```

```yaml
- name: Deploy test runner
  run: aws ecs run-task --cluster qa --task-definition runner || true
```

```text
Load test: 300 users, no think time, 90 s including a 60 s ramp-up. Result: avg 310 ms, errors 4 %. PASS.
```

<details>
<summary><b>Guide</b></summary>

1. **OIDC-002 (high):** every repository and branch of `acme` can assume the role. **OIDC-003 (medium):** no `aud` condition. Fix: `StringEquals` on `aud = sts.amazonaws.com` and `sub = repo:acme/<repo>:environment:<env>`.
2. **Reliability (high):** `|| true` turns any failure into success. Nothing waits for the task or reads its exit code, so the step is green whatever happens. Fix: wait for the task to stop, read its exit code, and gate on it (Day 17).
3. **Performance (invalid test):** only 30 s of steady state; no think time; the average alone; 4 % errors exceed any reasonable objective; a single run. Verdict: inconclusive at best, and the "PASS" is not supported by the evidence.
</details>

---

# Session B — Exam: Cloud Execution Audit (LO7, LO8, LO9) · 420 min

## B0 — The brief

> A product team built **"QA Platform v1"** to run their regression suite, a performance check, and mobile tests on AWS. They ask you, a senior test-automation engineer, for an **independent audit before it is used for release decisions**. They will challenge your conclusions in a review meeting.
>
> Assess the platform against **security, reliability, scalability, performance, and cost**. Recommend corrective actions, prioritised and verifiable, and **defend** them.

### Material (`exam/audit-case/`)

| File | Content |
|---|---|
| `template.yaml` | The team's CloudFormation: bucket, ECR, logs, NAT, security group, ECS cluster, roles, task definition, a Fargate **service** |
| `pipeline.yml` | Their GitHub Actions workflow |
| `evidence/jmeter-summary.md` | Their performance report and its conclusion |
| `evidence/cloudwatch-metrics.csv` | One-minute metrics recorded during that test |
| `evidence/cost-last-30-days.csv` | The last 30 days of AWS costs |
| `evidence/architecture-notes.md` | How the team says it works |

**For comparison:** the course's reference design (`cloud/cloudformation/*.yaml`, `.github/workflows/*.yml`, `docker/Dockerfile`).

**Allowed:** the project's tools (`python -m framework.cloud.audit`, `cfn-lint`, `actionlint`), the course documents (Units 1–4), and the AWS, GitHub, and JMeter documentation.

### How to run the tools on the case

```bash
python -m framework.cloud.audit exam/audit-case --fail-on high --out reports/exam-audit.md
```

```bash
cfn-lint exam/audit-case/template.yaml
```

```bash
actionlint exam/audit-case/pipeline.yml
```

> The audit tool prints **28 findings** on this case. Copying its output is worth few marks. The exam rewards:
> - **verifying** its findings;
> - **explaining** the impact of each;
> - **finding what it cannot see** (design, process, data, evidence quality);
> - **prioritising** a plan you can defend.

### Timing plan (420 min, with breaks)

| Time | Activity |
|---|---|
| 0–30 | Read everything once; run the tools; list your first impressions |
| 30–120 | Part 1 — Security |
| 120–175 | Part 2 — Reliability |
| 175–265 | Part 3 — Scalability and performance |
| 265–315 | Part 4 — Cost |
| 315–375 | Part 5 — Corrective action plan |
| 375–420 | Part 6 — Defence: prepare written answers; review; submit |

---

## B1 — Tasks and marks

| Part | Task | Marks |
|---|---|---|
| 1 Security | At least **10** findings in the finding format, with **at least 3 that the tool does not report**. For the top 3, describe the attack or failure path step by step | 25 |
| 2 Reliability | Find the ways a failure can look like success, and the ways a run cannot be reproduced or diagnosed. At least 6 findings | 15 |
| 3 Scalability and performance | (a) Is the performance test valid? Why or why not? (b) What saturates first, and how do you know? Use the metrics. (c) Apply Little's law to their numbers and interpret the result. (d) Design the re-test | 20 |
| 4 Cost | Break down the $326.30. Identify the waste and estimate the monthly saving per action, with your unit prices stated | 15 |
| 5 Corrective plan | A prioritised plan (P0–P3) with owner role, effort, dependency, and a **verification** for each action | 15 |
| 6 Defence | Written answers to the challenge questions in B3 | 10 |
| **Total** | | **100** |

### Report template

```markdown
# Audit report — QA Platform v1
Auditor: <name>   Date: <date>   Scope: exam/audit-case (template, pipeline, evidence)
Method: tools run (versions), manual review, calculations

## 1. Executive summary (≤ 10 lines)
Overall verdict per criterion (Red / Amber / Green), the 3 most important actions, the cost impact.

## 2. Findings
| Id | Criterion | Severity | Title | Tool-detected? |
(then one block per finding in the finding format)

## 3. Performance analysis
Validity · bottleneck · Little's law · re-test design

## 4. Cost analysis
Breakdown · waste · savings per action · assumptions (unit prices)

## 5. Corrective action plan
| Priority | Action | Fixes | Effort | Owner | Depends on | Verification |

## 6. Defence
Answers to B3

## Appendix
Tool outputs, calculations
```

---

## B2 — Marking rubric

| Criterion | Insufficient (0–40 %) | Basic (41–60 %) | Proficient (61–80 %) | Senior (81–100 %) |
|---|---|---|---|---|
| Security | Copies the tool's output | Correct severities; impact in general terms | Concrete attack paths; non-mechanical findings | Chains findings into attack paths (e.g. `pull_request_target` → keys → admin role); separates design flaws from configuration flaws |
| Reliability | Lists settings | Finds the false-success paths | Explains how each hides failures, with evidence | Shows how the whole pipeline can be green while nothing was tested, and how to prove a fix |
| Performance | Repeats the team's averages | Notices percentiles and errors | Identifies the invalid test **and** the DB/CPU saturation from the metrics | Uses Little's law to prove the generator problem; designs a valid re-test (workload model, steady state, objectives, safety) |
| Cost | Repeats the totals | Names the obvious waste | Estimates savings with stated prices | Ties every saving to a technical change and its risk; spots cost signals of reliability problems (hung devices) |
| Plan | Unordered list | Priorities | Priorities, effort, verification | A sequence that reduces risk fastest, with dependencies, owners, and measurable exit criteria |
| Defence | Restates the plan | Answers with opinions | Answers with evidence | Admits the trade-offs, quantifies them, and states what would change their mind |

---

## B3 — Challenge questions (Part 6)

Answer each in 5–10 lines, with evidence.

1. "Our tasks run in private subnets behind a NAT. Your design puts them in **public** subnets. That is less secure." Defend or revise your recommendation.
2. "Retrying a failing test 5 times keeps our build green. Why remove it?"
3. "A 24/7 service gives instant feedback. Running tasks on demand is slower." Answer with numbers.
4. "Just raise the database's max connections to 500." Is that the fix?
5. "The audit tool reported only 28 findings, and we will fix them all. Are we done?"
6. "Which **single** change gives the biggest risk reduction for one day of work?"

---

## B4 — Model answer guide (for self-assessment after the exam)

<details>
<summary><b>Open only after you submit</b></summary>

### Part 1 — Security (examples; a strong answer has more)

| Id | Severity | Finding | Tool? |
|---|---|---|---|
| SEC-01 | Critical | `pull_request_target` + checkout of the PR head: a fork's code runs with the repository's secrets, including `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | Yes (GHA-001, GHA-002) |
| SEC-02 | Critical | CI role: OIDC trust with **no `sub`** (any repository) **and** `AdministratorAccess` | Yes (OIDC-001, IAM-004) |
| SEC-03 | Critical | The reports bucket is public (`Principal: "*"` `s3:GetObject`, Block Public Access off). Reports can contain tokens, URLs, and customer data | Yes (S3-004, S3-001) |
| SEC-04 | Critical | One role is both execution role and task role, with `s3:*`, `logs:*`, `ecs:*` and `iam:PassRole` on `*`: test code can escalate | Partly (IAM-001/002); **the shared role is manual** |
| SEC-05 | High | Plain-text secrets in the task definition: the production admin password and a Slack token | Yes (ECS-001) |
| SEC-06 | Critical | **Supply chain:** the pipeline pushes PR code as `qa-runner:latest`, and the 24/7 service runs `latest`. An untrusted PR becomes running code with that role | **Manual** |
| SEC-07 | High | Tests use the **production** admin account and create real orders | **Manual** (architecture notes) |
| SEC-08 | High | Device Farm runs are started with a lead's **personal** long-lived access key from a laptop: no audit trail, no rotation | **Manual** |
| SEC-09 | High | SSH open to the internet on the runner's security group | Yes (NET-002) |
| SEC-10 | Medium | No `permissions:` block: the token gets default permissions | Yes (GHA-003) |
| SEC-11 | Low | Root user, writable root filesystem, no image scanning | Yes (ECS-006, ECS-003, ECR-002) |

**An attack path (top marks):**
1. An outsider opens a pull request.
2. `pull_request_target` checks out the PR's code with the repository's secrets.
3. Their build step prints or exfiltrates the AWS keys.
4. With those keys, or by assuming the CI role, which has no `sub` condition and `AdministratorAccess`, they control the whole AWS account.
5. Separately, their image becomes `latest` and runs in the service with `iam:PassRole *`.

### Part 2 — Reliability

| Finding | Why it matters |
|---|---|
| `run-task … \|\| true` and no wait | Every run is "green"; nothing ties a result to a commit |
| "Publish" step prints "Regression started" | Success is reported without any evidence |
| A loop service instead of one task per run | No per-run exit code; the results are not attributable |
| `latest` + mutable tags | No reproducibility; which image ran is unknown |
| No `logConfiguration` | No logs after a task stops (ECS-004) |
| Retries ×5, only the last reported | Flakiness and intermittent defects are hidden |
| One NAT gateway in one AZ, one private subnet | A single point of failure for every run |
| Cleanup by "a nightly script, when it works" | Data pollution; results depend on the previous runs |
| No timeouts (jobs, Device Farm) | Hung runs, as the cost file shows |
| Hourly schedule + PR trigger with no `concurrency` | Overlapping runs on shared data |

### Part 3 — Performance and scalability

**(a) Validity: the test does not support its "PASS".**

| Problem | Evidence |
|---|---|
| The load generator was saturated | "Load generator CPU during the run: 97–100 %" |
| Decision taken on the average only | Average 420 ms, but p95 **9.8 s**, p99 15 s (timeouts) |
| Error rate | **6.1 %** on checkout |
| Steady state | 0 → 200 users in 60 s of a 120-s run: only 60 s at full load |
| Workload model | No think time: 200 threads ≠ 200 users |
| Target | **Production**, with an admin account: unsafe, and it pollutes the data |
| Repetition | One run |

**(b) What saturates first** (`cloudwatch-metrics.csv`):

| Minute | Task CPU % | DB connections | Queue visible | Oldest (s) | Checkout 5xx |
|---|---|---|---|---|---|
| 0 | 35 | 40 / 100 | 0 | 0 | 0 |
| 1 | 71 | 72 / 100 | 120 | 8 | 3 |
| 2 | **96** | **100 / 100** | 980 | 41 | **61** |
| 3 | 98 | 100 / 100 | 2,210 | 95 | 240 |
| 4–5 | 97–98 | 100 / 100 | 3,405 → 4,120 | 152 → 201 | 295–310 |

- At minute 2, the **database connection pool is full** at the same moment the 5xx errors start, and the tasks' CPU is at 96 %.
- The number of tasks stays at **2**: there is no autoscaling.
- The queue's oldest message ages steadily, so the consumers are falling behind.

Two resources saturate together: the app tasks' CPU and the DB connections. The 5xx errors follow the connection limit. Raising only one moves the bottleneck to the other, as Day 16 showed. The recommendations are:
- a connection-pool limit per task, sized to `DB max ÷ tasks`;
- autoscaling of the service on CPU **and** on queue age;
- checking the DB side (max connections, a proxy);
- backpressure on the queue.

**(c) Little's law on their numbers:**
- **Throughput:** 11,820 + 23,504 samples in 120 s → **X ≈ 294 requests/s**.
- **Mean response time** (sample-weighted, from their averages): **R ≈ 0.204 s**.
- **Requests in progress:** N = X × R ≈ **60** on average.
- **Threads:** the average number of active threads over the run was (100 × 60 + 200 × 60) / 120 = **150**.

Only about 40 % of thread time was spent inside requests, although the plan had **no think time**. The rest is the load generator struggling (CPU 97–100 %). So the real load was far below "200 users", and the reported timings are distorted: the test is invalid on its own numbers.

**(d) A valid re-test:**
- a **test environment**, not production;
- an agreed **open** workload at the expected arrival rate (Open Model Thread Group or Precise Throughput Timer), plus a step-capacity test;
- think time where users are modelled;
- **≥ 10 minutes** of steady state (CloudWatch 1-minute resolution);
- **distributed** generators, each kept below 70 % CPU;
- percentile objectives (p95, p99), an error-rate objective, and `min_samples`;
- 3 runs;
- telemetry correlated on a UTC time axis (Day 16).

### Part 4 — Cost (unit prices: us-east-1, approximate, November 2026)

| Item | 30 days | Cause | Action | New estimate | Saving |
|---|---|---|---|---|---|
| Regression service 24/7 (4 vCPU / 16 GB) | 170.60 | Loop service, oversized | One task per trigger, 1 vCPU / 2 GB: ~30 runs/day × 15 min ≈ 225 h × $0.0494 | ≈ 11 | **≈ 160** |
| NAT gateway (hours + bytes) | 44.05 | Private subnet for a test runner | Public IP + no inbound, or an S3 gateway endpoint | ≈ 0 | **≈ 44** |
| Device Farm | 76.50 | 450 device minutes = **3 runs × 150 min**, hung until a long default timeout | 20-min job timeout + `stop-run` in cleanup | ≈ 10 | **≈ 66** |
| CloudWatch Logs ingestion and storage | 25.40 | 24/7 loop logs; no retention | Fewer runs; 14 days | ≈ 3 | ≈ 22 |
| S3 storage | 9.75 | Reports kept since 2024 | 30-day lifecycle | ≈ 1 | ≈ 9 |
| **Total** | **326.30** | | | **≈ 25** | **≈ 300 (≈ 92 %)** |

A senior answer also notes:
- **The cost file is also reliability evidence:** the device minutes reveal hung runs.
- **The savings follow from the security and reliability fixes.** The same changes that remove risk remove most of the cost.

### Part 5 — A defensible plan (example)

| Priority | Action | Fixes | Effort | Verification |
|---|---|---|---|---|
| **P0 (today)** | Remove `pull_request_target`; rotate the AWS keys, the admin password, and the Slack token; delete the long-lived keys | SEC-01, SEC-05, SEC-08 | S | The keys are deactivated in IAM; the audit shows no GHA-001/002 |
| P0 | Make the bucket private (Block Public Access, delete the public policy) | SEC-03 | S | The audit shows no S3-001/004; an anonymous GET returns 403 |
| P0 | CI role: OIDC with `sub = repo:<org>/<repo>:environment:<env>`, least privilege; detach `AdministratorAccess` | SEC-02 | M | The audit shows no OIDC-001 or IAM-004; an assume-role from another repository is denied |
| P1 | Separate execution and task roles; a narrow task role; `PassRole` limited to 2 roles | SEC-04 | M | The audit shows no IAM-001/002 |
| P1 | Replace the service with one task per trigger; wait; gate on the exit code; immutable `:<commit>` tags; scan gate | Reliability, SEC-06 | M | Each commit has a run record with its exit code |
| P1 | A test environment and test accounts; no production admin; cleanup inside the tests | SEC-07, data | L | No test orders in production; cleanup assertions pass |
| P2 | Timeouts everywhere; Device Farm job timeout of 20 min; cleanup `always()` | Cost, reliability | S | No run longer than its timeout in 30 days |
| P2 | Remove the NAT (public IP + no inbound) or use endpoints; log retention; S3 lifecycle; a budget alarm | Cost | S | Cost Explorer next month; a budget email received at 80 % |
| P2 | Remove the 5× retries; quarantine flaky tests with a register (strict xfail) | Reliability | M | The flake rate is reported per test |
| P3 | A valid performance re-test (B4 Part 3d); connection pool and autoscaling | Performance | L | p95 and error objectives met at the agreed rate, 3 runs |

### Part 6 — Defence notes

1. **Public subnets:** "Public" only means the task *has* an address. With no inbound rules, nothing can connect. The NAT design costs $44 a month and depends on one AZ. If policy forbids public IPs, use VPC endpoints (S3 gateway endpoint free; interface endpoints per hour). Either way, not a single-AZ NAT.
2. **Retries:** they hide intermittent product defects and make flakiness invisible. Quarantine known flaky tests in a register (visible, owned, with an expiry). Retry only classified environment errors (Unit 2).
3. **24/7 service:** about $171 a month for continuous loops that no commit asked for. On-demand tasks start in about a minute and run per commit. Feedback becomes *attributable*, which is worth more than instant but unattributed results.
4. **Max connections 500:** it moves the bottleneck back to the tasks' CPU (96–98 %), and may overload the database. Size the pools, autoscale on CPU and queue age, and re-test.
5. **28 findings:** the tool's findings are necessary, not sufficient. The supply-chain path, production data, personal keys, `|| true`, the invalid performance test, and hung devices are not tool findings, and several are critical.
6. **One day:** P0, which removes the exploit chain: drop `pull_request_target`, rotate and delete the keys, make the bucket private, and restrict the CI role. Each step is small and closes an open path today.
</details>

---

## After the exam: what Unit 4 delivered

| Day | Output | Where |
|---|---|---|
| 13 | Cloud execution design notes | Day13.md + `cloud/` reference |
| 14 | Pipeline and performance test design | Day14.md |
| 15 | An image run under Fargate's constraints, with its stop drill and retained artifacts | `docker/`, `framework/cloud/` |
| 16 | BlazeDemo results; a real bottleneck found, fixed, and verified; a Device Farm plan | `perf/`, `framework/perf/`, `cloud/devicefarm/` |
| 17 | A gated pipeline, linted and replayed, with every gate seen failing | `.github/workflows/` |
| 18 | An audit and a defended plan | Your report |

---

## Verification log

| Check | Result |
|---|---|
| `python -m framework.cloud.audit exam/audit-case` | 28 findings, 12 high or critical; rules include GHA-001/002/003/005, OIDC-001/003, IAM-001/002/004, S3-001/002/004, NET-001/002, LOG-001, ECS-001/004/005 |
| Unit test `test_the_exam_case_is_caught` | Passing: the expected rule set is a subset of what the tool finds |
| Model-answer calculations | Recomputed: X ≈ 294.4/s, R ≈ 0.2038 s, N ≈ 60.0; average threads 150; 450 device minutes = 3 × 150; total $326.30; 4 vCPU / 16 GB around the clock ≈ $170.12 at the stated unit prices |
| The case | Fictional and deliberately flawed; **never deployed** |
