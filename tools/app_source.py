"""Shared helpers for reading the My Demo App Android source tree."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path


def commit_of(src_root: Path) -> str:
    git = shutil.which("git")
    if git is None:
        return "unknown commit (git not installed)"
    result = subprocess.run(  # noqa: S603 - fixed arguments, resolved executable, no shell
        [git, "-C", str(src_root), "log", "-1", "--format=%h %cs"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() or "unknown commit"


def strings_of(res_dir: Path) -> dict[str, str]:
    text = (res_dir / "values" / "strings.xml").read_text(encoding="utf-8")
    return dict(re.findall(r'<string name="([^"]+)"[^>]*>(.*?)</string>', text, re.S))
