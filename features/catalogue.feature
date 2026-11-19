@web
Feature: Product catalogue
  Visitors find products and see their details.

  Rule: Search finds products by keyword

    @REQ-01 @risk-medium @regression
    Scenario: Searching for a keyword lists matching products
      When the visitor searches for "jacket"
      Then at least 2 products are found
      And every result mentions "jacket"

    @REQ-01 @risk-medium @regression
    Scenario: Searching for an unknown word finds nothing
      When the visitor searches for "zzqqxx"
      Then no products are found

  Rule: Product pages show the catalogue details

    @REQ-02 @risk-medium @regression
    Scenario Outline: Product page matches the catalogue
      Given the visitor is viewing the product "<product>"
      Then the product page shows the name "<product>"
      And the product page price matches the catalogue price

      Examples:
        | product     |
        | Grey jacket |
        | Noir jacket |
        | Striped top |

  Rule: The catalogue shows every product with its price and availability

    @REQ-02 @REQ-06 @risk-medium @regression
    Scenario: The catalogue lists every product and labels the sold-out ones
      When the visitor browses the catalogue
      Then every product in the store is listed with its catalogue price
      And exactly the sold-out products are labelled "Sold Out"
