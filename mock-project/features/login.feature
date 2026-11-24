Feature: Logging in
  As a shopper
  I want to sign in with my own account
  So that only I can shop with it

  Background:
    Given I am on the login page

  @smoke @risk-high @REQ-SL-01
  Scenario: The persona under test logs in and lands on the products page
    When I log in as the persona under test
    Then I see the products page
    And the session belongs to the persona under test

  @regression @risk-high @REQ-SL-02 @persona-independent
  Scenario Outline: Wrong, missing or blocked credentials are refused
    When I log in with username "<username>" and password "<password>"
    Then I stay on the login page
    And I see the login error "<error>"
    And the username and password fields are marked invalid

    Examples:
      | username        | password     | error                                                                     |
      | locked_out_user | (valid)      | Epic sadface: Sorry, this user has been locked out.                       |
      | standard_user   | wrong-secret | Epic sadface: Username and password do not match any user in this service |
      | (empty)         | (valid)      | Epic sadface: Username is required                                        |
      | standard_user   | (empty)      | Epic sadface: Password is required                                        |

  @regression @risk-high @REQ-SL-02 @persona-independent
  Scenario: Closing the error message clears it
    When I log in with username "standard_user" and password "(empty)"
    And I close the login error
    Then no login error is shown
