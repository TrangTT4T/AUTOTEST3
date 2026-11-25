from framework.adapters.mobile.screens.base import Screen
from framework.adapters.mobile.screens.cart import CartScreen
from framework.adapters.mobile.screens.catalog import CatalogScreen
from framework.adapters.mobile.screens.complete import CompleteScreen
from framework.adapters.mobile.screens.login import LoginScreen
from framework.adapters.mobile.screens.payment import PaymentScreen
from framework.adapters.mobile.screens.product import ProductScreen
from framework.adapters.mobile.screens.review import ReviewScreen
from framework.adapters.mobile.screens.shipping import ShippingScreen

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
