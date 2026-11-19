from framework.adapters.web.diagnostics import BrowserDiagnostics


def test_repeated_messages_are_counted_not_repeated() -> None:
    diagnostics = BrowserDiagnostics("https://shop.example")
    diagnostics.console_errors.update(["boom", "boom", "boom", "other"])
    assert diagnostics.as_dict()["console_errors"] == ["boom (x3)", "other"]
