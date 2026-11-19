# Unit 4 · Day 13 — AWS Test-Execution Architecture: IAM, Networking, ECR/ECS/Fargate, S3 Artifacts, CloudWatch, Device Farm

| | |
|---|---|
| **Course** | Advanced Automation Test Engineering (ATEST03) — Fast Track |
| **Unit** | Unit 4 — AWS Cloud Execution, Performance, and CI/CD |
| **Learning outcome** | **LO7** — Execute containerized and mobile automation securely using ECS/Fargate and AWS Device Farm with retained artifacts (Bloom **B3: Apply**) |
| **Format** | Concept/Lecture · Virtual · 120 minutes · no code to produce (the reference design is in the project, for reading) |
| **Code to read** | `Unit4/unit4-code/shop-bdd.zip`: `docker/`, `framework/cloud/`, `cloud/cloudformation/`, `cloud/devicefarm/` |
| **Output of the day** | Your one-page **cloud execution design notes** (end of this document) |

> **How the facts here were checked.**
> - **Run for real on a local machine:**
>   - The container image was built and run read-only, as a non-root user, with no network at all: 260 tests passed.
>   - Stopping the container with SIGTERM was tested.
>   - The S3 artifact store was tested against **moto**, a local fake of the S3 API.
>   - The Device Farm test package was built and installed offline in a clean container.
> - **Checked by tools, but never deployed:** the AWS templates passed `cfn-lint` 1.60.1, the workflows passed `actionlint` 1.7.12 with `shellcheck`, and both passed the project's own audit.
> - **Not done:** nothing was deployed to an AWS account. AWS behaviour is described from AWS documentation and is marked *(AWS docs)*.
> - **Prices:** checked in November 2026, mostly from third-party summaries of the AWS price pages. Treat them as approximate and check the AWS pricing pages before you rely on them.

---

## How to use this lecture

Units 1–3 ran tests on a laptop or a CI runner. Unit 4 moves the same suites into AWS:
- **containers** run the suites on **ECS/Fargate**;
- **real phones** run the mobile suite on **Device Farm**;
- the evidence is kept in **S3** and **CloudWatch**.

The questions change, from *"does the test pass?"* to:
- *who* is allowed to do *what*;
- *where* the traffic goes;
- *what* stays after the run;
- *what* it costs.

| Badge | Level | After this level you can… |
|---|---|---|
| 🟢 | **Foundation** | Name each AWS service in the design and say what it does for a test run |
| 🟡 | **Practitioner** | Read a task definition, an IAM policy, and a Device Farm test spec, and spot what is missing |
| 🔴 | **Senior** | Design least-privilege identities, network boundaries, artifact retention, and telemetry for a cloud test platform, and justify each choice in terms of security, reliability, and cost |

### Lecture plan (120 min)

| Time | Part |
|---|---|
| 0–10 | Part 0 — Why run tests in the cloud; the reference design |
| 10–30 | Part 1 — IAM: who may do what |
| 30–45 | Part 2 — Networking boundaries |
| 45–65 | Part 3 — Images: Docker and ECR |
| 65–85 | Part 4 — ECS and Fargate: running a test task |
| 85–95 | Part 5 — S3: retained artifacts |
| 95–105 | Part 6 — CloudWatch: logs and metrics as evidence |
| 105–118 | Part 7 — Device Farm: real phones |
| 118–120 | Part 8 — One run, end to end |

---

## Glossary

| Term | Meaning | Vietnamese |
|---|---|---|
| IAM role | An identity with permissions that a service or a CI job **assumes**; it gets temporary credentials | Vai trò IAM |
| Policy | A JSON document: which actions, on which resources, under which conditions | Chính sách quyền |
| Trust policy | Who may assume a role | Chính sách tin cậy |
| Least privilege | Only the permissions the job needs, nothing more | Đặc quyền tối thiểu |
| OIDC | A standard that lets GitHub prove "this is workflow X of repository Y" to AWS without stored keys | Đăng nhập liên kết OIDC |
| VPC / subnet | Your private network in AWS, and its parts | Mạng riêng ảo / mạng con |
| Security group | A firewall attached to a task | Nhóm bảo mật |
| NAT gateway | Lets private subnets reach the internet; billed per hour and per GB | Cổng NAT |
| ECR | AWS's container image registry | Kho ảnh container |
| ECS / Fargate | Runs containers; Fargate = serverless capacity, no machines to manage | Dịch vụ chạy container |
| Task definition | The recipe of a container run: image, CPU, memory, roles, logs | Định nghĩa tác vụ |
| Task | One run of a task definition | Tác vụ |
| S3 | Object storage | Lưu trữ đối tượng |
| CloudWatch | Logs, metrics, alarms | Giám sát |
| Device Farm | Runs app tests on real phones and tablets in AWS | Phòng thiết bị thật |
| Artifact | A file a run leaves behind: reports, screenshots, videos, logs | Tạo phẩm kiểm thử |

---

## Part 0 — Why run tests in the cloud 🟢

| Need | Laptop / CI runner | Cloud execution |
|---|---|---|
| Same environment every run | "Works on my machine" | The same image, with its digest recorded |
| Parallel capacity | Limited by one machine | Many tasks at once, paid per second |
| Real devices | One emulator | Many real phones (Device Farm) |
| Evidence that outlives the run | Lost with the runner | Kept in S3 and CloudWatch, with a retention period |
| Network position | Outside | Next to the system under test, or deliberately outside it |

### 0.1 The reference design (in the project, not deployed)

```
GitHub Actions ──OIDC──▶ IAM role (one repo + one environment)
     │                     │ may: push one ECR repo, run one task family, pass two roles, read logs/artifacts
     ▼                     ▼
docker build ──▶ ECR repo (immutable tags, scan on push, keep last 10)
                           │
                           ▼
              ECS cluster ──▶ Fargate task (public subnet, public IP, NO inbound rules)
                               │  task role: may only PutObject to s3://bucket/runs/*
                               ├──▶ CloudWatch Logs  /ecs/shop-bdd-tests  (14 days)
                               ├──▶ Container Insights metrics (CPU, memory per task)
                               └──▶ S3 bucket  runs/<run-id>/...  (encrypted, private, TLS-only, 30 days)

Device Farm project (us-west-2) ──▶ device pool (2 Android phones) ──▶ artifacts: video, logs, our reports
Budget: email at 80 % of $10 (actual) and 100 % (forecast)
```

Files:
- `cloud/cloudformation/test-execution.yaml` — ECR, S3, CloudWatch, ECS, IAM, OIDC, and the budget.
- `cloud/cloudformation/device-farm.yaml` — the Device Farm project and device pool.
- `docker/Dockerfile` — the test-runner image.
- `framework/cloud/run_suite.py` — the container's entry point.

---

## Part 1 — IAM: who may do what 🟢 → 🔴

### 1.1 🟢 Three identities, three jobs

| Identity | Used by | May do | Must NOT do |
|---|---|---|---|
| **Task execution role** | ECS itself, before your code starts | Pull the image, write logs | Anything your tests do |
| **Task role** | Your test code inside the container | Write this suite's artifacts: `s3:PutObject` on `bucket/runs/*` | Read other data, change infrastructure |
| **CI role** | GitHub Actions, through OIDC | Push one image, register and run one task family, pass the two roles above, read logs and artifacts | Anything else in the account |

Keeping the execution role and the task role separate is a classic exam point. The exam case on Day 18 uses **one** role for both, and gives it `s3:*`, `logs:*`, `ecs:*`, and `iam:PassRole` on everything.

### 1.2 🟡 Reading a policy statement

The task role from `cloud/cloudformation/test-execution.yaml`:

```yaml
      Policies:
        - PolicyName: write-run-artifacts
          PolicyDocument:
            Version: "2012-10-17"
            Statement:
              - Effect: Allow
                Action:
                  - s3:PutObject
                  - s3:AbortMultipartUpload
                Resource: !Sub "${ArtifactsBucket.Arn}/runs/*"
```

Read it as: **allow** *these two actions* on *objects under `runs/` in this one bucket*. If the test code is compromised, it cannot read, list, or delete anything.

### 1.3 🔴 `iam:PassRole`: the permission that grants permissions

Starting a task means *giving* it roles. Whoever may pass **any** role can start a task with an administrator role and act through it. That is privilege escalation. The CI role may pass exactly two roles, and only to ECS:

```yaml
              - Sid: PassOnlyTheTwoTaskRoles
                Effect: Allow
                Action: iam:PassRole
                Resource:
                  - !GetAtt TaskExecutionRole.Arn
                  - !GetAtt TaskRole.Arn
                Condition:
                  StringEquals:
                    iam:PassedToService: ecs-tasks.amazonaws.com
```

### 1.4 🔴 CI without stored keys: GitHub OIDC

On every run, GitHub issues a short-lived signed token. AWS exchanges it for temporary credentials **only if** the trust policy's conditions match:

```yaml
            Condition:
              StringEquals:
                token.actions.githubusercontent.com:aud: sts.amazonaws.com
                token.actions.githubusercontent.com:sub: !Sub "repo:${GitHubRepository}:environment:${GitHubEnvironment}"
```

| Trust condition | Who can assume the role |
|---|---|
| No `sub` condition | **Every GitHub repository in the world** (critical) |
| `repo:my-org/*` | Every repository and branch of the organisation |
| `repo:my-org/shop-bdd:environment:aws-lab` | Only jobs of this repository that run in the `aws-lab` environment, which a reviewer must approve |

Compared with access keys stored as GitHub secrets, OIDC credentials expire within an hour, there is nothing to rotate, and nothing can leak from a repository setting. *(AWS docs, GitHub docs)*

### 1.5 🟡 Confused deputy

Both ECS roles trust `ecs-tasks.amazonaws.com` with the condition `aws:SourceAccount = <this account>`. Without it, a task from **another** account could, in principle, use the same service principal to assume them. The condition costs one line.

### 1.6 Policy as code: the project's audit

`python -m framework.cloud.audit` reads IAM JSON, task definitions, CloudFormation, and workflows. These are its IAM and OIDC rules:

| Rule | Severity | Catches |
|---|---|---|
| IAM-001 | high | Wildcard actions (`*`, `s3:*`) |
| IAM-002 | critical | `iam:PassRole` on `*` |
| IAM-003 | medium | Write actions on `Resource: "*"`. Actions that AWS only allows on `*`, such as `ecr:GetAuthorizationToken`, are exempt |
| IAM-004 | critical | `AdministratorAccess`, `PowerUserAccess`, or `IAMFullAccess` attached |
| OIDC-001/002/003 | critical/high/medium | Missing `sub`; a wildcard `sub`; missing `aud` |

On the reference design it reports **1 info** finding: the Device Farm template has no budget of its own. On the Day 18 exam case it reports **28** findings, 12 of them high or critical. A tool like this catches the mechanical mistakes. It cannot judge the design; that is the auditor's job.

---

## Part 2 — Networking boundaries 🟡 → 🔴

### 2.1 Where a test task sits

| Question | Our answer | Why |
|---|---|---|
| Inbound traffic? | **None.** The security group has no ingress rules | A test runner serves nothing. The exam case opens SSH to the internet |
| Outbound? | TCP 443 only | ECR, S3, CloudWatch Logs, and the systems under test are all HTTPS |
| How does it reach AWS APIs? | Public subnet + public IP | The cheapest option, with no NAT gateway (see 2.2) |
| Which systems may it test? | Test environments, and agreed public targets | Never production with production credentials (exam case) |

### 2.2 🔴 Three ways out, three cost profiles

| Option | Security | Cost (us-east-1, approximate) | Good for |
|---|---|---|---|
| **Public subnet + public IP**, no inbound rules | The IP is reachable, but the security group drops every inbound packet | No hourly charge for the path | Short test tasks (our choice) |
| **Private subnet + NAT gateway** | No public IP at all | About $0.045 per hour **per gateway, all month**, plus about $0.045 per GB processed | Long-running services with strict rules |
| **Private subnet + VPC endpoints** (S3 gateway; ECR, Logs interface endpoints) | Traffic stays inside AWS | The S3 gateway endpoint is free; each interface endpoint is billed per hour per AZ | Regulated environments; no internet needed |

The exam case pays **$44.05 a month** for one NAT gateway (hours plus bytes) that serves a test suite. The traffic it carries could have gone through a public IP for nothing. A NAT gateway in a single AZ is also a single point of failure.

### 2.3 The data boundary

A test platform also has a **data** boundary: which data a test may touch. The rules:
- test environments and synthetic data;
- per-run correlation ids (Unit 3);
- no production admin accounts;
- cleanup that is part of the test, not a "nightly script when it works" (exam case).

---

## Part 3 — Images: Docker and ECR 🟢 → 🔴

### 3.1 🟢 The image is the environment

`docker/Dockerfile` (excerpt):

```dockerfile
# Pinned by digest: the same bytes on every build (update deliberately, e.g. with Dependabot).
FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b
...
COPY requirements.txt .
RUN --mount=type=secret,id=proxy_ca,required=false \
    if [ -f /run/secrets/proxy_ca ]; then export PIP_CERT=/run/secrets/proxy_ca; fi; \
    pip install -r requirements.txt

# Then the code. .dockerignore keeps out git data, CI files, reports, caches, and virtual environments.
COPY . .
...
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin runner \
    && mkdir -p /app/reports && chown runner /app/reports
USER 10001

ENTRYPOINT ["python", "-m", "framework.cloud.run_suite"]
CMD ["--suite", "offline"]
```

| Choice | Reason |
|---|---|
| Base image pinned **by digest** | A tag such as `3.12-slim` moves; a digest never does. Updates become deliberate, reviewable changes |
| Dependencies copied before the code | Docker caches layers: changing a test does not reinstall packages |
| Proxy CA as a **build secret** | Builds behind a TLS-inspecting proxy work, and the certificate never enters an image layer |
| Non-root, fixed UID 10001 | A compromised test cannot act as root; the task definition sets the same user |
| `ENTRYPOINT` = our runner | Every run produces the same log format, artifacts, and exit-code contract (Part 4.4) |

What came out of the real build: an image of **638 MB**, user `10001`, entry point `python -m framework.cloud.run_suite`. Most of the size is Python packages: Playwright's driver, the AWS SDK, and moto. A senior reviewer notices this. The offline suites do not need Playwright, but the framework imports it at start-up, so the image carries it. Day 16 returns to this coupling.

### 3.2 🟡 ECR settings that matter

| Setting (template) | Effect |
|---|---|
| `ImageTagMutability: IMMUTABLE` | The tag `3f2a…` (a commit) always means the same image. A mutable `latest` is how the exam case ships untested code |
| `ScanOnPush: true` | A vulnerability scan on every push; the cloud pipeline fails if there are CRITICAL findings |
| Lifecycle policy: keep the last 10 | Old images are deleted automatically (storage cost) |
| Encryption AES256 | Encrypted at rest |

---

## Part 4 — ECS and Fargate: running a test task 🟢 → 🔴

### 4.1 🟢 Words first

- **Cluster:** a named place to run tasks. With Fargate there are no servers to manage.
- **Task definition:** the recipe, versioned. Each change creates a new **revision**.
- **Task:** one run of that recipe.
- **Service:** keeps N tasks running *forever*.

> 🔴 **Tests are tasks, never services.** A test run starts, ends, and reports an exit code. A service restarts a task that ends, so it runs the suite in a loop, 24 hours a day. In the exam case that costs **$170.60** a month (118.20 + 52.40).

### 4.2 🟡 The task definition, line by line

```yaml
      Cpu: "1024"
      Memory: "2048"
      RuntimePlatform:
        OperatingSystemFamily: LINUX
        CpuArchitecture: X86_64
      ExecutionRoleArn: !GetAtt TaskExecutionRole.Arn
      TaskRoleArn: !GetAtt TaskRole.Arn
      Volumes:
        - Name: reports
        - Name: tmp
      ContainerDefinitions:
        - Name: tests
          Image: !Sub "${Repository.RepositoryUri}:${ImageTag}"
          Essential: true
          User: "10001"
          ReadonlyRootFilesystem: true
          StopTimeout: 30
          MountPoints:
            - SourceVolume: reports
              ContainerPath: /app/reports
            - SourceVolume: tmp
              ContainerPath: /tmp
```

| Line | Why |
|---|---|
| 1 vCPU / 2 GB | Enough for the offline suite with `-n auto`. Fargate accepts only certain CPU and memory pairs *(AWS docs)* |
| X86_64 | ARM64 (Graviton) costs about 20 % less per vCPU-hour, but the image must be built for `linux/arm64` |
| Two roles | Part 1.1 |
| `ReadonlyRootFilesystem` + two writable volumes | The code cannot change itself; only the reports and `/tmp` are writable |
| `StopTimeout: 30` | After SIGTERM, ECS waits 30 s before SIGKILL. The runner uses that time to save evidence |

### 4.3 🔴 Proving it locally: read-only, non-root, no network

The same constraints with Docker, as run for this lecture:

```bash
docker run --rm --read-only --tmpfs /tmp --tmpfs /app/reports:uid=10001 --network none -v "$PWD/archive:/archive" shop-bdd-tests:local --suite offline --artifacts /archive
```

```
{"time": "2026-11-18T19:24:33.483+00:00", "event": "run.start", "run_id": "local-2", "suite": "offline", ...}
================== 236 passed, 2 skipped, 5 xfailed in 8.90s ===================
{"time": "2026-11-18T19:24:43.933+00:00", "event": "run.end", "run_id": "local-2", "suite": "offline", "pytest_exit_code": 0, "exit_code": 0, "interrupted": false, "duration_s": 10.4, "artifacts": "/archive/local-2"}
```

(With the final Unit 4 code the same command gives **260 passed**: the new unit tests ran too.)

**The first attempt failed, and that was the point of testing it this way.**

| What failed | Why | Fix |
|---|---|---|
| `artifacts.failed … OSError(30, 'Read-only file system')` | The runner wrote the manifest next to the reports folder, inside the read-only image | Write it to a temporary directory |
| One test failed | A new module used `time.sleep` without being on the architecture test's allow-list | Allow-list it, with the reason |

On Fargate, the first problem would have meant **"tests passed, evidence lost"**, which the runner reports as exit code **75**. Run the container under production constraints *before* you go to the cloud.

### 4.4 🔴 The runner's contract (`framework/cloud/run_suite.py`)

| Situation | Exit code | Evidence |
|---|---|---|
| All tests pass, artifacts stored | 0 | Reports + `run.json` + `manifest.json` |
| A test fails | pytest's code (1) | Reports stored anyway: failures are when evidence matters most |
| Tests pass, storing fails | **75** | The error is logged. A run without evidence is not a pass |
| Stopped (SIGTERM) | 2 | Partial reports stored, `interrupted: true` |

The stop behaviour was checked locally (`docker stop` sends SIGTERM, as ECS StopTask does):

```
{"event": "run.signal", "run_id": "local-stop", "signal": "SIGTERM"}
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! KeyboardInterrupt !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
{"event": "run.end", "run_id": "local-stop", "pytest_exit_code": 2, "exit_code": 2, "interrupted": true, "duration_s": 4.2, "artifacts": "/archive/local-stop"}
container exit code: 2
```

The run stopped and stored its evidence 0.4 s after the signal, well within the 30 s stop timeout.

### 4.5 🟡 Cost of one run

At about $0.04048 per vCPU-hour and $0.004445 per GB-hour (Linux/x86, us-east-1), a 1 vCPU / 2 GB task costs about $0.049 per hour. **A 10-minute suite therefore costs under one cent.** The expensive things are what keeps running: services, NAT gateways, logs that never expire, and devices left on.

---

## Part 5 — S3: retained artifacts 🟢 → 🔴

### 5.1 Layout and the manifest

```
s3://<bucket>/runs/<run-id>/run.json
                           /traceability.md, traceability.csv
                           /events/evidence.md ...
                           /manifest.json          ← written LAST: path, size, SHA-256 of every file
```

A reader who finds `manifest.json` knows the upload finished, and can verify every file. From the moto-backed unit test (`tests/unit/test_cloud.py`):

```python
    assert keys == ["runs/run-7/events/evidence.md", "runs/run-7/manifest.json", "runs/run-7/traceability.md"]
    head = client.head_object(Bucket="artifacts", Key="runs/run-7/traceability.md")
    assert head["ServerSideEncryption"] == "AES256"
    assert head["Metadata"] == {"run-id": "run-7"}
```

### 5.2 🔴 The bucket's guard rails

| Setting | Protects against |
|---|---|
| Block Public Access (all four flags) | Reports, which contain URLs, data, and sometimes tokens, becoming public. The exam case makes its bucket public on purpose "so the team can open reports" |
| Encryption by default | Data at rest |
| `BucketOwnerEnforced` | ACL confusion |
| Deny `aws:SecureTransport = false` | Unencrypted transfers |
| Lifecycle: expire `runs/` after 30 days; abort incomplete uploads after 1 day | Paying forever for old evidence |

**How long should evidence be kept?** Long enough to diagnose a failure and to answer an audit; no longer. Choose deliberately, for example 30 days for routine runs and longer for release runs under a different prefix.

---

## Part 6 — CloudWatch: logs and metrics as evidence 🟡 → 🔴

### 6.1 Logs

The `awslogs` driver ships each line the container prints to the log group, under the stream `run/tests/<task-id>`. The runner prints **one JSON object per line**, so CloudWatch Logs Insights can query the runs:

```
fields @timestamp, run_id, suite, exit_code, duration_s
| filter event = "run.end"
| sort @timestamp desc
| limit 20
```

```
fields @timestamp, run_id, error
| filter event = "artifacts.failed"
```

Set a retention period: 14 days in the template. Ingestion is billed per GB, and storage per GB-month.

### 6.2 Metrics

| Need | Metric source | Note |
|---|---|---|
| CPU and memory of a test task | **Container Insights**, enabled on the cluster | Standalone tasks get no per-task metrics without it *(AWS docs)*; billed as custom metrics |
| Queue depth, age of the oldest message | SQS `ApproximateNumberOfMessagesVisible`, `ApproximateAgeOfOldestMessage` | In Unit 3's sandbox this is `/metrics` → `queued` |
| Errors and latency of the system under test | Its own load balancer and application metrics | Correlate them with your load test (Day 16) |

> 🔴 **The local equivalent.** The order-events sandbox has a `/metrics` endpoint (queued, in flight, processed, failed per consumer). `framework/perf/telemetry.py` samples it once a second during a load test. Day 16 lines this telemetry up with the JMeter results, exactly as you would line up CloudWatch metrics with a load test on AWS.

---

## Part 7 — Device Farm: real phones 🟢 → 🔴

### 7.1 🟢 Concepts

| Term | Meaning |
|---|---|
| Project | A container for runs and settings, such as the default job timeout |
| Device pool | Rules that select devices (platform, OS version, form factor, availability) and a maximum count |
| Upload | The app (`ANDROID_APP`), the tests (`APPIUM_PYTHON_TEST_PACKAGE`), and the test spec (`APPIUM_PYTHON_TEST_SPEC`) |
| Run → job → suite → test | One run has one job **per device**; each job runs the suite on that device |
| Custom test environment | A YAML test spec with your own install and test commands. Device Farm injects **no** Appium capabilities *(AWS docs)* |
| Artifacts | Video, device logs, the Appium log, and anything you copy into `$DEVICEFARM_LOG_DIR` |

**Region:** Device Farm runs in **us-west-2**. `cfn-lint` confirmed this while the template was being checked: linted for us-east-1, it reported `Resource type 'AWS::DeviceFarm::Project' does not exist in 'us-east-1'`. The template now declares its region for the linter.

### 7.2 🟡 The test spec (`cloud/devicefarm/testspec.yml`, excerpt)

```yaml
phases:
  install:
    commands:
      - devicefarm-cli use python 3.12
      - devicefarm-cli use appium 2
      - appium driver install uiautomator2
      - cd $DEVICEFARM_TEST_PACKAGE_PATH
      - python -m venv $DEVICEFARM_TEST_PACKAGE_PATH/venv
      - . $DEVICEFARM_TEST_PACKAGE_PATH/venv/bin/activate
      # Offline install from the wheels packed with the tests: no PyPI access needed on the host.
      - pip install --no-index --find-links=./wheelhouse -r requirements.txt
  ...
  test:
    commands:
      - cd $DEVICEFARM_TEST_PACKAGE_PATH && . venv/bin/activate
      - export SHOP_APPIUM_URL=http://127.0.0.1:4723
      - export SHOP_ANDROID_APP=$DEVICEFARM_APP_PATH
      - export SHOP_ANDROID_DEVICE="$DEVICEFARM_DEVICE_NAME"
```

**The Unit 3 framework did not change.** Its capabilities already come from the `SHOP_*` variables, which this spec sets from Device Farm's `DEVICEFARM_*` variables. The `pre_test` phase waits for the Appium server with a deadline: Unit 3's rule, "wait for a condition, never for a fixed time", applies here too.

### 7.3 🔴 The test package: built for the *host*, not for your laptop

`cloud/devicefarm/build_test_package.sh` downloads wheels for **Linux x86_64, Python 3.12**. It then checks that every wheel runs on **glibc 2.26**, the C library of the Amazon Linux 2 host. A wheel built only for a newer glibc would install on a modern laptop and fail on the device host. Built here: **94 MB, 60 wheels**, and the check printed "all wheels run on glibc 2.26". It was then installed with `--no-index` inside a clean `python:3.12-slim` container **with no network**, and pytest collected the 10 mobile tests. So the package is complete on its own.

### 7.4 Cost and limits *(AWS pricing page, November 2026)*

| Item | Value |
|---|---|
| Metered | $0.17 per device minute; a one-time free trial of 1,000 minutes ("limited time"; otherwise 250) |
| Unmetered | $250 per device slot per month |
| Default job timeout | Set it. Our project uses **20 minutes**; the exam case lost $76.50 to runs that hung until a much longer default |
| Parallelism | One job per device in the pool: 2 devices = 2× the minutes |

---

## Part 8 — One run, end to end 🔴

```
1. GitHub job (environment aws-lab, a reviewer approves) ──OIDC──▶ CI role (≤ 1 h credentials)
2. docker build → push ECR :<commit>  → wait for the scan → gate: 0 CRITICAL
3. register task-definition revision (image = :<commit>)
4. ecs run-task (FARGATE, public IP, no inbound rules, RUN_ID=gha-<run>)
5. container: run.start → pytest → run.json → S3 runs/<run-id>/… → manifest.json → run.end
6. aws ecs wait tasks-stopped → exitCode → gate (0 = pass; 1 = tests; 75 = evidence lost)
7. evidence: s3 sync runs/<run-id>/ + CloudWatch log events → CI artifact
8. cleanup (always): stop the task if it still runs; old revisions and images expire by policy
```

This is `.github/workflows/cloud.yml`. You will walk through it in detail on Day 17.

---

## Your output: cloud execution design notes (one page)

| Topic | Your decision and the reason |
|---|---|
| Identities: the roles, what each may do, how CI authenticates | |
| Network: subnet type, inbound and outbound rules, how tasks reach AWS APIs, cost | |
| Image: base pinning, user, filesystem, size, scanning, tags | |
| Task: CPU and memory, architecture, stop behaviour, exit-code contract | |
| Artifacts: layout, completeness check, encryption, access, retention | |
| Telemetry: log format, retention, the metrics you need as evidence | |
| Devices: pool rules, job timeout, package build, cost per run | |
| Cost guard rails: budget, alarms, what must never run 24/7 | |

---

## Self-check (answers below — try first)

1. Why are the task execution role and the task role separate?
2. What can someone do with `iam:PassRole` on `*`?
3. What does the `sub` condition in the GitHub trust policy protect against?
4. Why does the design use public subnets, and why is that not "insecure"?
5. Why must a test run be a task and not a service?
6. Why pin the base image by digest, and why make ECR tags immutable?
7. What did running the container read-only find, and what would that problem have cost on Fargate?
8. Why is `manifest.json` uploaded last?
9. Why does the runner exit with 75 when tests pass but the upload fails?
10. What two things must you configure for a Device Farm run that you would forget on a laptop?

<details>
<summary><b>Answer guide</b></summary>

1. They do different jobs for different principals: ECS pulls the image and writes logs, while the test code writes artifacts. Merging them gives the test code the pull and log rights, and usually more.
2. Start a task (or another service) with any role, including an administrator role, and act through it: privilege escalation.
3. Without it, a workflow in any GitHub repository could obtain a token that the role accepts. With `repo:<org>/<repo>:environment:<env>`, only this repository's jobs in the approved environment can.
4. To avoid a NAT gateway: no hourly charge, and no single-AZ dependency. The security group has no inbound rules, so nothing can connect to the task. The public IP only lets the task reach out.
5. A service keeps N copies running and restarts any that end, so the suite runs in a loop, pays 24/7, and no single run has an exit code.
6. Both make "the same name means the same bytes" true. Upgrades become deliberate changes, and a commit's tests always run the image built from that commit.
7. The manifest was written inside the read-only image. On Fargate the tests would pass but the evidence would be missing. The runner would report exit code 75, after a costly cloud round trip to find a bug that a local `--read-only` run finds in seconds.
8. Its presence means the upload completed. It also lists every file's size and SHA-256, so readers can check that nothing is missing or corrupted.
9. A pass without evidence cannot be verified or audited. The pipeline should treat it as an infrastructure failure, not as green.
10. The region (us-west-2), and a job timeout. Also wheels built for the host's platform and glibc, and Appium capabilities, because Device Farm injects none in a custom environment.
</details>

## Next: Day 14

Cloud CI/CD and performance concepts: secure parameters and secrets, quality gates, cleanup, distributed workload, cost controls, and the performance-testing vocabulary you need for Day 16.

---

## Verification log

| Check | Result |
|---|---|
| `docker build` (`docker/Dockerfile`, digest-pinned base) | Built; 638 MB; user 10001; entry point `framework.cloud.run_suite` |
| Container run: `--read-only`, tmpfs reports and /tmp, `--network none` | First attempt: 1 failed test + evidence lost (read-only manifest); after the fixes: 236, then 260 passed with the final code; exit 0 |
| `docker stop` (SIGTERM) during a run | `interrupted: true`, exit 2, evidence stored 0.4 s after the signal |
| S3 artifact store | moto 5.2.5: keys, SSE `AES256`, run-id metadata, manifest last |
| `cfn-lint` 1.60.1 on both templates | Clean. Device Farm types do not exist in us-east-1; the template declares us-west-2 |
| `actionlint` 1.7.12 + shellcheck 0.11 on the workflows | Clean after fixing 5 shellcheck findings |
| Project audit on `cloud/` and the workflows | 1 info, 0 high |
| Device Farm package | 94 MB, 60 wheels, glibc ≤ 2.26 check passed; offline install + collection of 10 mobile tests in a clean container with no network |
| **Deployed to AWS** | **No.** No account was used: all AWS behaviour is from AWS documentation |
| Prices | From the AWS pricing pages as summarised by third-party sources (November 2026): approximate |
