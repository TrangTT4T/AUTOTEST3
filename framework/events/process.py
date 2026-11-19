"""Start and stop the sandbox as a separate process (one per pytest-xdist worker)."""

from __future__ import annotations

import queue
import subprocess
import sys
import threading
from pathlib import Path
from typing import IO

from framework.errors import EnvironmentBlockedError

READY = "SANDBOX READY "


class SandboxProcess:
    def __init__(self, root: Path, build: str, log_path: Path) -> None:
        self.root = root
        self.build = build
        self.log_path = log_path
        self._process: subprocess.Popen[str] | None = None

    def start(self, timeout: float = 20.0) -> str:
        """Start ``python -m sandbox`` on a free port; return its base URL."""
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        log = self.log_path.open("w", encoding="utf-8")
        command = [
            sys.executable,
            "-m",
            "sandbox",
            "--port",
            "0",
            "--build",
            self.build,
            "--log",
            str(self.log_path),
        ]
        self._process = subprocess.Popen(  # noqa: S603 - a fixed command, no shell
            command, cwd=self.root, stdout=subprocess.PIPE, stderr=log, text=True
        )
        log.close()  # the child keeps its own handle
        if self._process.stdout is None:  # Popen with stdout=PIPE always sets it; this narrows the type
            raise RuntimeError("the sandbox process has no stdout pipe")
        lines: queue.Queue[str] = queue.Queue()
        threading.Thread(target=_forward, args=(self._process.stdout, lines), daemon=True).start()
        try:
            line = lines.get(timeout=timeout)
        except queue.Empty:
            line = ""
        if not line.startswith(READY):
            self.stop()
            tail = self.log_path.read_text(encoding="utf-8", errors="replace")[-800:]
            raise EnvironmentBlockedError(
                f"the events sandbox did not start within {timeout}s: {line!r} {tail}"
            )
        return line.removeprefix(READY).strip()

    def stop(self) -> None:
        if self._process is None:
            return
        if self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=5)
        if self._process.stdout is not None:
            self._process.stdout.close()


def _forward(stream: IO[str], lines: queue.Queue[str]) -> None:
    for line in stream:
        lines.put(line)
