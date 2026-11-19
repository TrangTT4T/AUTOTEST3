@web
Feature: Site navigation
  Information pages are reachable from the main menu.

  Rule: Main menu links open their pages

    @REQ-09 @risk-low @regression
    Scenario Outline: Main menu opens an information page
      When the visitor opens "<link>" from the main menu
      Then a page titled "<title>" is shown

      Examples:
        | link     | title    |
        | About Us | About Us |
        | Blog     | News     |

  Rule: Content and unknown addresses are handled

    @REQ-09 @risk-low @regression
    Scenario: The latest blog article opens from the blog
      When the visitor opens the latest blog article
      Then the article page shows the title it had in the blog list

    @REQ-09 @risk-low @regression
    Scenario: An unknown address shows the not-found page
      When the visitor opens an address that does not exist
      Then the visitor sees the not-found page
