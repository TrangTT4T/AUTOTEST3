"""Components: parts that appear on many pages. Page objects are built from them."""

from framework.adapters.web.components.breadcrumb import Breadcrumb
from framework.adapters.web.components.header import Header
from framework.adapters.web.components.main_menu import MainMenu
from framework.adapters.web.components.mini_cart import MiniCart
from framework.adapters.web.components.product_grid import ProductGrid

__all__ = ["Breadcrumb", "Header", "MainMenu", "MiniCart", "ProductGrid"]
