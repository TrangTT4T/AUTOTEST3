from framework.testdata import new_customer, unique_email


def test_unique_emails_never_repeat_and_are_undeliverable() -> None:
    emails = {unique_email() for _ in range(200)}
    assert len(emails) == 200
    assert all(email.endswith("@example.com") for email in emails)


def test_new_customer_allows_overrides() -> None:
    customer = new_customer(first_name="Ada")
    assert customer.first_name == "Ada"
    assert customer.email != new_customer().email
