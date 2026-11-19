"""Product detail: price, quantity selector, Add to cart."""

from __future__ import annotations

from framework.adapters.mobile.locators import by_accessibility_id, by_id
from framework.adapters.mobile.screens.base import Screen, number
from framework.domain import Money, Product


class ProductScreen(Screen):
    def wait_until_loaded(self) -> None:
        self.visible(self._add_to_cart)

    def read(self) -> Product:
        self.wait_until_loaded()
        return Product(
            name=self.visible(self._title).text.strip(),
            price=Money.parse(self.visible(self._price).text, "USD"),
            available=self.visible(self._add_to_cart).is_enabled(),
        )

    def quantity(self) -> int:
        return number(self.visible(self._quantity).text)

    def set_quantity(self, quantity: int) -> None:
        for _ in range(20):
            current = self.quantity()
            if current == quantity:
                return
            self.tap(self._plus if current < quantity else self._minus)
        raise AssertionError(f"could not set quantity to {quantity}; it shows {self.quantity()}")

    def add_to_cart(self, quantity: int = 1) -> None:
        """Set the quantity, tap once, and wait for the evidence: the header badge."""
        before = self.cart_count()
        self.set_quantity(quantity)
        self.tap(self._add_to_cart)
        self.wait_for_cart_count(before + quantity)

    # --- Locators -----------------------------------------------------------------
    _title = by_id("productTV", "fragment_product_detail")  # the product's name
    _price = by_id("priceTV", "fragment_product_detail")
    _plus = by_accessibility_id("Increase item quantity", "fragment_product_detail")
    _minus = by_accessibility_id("Decrease item quantity", "fragment_product_detail")
    _quantity = by_id("noTV", "fragment_product_detail")
    _add_to_cart = by_accessibility_id("Tap to add product to cart", "fragment_product_detail")
