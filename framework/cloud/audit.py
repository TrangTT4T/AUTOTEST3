"""Static audit of cloud test-execution configuration: policy as code (Unit 4, Days 13, 17 and 18).

    python -m framework.cloud.audit cloud .github/workflows --fail-on high

Reads IAM policy JSON, ECS task definitions, CloudFormation templates, and GitHub Actions
workflows. Every rule names its category (security, reliability, cost, ...) so findings map
directly to the Day 18 audit criteria. It catches the common, mechanical mistakes; a human
review still has to judge design, data flows, and anything the rules do not know.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

SEVERITIES = ("info", "low", "medium", "high", "critical")
SECRET_NAME = re.compile(r"(PASSWORD|PASSWD|SECRET|TOKEN|API_?KEY|ACCESS_?KEY|PRIVATE_?KEY|CREDENTIAL)", re.I)
# Actions that AWS only allows on Resource "*" (no resource-level permissions).
STAR_ONLY_ACTIONS = {
    "ecr:getauthorizationtoken",
    "ecs:registertaskdefinition",
    "ecs:describetaskdefinition",
    "ecs:deregistertaskdefinition",
    "cloudwatch:getmetricdata",
    "cloudwatch:listmetrics",
    "devicefarm:listdevices",
    "devicefarm:listdevicepools",
}
READ_PREFIXES = ("get", "list", "describe", "batchget", "filter")


@dataclass(frozen=True)
class Finding:
    severity: str
    category: str
    rule: str
    where: str
    message: str

    @property
    def rank(self) -> int:
        return SEVERITIES.index(self.severity)


# --------------------------------------------------------------------------------- loading
class _CfnLoader(yaml.SafeLoader):
    """Keeps CloudFormation short-form intrinsics (!Ref, !Sub, ...) as {"Fn::X": value}."""


def _intrinsic(loader: yaml.SafeLoader, suffix: str, node: yaml.Node) -> Any:
    name = "Ref" if suffix == "Ref" else f"Fn::{suffix}"
    if isinstance(node, yaml.ScalarNode):
        value: Any = loader.construct_scalar(node)
    elif isinstance(node, yaml.SequenceNode):
        value = loader.construct_sequence(node, deep=True)
    else:
        value = loader.construct_mapping(node, deep=True)  # type: ignore[arg-type]
    return {name: value}


_CfnLoader.add_multi_constructor("!", _intrinsic)


def load(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        return json.loads(text)
    return yaml.load(text, Loader=_CfnLoader)  # noqa: S506 - _CfnLoader subclasses SafeLoader: no arbitrary objects


# ------------------------------------------------------------------------------ IAM rules
def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else [value]


def _text(value: Any) -> str:
    """A resource or condition value as text, intrinsics included (for pattern checks)."""
    return json.dumps(value) if not isinstance(value, str) else value


def check_policy(document: dict[str, Any], where: str) -> Iterator[Finding]:
    for i, statement in enumerate(_as_list(document.get("Statement", []))):
        if not isinstance(statement, dict) or statement.get("Effect") != "Allow":
            continue
        at = f"{where} Statement[{i}]"
        actions = [str(a).lower() for a in _as_list(statement.get("Action", []))]
        resources = [_text(r) for r in _as_list(statement.get("Resource", []))]
        wildcard = "*" in actions or any(a.endswith(":*") for a in actions)
        if wildcard:
            yield Finding(
                "high", "security", "IAM-001", at, f"wildcard action {actions}: grant named actions only"
            )
        if "iam:passrole" in actions and "*" in resources:
            yield Finding(
                "critical", "security", "IAM-002", at, "iam:PassRole on any role allows privilege escalation"
            )
        writes = [
            a
            for a in actions
            if a not in STAR_ONLY_ACTIONS
            and a != "iam:passrole"
            and not a.split(":")[-1].startswith(READ_PREFIXES)
        ]
        if "*" in resources and writes and not wildcard:  # a wildcard action is already IAM-001
            yield Finding(
                "medium", "security", "IAM-003", at, f"write actions on Resource '*': {sorted(writes)}"
            )


def check_trust(document: dict[str, Any], where: str) -> Iterator[Finding]:
    """GitHub OIDC trust must pin the repository (and ideally the environment) in the 'sub' claim."""
    for i, statement in enumerate(_as_list(document.get("Statement", []))):
        if not isinstance(statement, dict):
            continue
        federated = (
            _text(statement.get("Principal", {}).get("Federated", ""))
            if isinstance(statement.get("Principal"), dict)
            else ""
        )
        if "token.actions.githubusercontent.com" not in federated:
            continue
        conditions = _text(statement.get("Condition", {}))
        at = f"{where} Statement[{i}]"
        if "token.actions.githubusercontent.com:sub" not in conditions:
            yield Finding(
                "critical",
                "security",
                "OIDC-001",
                at,
                "no 'sub' condition: ANY GitHub repository can assume this role",
            )
        elif re.search(r"repo:\*|repo:[^\"/]+/\*", conditions):
            yield Finding(
                "high", "security", "OIDC-002", at, "'sub' allows every repository or branch of an owner"
            )
        if "token.actions.githubusercontent.com:aud" not in conditions:
            yield Finding(
                "medium", "security", "OIDC-003", at, "no 'aud' condition (expected sts.amazonaws.com)"
            )


# ----------------------------------------------------------------------- task definitions
def check_containers(containers: Iterable[dict[str, Any]], where: str) -> Iterator[Finding]:
    for c in containers:
        name = c.get("Name") or c.get("name") or "?"
        at = f"{where} container {name}"
        env = c.get("Environment") or c.get("environment") or []
        for item in env:
            key = str(item.get("Name") or item.get("name") or "")
            if SECRET_NAME.search(key):
                yield Finding(
                    "high",
                    "security",
                    "ECS-001",
                    at,
                    f"'{key}' passed in plain text: use 'secrets' (SSM Parameter Store / Secrets Manager)",
                )
        if c.get("Privileged") or c.get("privileged"):
            yield Finding("high", "security", "ECS-002", at, "privileged container")
        if not (c.get("ReadonlyRootFilesystem") or c.get("readonlyRootFilesystem")):
            yield Finding("low", "security", "ECS-003", at, "root filesystem is writable")
        if not (c.get("LogConfiguration") or c.get("logConfiguration")):
            yield Finding(
                "medium", "reliability", "ECS-004", at, "no logConfiguration: no logs after the task stops"
            )
        image = _text(c.get("Image") or c.get("image") or "")
        if re.search(r":latest\b", image) or (
            ":" not in image.rsplit("/", 1)[-1]
            and "@sha256" not in image
            and "Fn::" not in image
            and "Ref" not in image
        ):
            yield Finding(
                "medium", "reliability", "ECS-005", at, f"image '{image}' is not pinned to a tag or digest"
            )
        user = str(c.get("User") or c.get("user") or "")
        if user in ("", "0", "root"):
            yield Finding("low", "security", "ECS-006", at, "runs as root (set 'user')")


# --------------------------------------------------------------------------- CloudFormation
def _bucket(props: dict[str, Any], at: str) -> Iterator[Finding]:
    block = props.get("PublicAccessBlockConfiguration", {})
    flags = ("BlockPublicAcls", "BlockPublicPolicy", "IgnorePublicAcls", "RestrictPublicBuckets")
    if not all(block.get(f) is True for f in flags):
        yield Finding("high", "security", "S3-001", at, "public access not fully blocked")
    if "LifecycleConfiguration" not in props:
        yield Finding(
            "medium", "cost", "S3-002", at, "no lifecycle rule: artifacts are kept (and paid) forever"
        )
    if "BucketEncryption" not in props:
        yield Finding(
            "low", "security", "S3-003", at, "no explicit encryption (S3 applies SSE-S3 by default)"
        )


def _bucket_policy(props: dict[str, Any], at: str) -> Iterator[Finding]:
    policy = props.get("PolicyDocument", {})
    for st in _as_list(policy.get("Statement", [])):
        if st.get("Effect") == "Allow" and st.get("Principal") in ("*", {"AWS": "*"}):
            yield Finding("critical", "security", "S3-004", at, "bucket policy allows anyone")
    if "aws:SecureTransport" not in _text(policy):
        yield Finding("low", "security", "S3-005", at, "no deny for non-TLS requests (aws:SecureTransport)")


def _log_group(props: dict[str, Any], at: str) -> Iterator[Finding]:
    if "RetentionInDays" not in props:
        yield Finding("medium", "cost", "LOG-001", at, "log group never expires")


def _nat(_props: dict[str, Any], at: str) -> Iterator[Finding]:  # every NAT gateway is a finding
    yield Finding("medium", "cost", "NET-001", at, "NAT gateway: hourly + per-GB charges even when idle")


def _security_group(props: dict[str, Any], at: str) -> Iterator[Finding]:
    for rule in props.get("SecurityGroupIngress", []) or []:
        if rule.get("CidrIp") == "0.0.0.0/0" or rule.get("CidrIpv6") == "::/0":
            yield Finding(
                "high", "security", "NET-002", at, "ingress open to the internet; test tasks need none"
            )


def _repository(props: dict[str, Any], at: str) -> Iterator[Finding]:
    if props.get("ImageTagMutability") != "IMMUTABLE":
        yield Finding(
            "low", "reliability", "ECR-001", at, "mutable tags: a tag can point to different images"
        )
    if not (props.get("ImageScanningConfiguration") or {}).get("ScanOnPush"):
        yield Finding("low", "security", "ECR-002", at, "images are not scanned on push")
    if "LifecyclePolicy" not in props:
        yield Finding("low", "cost", "ECR-003", at, "no lifecycle policy: old images accumulate")


def _task_definition(props: dict[str, Any], at: str) -> Iterator[Finding]:
    yield from check_containers(props.get("ContainerDefinitions", []), at)


def _role(props: dict[str, Any], at: str) -> Iterator[Finding]:
    yield from check_trust(props.get("AssumeRolePolicyDocument", {}), f"{at} trust")
    for arn in props.get("ManagedPolicyArns", []) or []:
        if re.search(r"policy/(AdministratorAccess|PowerUserAccess|IAMFullAccess)$", _text(arn)):
            yield Finding("critical", "security", "IAM-004", at, f"broad managed policy {_text(arn)}")
    for policy in props.get("Policies", []) or []:
        yield from check_policy(policy.get("PolicyDocument", {}), f"{at} {policy.get('PolicyName', '')}")


def _policy(props: dict[str, Any], at: str) -> Iterator[Finding]:
    yield from check_policy(props.get("PolicyDocument", {}), at)


RESOURCE_CHECKS = {
    "AWS::S3::Bucket": _bucket,
    "AWS::S3::BucketPolicy": _bucket_policy,
    "AWS::Logs::LogGroup": _log_group,
    "AWS::EC2::NatGateway": _nat,
    "AWS::EC2::SecurityGroup": _security_group,
    "AWS::ECR::Repository": _repository,
    "AWS::ECS::TaskDefinition": _task_definition,
    "AWS::IAM::Role": _role,
    "AWS::IAM::Policy": _policy,
    "AWS::IAM::ManagedPolicy": _policy,
}


def check_template(template: dict[str, Any], where: str) -> Iterator[Finding]:
    resources: dict[str, Any] = template.get("Resources", {}) or {}
    for logical_id, resource in resources.items():
        check = RESOURCE_CHECKS.get(resource.get("Type", ""))
        if check:
            yield from check(resource.get("Properties", {}) or {}, f"{where} {logical_id}")
    if resources and not any(r.get("Type") == "AWS::Budgets::Budget" for r in resources.values()):
        yield Finding(
            "info", "cost", "COST-001", where, "no AWS Budget in this template (fine if the account has one)"
        )


# --------------------------------------------------------------------------- GitHub Actions
def check_workflow(workflow: dict[Any, Any], where: str) -> Iterator[Finding]:
    triggers = workflow.get("on", workflow.get(True, {}))  # YAML 1.1 reads the key `on` as True
    text = json.dumps(workflow)
    if "pull_request_target" in _text(triggers) and "github.event.pull_request.head" in text:
        yield Finding(
            "critical",
            "security",
            "GHA-001",
            where,
            "pull_request_target + checkout of the PR head runs untrusted code with secrets",
        )
    if re.search(r"secrets\.AWS_(SECRET_)?ACCESS_KEY", text) or "aws-secret-access-key" in text:
        yield Finding("high", "security", "GHA-002", where, "long-lived AWS keys: use OIDC (role-to-assume)")
    if "permissions" not in workflow:
        yield Finding(
            "medium", "security", "GHA-003", where, "no top-level 'permissions': the token gets defaults"
        )
    for job_id, job in (workflow.get("jobs") or {}).items():
        if isinstance(job, dict) and "timeout-minutes" not in job:
            yield Finding(
                "low", "cost", "GHA-004", f"{where} job {job_id}", "no timeout-minutes (default 360)"
            )
        for step in (job.get("steps") or []) if isinstance(job, dict) else []:
            run = str(step.get("run", ""))
            if re.search(r"-Jusers=(\d{3,})|threads\s*=\s*\d{3,}", run):
                yield Finding(
                    "high",
                    "safety",
                    "GHA-005",
                    f"{where} job {job_id}",
                    "hundreds of virtual users: is the target yours, and was the test agreed?",
                )


# ------------------------------------------------------------------------------ dispatch
def _kind(data: dict[str, Any]) -> str:
    if "AWSTemplateFormatVersion" in data or "Resources" in data:
        return "template"
    if "jobs" in data:
        return "workflow"
    if "containerDefinitions" in data:
        return "task"
    if "Statement" in data:
        actions = _text([s.get("Action") for s in _as_list(data["Statement"]) if isinstance(s, dict)])
        return "trust" if "sts:AssumeRoleWithWebIdentity" in actions else "policy"
    return "unknown"


def audit_file(path: Path) -> list[Finding]:
    try:
        data = load(path)
    except (yaml.YAMLError, json.JSONDecodeError) as error:
        return [Finding("high", "reliability", "PARSE", str(path), f"cannot parse: {error}")]
    if not isinstance(data, dict):
        return []
    where = path.as_posix()
    checks = {
        "template": lambda: check_template(data, where),
        "workflow": lambda: check_workflow(data, where),
        "task": lambda: check_containers(data["containerDefinitions"], where),
        "trust": lambda: check_trust(data, where),
        "policy": lambda: check_policy(data, where),
    }
    kind = _kind(data)
    return list(checks[kind]()) if kind in checks else []


def audit_paths(paths: Sequence[Path]) -> list[Finding]:
    files = sorted(
        f
        for p in paths
        for f in ([p] if p.is_file() else p.rglob("*"))
        if f.is_file() and f.suffix in {".json", ".yaml", ".yml"}
    )
    findings = [finding for f in files for finding in audit_file(f)]
    return sorted(findings, key=lambda f: (-f.rank, f.where, f.rule))


def to_markdown(findings: Sequence[Finding]) -> str:
    lines = ["# Cloud configuration audit", "", f"{len(findings)} finding(s)", ""]
    lines += ["| Severity | Category | Rule | Where | Finding |", "|---|---|---|---|---|"]
    lines += [f"| {f.severity} | {f.category} | {f.rule} | {f.where} | {f.message} |" for f in findings]
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m framework.cloud.audit", description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--fail-on", choices=SEVERITIES, default="high")
    parser.add_argument("--out", type=Path, default=Path("reports/audit.md"))
    args = parser.parse_args(argv)
    findings = audit_paths(args.paths)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(to_markdown(findings), encoding="utf-8")
    for f in findings:
        print(f"{f.severity.upper():<8} {f.category:<11} {f.rule:<8} {f.where}: {f.message}")
    threshold = SEVERITIES.index(args.fail_on)
    blocking = [f for f in findings if f.rank >= threshold]
    print(f"audit: {len(findings)} finding(s), {len(blocking)} at or above '{args.fail_on}' -> {args.out}")
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
