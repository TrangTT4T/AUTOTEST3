"""Collects browser-side clues during a scenario; written out only on failure."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from playwright.sync_api import ConsoleMessage, Page, Response


@dataclass
class BrowserDiagnostics:
    base_url: str
    console_errors: Counter[str] = field(default_factory=Counter)
    failed_requests: Counter[str] = field(default_factory=Counter)

    def attach(self, page: Page) -> None:
        page.on("console", self._on_console)
        page.on("response", self._on_response)

    def _on_console(self, message: ConsoleMessage) -> None:
        if message.type == "error":
            self.console_errors[message.text[:300]] += 1

    def _on_response(self, response: Response) -> None:
        # Only the shop's own requests: third-party analytics noise is not evidence.
        if response.status >= 400 and response.url.startswith(self.base_url):
            self.failed_requests[f"{response.status} {response.request.method} {response.url}"] += 1

    @staticmethod
    def _summary(counter: Counter[str]) -> list[str]:
        return [f"{text} (x{count})" if count > 1 else text for text, count in counter.most_common()]

    def as_dict(self) -> dict[str, list[str]]:
        return {
            "console_errors": self._summary(self.console_errors),
            "failed_requests": self._summary(self.failed_requests),
        }
