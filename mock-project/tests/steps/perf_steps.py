"""Steps that time interactions and check them against perf-budgets.toml."""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_bdd import parsers, then, when

from swaglabs.app import SwagLabs
from swaglabs.perf import Measurement, load_budgets

CUSTOMER = ("Ada", "Lovelace", "10115")


@pytest.fixture(scope="session")
def budgets(pytestconfig: pytest.Config) -> dict[str, float]:
    return load_budgets(Path(pytestconfig.rootpath, str(pytestconfig.getini("perf_budgets"))))


def _verdict(m: Measurement, budget: float) -> str:
    return (
        f"{m.action}: {m.duration_ms:.0f} ms (budget {budget:.0f} ms) - network busy "
        f"{m.network_busy_ms:.0f} ms, client {m.client_ms:.0f} ms, {m.requests} requests"
        f" -> {m.bottleneck}-bound"
    )


@then(parsers.parse('the "{action}" interaction stayed within its budget'))
def within_budget(shop: SwagLabs, budgets: dict[str, float], action: str) -> None:
    measurement = shop.perf.last(action)
    budget = budgets[action]
    assert measurement.duration_ms <= budget, _verdict(measurement, budget)


@when(parsers.parse('I buy "{name}" through the shop'))
def buy(shop: SwagLabs, name: str) -> None:
    product = shop.catalogue.by_name(name)
    inventory = shop.inventory()
    with shop.perf.measure("add-to-cart"):
        inventory.add(product)
        inventory.expect_in_cart(product)
    with shop.perf.measure("open-cart"):
        shop.header.open_cart()
        shop.cart().wait_until_loaded()
    shop.cart().check_out()
    info = shop.checkout_info()
    info.wait_until_loaded()
    info.enter_details(*CUSTOMER)
    with shop.perf.measure("checkout-overview"):
        info.continue_()
        shop.overview().wait_until_loaded()
    with shop.perf.measure("finish-order"):
        shop.overview().finish()
        shop.complete().wait_until_loaded()


@then("every timed interaction of the purchase stayed within its budget")
def purchase_within_budgets(shop: SwagLabs, budgets: dict[str, float]) -> None:
    over = [
        _verdict(m, budgets[m.action])
        for m in shop.perf.measurements
        if m.action in budgets and m.duration_ms > budgets[m.action]
    ]
    assert not over, "over budget:\n  " + "\n  ".join(over)
