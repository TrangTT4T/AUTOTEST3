"""Unit tests for framework/cloud: artifact storage (S3 via moto), the entry point, the audit rules."""

import json
import os
import signal
import sys
import threading
from pathlib import Path

import boto3
import pytest
from moto import mock_aws

from framework.cloud import audit, run_suite
from framework.cloud.artifacts import LocalArtifactStore, S3ArtifactStore, store_from_uri, upload_reports
from framework.cloud.run_suite import EXIT_ARTIFACTS_FAILED, build_command, default_run_id, final_exit_code

ROOT = Path(__file__).resolve().parents[2]


def _reports(tmp_path: Path) -> Path:
    root = tmp_path / "reports"
    (root / "events").mkdir(parents=True)
    (root / "traceability.md").write_text("| REQ |\n", encoding="utf-8")
    (root / "events" / "evidence.md").write_text("# evidence\n", encoding="utf-8")
    return root


# --- artifacts ------------------------------------------------------------------------
def test_local_store_copies_files_and_writes_the_manifest_last(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path / "archive")
    location = upload_reports(store, _reports(tmp_path), "run-1")
    manifest = json.loads(Path(location, "manifest.json").read_text(encoding="utf-8"))
    assert [f["path"] for f in manifest["files"]] == ["events/evidence.md", "traceability.md"]
    assert Path(location, "events/evidence.md").read_text(encoding="utf-8") == "# evidence\n"
    assert not list((tmp_path / "reports").glob("*manifest*"))  # nothing left in the reports folder


@mock_aws
def test_s3_store_encrypts_and_tags_every_object(tmp_path: Path) -> None:
    client = boto3.client("s3", region_name="us-east-1")
    client.create_bucket(Bucket="artifacts")
    location = upload_reports(S3ArtifactStore("artifacts", "/runs/", client), _reports(tmp_path), "run-7")
    assert location == "s3://artifacts/runs/run-7/"
    keys = sorted(o["Key"] for o in client.list_objects_v2(Bucket="artifacts")["Contents"])
    assert keys == ["runs/run-7/events/evidence.md", "runs/run-7/manifest.json", "runs/run-7/traceability.md"]
    head = client.head_object(Bucket="artifacts", Key="runs/run-7/traceability.md")
    assert head["ServerSideEncryption"] == "AES256"
    assert head["Metadata"] == {"run-id": "run-7"}
    assert head["ContentType"] == "text/markdown"


def test_store_from_uri(tmp_path: Path) -> None:
    assert isinstance(store_from_uri(str(tmp_path)), LocalArtifactStore)
    assert isinstance(store_from_uri(f"file://{tmp_path}"), LocalArtifactStore)
    s3 = store_from_uri("s3://bucket/runs", s3_client=object)
    assert isinstance(s3, S3ArtifactStore)
    assert s3.location("r") == "s3://bucket/runs/r/"
    with pytest.raises(ValueError, match="unsupported"):
        store_from_uri("gs://bucket")


# --- entry point ---------------------------------------------------------------------------
def test_exit_code_never_hides_a_failure_or_a_lost_evidence() -> None:
    assert final_exit_code(0, artifacts_ok=True) == 0
    assert final_exit_code(1, artifacts_ok=False) == 1  # the test failure wins
    assert final_exit_code(0, artifacts_ok=False) == EXIT_ARTIFACTS_FAILED


def test_suite_commands_and_run_ids() -> None:
    command = build_command("events", ["-k", "ordering"])
    assert command[1:] == [
        "-m",
        "pytest",
        "-p",
        "no:cacheprovider",
        "--store",
        "fake",
        "tests/events",
        "tests/test_order_events.py",
        "-n",
        "auto",
        "-k",
        "ordering",
    ]
    with pytest.raises(ValueError, match="unknown suite"):
        build_command("everything", [])
    assert default_run_id({"RUN_ID": "gha-1"}) == "gha-1"
    assert default_run_id({"GIT_SHA": "abcdef123456"}).endswith("-abcdef1")


# --- audit rules ---------------------------------------------------------------------------
def _rules(findings: list[audit.Finding]) -> set[str]:
    return {f.rule for f in findings}


def test_policy_rules() -> None:
    policy = {
        "Statement": [
            {"Effect": "Allow", "Action": "s3:*", "Resource": "*"},
            {"Effect": "Allow", "Action": "iam:PassRole", "Resource": "*"},
            {"Effect": "Allow", "Action": "ecr:GetAuthorizationToken", "Resource": "*"},  # needs "*": fine
            {"Effect": "Deny", "Action": "*", "Resource": "*"},  # denies are never findings
        ]
    }
    findings = list(audit.check_policy(policy, "p"))
    assert _rules(findings) == {"IAM-001", "IAM-002"}
    assert all("Statement[2]" not in f.where for f in findings)


@pytest.mark.parametrize(
    ("condition", "rules"),
    [
        ({}, {"OIDC-001", "OIDC-003"}),
        (
            {"StringLike": {"token.actions.githubusercontent.com:sub": "repo:my-org/*"}},
            {"OIDC-002", "OIDC-003"},
        ),
        (
            {
                "StringEquals": {
                    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
                    "token.actions.githubusercontent.com:sub": "repo:my-org/shop:environment:aws-lab",
                }
            },
            set(),
        ),
    ],
)
def test_github_trust_rules(condition: dict[str, object], rules: set[str]) -> None:
    trust = {
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "sts:AssumeRoleWithWebIdentity",
                "Condition": condition,
                "Principal": {
                    "Federated": "arn:aws:iam::1:oidc-provider/token.actions.githubusercontent.com"
                },
            }
        ]
    }
    assert _rules(list(audit.check_trust(trust, "t"))) == rules


def test_container_rules() -> None:
    bad = {"name": "c", "image": "repo/app:latest", "environment": [{"name": "DB_PASSWORD", "value": "x"}]}
    good = {
        "name": "c",
        "image": "repo/app@sha256:abc",
        "user": "10001",
        "readonlyRootFilesystem": True,
        "logConfiguration": {"logDriver": "awslogs"},
        "environment": [{"name": "SUITE", "value": "offline"}],
    }
    assert _rules(list(audit.check_containers([bad], "td"))) == {
        "ECS-001",
        "ECS-003",
        "ECS-004",
        "ECS-005",
        "ECS-006",
    }
    assert list(audit.check_containers([good], "td")) == []


def test_the_reference_design_has_nothing_high() -> None:
    findings = audit.audit_paths([ROOT / "cloud"])
    assert [f for f in findings if f.rank >= audit.SEVERITIES.index("high")] == []


def test_the_exam_case_is_caught() -> None:
    """The audit must keep catching the planted mechanical flaws (the rest is for the human auditor)."""
    found = _rules(audit.audit_paths([ROOT / "exam/audit-case"]))
    expected = {
        "GHA-001",
        "GHA-002",
        "GHA-003",
        "GHA-005",
        "OIDC-001",
        "IAM-001",
        "IAM-002",
        "IAM-004",
        "S3-001",
        "S3-002",
        "S3-004",
        "NET-001",
        "NET-002",
        "LOG-001",
        "ECS-001",
        "ECS-004",
        "ECS-005",
    }
    assert expected <= found, sorted(expected - found)


def test_audit_cli_exit_code(tmp_path: Path) -> None:
    out = tmp_path / "audit.md"
    assert audit.main([str(ROOT / "exam/audit-case"), "--fail-on", "critical", "--out", str(out)]) == 1
    assert audit.main([str(ROOT / "cloud"), "--fail-on", "high", "--out", str(out)]) == 0


# --- the entry point, end to end (with a stand-in for pytest) --------------------------------
def _fake_suite(monkeypatch: pytest.MonkeyPatch, code: str) -> None:
    """Replace the pytest command with a tiny Python program, so main() runs in milliseconds."""
    monkeypatch.setattr(run_suite, "build_command", lambda _suite, _extra: [sys.executable, "-c", code])


def test_main_stores_evidence_and_passes_the_exit_code_through(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _fake_suite(monkeypatch, "import sys; sys.exit(1)")  # "tests failed"
    reports, archive = tmp_path / "reports", tmp_path / "archive"
    code = run_suite.main(
        ["--suite", "unit", "--artifacts", str(archive), "--run-id", "r1", "--reports", str(reports)]
    )
    assert code == 1
    summary = json.loads((archive / "r1" / "run.json").read_text(encoding="utf-8"))
    assert (summary["pytest_exit_code"], summary["interrupted"]) == (1, False)
    assert (archive / "r1" / "manifest.json").exists()
    events = [json.loads(line)["event"] for line in capsys.readouterr().out.splitlines()]
    assert events == ["run.start", "run.end"]


def test_main_turns_a_pass_without_evidence_into_75(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_suite(monkeypatch, "pass")  # "tests passed"
    code = run_suite.main(
        ["--artifacts", "gs://nowhere", "--run-id", "r2", "--reports", str(tmp_path / "rep")]
    )
    assert code == EXIT_ARTIFACTS_FAILED


def test_sigterm_is_forwarded_and_reported() -> None:
    """What ECS StopTask does: SIGTERM to the runner, which interrupts the suite cleanly."""
    seen: list[int] = []
    timer = threading.Timer(0.5, os.kill, args=(os.getpid(), signal.SIGTERM))
    timer.start()
    try:
        code, interrupted = run_suite.run([sys.executable, "-c", "import time; time.sleep(30)"], seen.append)
    finally:
        timer.cancel()
    assert interrupted
    assert seen == [signal.SIGTERM]
    assert code != 0  # the child was interrupted, not finished
    assert signal.getsignal(signal.SIGTERM) is not None  # the previous handler is restored
