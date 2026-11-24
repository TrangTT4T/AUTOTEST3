Feature: Sessions
  As the shop owner
  I want every page behind the login to need a session
  So that nobody shops, or sees a cart, without signing in

  @smoke @risk-high @REQ-SL-03 @persona-independent
  Scenario Outline: A visitor without a session is sent to the login page
    When I open "<path>" without logging in
    Then I see the login page
    And I see the login error "Epic sadface: You can only access '<path>' when you are logged in."

    Examples:
      | path                    |
      | /inventory.html         |
      | /cart.html              |
      | /checkout-step-one.html |

  @regression @risk-high @REQ-SL-01 @REQ-SL-03
  Scenario: The quick-login shortcut creates the same session as the login form
    Given I am on the login page
    When I log in as the persona under test
    Then the session cookie is the one the quick-login shortcut sets

  @smoke @risk-high @REQ-SL-03
  Scenario: Logging out ends the session
    Given I am logged in
    When I log out
    Then I see the login page
    And opening "/inventory.html" sends me back to the login page

  @regression @risk-high @REQ-SL-03
  Scenario: Back after logging out does not show the products again
    Given I am logged in
    When I log out
    And I go back in the browser
    # The login button is still on screen right after Back: assert the guard's message instead,
    # which only a real redirect shows - no race with the history navigation.
    Then I see the login error "Epic sadface: You can only access '/inventory.html' when you are logged in."

  @regression @risk-low @REQ-SL-12
  Scenario: Reset App State empties the cart
    Given I am logged in
    And my cart holds "Sauce Labs Backpack" and "Sauce Labs Onesie"
    When I reset the app state from the menu
    Then the cart badge is empty
    And the stored cart is empty

  @regression @risk-low @REQ-SL-12 @area-reset-state
  Scenario: Reset App State also resets the buttons on the page
    Given I am logged in
    And my cart holds "Sauce Labs Backpack"
    When I reset the app state from the menu
    Then every product offers "Add to cart"
