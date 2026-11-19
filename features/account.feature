@web
Feature: Customer accounts
  Sign-up and login pages are protected by CAPTCHA (verified on the live site),
  so these flows stay manual. See the Day 1 strategy, section 4.3.

  Rule: Account flows stay manual

    @REQ-08 @manual
    Scenario: Visitor signs up for an account
      Given the visitor is on the sign-up page
      When they register with a new email address
      Then they are logged in to their new account

    @REQ-08 @manual
    Scenario: Registered customer logs in
      Given a registered customer is on the login page
      When they log in with their email and password
      Then they see their account page
