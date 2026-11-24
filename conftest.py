"""Root conftest: only plugin registration. Logic lives in framework/plugins."""

pytest_plugins = [
    "framework.plugins.trace_steps",  # before fixtures, which imports it
    "framework.plugins.fixtures",
    "framework.plugins.tags",
    "framework.plugins.evidence",
    "framework.plugins.traceability",
    "framework.plugins.mobile",
    "framework.plugins.events",
    "framework.plugins.selection",
    "tests.steps.cart_steps",
    "tests.steps.catalogue_steps",
    "tests.steps.navigation_steps",
    "tests.steps.order_event_steps",
]
