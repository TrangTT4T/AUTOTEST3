"""Navigation steps: checkout and information pages."""

from pytest_bdd import then, when

from framework.domain import OrderSummary
from framework.ports import Store
from framework.step_types import parsed


@when("they proceed to checkout", target_fixture="page_title")
def proceed_to_checkout(store: Store) -> str:
    return store.go_to_checkout()


@then("the checkout page is shown")
def checkout_shown(page_title: str) -> None:
    assert page_title.startswith("Checkout"), f"expected the checkout page, got {page_title!r}"


@when(parsed('the visitor opens "{link:Quoted}" from the main menu'), target_fixture="page_title")
def open_menu_page(store: Store, link: str) -> str:
    return store.open_menu_page(link)


@then(parsed('a page titled "{title:Quoted}" is shown'))
def page_titled(page_title: str, title: str) -> None:
    assert title in page_title, f"expected a title containing {title!r}, got {page_title!r}"


@then("the order summary lists the same products and quantities as the cart", target_fixture="summary")
def summary_matches_cart(store: Store) -> OrderSummary:
    summary = store.checkout_summary()
    cart = store.cart()
    assert summary.quantities() == cart.quantities(), (
        f"checkout {summary.quantities()} vs cart {cart.quantities()}"
    )
    return summary


@then("the order total equals the cart total")
def order_total_matches(store: Store, summary: OrderSummary) -> None:
    cart_total = store.cart().total
    assert summary.subtotal == cart_total, f"checkout subtotal {summary.subtotal} vs cart {cart_total}"
    assert summary.total == cart_total, f"checkout total {summary.total} vs cart {cart_total}"


@when("the visitor opens the latest blog article", target_fixture="article_titles")
def open_latest_article(store: Store) -> tuple[str, str]:
    return store.open_latest_article()


@then("the article page shows the title it had in the blog list")
def article_title_matches(article_titles: tuple[str, str]) -> None:
    listed, shown = article_titles
    assert shown == listed, f"blog list says {listed!r}, article page says {shown!r}"


@when("the visitor opens an address that does not exist", target_fixture="missing_page")
def open_missing(store: Store) -> tuple[int | None, str]:
    return store.open_missing_page()


@then("the visitor sees the not-found page")
def not_found_shown(missing_page: tuple[int | None, str]) -> None:
    # HTTP status belongs in the step, not in business-facing Gherkin.
    status, title = missing_page
    assert status == 404, f"expected HTTP 404, got {status} (title {title!r})"
    assert "404" in title, f"title {title!r}"
