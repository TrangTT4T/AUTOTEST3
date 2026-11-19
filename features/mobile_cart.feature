@mobile
Feature: Shopping cart in the mobile app
  The Unit 1 cart behaviour, specified with the same steps, for My Demo App (Android).
  The app is a different product with its own catalogue (USD); see Unit 3, Day 11.

  Background:
    Given a visitor with an empty cart

  Rule: Added products appear in the cart with a correct subtotal

    @REQ-03 @REQ-04 @risk-high @smoke
    Scenario: Adding a product in the app puts it in the cart
      Given the visitor is viewing the product "Sauce Labs Backpack"
      When they add the product to the cart
      Then the cart contains 1 "Sauce Labs Backpack"
      And the cart subtotal equals the product price times 1

    @REQ-04 @risk-high @regression
    Scenario Outline: The app's subtotal follows the quantity chosen
      Given the visitor is viewing the product "<product>"
      When they add the product to the cart <times> times
      Then the cart contains <times> "<product>"
      And the cart subtotal equals the product price times <times>

      Examples:
        | product              | times |
        | Sauce Labs Backpack  | 2     |
        | Sauce Labs Bike Light | 3    |

  Rule: Several products can be added

    @REQ-04 @risk-high @regression
    Scenario: The app's cart holds several products
      When they add these products to the cart:
        | product               | quantity |
        | Sauce Labs Backpack   | 1        |
        | Sauce Labs Bike Light | 2        |
      Then the cart has 3 items in total

  Rule: Changing the cart updates the subtotal

    @REQ-05 @risk-high @regression
    Scenario: Removing one product in the app keeps the others
      Given the cart contains these products:
        | product               | quantity |
        | Sauce Labs Backpack   | 1        |
        | Sauce Labs Bike Light | 2        |
      When they remove "Sauce Labs Backpack" from the cart
      Then the cart contains 0 "Sauce Labs Backpack"
      And the cart contains 2 "Sauce Labs Bike Light"
      And the cart has 2 items in total

    @REQ-05 @risk-high @regression
    Scenario: Changing the quantity in the app updates the subtotal
      Given the cart contains these products:
        | product             | quantity |
        | Sauce Labs Backpack | 1        |
      When they change the quantity of "Sauce Labs Backpack" to 3
      Then the cart contains 3 "Sauce Labs Backpack"
      And the cart subtotal equals 3 times the catalogue price of "Sauce Labs Backpack"
