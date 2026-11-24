Feature: Dynamic catalogue
  As a shopper on a slow connection
  I want content that loads later to arrive complete and correct
  So that what I finally see can be trusted

  Background:
    Given I am logged in

  @regression @risk-medium @REQ-SL-13
  Scenario: Products appear once the spinner has gone
    When I open the spinner catalogue
    Then the products appear once the spinner has gone
    And every tile shows a reference product at its reference price

  @regression @risk-medium @REQ-SL-13
  Scenario: Scrolling loads more products without duplicates or gaps
    When I open the lazy-loading catalogue
    And I scroll down until at least 30 products have loaded
    Then every tile on screen finishes loading
    And every loaded tile shows a reference product at its reference price
    And the tiles are numbered without duplicates or gaps

  @regression @risk-medium @REQ-SL-13
  Scenario: The slider's active dot always names the product on show
    When I open the product slider
    Then for 6 seconds the active dot always names the product on show
    And the slider moved on by itself

  @regression @risk-medium @REQ-SL-13
  Scenario: Choosing a dot shows that product
    When I open the product slider
    And I choose the slider dot for "Sauce Labs Fleece Jacket"
    Then "Sauce Labs Fleece Jacket" is shown after my choice
