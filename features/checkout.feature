@web
Feature: Checkout
  Visitors move from the cart to checkout. Payment is never automated.

  Rule: A visitor with items in the cart can reach checkout

    @REQ-07 @risk-medium @smoke
    Scenario: Proceeding from the cart reaches the checkout page
      Given the cart contains these products:
        | product     | quantity |
        | Grey jacket | 1        |
      When they proceed to checkout
      Then the checkout page is shown

    @REQ-07 @risk-medium @regression
    Scenario: The order summary matches the cart
      Given the cart contains these products:
        | product     | quantity |
        | Grey jacket | 2        |
        | Noir jacket | 1        |
      When they proceed to checkout
      Then the order summary lists the same products and quantities as the cart
      And the order total equals the cart total
