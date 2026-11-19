"""Where a run's reports go: a local folder, or S3 (Unit 4, Day 15: retained artifacts).

Layout: <prefix>/<run id>/<path inside reports/>, plus ``manifest.json`` written LAST,
so a reader knows the upload finished and can check every file's size and SHA-256.
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
import shutil
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlparse


class ArtifactStore(Protocol):
    def location(self, run_id: str) -> str: ...

    def put(self, path: Path, key: str) -> None: ...


@dataclass(frozen=True)
class ManifestEntry:
    path: str
    size: int
    sha256: str


def manifest_of(root: Path) -> list[ManifestEntry]:
    entries = []
    for file in sorted(p for p in root.rglob("*") if p.is_file()):
        digest = hashlib.sha256(file.read_bytes()).hexdigest()
        entries.append(ManifestEntry(file.relative_to(root).as_posix(), file.stat().st_size, digest))
    return entries


def upload_reports(store: ArtifactStore, root: Path, run_id: str) -> str:
    """Upload every file under ``root``, then the manifest. Returns the run's location."""
    entries = manifest_of(root)
    for entry in entries:
        store.put(root / entry.path, f"{run_id}/{entry.path}")
    # The manifest goes through a temporary file: in a read-only container only /tmp and the
    # reports volume are writable, and the manifest must not list itself.
    with tempfile.TemporaryDirectory() as scratch:
        manifest = Path(scratch, "manifest.json")
        manifest.write_text(
            json.dumps({"run_id": run_id, "files": [e.__dict__ for e in entries]}, indent=2), "utf-8"
        )
        store.put(manifest, f"{run_id}/manifest.json")
    return store.location(run_id)


class LocalArtifactStore:
    def __init__(self, base: Path) -> None:
        self.base = base

    def location(self, run_id: str) -> str:
        return str(self.base / run_id)

    def put(self, path: Path, key: str) -> None:
        target = self.base / key
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)


class S3ArtifactStore:
    """Encrypted at rest (SSE-S3, or SSE-KMS with ``kms_key_id``); tagged with the run id."""

    def __init__(self, bucket: str, prefix: str, client: Any, kms_key_id: str | None = None) -> None:
        self.bucket = bucket
        self.prefix = prefix.strip("/")
        self.client = client
        self.kms_key_id = kms_key_id

    def _key(self, key: str) -> str:
        return f"{self.prefix}/{key}" if self.prefix else key

    def location(self, run_id: str) -> str:
        return f"s3://{self.bucket}/{self._key(run_id)}/"

    def put(self, path: Path, key: str) -> None:
        extra: dict[str, Any] = {
            "ContentType": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
            "Metadata": {"run-id": key.split("/", 1)[0]},
        }
        if self.kms_key_id:
            extra |= {"ServerSideEncryption": "aws:kms", "SSEKMSKeyId": self.kms_key_id}
        else:
            extra["ServerSideEncryption"] = "AES256"
        self.client.upload_file(str(path), self.bucket, self._key(key), ExtraArgs=extra)


def _boto3_s3() -> Any:
    import boto3  # noqa: PLC0415 - lazy on purpose: only a run that uploads to S3 needs boto3

    return boto3.client("s3")


def store_from_uri(uri: str, s3_client: Callable[[], Any] = _boto3_s3) -> ArtifactStore:
    """``s3://bucket/prefix``, ``file:///abs/path``, or a plain path."""
    parsed = urlparse(uri)
    if parsed.scheme == "s3":
        if not parsed.netloc:
            raise ValueError(f"no bucket in {uri!r}")
        return S3ArtifactStore(parsed.netloc, parsed.path, s3_client())
    if parsed.scheme in ("", "file"):
        return LocalArtifactStore(Path(parsed.path if parsed.scheme else uri))
    raise ValueError(f"unsupported artifact location {uri!r}: use s3://, file://, or a path")
