@web
Feature: Shopping cart
  Visitors collect products in a cart before checkout.

  Background:
    Given a visitor with an empty cart

  Rule: Added products appear in the cart with a correct subtotal

    @REQ-03 @REQ-04 @risk-high @smoke
    Scenario: Adding an available product puts it in the cart
      Given the visitor is viewing the product "Grey jacket"
      When they add the product to the cart
      Then the cart contains 1 "Grey jacket"
      And the cart subtotal equals the product price times 1

    @REQ-04 @risk-high @regression
    Scenario Outline: Subtotal follows quantity
      Given the visitor is viewing the product "<product>"
      When they add the product to the cart <times> times
      Then the cart contains <times> "<product>"
      And the cart subtotal equals the product price times <times>

      Examples:
        | product     | times |
        | Grey jacket | 2     |
        | Noir jacket | 3     |

  Rule: Visitors choose the variant they want

    @REQ-03 @risk-high @regression
    Scenario: Adding a chosen variant puts exactly that variant in the cart
      Given the visitor is viewing the product "Noir jacket"
      When they add the variant "L / Red" to the cart
      Then the cart contains 1 "Noir jacket" in variant "L / Red"

  Rule: Several products can be added at once

    @REQ-04 @risk-high @regression
    Scenario: Cart with several products
      When they add these products to the cart:
        | product     | quantity |
        | Grey jacket | 1        |
        | Noir jacket | 2        |
      Then the cart has 3 items in total

  Rule: Changing the cart updates the subtotal

    @REQ-05 @risk-high @regression
    Scenario: Removing one product keeps the others
      Given the cart contains these products:
        | product     | quantity |
        | Grey jacket | 1        |
        | Noir jacket | 2        |
      When they remove "Grey jacket" from the cart
      Then the cart contains 0 "Grey jacket"
      And the cart contains 2 "Noir jacket"
      And the cart has 2 items in total

    @REQ-05 @risk-high @regression
    Scenario: Changing the quantity updates the subtotal
      Given the cart contains these products:
        | product     | quantity |
        | Grey jacket | 1        |
      When they change the quantity of "Grey jacket" to 3
      Then the cart contains 3 "Grey jacket"
      And the cart subtotal equals 3 times the catalogue price of "Grey jacket"

  Rule: Sold-out products cannot be bought

    @REQ-06 @risk-medium @regression
    Scenario: A sold-out product cannot be added to the cart
      Given the visitor is viewing a sold-out product
      When they try to add the product to the cart
      Then the product is not added
      And the cart has 0 items in total
