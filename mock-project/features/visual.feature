Feature: Visual appearance
  As a shopper
  I want pages to look as designed
  So that the shop feels trustworthy

  # Not automated in this project: a pixel comparison needs approved baselines per browser and
  # viewport and a review workflow (docs/01-strategy.md, "Out of scope"). Checked by hand.

  @manual @REQ-SL-16
  Scenario: Layout, alignment and images match the design
    Given a reviewer compares every page with the approved design
    Then nothing is misplaced, misaligned, cropped or overlapping
