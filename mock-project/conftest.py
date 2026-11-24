"""Root conftest: plugin registration only. Logic lives in swaglabs/ (pure) and swaglabs/plugins/."""

pytest_plugins = [
    "swaglabs.plugins.registry",
    "swaglabs.plugins.findings",
    "swaglabs.plugins.browser",
    "swaglabs.plugins.reporting",
    "tests.steps.memo",
    "tests.steps.common_steps",
    "tests.steps.session_steps",
    "tests.steps.catalogue_steps",
    "tests.steps.cart_steps",
    "tests.steps.checkout_steps",
    "tests.steps.dynamic_steps",
    "tests.steps.perf_steps",
]
