Feature: Response times
  As a shopper
  I want the shop to react quickly
  So that I do not give up

  # Single-user timings in a real browser - not load tests. Budgets: perf-budgets.toml.

  @regression @risk-medium @REQ-SL-14 @area-response-time
  Scenario: Logging in stays within its budget
    Given I am on the login page
    When I log in as the persona under test
    Then the "login" interaction stayed within its budget

  @regression @risk-medium @REQ-SL-14 @area-response-time @area-sorting
  Scenario: Sorting stays within its budget
    Given I am logged in
    When I sort the products by "Price (low to high)"
    Then the "sort" interaction stayed within its budget

  @regression @risk-high @REQ-SL-14 @REQ-SL-07 @REQ-SL-11 @area-last-name-entry @area-finish-order
  Scenario: Every step of a purchase stays within its budget
    Given I am logged in
    When I buy "Sauce Labs Onesie" through the shop
    Then every timed interaction of the purchase stayed within its budget
