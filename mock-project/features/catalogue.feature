Feature: Product catalogue
  As a shopper
  I want to see every product with its real price, picture and details
  So that I know what I am buying

  Background:
    Given I am logged in

  @smoke @risk-medium @REQ-SL-04
  Scenario: The catalogue lists every product
    Then the catalogue lists the 6 reference products

  @regression @risk-medium @REQ-SL-04 @area-catalogue-prices
  Scenario: Every card shows the product's real price
    Then every card shows its product's reference price

  @regression @risk-medium @REQ-SL-04 @area-catalogue-images
  Scenario: Every card shows the product's own picture
    Then every card shows its product's own image

  @regression @risk-medium @REQ-SL-05 @area-sorting
  Scenario Outline: Sorting re-orders the catalogue
    When I sort the products by "<order>"
    Then the products are listed in "<order>" order
    And no error dialog appeared

    Examples:
      | order               |
      | Name (Z to A)       |
      | Price (low to high) |
      | Price (high to low) |

  @regression @risk-medium @REQ-SL-05 @area-sorting
  Scenario: Name (A to Z) restores the default order
    When I sort the products by "Price (high to low)"
    And I sort the products by "Name (A to Z)"
    Then the products are listed in "Name (A to Z)" order
    And no error dialog appeared

  @smoke @risk-medium @REQ-SL-06 @area-product-links @area-catalogue-prices @area-catalogue-images
  Scenario Outline: A product page agrees with the card that opened it
    When I open "<product>" from its card
    Then the product page shows the same name, price and image as the card

    Examples:
      | product                  |
      | Sauce Labs Backpack      |
      | Sauce Labs Fleece Jacket |
