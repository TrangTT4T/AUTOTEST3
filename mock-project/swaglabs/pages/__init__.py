"""Page objects: one class per file, its selectors declared at the bottom of the class."""

from swaglabs.pages.cart import CartPage
from swaglabs.pages.checkout_complete import CheckoutCompletePage
from swaglabs.pages.checkout_info import CheckoutInfoPage
from swaglabs.pages.checkout_overview import CheckoutOverviewPage
from swaglabs.pages.header import Header
from swaglabs.pages.inventory import InventoryPage
from swaglabs.pages.lazy_load_catalog import LazyLoadCatalogPage
from swaglabs.pages.login import LoginPage
from swaglabs.pages.product import ProductPage
from swaglabs.pages.side_menu import SideMenu
from swaglabs.pages.slider_catalog import SliderCatalogPage
from swaglabs.pages.spinner_catalog import SpinnerCatalogPage

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
