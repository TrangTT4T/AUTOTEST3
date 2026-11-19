"""Live status stream over WebSocket: subscribe BEFORE acting, then wait for pushed frames (Day 10, 3.4).

A background thread receives frames into a list; tests wait on a condition variable,
so there is no polling interval at all. Every frame keeps the moment this test received
it, which is how convergence time is measured.
"""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable
from contextlib import ExitStack

from websockets.exceptions import ConnectionClosed, InvalidHandshake
from websockets.sync.client import ClientConnection, connect

from framework.errors import EnvironmentBlockedError
from framework.events.model import Frame


class StatusStream:
    def __init__(self, url_for: Callable[[int], str], open_timeout: float = 5.0) -> None:
        """``url_for(since)`` builds the subscription URL for a (re)connection."""
        self._url_for = url_for
        self._open_timeout = open_timeout
        self._frames: list[Frame] = []
        self._changed = threading.Condition()
        self._ws: ClientConnection | None = None
        self._connection = ExitStack()  # websockets 17: connections are context managers
        self._reader: threading.Thread | None = None
        self.connected = False
        self.connections = 0
        self.close_reasons: list[str] = []

    # --- connection -------------------------------------------------------------------
    def connect(self) -> None:
        since = self._frames[-1].frame if self._frames else 0
        try:
            ws = self._connection.enter_context(
                connect(self._url_for(since), open_timeout=self._open_timeout, proxy=None, close_timeout=1)
            )
        except (OSError, InvalidHandshake, TimeoutError) as error:
            raise EnvironmentBlockedError(f"cannot subscribe to the status stream: {error}") from error
        with self._changed:
            self._ws, self.connected = ws, True
            self.connections += 1
        self._reader = threading.Thread(target=self._receive, args=(ws,), name="status-stream", daemon=True)
        self._reader.start()

    def reconnect(self) -> None:
        """Resume from the last frame received: the server should replay what was missed."""
        self.close()
        self.connect()

    def close(self) -> None:
        self._connection.close()  # closes the current connection, if any
        if self._reader is not None:
            self._reader.join(timeout=2)

    def _receive(self, ws: ClientConnection) -> None:
        reason = "closed by the client"
        try:
            for message in ws:
                frame = Frame.from_json(json.loads(message), received_at=time.monotonic())
                with self._changed:
                    self._frames.append(frame)
                    self._changed.notify_all()
        except ConnectionClosed as closed:
            reason = f"closed by the server: {closed.rcvd}"
        finally:
            if ws.close_code not in (None, 1000) and reason == "closed by the client":
                reason = f"closed: code {ws.close_code} {ws.close_reason}"
            with self._changed:
                if self._ws is ws:
                    self.connected = False
                self.close_reasons.append(reason)
                self._changed.notify_all()

    # --- reading ------------------------------------------------------------------------
    @property
    def frames(self) -> list[Frame]:
        with self._changed:
            return list(self._frames)

    def statuses(self) -> list[str]:
        return [f.status for f in self.frames]

    def wait_for(self, done: Callable[[list[Frame]], bool], timeout: float, what: str) -> list[Frame]:
        with self._changed:
            if not self._changed.wait_for(lambda: done(self._frames), timeout=timeout):
                seen = [f.status for f in self._frames]
                state = "connected" if self.connected else f"disconnected ({self.close_reasons[-1:]})"
                raise TimeoutError(
                    f"{what} not seen within {timeout}s; frames so far: {seen}; stream {state}"
                )
            return list(self._frames)

    def wait_for_status(self, status: str, timeout: float) -> Frame:
        frames = self.wait_for(lambda fs: any(f.status == status for f in fs), timeout, f"status {status!r}")
        return next(f for f in frames if f.status == status)

    def wait_disconnected(self, timeout: float) -> None:
        with self._changed:
            if not self._changed.wait_for(lambda: not self.connected, timeout=timeout):
                raise TimeoutError(f"the stream was still connected after {timeout}s")
