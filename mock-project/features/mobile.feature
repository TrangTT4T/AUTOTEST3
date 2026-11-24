@phone
Feature: Shopping on a phone
  As a shopper on a phone
  I want the core journey to work with touch on a narrow screen
  So that I can buy without a computer

  Background:
    Given I am logged in

  @smoke @risk-medium @REQ-SL-15
  Scenario: Adding to the cart and opening it by touch
    When I tap Add to cart for "Sauce Labs Bike Light"
    And I tap the cart
    Then the cart page lists only "Sauce Labs Bike Light"
    And the page fits the screen without sideways scrolling

  @regression @risk-medium @REQ-SL-15
  Scenario: The menu opens and closes by touch
    When I tap the menu button
    Then the menu offers "All Items", "Dynamic Catalog", "About", "Logout", "Reset App State"
    When I close the menu
    Then the products page is usable again
