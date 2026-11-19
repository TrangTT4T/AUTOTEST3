# Unit 4 · Day 15 — AWS Execution Lab: Package and Run Containerized Automation on ECR/ECS/Fargate with Retained Artifacts

| | |
|---|---|
| **Course** | Advanced Automation Test Engineering (ATEST03) — Fast Track |
| **Unit** | Unit 4 — AWS Cloud Execution, Performance, and CI/CD |
| **Learning outcome** | **LO7** — Execute containerized and mobile automation securely using ECS/Fargate and AWS Device Farm with retained artifacts (B3: Apply) |
| **Format** | Assignment/Lab · 150 minutes |
| **Code** | `Unit4/unit4-code/shop-bdd.zip`: `docker/`, `framework/cloud/`, `cloud/cloudformation/test-execution.yaml` |
| **Output of the day** | A built image, a run under Fargate's constraints with its retained artifacts, a stop drill, and a filled **cloud run record** |

> **How this lab works without an AWS account.**
> - **Parts 1–4 run on your machine with Docker.** They use the **same constraints** Fargate applies (read-only root, non-root user, writable volumes only for reports and `/tmp`, SIGTERM on stop), and they were run for real while this lab was written; the outputs are copied from those runs.
> - **Part 5 walks through the AWS deployment as theory.** The commands are complete and the templates pass `cfn-lint`, but they were **not executed**. Their outputs are shown as *the shape you would see*, never as a real result.
> - **The design rule:** if it works locally under the same constraints, the AWS run can only fail for AWS reasons (IAM, network, quotas), and Part 6 lists those.

---

## How to use this lab

| Badge | Level | After this level you can… |
|---|---|---|
| 🟢 | **Foundation** | Build the image, run a suite in it, and find the artifacts |
| 🟡 | **Practitioner** | Run under production constraints, read the JSON logs and the manifest, explain the exit codes |
| 🔴 | **Senior** | Prove stop behaviour, diagnose every Fargate failure class, and defend each security and cost choice |

### Lab plan (150 min)

| Time | Part |
|---|---|
| 0–15 | Part 0 — Setup; what runs where |
| 15–40 | Part 1 — Package: the image |
| 40–65 | Part 2 — Run it as Fargate would |
| 65–80 | Part 3 — Stop drill (SIGTERM) |
| 80–95 | Part 4 — Retained artifacts: local and S3 |
| 95–130 | Part 5 — On AWS: ECR → ECS/Fargate → CloudWatch → S3 (walkthrough) |
| 130–145 | Part 6 — Failure drills: read the symptoms |
| 145–150 | Part 7 — Deliverables |

---

## Part 0 — Setup 🟢

| You need | Check |
|---|---|
| Docker (Docker Desktop on Windows or macOS, or Docker Engine on Linux) | `docker version` shows a server |
| The project | `unzip shop-bdd.zip && cd shop-bdd` |
| Python 3.12 + `requirements-dev.txt` (for the unit tests and tools) | `pytest --store fake tests/unit -q` |

| Step | Runs here | On AWS |
|---|---|---|
| Build the image | ✔ `docker build` | ✔ the same command in CI, then `docker push` to ECR |
| Run the suite | ✔ `docker run` with Fargate-like flags | ECS `run-task` on Fargate |
| Logs | ✔ standard output (JSON lines) | CloudWatch Logs (`awslogs` driver) |
| Artifacts | ✔ a mounted folder | S3 `runs/<run-id>/` |
| Stop | ✔ `docker stop` (SIGTERM, then SIGKILL) | `StopTask` (SIGTERM, then SIGKILL after `stopTimeout`) |

---

## Part 1 — Package: the image 🟢 → 🟡

### 1.1 Build

```bash
docker build -f docker/Dockerfile -t shop-bdd-tests:local --build-arg GIT_SHA=$(git rev-parse HEAD 2>/dev/null || echo local) .
```

Behind a corporate proxy that inspects TLS, pass its CA certificate as a **build secret**: it is used during `pip install` and never stored in the image.

```bash
docker build -f docker/Dockerfile -t shop-bdd-tests:local --secret id=proxy_ca,src=/path/to/proxy-ca.pem --build-arg HTTPS_PROXY=$HTTPS_PROXY .
```

### 1.2 Inspect what you built

```bash
docker image inspect shop-bdd-tests:local --format '{{.Size}} {{.Config.User}} {{json .Config.Entrypoint}}'
```

What this lab's build printed:

```
638117263 10001 ["python","-m","framework.cloud.run_suite"]
```

| Check | Expected | Why |
|---|---|---|
| User | `10001` (not empty, not `0`) | Non-root; must match `User` in the task definition |
| Entry point | The runner | Same logs, artifacts, and exit codes everywhere |
| Size | ~640 MB | See 1.4 |
| No secrets | `docker history` shows no keys or tokens | Layers are readable by anyone who can pull the image |

### 1.3 🟡 What goes into the image: `.dockerignore`

```
.git
.github
.venv
venv
**/__pycache__
**/.pytest_cache
.mypy_cache
.ruff_cache
reports
archive
build
docker
*.md
```

**Everything that is needed to *run* the suites goes in; nothing else.** This lab found a real case. The first image could not run the new unit tests, because `moto` and `PyYAML` were listed only as *development* dependencies. Since the image exists to run tests, everything the tests import belongs in `requirements.txt`, and linters and type checkers stay in `requirements-dev.txt`. The rule: *requirements.txt = what the test runner needs*.

### 1.4 🔴 Review question: why 638 MB?

Most of the size is Python packages: the Playwright driver, the AWS SDK, and moto. The offline suites never open a browser, but `framework/plugins/fixtures.py` imports Playwright at start-up for the web store, so the package must be installed. **Your turn:** propose a change that would let a "no-browser" image skip Playwright, for example importing the web adapter lazily in the `store` fixture. Then estimate the saving with `pip show -f playwright`. Day 18 asks you to weigh such design debt.

---

## Part 2 — Run it as Fargate would 🟡 → 🔴

### 2.1 The command

```bash
mkdir -p archive && chmod 777 archive
```

```bash
docker run --rm --read-only --tmpfs /tmp --tmpfs /app/reports:uid=10001 --network none -v "$PWD/archive:/archive" -e RUN_ID=lab-1 shop-bdd-tests:local --suite offline --artifacts /archive
```

| Flag | Fargate equivalent |
|---|---|
| `--read-only` | `ReadonlyRootFilesystem: true` |
| `--tmpfs /tmp`, `--tmpfs /app/reports:uid=10001` | The two task volumes `tmp` and `reports` |
| `--network none` | Stronger than Fargate: proves the offline suite needs **no** network at all |
| `-v archive:/archive` + `--artifacts /archive` | `ARTIFACTS=s3://…/runs` |
| `-e RUN_ID=lab-1` | `containerOverrides` environment in `run-task` |

### 2.2 What a run prints (real, final code)

```
{"time": "…", "event": "run.start", "run_id": "fresh-1", "suite": "offline", "command": ["-m", "pytest", "-p", "no:cacheprovider", "--store", "fake", "-n", "auto", "--fail-on-uncovered"], "python": "3.12.16", "image": "unknown"}
...
================== 260 passed, 2 skipped, 5 xfailed in 10.29s ==================
{"time": "2026-11-18T19:33:21.179+00:00", "event": "run.end", "run_id": "fresh-1", "suite": "offline", "pytest_exit_code": 0, "exit_code": 0, "interrupted": false, "duration_s": 11.8, "artifacts": "/archive/fresh-1"}
```

Read it like CloudWatch would:
- one JSON object per event;
- the `run_id` on every line;
- the exit code in the last line.

The 5 xfails are the Unit 3 known defects (D-12-01…03) and the web tripwires, all registered.

### 2.3 🔴 What the read-only run found while this lab was written

| Attempt | Symptom | Cause | Fix |
|---|---|---|---|
| 1 | `{"event": "artifacts.failed", "error": "OSError(30, 'Read-only file system')"}` | The manifest was written next to `reports/`, inside the image | Write it in a temporary directory (`/tmp` is writable) |
| 1 | `1 failed` — `fixed waits found … framework/perf/telemetry.py:48` | A new module used `time.sleep` and was not on the architecture test's allow-list | Allow-list it with a reason ("sampling period of a telemetry collector") |
| 2 (from the zip) | `1 error` | `moto` / `PyYAML` not in the image (§1.3) | Moved to `requirements.txt` |
| 3 | `260 passed` | — | — |

> **The lesson:** every one of these would have appeared **on Fargate** as a failed or evidence-less run, after a build, a push, and a deployment. The local read-only run found each in seconds.

---

## Part 3 — Stop drill (SIGTERM) 🔴

ECS stops a task with SIGTERM and, after `stopTimeout` (our task definition: 30 s), SIGKILL. This happens when someone presses *Stop*, when a pipeline is cancelled, or when capacity is reclaimed. A suite that ignores SIGTERM loses everything.

```bash
docker run -d --name stoptest --read-only --tmpfs /tmp --tmpfs /app/reports:uid=10001 --network none -v "$PWD/archive:/archive" -e RUN_ID=lab-stop shop-bdd-tests:local --suite offline --artifacts /archive
```

Wait about 4 seconds, then:

```bash
docker stop -t 30 stoptest && docker logs stoptest | grep event && docker inspect stoptest --format '{{.State.ExitCode}}' && docker rm stoptest
```

Real output:

```
{"event": "run.signal", "run_id": "local-stop", "signal": "SIGTERM"}
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! KeyboardInterrupt !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
{"event": "run.end", "run_id": "local-stop", "pytest_exit_code": 2, "exit_code": 2, "interrupted": true, "duration_s": 4.2, "artifacts": "/archive/local-stop"}
2
```

How it works (`framework/cloud/run_suite.py`):

```python
    def forward(signum: int, _frame: FrameType | None) -> None:
        nonlocal interrupted
        interrupted = True
        if on_signal:
            on_signal(signum)
        child.send_signal(signal.SIGINT)  # pytest stops cleanly on SIGINT and writes its reports
```

The runner is PID 1 in the container and handles signals itself, so it needs no `--init`. It turns SIGTERM into pytest's clean interrupt (SIGINT), waits, writes `run.json` with `"interrupted": true`, and still uploads what exists. Here that took 0.4 s, well within the 30 s budget.

---

## Part 4 — Retained artifacts 🟡 → 🔴

### 4.1 What a run leaves

```
archive/fresh-1/
  run.json                 suite, exit codes, interrupted, duration, image, git sha
  traceability.md / .csv   requirement matrix
  events/evidence.md       Unit 3 async evidence record
  ...
  manifest.json            written LAST: every file with size and SHA-256
```

```bash
python -c "import json; m=json.load(open('archive/fresh-1/manifest.json')); print(len(m['files']), m['files'][0])"
```

From a run of this lab: `52 {'path': 'events/evidence.md', 'size': 6878, 'sha256': '9ee916c6…'}`.

### 4.2 🔴 S3, tested without AWS

`S3ArtifactStore` uploads each file with **server-side encryption** and the run id as metadata. `tests/unit/test_cloud.py` checks it against **moto**, which fakes the S3 API in memory:

```python
@mock_aws
def test_s3_store_encrypts_and_tags_every_object(tmp_path: Path) -> None:
    client = boto3.client("s3", region_name="us-east-1")
    client.create_bucket(Bucket="artifacts")
    location = upload_reports(S3ArtifactStore("artifacts", "/runs/", client), _reports(tmp_path), "run-7")
    assert location == "s3://artifacts/runs/run-7/"
```

Run it yourself (no account, no network):

```bash
pytest tests/unit/test_cloud.py -q
```

> **Your turn (🟡).** Add a test that a failing upload of **one** file still leaves no `manifest.json`. Make the fake store raise on the second `put`. Why does that property matter to someone reading the bucket?

---

## Part 5 — On AWS: the walkthrough 🟡 → 🔴

> ⚠️ **Not executed.** These commands need an AWS account, cost money, and create resources. Read them as a script you understand line by line. Outputs below are **illustrative shapes**, not results.

### 5.1 Create the platform once (CloudFormation)

```bash
aws cloudformation deploy --stack-name shop-bdd-tests --template-file cloud/cloudformation/test-execution.yaml --capabilities CAPABILITY_IAM --parameter-overrides VpcId=vpc-0abc GitHubRepository=my-org/shop-bdd AlertEmail=qa-team@example.com
```

```bash
aws cloudformation describe-stacks --stack-name shop-bdd-tests --query "Stacks[0].Outputs"
```

The outputs are `RepositoryUri`, `ArtifactsBucketName`, `ClusterArn`, `TaskDefinitionArn`, `SecurityGroupId`, `LogGroupName`, and `CiRoleArn`. You need them below. `CAPABILITY_IAM` is required because the stack creates roles: CloudFormation makes you say so explicitly.

### 5.2 Push the image (immutable tag = commit)

```bash
aws ecr get-login-password | docker login --username AWS --password-stdin 111122223333.dkr.ecr.us-east-1.amazonaws.com
```

```bash
docker tag shop-bdd-tests:local 111122223333.dkr.ecr.us-east-1.amazonaws.com/shop-bdd-tests:3f2a9c1
```

```bash
docker push 111122223333.dkr.ecr.us-east-1.amazonaws.com/shop-bdd-tests:3f2a9c1
```

Pushing `:3f2a9c1` a second time **fails**, because tags are immutable. That is a feature: each commit has exactly one image.

### 5.3 Run the suite

```bash
aws ecs run-task --cluster shop-bdd-tests --task-definition shop-bdd-tests --launch-type FARGATE --count 1 --started-by lab-1 --overrides '{"containerOverrides":[{"name":"tests","environment":[{"name":"RUN_ID","value":"lab-1"}]}]}' --network-configuration "awsvpcConfiguration={subnets=[subnet-0aaa,subnet-0bbb],securityGroups=[sg-0ccc],assignPublicIp=ENABLED}"
```

```bash
aws ecs wait tasks-stopped --cluster shop-bdd-tests --tasks <taskArn>
```

```bash
aws ecs describe-tasks --cluster shop-bdd-tests --tasks <taskArn> --query "tasks[0].{exit: containers[0].exitCode, reason: stoppedReason, stopCode: stopCode}"
```

Shape of the answer for a passing run: `{"exit": 0, "reason": "Essential container in task exited", "stopCode": "EssentialContainerExited"}`.

The task goes through PROVISIONING → PENDING → ACTIVATING → RUNNING → DEACTIVATING → STOPPING → DEPROVISIONING → STOPPED *(AWS docs)*. The `wait` command polls until STOPPED, with a built-in limit.

### 5.4 Evidence

```bash
aws s3 ls s3://<ArtifactsBucketName>/runs/lab-1/
```

```bash
aws s3 cp s3://<ArtifactsBucketName>/runs/lab-1/manifest.json -
```

In CloudWatch Logs Insights, on the log group `/ecs/shop-bdd-tests`:

```
fields @timestamp, event, run_id, exit_code, duration_s, artifacts
| filter run_id = "lab-1"
| sort @timestamp asc
```

### 5.5 Cleanup and cost

| Resource | After the lab |
|---|---|
| Stopped tasks | Nothing to do: they cost nothing once STOPPED |
| Image, artifacts, logs | Expire by policy (last 10 images, 30 days, 14 days) |
| The whole platform | `aws cloudformation delete-stack --stack-name shop-bdd-tests`. Empty the bucket first (CloudFormation does not delete a bucket that still has objects); the ECR repository must be empty too |
| Cost of the lab run | 1 vCPU / 2 GB for ~1 minute ≈ $0.001, plus cents of logs and S3 |

---

## Part 6 — Failure drills: read the symptoms 🔴

For each symptom, name the layer and the fix **before** you open the answer.

| # | `stoppedReason` / log | 
|---|---|
| 1 | `CannotPullContainerError: … pull access denied` |
| 2 | `ResourceInitializationError: unable to pull secrets or registry auth: … i/o timeout` |
| 3 | Container exit 75; log `{"event": "artifacts.failed", "error": "ClientError('An error occurred (AccessDenied) when calling the PutObject operation…')"}` |
| 4 | Container exit 137, `reason: OutOfMemoryError: Container killed due to memory usage` |
| 5 | Container exit 1; `run.end` shows `pytest_exit_code: 1` |
| 6 | Container exit 2, `interrupted: true`, `stopCode: UserInitiated` |
| 7 | The task never leaves PROVISIONING; error `You've reached the limit on the number of tasks you can run concurrently` |

<details>
<summary><b>Answers</b></summary>

1. **IAM / image:** the execution role cannot pull, or the image tag does not exist. Check the tag, the repository policy, and `AmazonECSTaskExecutionRolePolicy`.
2. **Network:** the task cannot reach ECR, Secrets Manager, or SSM. In a public subnet, `assignPublicIp` was probably `DISABLED`. In a private subnet, there is no NAT gateway and no VPC endpoints.
3. **Task role:** it lacks `s3:PutObject` on that prefix (or a bucket policy denies it). The tests passed, but the evidence was lost, so the run is **not green**.
4. **Sizing:** the suite needs more memory (with `-n auto`, more CPUs means more workers and more memory), or something leaks. Check Container Insights `MemoryUtilized` before you raise memory.
5. **Product or test:** a real test failure. Open `runs/<id>/` (reports, traceability, evidence).
6. **Someone or something stopped it** (cancel, StopTask). Partial evidence was kept. Rerun it; it is not a product signal.
7. **Account quota:** the Fargate on-demand vCPU limit. Lower the parallelism, or ask for a quota increase. It is an environment block (BLOCKED), not a failure.
</details>

---

## Part 7 — Deliverables

- [ ] Image built; the `inspect` output recorded (size, user, entry point)
- [ ] One run under Fargate constraints: the `run.start` and `run.end` lines, the pytest summary, and the archive listing with the manifest
- [ ] The stop drill: the signal line, `interrupted: true`, exit 2, the evidence kept
- [ ] `pytest tests/unit/test_cloud.py` green, plus your "Your turn" test (§4.2)
- [ ] Your answer to §1.4 (image size) with an estimate
- [ ] The Part 6 drill answered **before** you opened the answers
- [ ] **Cloud run record** (template below), filled from your local run, with the AWS column filled as "planned"

```markdown
# Cloud run record — <run id>

| Field | Local (Fargate-like) | AWS (planned) |
|---|---|---|
| Image (tag / digest) | | ECR :<commit> |
| CPU / memory / architecture | Docker defaults | 1 vCPU / 2 GB / X86_64 |
| Filesystem, user, network | read-only, 10001, none | read-only, 10001, public IP + no inbound |
| Suite, duration, pytest result | | |
| Exit code and meaning | | |
| Artifacts location, file count, manifest present | | s3://<bucket>/runs/<id>/ |
| Logs | stdout JSON lines | /ecs/shop-bdd-tests, stream run/tests/<task> |
| Stop behaviour verified | | |
| Estimated cost of one run | 0 | ≈ $0.001–0.01 |
```

---

## Common errors

| Error | Meaning | Fix |
|---|---|---|
| `Cannot connect to the Docker daemon` | Docker is not running | Start Docker Desktop, or `sudo systemctl start docker` |
| `pip … SSL: CERTIFICATE_VERIFY_FAILED` during the build | A TLS-inspecting proxy | Pass `--secret id=proxy_ca,src=<ca.pem>` (§1.1) |
| `Permission denied: '/archive/…'` | The mounted folder is not writable by UID 10001 | `chmod 777 archive` (lab), or `chown 10001` |
| `OSError(30, 'Read-only file system')` | Something writes outside `/tmp` or `/app/reports` | Point it to a writable volume |
| Exit 75 | Tests passed, artifacts not stored | Read `artifacts.failed` in the log |

---

## Self-check (answers below — try first)

1. Which three Fargate constraints did the local run reproduce, and which did it make stricter?
2. Why did the suite need `moto` and `PyYAML` in `requirements.txt`, not only in `requirements-dev.txt`?
3. What does exit code 75 tell a pipeline?
4. Why does the runner send SIGINT to pytest when it receives SIGTERM?
5. What does an image tag being immutable change for a rerun of an old commit?
6. A task stops with `ResourceInitializationError … i/o timeout`. What is wrong?
7. Name two leftovers that would cost money if Part 5's cleanup were skipped.

<details>
<summary><b>Answer guide</b></summary>

1. A read-only root filesystem, a non-root user, and writable volumes for reports and `/tmp` (plus SIGTERM on stop). It was stricter on the network: `--network none` instead of HTTPS-only egress.
2. The image runs the test suite, and those tests import them. Whatever the test runner imports is a runtime dependency of the runner image.
3. The tests passed, but their evidence was not stored. Treat it as a failure of the infrastructure, not as green.
4. pytest handles SIGINT as a clean interrupt: it stops, writes its reports, and exits with code 2. The runner then still writes `run.json` and uploads the evidence.
5. The commit's tag still points to exactly the image that was tested then, so the rerun uses the same bytes.
6. The task could not reach the registry or the secret store: in a public subnet without a public IP, or in a private subnet with no NAT gateway and no endpoints.
7. Any one of these: the S3 objects and ECR images (small, until they expire), the stack's resources if it is never deleted (Container Insights metrics, the budget), and, in other designs, a NAT gateway or a service left running.
</details>

## Next: Day 16

Topic revision of LO7, then the Device Farm and performance lab: Appium on real devices (walkthrough), JMeter against BlazeDemo and the local sandbox, telemetry correlation, and a real bottleneck.

---

## Verification log

| Check | Result |
|---|---|
| `docker build` from the Unit 4 zip | OK; 638 MB; user 10001 |
| Run: read-only, tmpfs, `--network none`, artifacts to a mounted folder | 260 passed, 2 skipped, 5 xfailed; exit 0; manifest with 52 files (earlier run) |
| Problems found by the read-only run | Manifest on the read-only filesystem, an architecture-test allow-list, missing test dependencies in the image: all fixed and re-run |
| Stop drill | SIGTERM → `interrupted: true`, exit 2, evidence stored after 0.4 s |
| `tests/unit/test_cloud.py` (moto 5.2.5) | Passing (part of the 260) |
| `cfn-lint` on `test-execution.yaml` | Clean |
| Part 5 AWS commands | **Not executed** (no account); outputs are illustrative shapes from AWS documentation |
