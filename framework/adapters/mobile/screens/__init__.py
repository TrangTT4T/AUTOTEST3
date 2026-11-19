from framework.adapters.mobile.screens.base import Screen
from framework.adapters.mobile.screens.cart import CartScreen
from framework.adapters.mobile.screens.catalog import CatalogScreen
from framework.adapters.mobile.screens.checkout import (
    CompleteScreen,
    LoginScreen,
    PaymentScreen,
    ReviewScreen,
    ShippingScreen,
)
from framework.adapters.mobile.screens.product import ProductScreen

# Every screen class: the locator contract test reads their Locators sections.
ALL_SCREENS = (
    Screen,
    CatalogScreen,
    ProductScreen,
    CartScreen,
    LoginScreen,
    ShippingScreen,
    PaymentScreen,
    ReviewScreen,
    CompleteScreen,
)

__all__ = [
    "ALL_SCREENS",
    "CartScreen",
    "CatalogScreen",
    "CompleteScreen",
    "LoginScreen",
    "PaymentScreen",
    "ProductScreen",
    "ReviewScreen",
    "Screen",
    "ShippingScreen",
]
