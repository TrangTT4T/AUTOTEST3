"""Page objects. Each owns the selectors of one page, declared at the bottom of its class."""

from swaglabs.pages.cart import CartPage
from swaglabs.pages.checkout import CheckoutCompletePage, CheckoutInfoPage, CheckoutOverviewPage
from swaglabs.pages.dynamic import LazyLoadCatalogPage, SliderCatalogPage, SpinnerCatalogPage
from swaglabs.pages.header import Header, SideMenu
from swaglabs.pages.inventory import InventoryPage
from swaglabs.pages.login import LoginPage
from swaglabs.pages.product import ProductPage

__all__ = [
    "CartPage",
    "CheckoutCompletePage",
    "CheckoutInfoPage",
    "CheckoutOverviewPage",
    "Header",
    "InventoryPage",
    "LazyLoadCatalogPage",
    "LoginPage",
    "ProductPage",
    "SideMenu",
    "SliderCatalogPage",
    "SpinnerCatalogPage",
]
