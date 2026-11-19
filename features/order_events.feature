@events
Feature: Order events are processed reliably
  An order is accepted at once; payment, packing and shipping happen later, through
  messages that can arrive twice, late, out of order, or not at all. The customer follows
  the status live. Unit 3, Day 12 — the system is the order-events sandbox.

  Background:
    Given a customer following their order's status

  Rule: Every order is charged exactly once

    @REQ-10 @REQ-13 @risk-high @smoke
    Scenario: An order is paid, packed and shipped
      When they place an order
      Then the order is "shipped" within the consistency target
      And they were charged exactly once
      And they saw the statuses "placed, paid, packed, shipped" in that order

    @REQ-10 @risk-high @regression
    Scenario Outline: Delivery problems in the payment step never charge twice
      Given the payment step will suffer "<problem>"
      When they place an order
      Then the order is "shipped" within the consistency target
      And they were charged exactly once

      Examples:
        | problem                  |
        | a duplicate delivery     |
        | a lost acknowledgement   |
        | a gateway failure        |

  Rule: The status never goes backwards

    @REQ-11 @risk-high @regression @defect-D-12-02
    Scenario: A late packing update does not undo shipping
      Given the "packed" update will reach the order screen after the "shipped" update
      When they place an order
      Then the order is "shipped" within the consistency target
      And the status they saw never went backwards

  Rule: Messages that cannot be processed are parked without blocking others

    @REQ-12 @risk-medium @regression
    Scenario: A malformed order message is parked at once
      Given another system has sent a malformed order message
      When they place an order
      Then the malformed message was parked after 1 attempt
      And the order is "shipped" within the consistency target

  Rule: Customers keep up with their order after losing the connection

    @REQ-13 @risk-medium @regression @defect-D-12-03
    Scenario: The live status catches up after a reconnect
      Given their connection will drop after the "paid" update
      And they have placed an order
      When they reconnect after the order has shipped
      Then they saw the statuses "placed, paid, packed, shipped" in that order
