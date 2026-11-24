"""Evidence: structured logs without secrets, the run record and a tamper-evident manifest.

Pure logic, unit-tested. swaglabs/plugins/evidence.py wires it into pytest.

What a reviewer gets for every run (``reports/``):
    log-<worker>.jsonl  one JSON object per log line, secrets masked
    run.json          who/what/where: persona, browser, versions, commit, outcome counts
    evidence/<test>/  for each failed step: screenshot, page HTML, console errors, dialogs
    artifacts/        Playwright traces and screenshots of failed tests
    manifest.json     SHA-256 of every file above, so a copied report can be verified

``reports/`` is the evidence of exactly ONE run: ``reset_folder`` empties it once, on the controller,
before any worker starts (a global setup), so nothing from an earlier run is fingerprinted as ours.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import shutil
import sys
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MASK = "***"
MANIFEST = "manifest.json"
_SLUG = re.compile(r"[^A-Za-z0-9._-]+")


def reset_folder(folder: Path) -> None:
    """Empty ``folder``, keeping the folder itself (in a container it is a mounted volume).

    Idempotent: safe on a missing, an empty or a half-written folder (a crashed earlier run).
    """
    folder.mkdir(parents=True, exist_ok=True)
    for entry in folder.iterdir():
        if entry.is_dir() and not entry.is_symlink():
            shutil.rmtree(entry)
        else:
            entry.unlink()


def slug(text: str, limit: int = 100) -> str:
    """A file-system-safe name (no spaces, no path separators)."""
    return _SLUG.sub("_", text).strip("_")[:limit] or "unnamed"


def redact(text: str, secrets: Iterable[str]) -> str:
    """Replace every secret value in ``text`` with ``***``. Empty secrets are ignored."""
    for secret in sorted({s for s in secrets if s}, key=len, reverse=True):
        text = text.replace(secret, MASK)
    return text


class JsonLineFormatter(logging.Formatter):
    """One JSON object per record: machine-readable, so logs can be searched and charted."""

    def __init__(self, secrets: Iterable[str] = (), static: Mapping[str, str] | None = None) -> None:
        super().__init__()
        self._secrets = tuple(secrets)
        self._static = dict(static or {})

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": redact(record.getMessage(), self._secrets),
            **self._static,
        }
        if record.exc_info:
            entry["exception"] = redact(self.formatException(record.exc_info), self._secrets)
        return json.dumps(entry, ensure_ascii=False)


class RedactingFilter(logging.Filter):
    """Masks secrets in records before ANY handler (console, file, pytest capture) sees them."""

    def __init__(self, secrets: Iterable[str]) -> None:
        super().__init__()
        self._secrets = tuple(secrets)

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        masked = redact(message, self._secrets)
        if masked != message:
            record.msg, record.args = masked, None
        return True


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 16), b""):
            digest.update(block)
    return digest.hexdigest()


def build_manifest(root: Path) -> dict[str, Any]:
    """SHA-256 and size of every file under ``root`` (except the manifest itself)."""
    files = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != MANIFEST):
        files[path.relative_to(root).as_posix()] = {"sha256": sha256_of(path), "bytes": path.stat().st_size}
    return {"created": datetime.now(tz=UTC).isoformat(timespec="seconds"), "files": files}


def write_manifest(root: Path) -> Path:
    target = root / MANIFEST
    target.write_text(json.dumps(build_manifest(root), indent=2), encoding="utf-8")
    return target


def verify_manifest(root: Path) -> list[str]:
    """Problems found when re-checking a report folder against its manifest (empty = intact)."""
    manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    problems = []
    for name, entry in manifest["files"].items():
        path = root / name
        if not path.is_file():
            problems.append(f"missing: {name}")
        elif sha256_of(path) != entry["sha256"]:
            problems.append(f"changed: {name}")
    listed = set(manifest["files"])
    problems += [
        f"not in manifest: {p.relative_to(root).as_posix()}"
        for p in sorted(root.rglob("*"))
        if p.is_file() and p.name != MANIFEST and p.relative_to(root).as_posix() not in listed
    ]
    return problems


def run_record(
    *,
    settings: Mapping[str, Any],
    outcomes: Mapping[str, int],
    started: datetime,
    finished: datetime,
    environment: Mapping[str, str],
) -> dict[str, Any]:
    """The run's identity card. ``environment`` = selected CI variables (commit, run id ...)."""
    return {
        "started": started.isoformat(timespec="seconds"),
        "finished": finished.isoformat(timespec="seconds"),
        "duration_s": round((finished - started).total_seconds(), 1),
        "settings": dict(settings),
        "outcomes": dict(sorted(outcomes.items())),
        "environment": dict(sorted(environment.items())),
    }


def main(argv: list[str] | None = None) -> int:
    """``python -m swaglabs.evidence reports/``: re-check a report folder against its manifest."""
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        sys.stderr.write("usage: python -m swaglabs.evidence <reports-folder>\n")
        return 2
    problems = verify_manifest(Path(args[0]))
    for problem in problems:
        sys.stderr.write(f"{problem}\n")
    sys.stdout.write("evidence intact\n" if not problems else f"{len(problems)} problem(s)\n")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
