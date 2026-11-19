# Unit 4 · Day 17 — Topic Revision (LO5, LO7, LO8), then the CI/CD Integration Lab

| | |
|---|---|
| **Course** | Advanced Automation Test Engineering (ATEST03) — Fast Track |
| **Unit** | Unit 4 — AWS Cloud Execution, Performance, and CI/CD |
| **Session A** | Topic Revision · Guides/Review · Virtual · **60 min** · **LO5, LO7, LO8** |
| **Session B** | CI/CD integration lab: orchestrate container, Device Farm, performance stages, quality gates, reports, and cleanup · Assignment/Lab · Hybrid · **150 min** · **LO7, LO8** |
| **Code** | `Unit4/unit4-code/shop-bdd.zip`: `.github/workflows/ci.yml` (runnable), `.github/workflows/cloud.yml` (reference) |
| **CI/CD platform** | **GitHub Actions** (reasons in Day 14, Part 0) |
| **Output of the day** | A: quiz answers and a revision mind map. B: the pipeline map, each stage replayed locally with its evidence, four gates made to fail on purpose, and your pipeline review |

> **How this lab was checked.**
> - **Linted, not run on GitHub:** both workflows pass `actionlint` 1.7.12 with shellcheck 0.11. No GitHub account was used, so neither workflow was run there.
> - **Replayed locally, command for command:** every stage of `ci.yml` (quality, container, performance), with the outputs quoted below. The four "make the gate fail" experiments were run too.
> - **Not executed:** `cloud.yml`'s AWS stages. They are explained line by line.

---

# Session A — Topic Revision: Mobile, Cloud, Performance (LO5, LO7, LO8) · 60 min

| Time | Activity |
|---|---|
| 0–10 | A.1 The thread through Units 3–4 |
| 10–35 | A.2 Quiz (12 questions) |
| 35–60 | A.3 Mind map: one test's journey from a commit to evidence |

## A.1 The thread

```
Unit 3 Day 11  Appium suite (LO5)  ──▶ Day 16: the same suite, packaged for Device Farm (LO7)
Unit 3 Day 12  async sandbox (LO6) ──▶ Day 16: the system under load; its /metrics = our CloudWatch (LO8)
Unit 4 Day 15  container + artifacts (LO7) ──▶ Day 17: a pipeline stage with gates
Unit 4 Day 16  bottleneck evidence (LO8)   ──▶ Day 17: a performance gate that stops a regression
```

## A.2 Quiz (answers below — try first)

1. (LO5) Device Farm injects no Appium capabilities in a custom environment. How does our suite still get the right ones?
2. (LO5) Which Unit 3 rule does the test spec's `pre_test` loop follow?
3. (LO7) What are the three identities in the reference design, and which one does the CI job use?
4. (LO7) A Fargate task stopped with `exit 75`. What will the pipeline's gate do, and why?
5. (LO7) Why does `cloud.yml` register a **new** task definition revision for every run?
6. (LO8) Users doubled, throughput stayed flat, p95 tripled. What do you look for in the telemetry?
7. (LO8) Why did adding payments workers change nothing in Day 16's experiment?
8. (LO8) Why must a performance gate have `min_samples`?
9. (LO8) Which CloudWatch metric is the best single alarm for "consumers are falling behind"?
10. (LO7/LO8) Why is BlazeDemo limited to 10 users while the sandbox may be stressed?
11. (LO7) Why can a 10-minute device run cost more than a whole month of container runs?
12. (LO5/LO7) What evidence must a failed Device Farm job leave for diagnosis?

<details>
<summary><b>Answer guide</b></summary>

1. The framework builds capabilities from `SHOP_*` variables; the test spec sets them from `DEVICEFARM_APP_PATH` and `DEVICEFARM_DEVICE_NAME`.
2. Wait for a condition, with a deadline: poll `/status` until it is ready, for at most 30 tries, then fail.
3. The task execution role, the task role, and the CI role. The CI job uses the **CI role**, through OIDC, restricted to one repository and one environment.
4. It fails the run. The tests passed, but their evidence was not stored, and a pass that cannot be checked is not a pass.
5. Tags are immutable and the image changes with every commit. A task definition revision pins the exact image the run used.
6. The queue that grows while its processing rate stays flat. That consumer is the bottleneck.
7. Payments was not saturated (its queue was about 0). The limit was fulfilment, at about 9.8/s.
8. Without it, a run with too few (or zero) samples would "pass". Missing evidence must fail.
9. SQS `ApproximateAgeOfOldestMessage`: it rises when consumers cannot keep up, whatever the traffic level.
10. BlazeDemo is someone else's service, so the course only sends light, practice-level traffic. The sandbox is ours.
11. Device minutes cost $0.17 each, and they multiply with every device in the pool (2 × 10 min = $3.40). A 10-minute Fargate run costs under a cent.
12. The video; the device log; the Appium log; our framework's evidence (screenshot, page source, logcat, step log) copied into `$DEVICEFARM_LOG_DIR`; and the run's result and counters.
</details>

## A.3 Mind map exercise

Draw one test's journey: commit → CI → image → Fargate task → S3 → gate → report. Do the same for one mobile test: commit → package → Device Farm → artifacts → gate. At each arrow, write: **who** acts (identity), **what proves it happened** (evidence), and **what stops the pipeline** (gate). Compare with a partner.

---

# Session B — CI/CD Integration Lab (LO7, LO8) · 150 min

## Lab plan

| Time | Part |
|---|---|
| 0–15 | B0 — The pipeline map |
| 15–45 | B1 — Stage 1: quality (replay locally) |
| 45–65 | B2 — Stage 2: container |
| 65–90 | B3 — Stage 3: performance |
| 90–115 | B4 — Stage 4: the cloud pipeline (`cloud.yml`, walkthrough) |
| 115–135 | B5 — Make every gate fail on purpose |
| 135–150 | B6 — Review and deliverables |

## B0 — The pipeline map 🟢

```
                      ┌──────────── ci.yml (every push / PR, free runners) ────────────┐
push / PR ──▶ quality ─┬─▶ container   (build image, run the offline suite read-only)
                       ├─▶ performance (JMeter → sandbox, telemetry, bottleneck report, SLA gate;
                       │                BlazeDemo only on manual runs)
                       └─▶ live        (real shop, serial; main / nightly / manual only)
                      └─────────────────────────────────────────────────────────────────┘
                      ┌──────────── cloud.yml (manual, reviewer approval, costs money) ─────┐
workflow_dispatch ──▶ fargate      OIDC → ECR push → scan gate → task def → run-task → wait
                       │                → evidence (S3 + CloudWatch) → exit-code gate → cleanup
                      └─▶ device-farm  package → 3 uploads → schedule-run → wait
                                       → artifacts → result gate → cleanup
                      └──────────────────────────────────────────────────────────────────────┘
```

| Design choice | Where | Why |
|---|---|---|
| `permissions: contents: read` at the top | Both workflows | The default token gets nothing it does not need (audit GHA-003) |
| `id-token: write` only in `cloud.yml` | `cloud.yml` | Needed for OIDC, nowhere else |
| `timeout-minutes` on every job | Both | A hung job costs at most its timeout (GHA-004) |
| `environment: aws-lab` | `cloud.yml` | A human approves every run that spends money; environment secrets stay there |
| `concurrency: group: cloud` | `cloud.yml` | One cloud run at a time: predictable cost, no clashes |
| `if: vars.AWS_ROLE_ARN != ''` | `cloud.yml` | Without AWS set up, the jobs are **skipped**, not failed |
| `if: always()` on evidence and cleanup | Both | Evidence and cleanup matter most when something failed |
| Artifacts uploaded with a retention period | Both | Reports outlive the runner, for 14 days |

---

## B1 — Stage 1: quality 🟡

The steps, in the order `ci.yml` runs them (each one is a gate):

```bash
pip install -r requirements-dev.txt
```

```bash
ruff check . && ruff format --check . && mypy
```

```bash
python -m framework.review --strict
```

```bash
pytest --store fake -n auto --fail-on-uncovered --cov --cov-report=term --cov-report=xml:reports/coverage.xml
```

```bash
pytest --store fake tests/events tests/test_order_events.py -n auto --sandbox-build fixed
```

```bash
cfn-lint cloud/cloudformation/test-execution.yaml cloud/cloudformation/device-farm.yaml
```

```bash
actionlint .github/workflows/ci.yml .github/workflows/cloud.yml
```

```bash
python -m framework.cloud.audit cloud .github/workflows --fail-on high
```

The real replay (a fresh install from the Unit 4 zip):

```
All checks passed!
148 files already formatted
Success: no issues found in 140 source files
… Problems found: 0
Required test coverage of 90.0% reached. Total coverage: 91.66%
294 passed, 2 skipped, 5 xfailed in 8.18s
20 passed in 5.09s
cfn ok
actionlint ok
audit: 1 finding(s), 0 at or above 'high' -> reports/audit.md
```

> 🔴 **What linting the workflows found while this lab was written.** With shellcheck installed, `actionlint` reported 5 issues in the scripts inside the workflows:
> - an unused loop variable;
> - unquoted paths (twice);
> - a JMESPath backtick inside single quotes;
> - an unused `read` variable.
>
> None of them would have shown up until a run on GitHub. Linting the pipeline is part of the pipeline.

---

## B2 — Stage 2: container 🟡

```yaml
      - name: Run as on Fargate (read-only root, non-root user, writable reports and /tmp only)
        run: |
          mkdir -p archive && chmod 777 archive
          docker run --rm --read-only --tmpfs /tmp --tmpfs /app/reports:uid=10001 \
            -v "$PWD/archive:/archive" -e RUN_ID=ci-${{ github.run_id }} \
            shop-bdd-tests:${{ github.sha }} --suite offline --artifacts /archive
```

The local replay of this stage: 260 passed, exit 0, artifacts with `manifest.json` (Day 15, Part 2). This stage proves on every push that the image builds and runs under Fargate's constraints, **for free**, so `cloud.yml` should only fail for AWS reasons.

---

## B3 — Stage 3: performance 🟡 → 🔴

```yaml
env:
  JMETER_VERSION: "5.6.3"
  # SHA-512 published by Apache for apache-jmeter-5.6.3.tgz: a download that does not match never runs.
  JMETER_SHA512: "5978a1a35edb5a7d428e270564ff49d2b1b257a65e17a759d259a9283fc17093e522fe46f474a043864aea6910683486340706d745fcdf3db1505fd71e689083"
```

```yaml
      - name: Load test with telemetry (5 users, 30 s)
        run: |
          python -m framework.perf.telemetry http://127.0.0.1:8765 --out reports/perf/telemetry.csv --duration 40 &
          "apache-jmeter-${JMETER_VERSION}/bin/jmeter" -n -t perf/orders_sandbox.jmx -q perf/jmeter.properties \
            -l reports/perf/orders.jtl -e -o reports/perf/orders-html \
            -Jusers=5 -Jrampup=5 -Jduration=30 -Jrun=ci-${{ github.run_id }}
          wait
      - name: Bottleneck report (load vs telemetry)
        run: python -m framework.perf.correlate reports/perf/orders.jtl reports/perf/telemetry.csv
      - name: SLA gate
        run: python -m framework.perf.gate reports/perf/orders.jtl --profile sandbox
```

The real local replay of this stage:

```
summary =   1927 in 00:00:30 =   64.3/s Avg:     1 Min:     0 Max:   582 Err:     0 (0.00%)
bottleneck: fulfilment; at full load (5 users, 6 windows): mean queue fulfilment 2.8; payments 0.0, projector 0.0;
            processing rates: fulfilment 9.2/s, payments 9.4/s, projector 37.3/s; client side: 9.5 completed/s, p95 519 ms
PASS  TX order completed  p95 ms  expected <= 2000  actual 520
perf gate sandbox: PASSED -> reports/perf/gate-sandbox.md
```

| Choice | Why |
|---|---|
| A **small** load (5 users, 30 s) on every push | Fast and cheap, and enough to catch a regression: if someone halves fulfilment's speed, p95 doubles and the gate trips. It is a **smoke**, not a capacity test |
| The system under load is started **inside** the job | Reproducible, isolated, and nobody else's server |
| The bottleneck report runs even when the gate passes | The trend matters. Even at 5 users, fulfilment already queues (2.8): an early warning recorded in every run |
| BlazeDemo only on `workflow_dispatch` with an input | Someone else's site: never on every push |
| JMeter cached, and its checksum verified | Speed, and supply-chain safety |

> **Your turn (🔴).** Capacity tests (Day 16's 40-user steps) do not belong on every push. Add a `schedule` trigger and a separate job `capacity` that runs the 40-user test nightly and uploads the bottleneck report. What must it **not** do on failure? (Hint: it should notify, but should it block merges?)

---

## B4 — Stage 4: the cloud pipeline (`cloud.yml`, walkthrough) 🟡 → 🔴

> ⚠️ **Not executed**: it needs an AWS account set up with `cloud/cloudformation/*.yaml` and these repository variables: `AWS_REGION`, `AWS_ROLE_ARN`, `ECR_REPOSITORY`, `ECS_CLUSTER`, `TASK_FAMILY`, `SUBNET_IDS`, `SECURITY_GROUP_ID`, `ARTIFACTS_BUCKET`, `DEVICEFARM_PROJECT_ARN`, `DEVICEFARM_POOL_ARN`, `ANDROID_APP_URL`. Without them, every job is skipped.

### B4.1 Fargate job: the gates

| Step | Gate | Fails when |
|---|---|---|
| Build and push `:<commit>` | — | The build fails |
| `aws ecr wait image-scan-complete` + scan findings | **Image gate** | Any CRITICAL vulnerability |
| Register a task definition revision | — | IAM (`ecs:RegisterTaskDefinition`, `iam:PassRole`) |
| `run-task` → `wait tasks-stopped` | Bounded wait | The task does not stop in time |
| Collect evidence (`s3 sync`, `logs get-log-events`) | — (`if: always()`) | Never blocks: evidence is gathered whatever happened |
| Exit-code gate | **Run gate** | Exit ≠ 0 (1 tests, 75 evidence lost, `null` never started) |
| Cleanup | — (`if: always()`) | Stops the task if it still runs |

The scan gate, as linted:

```yaml
          critical=$(aws ecr describe-image-scan-findings --repository-name "${{ vars.ECR_REPOSITORY }}" \
            --image-id imageTag="$IMAGE_TAG" --query 'imageScanFindings.findingSeverityCounts.CRITICAL' --output text)
          [ "$critical" = "None" ] && critical=0 # no CRITICAL key = none found
          echo "critical findings: $critical"
          test "$critical" -eq 0
```

### B4.2 Device Farm job: bounded waits and cleanup

```yaml
      - name: Cleanup - stop an unfinished run, delete the uploads
        if: always()
        run: |
          if [ -n "${RUN_ARN:-}" ] && [ "$(aws devicefarm get-run --arn "$RUN_ARN" --query run.status --output text)" != "COMPLETED" ]; then
            aws devicefarm stop-run --arn "$RUN_ARN"
          fi
          for arn in "${APP_ARN:-}" "${PACKAGE_ARN:-}" "${SPEC_ARN:-}"; do
            [ -n "$arn" ] && aws devicefarm delete-upload --arn "$arn" || true
          done
```

| Safeguard | Effect |
|---|---|
| `jobTimeoutMinutes=20` in `schedule-run` (and as the project's default) | A hung device costs at most 20 minutes |
| A polling loop of at most 120 × 15 s | The pipeline never waits forever |
| `stop-run` in `if: always()` | A cancelled pipeline does not leave devices running (the exam case lost $76.50 to exactly this) |
| Gate on `result = PASSED` | `ERRORED` (device problems) and `FAILED` (tests) both stop the pipeline; the evidence tells which |

### B4.3 🔴 Reports: what a reviewer gets

| Artifact | From | Contents |
|---|---|---|
| `offline-reports` | quality | The traceability matrix, the async evidence record, the BDD review, the audit |
| `container-run-artifacts` | container | `run.json`, `manifest.json`, all reports from inside the image |
| `performance-reports` | performance | JTL, the JMeter HTML dashboard, telemetry, `bottleneck.md`, the gate (`.md` + `.json`) |
| `fargate-evidence` | cloud | S3 artifacts of the run, CloudWatch log lines, the task result |
| `device-farm-evidence` | cloud | Video, logs, screenshots, our framework's reports |

---

## B5 — Make every gate fail on purpose 🔴

A gate you have never seen fail is a gate you do not trust. Each experiment was run against a copy of the project:

| # | Change | Gate | Real result |
|---|---|---|---|
| 1 | Tighten the objective: `p95_ms = 300` for "TX order completed" | Performance | `FAIL  TX order completed  p95 ms  expected <= 300  actual 520` → `FAILED (1 objective(s))`, **exit 1** |
| 2 | Add `cloud/iam/quick-fix.json` with `"Action": "s3:*", "Resource": "*"` | Audit | `audit: 2 finding(s), 1 at or above 'high'`, **exit 1** |
| 3 | `timeout-minutes: fifteen` in `ci.yml` | Workflow lint | `ci.yml:86:22: expecting a single ${{...}} expression or float number literal, but found plain text node [syntax-check]` |
| 4 | An empty JTL (header only: the script broke) | Performance | `FAIL  POST /orders  samples  expected >= 20  actual 0` and the same for "TX order completed" → `FAILED (2 objective(s))` |

Experiment 4 is the most important. Without `min_samples`, a broken load script would produce **no data, and a green gate**.

> **Your turn (🟡).** Make two more gates fail on purpose:
> - put `SHOP_API_TOKEN` in a task definition's `Environment` (the audit should catch ECS-001);
> - make the container write to `/app/new.txt` (the read-only run should fail).
>
> Record the exact message of each.

---

## B6 — Review and deliverables

### B6.1 Pipeline review checklist

| # | Check | ✔/✘ |
|---|---|---|
| 1 | No long-lived cloud keys anywhere; OIDC is restricted to one repository and one environment | |
| 2 | The default token permissions are read-only; extra permissions are granted per workflow | |
| 3 | Every job has a timeout; every wait has a bound | |
| 4 | Every gate fails closed (no data = fail) and writes a report | |
| 5 | Evidence and cleanup steps run `always()` | |
| 6 | Paid stages need a human approval and run one at a time | |
| 7 | Third-party targets get only agreed load, and never on every push | |
| 8 | Downloads are verified (checksums), and the base image is pinned | |
| 9 | Reports are uploaded with a retention period | |
| 10 | Each gate has been seen to fail (B5) | |

### B6.2 Deliverables

- [ ] The B0 map, redrawn with **your** stage names and gates
- [ ] The local replay of B1–B3, with your outputs
- [ ] The four B5 experiments plus your two, each with its exact failure message
- [ ] The B3 "Your turn": the `capacity` job, and your answer on blocking vs notifying
- [ ] The B6.1 checklist filled in for `ci.yml` **and** `cloud.yml`, with one improvement you would make to each

---

## Common errors

| Error | Meaning | Fix |
|---|---|---|
| `actionlint: no project was found` | Run outside a git repository | Pass the files: `actionlint .github/workflows/ci.yml .github/workflows/cloud.yml` |
| `cfn-lint E3006 … does not exist in 'us-east-1'` | Device Farm types are only in us-west-2 | The template declares `Metadata: cfn-lint: config: regions: [us-west-2]` |
| A job is skipped in `cloud.yml` | The AWS variables are not set | Expected without an AWS account |
| `Not authorized to perform sts:AssumeRoleWithWebIdentity` | The trust policy's `sub` does not match (wrong repository or environment name) | Compare it with `repo:<owner>/<repo>:environment:aws-lab` |
| The performance gate fails only in CI | The runner is slower than your laptop | Compare the bottleneck report. Set objectives with headroom for the CI runner, or run performance on a dedicated runner |

---

## Self-check (answers below — try first)

1. Why does `ci.yml` run a container stage if `cloud.yml` runs the image on Fargate anyway?
2. Why is the performance stage only 5 users for 30 s?
3. Which `cloud.yml` steps must run even when the tests fail, and why?
4. Why does `cloud.yml` skip instead of fail when AWS is not configured?
5. What did gate experiment 4 prove?
6. Name three ways the pipeline limits cost.
7. Why lint the workflows themselves?

<details>
<summary><b>Answer guide</b></summary>

1. To catch packaging and runtime problems (read-only filesystem, missing dependencies) for free on every push, so the cloud run fails only for AWS reasons.
2. It is a regression smoke on every push: fast, cheap, and still sensitive to a slowdown. Capacity tests run separately, on a schedule.
3. Evidence collection and cleanup (`if: always()`): failures are exactly when you need the evidence, and when resources are most likely to be left running.
4. A missing optional integration is not a defect. Skipping keeps the pipeline green for forks and for users without AWS, while making clear that nothing ran.
5. That a broken script producing no samples fails the gate instead of passing it: fail closed.
6. Any three of: manual approval, one cloud run at a time, job timeouts, Device Farm job timeouts, cleanup steps, artifact retention, small performance smokes.
7. Workflows are code that runs with credentials. Syntax errors and shell bugs would otherwise surface only during a (possibly paid) run; shellcheck found five here.
</details>

## Next: Day 18

Topic revision of LO7 and LO8, then the **cloud execution audit exam**: evaluate the security, reliability, scalability, performance, and cost of a test platform, recommend corrective actions, and defend them (LO7–LO9).

---

## Verification log

| Check | Result |
|---|---|
| Stage 3 replay with `-q perf/jmeter.properties` (5 users, 30 s) | 1,939 samples, 0 errors; gate PASSED; fulfilment queue 2.8 at 5 users |
| Playwright `expect` timeout | Aligned with `--ui-timeout` (`expect.set_options`): a missing element now fails after the configured time (checked: 5.0 s default → 1.0 s when set to 1,000 ms) |
| Live web suite after the changes | 49 passed, 3 xfailed (known defects) |
| `actionlint` 1.7.12 + shellcheck 0.11 (`ci.yml`, `cloud.yml`) | Clean, after fixing 5 shellcheck findings |
| Stage 1 replay (fresh install from the zip, re-run after the senior-level hardening) | All clean; 294 passed / 2 skipped / 5 xfailed; code coverage 91.66 % (gate 90 %); fixed build 20 passed; cfn-lint, actionlint, audit OK |
| Stage 2 replay | Image built; offline suite read-only: 260 passed, exit 0 |
| Stage 3 replay (5 users, 30 s) | 1,927 samples, 0 errors; gate PASSED (TX p95 520 ms); bottleneck report written |
| B5 gate experiments 1–4 | Run on a copy of the project; messages copied above (exit codes checked) |
| **`ci.yml` / `cloud.yml` on GitHub** | **Not run** (no GitHub or AWS account used) |
