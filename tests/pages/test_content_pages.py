"""Content, blog, account, and error pages."""

import re

import pytest
from playwright.sync_api import expect

from framework.adapters.web.shop import Shop
from framework.testdata import new_customer

pytestmark = pytest.mark.web


def test_about_us_content_page(shop: Shop) -> None:
    page = shop.content().open_page("about-us")
    assert page.heading_text() == "About Us"
    assert page.breadcrumb.trail() == ["Home", "About Us"]


def test_blog_lists_articles_that_open(shop: Shop) -> None:
    blog = shop.blog().open()
    articles = blog.article_list()
    assert articles, "the blog has no articles"
    article = blog.open_article(articles[0].title)
    assert article.heading_text() == articles[0].title
    assert article.author() == "Shopify"
    expect(shop.page).to_have_url(re.compile(re.escape(articles[0].handle) + "$"))


def test_article_opens_directly_by_its_handle(shop: Shop) -> None:
    latest = shop.blog().open().article_list()[0]  # handle taken from the site, not hard-coded
    article = shop.article().open_article(latest.handle)
    assert article.heading_text() == latest.title


def test_header_links_open_the_account_pages(shop: Shop) -> None:
    home = shop.home().open()
    home.header.go_to_log_in()
    shop.login().wait_until_loaded()
    shop.login().header.go_to_sign_up()
    shop.register().wait_until_loaded()


def test_login_page_and_password_recovery_toggle(shop: Shop) -> None:
    # Never submitted: the live shop uses CAPTCHA, and recovery sends real e-mail.
    login = shop.login().open()
    login.fill_credentials("someone@example.com", "not-submitted")
    expect(login.email).to_have_value("someone@example.com")
    login.show_password_recovery()
    login.hide_password_recovery()


def test_register_form_accepts_a_customer(shop: Shop) -> None:
    # Never submitted: it would create a real account on someone else's shop.
    register = shop.register().open()
    customer = new_customer()
    register.fill_form(customer)
    expect(register.email).to_have_value(customer.email)
    expect(register.first_name).to_have_value(customer.first_name)


def test_unknown_address_shows_the_404_page(shop: Shop) -> None:
    page = shop.not_found().open_missing("/pages/this-page-does-not-exist")
    assert page.is_shown()
    assert "404" in page.page_title()
