Feature: Checkout
  As a shopper
  I want to give my details, see what I will pay and confirm
  So that my order is placed correctly

  Background:
    Given I am logged in
    And my cart holds "Sauce Labs Backpack" and "Sauce Labs Bike Light"
    And I am on the checkout information page

  @regression @risk-high @REQ-SL-09
  Scenario Outline: Each missing detail is refused with its own message
    When I enter first name "<first>", last name "<last>" and postal code "<postal>"
    And I continue
    Then I stay on the checkout information page
    And I see the checkout error "<error>"

    Examples: Nothing typed
      | first | last | postal | error                         |
      |       |      |        | Error: First Name is required |

    @area-last-name-required
    Examples: Last Name left empty
      | first | last | postal | error                        |
      | Ada   |      | 10115  | Error: Last Name is required |

    @area-last-name-entry
    Examples: Last Name typed
      | first | last     | postal | error                          |
      |       | Lovelace | 10115  | Error: First Name is required  |
      | Ada   | Lovelace |        | Error: Postal Code is required |

  @smoke @risk-high @REQ-SL-10 @area-last-name-entry
  Scenario: The overview adds 8 % tax to the item total
    When I enter first name "Ada", last name "Lovelace" and postal code "10115"
    And I continue
    Then the overview lists the products in my cart at their reference prices
    And the overview shows the item total, tax and total for them

  @smoke @risk-high @REQ-SL-11 @area-last-name-entry @area-finish-order
  Scenario: Finishing the order confirms it and empties the cart
    When I enter first name "Ada", last name "Lovelace" and postal code "10115"
    And I continue
    And I finish the order
    Then I see the confirmation "Thank you for your order!"
    And the cart badge is empty
    And the stored cart is empty
