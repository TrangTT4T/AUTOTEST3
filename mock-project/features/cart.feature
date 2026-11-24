Feature: Shopping cart
  As a shopper
  I want the cart to hold exactly what I chose
  So that I pay for the right things

  Background:
    Given I am logged in

  @smoke @risk-high @REQ-SL-07
  Scenario: Adding products updates the badge and the cart
    When I add "Sauce Labs Backpack" to the cart
    And I add "Sauce Labs Bike Light" to the cart
    Then the cart badge shows 2
    And the cart holds exactly:
      | product               | quantity | price  |
      | Sauce Labs Backpack   | 1        | $29.99 |
      | Sauce Labs Bike Light | 1        | $9.99  |

  @regression @risk-high @REQ-SL-07 @area-add-any-product
  Scenario: Every product can be added from the catalogue
    When I add every product to the cart
    Then the cart badge shows 6
    And the stored cart holds every product

  @regression @risk-high @REQ-SL-07 @area-remove-from-catalogue
  Scenario: Remove on the catalogue takes a product out of the cart
    Given my cart holds "Sauce Labs Backpack" and "Sauce Labs Bike Light"
    When I remove "Sauce Labs Backpack" on the catalogue page
    Then the cart badge shows 1
    And the stored cart holds only "Sauce Labs Bike Light"

  @regression @risk-high @REQ-SL-07
  Scenario: Remove on the cart page takes a product out of the cart
    Given my cart holds "Sauce Labs Backpack" and "Sauce Labs Bike Light"
    When I open the cart
    And I remove "Sauce Labs Backpack" on the cart page
    Then the cart page lists only "Sauce Labs Bike Light"
    And the cart badge shows 1

  @regression @risk-high @REQ-SL-07
  Scenario: Double-clicking Add to cart never puts a product in twice
    When I double-click Add to cart for "Sauce Labs Onesie"
    Then the stored cart holds "Sauce Labs Onesie" at most once
    And the cart badge agrees with the stored cart

  @regression @risk-medium @REQ-SL-08
  Scenario: The cart survives navigation and a reload
    Given my cart holds "Sauce Labs Backpack" and "Sauce Labs Onesie"
    When I open "Sauce Labs Bike Light" from its card
    And I go back to the products
    And I reload the page
    Then the cart badge shows 2

  @regression @risk-medium @REQ-SL-08
  Scenario: A change made in a second tab reaches the first tab
    Given my cart holds "Sauce Labs Backpack" and "Sauce Labs Onesie"
    And a second tab shows the cart
    When I remove "Sauce Labs Onesie" in the second tab
    Then the stored cart eventually holds only "Sauce Labs Backpack"
    And after a reload the first tab's badge shows 1
