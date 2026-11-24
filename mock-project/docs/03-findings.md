# Findings report — Swag Labs

**System under test:** https://www.saucedemo.com (public demo shop by Sauce Labs).
**How found:** exploratory sessions per persona (Day 19), then confirmed by the automated suite
(Day 20–21). Every finding below is reproduced on **every CI run** by at least one scenario with
the finding's `@area-*` tag; the register that drives this is [`findings.toml`](../findings.toml).

**Reading a finding.** *Personas* = the demo accounts that show it (the password for every
account is printed on the login page). *Area* = the behaviour the finding breaks; every scenario
tagged `@area-<name>` is a **strict expected failure** when the suite runs as an affected persona.
*Severity* uses the scale in [01-strategy.md](01-strategy.md#severity-scale).

| Id | Title | Personas | Requirement | Severity |
|---|---|---|---|---|
| SL-01 | Every catalogue card shows the same wrong image | problem_user | REQ-SL-04 | minor |
| SL-02 | Sorting does nothing | problem_user | REQ-SL-05 | major |
| SL-03 | Sorting opens an alert and does nothing | error_user | REQ-SL-05 | major |
| SL-04 | Add to cart does nothing for three products | problem_user, error_user | REQ-SL-07 | critical |
| SL-05 | Remove on the catalogue page does nothing | problem_user, error_user | REQ-SL-07 | major |
| SL-06 | A card opens a different product's page | problem_user | REQ-SL-06 | major |
| SL-07 | Text typed into Last Name is lost | problem_user, error_user | REQ-SL-09 | critical |
| SL-08 | Finish does not complete the order | error_user | REQ-SL-11 | critical |
| SL-09 | Catalogue prices are random | visual_user | REQ-SL-04 | critical |
| SL-10 | The Backpack card shows the wrong image | visual_user | REQ-SL-04 | minor |
| SL-11 | Login and sorting take about 5 s | performance_glitch_user | REQ-SL-14 | major |
| SL-12 | Reset App State leaves Remove buttons | all personas | REQ-SL-12 | minor |
| SL-14 | Checkout accepts an empty Last Name | error_user | REQ-SL-09 | major |

SL-13 was retired before it was registered — see [Retired observations](#retired-observations).

---

### SL-01 Every catalogue card shows the same wrong image

- **Persona:** problem_user · **Area:** `catalogue-images` · **Severity:** minor
- **Steps:** log in as problem_user; look at the products page.
- **Expected:** each card shows its product's photo (e.g. the backpack shows `sauce-backpack-…jpg`).
- **Actual:** all six cards show the same placeholder picture (`sl-404-…jpg`, a dog).
- **Detected by:** *Every card shows the product's own picture* (compares each `<img src>` with
  the reference catalogue, ignoring the build hash in the file name).

### SL-02 Sorting does nothing: the order never changes

- **Persona:** problem_user · **Area:** `sorting` · **Severity:** major
- **Steps:** log in; choose *Price (low to high)* in the sort menu.
- **Expected:** Sauce Labs Onesie ($7.99) first, Fleece Jacket ($49.99) last.
- **Actual:** the list stays in A-to-Z order for every option; no error is shown.
- **Detected by:** *Sorting re-orders the catalogue* (3 examples), *Name (A to Z) restores the
  default order*, *Sorting stays within its budget*.

### SL-03 Sorting opens an alert 'Sorting is broken!' and the order does not change

- **Persona:** error_user · **Area:** `sorting` · **Severity:** major
- **Steps:** log in; choose any sort option.
- **Expected:** the list is re-ordered, no dialog.
- **Actual:** a JavaScript `alert("Sorting is broken! This error has been reported to Backtrace.")`
  opens; the order stays A to Z. The app also tries to send the error to a third-party error
  tracker — our network policy blocks that call (see [02-architecture.md](02-architecture.md#network-control)).
- **Detected by:** the sorting scenarios; the dialog is recorded in the failure evidence
  (`dialogs` in the step's JSON file) and checked by *no error dialog appeared*.

### SL-04 Add to cart does nothing for three of the six products

- **Personas:** problem_user, error_user · **Area:** `add-any-product` · **Severity:** critical
- **Steps:** log in; click *Add to cart* on every product.
- **Expected:** six products in the cart, badge 6.
- **Actual:** Bolt T-Shirt, Fleece Jacket and Test.allTheThings() T-Shirt stay on *Add to cart*;
  the badge stops at 3. Backpack, Bike Light and Onesie work — which is exactly why a test that
  only adds the first product would never find this.
- **Detected by:** *Every product can be added from the catalogue*.

### SL-05 Remove on the catalogue page does nothing

- **Personas:** problem_user, error_user · **Area:** `remove-from-catalogue` · **Severity:** major
- **Steps:** have Backpack and Bike Light in the cart; click *Remove* on the Backpack card.
- **Expected:** the button returns to *Add to cart*, badge 1.
- **Actual:** nothing changes. *Remove on the cart page* still works (that scenario passes for
  both personas), so a shopper has a workaround — hence major, not critical.
- **Detected by:** *Remove on the catalogue takes a product out of the cart*.

### SL-06 A catalogue card opens the page of a different product (id + 1)

- **Persona:** problem_user · **Area:** `product-links` · **Severity:** major
- **Steps:** click the name on the *Sauce Labs Backpack* card (product id 4).
- **Expected:** `inventory-item.html?id=4` showing the backpack.
- **Actual:** `?id=5` (Fleece Jacket). The Fleece Jacket card (id 5) opens `?id=6`, which shows
  *ITEM NOT FOUND*.
- **Detected by:** *A product page agrees with the card that opened it* (2 examples).

### SL-07 Text typed into Last Name is lost (moved into First Name, or dropped)

- **Personas:** problem_user, error_user · **Area:** `last-name-entry` · **Severity:** critical
- **Steps:** on *Checkout: Your Information* type `Ada`, `Lovelace`, `10115`.
- **Expected:** each field keeps its text.
- **Actual:** problem_user — typing in Last Name overwrites First Name (it ends up `Lovelace`,
  Last Name stays empty); error_user — Last Name stays empty. The checkout cannot be completed
  with a valid name, so every purchase scenario is blocked for these personas.
- **Detected by:** `fill_verified` in the page object checks each field right after typing,
  so the failure points at the field instead of at a confusing error two steps later.
  Scenarios: two *Each missing detail…* examples, *The overview adds 8 % tax…*, *Finishing the
  order…*, *Every step of a purchase…*.

### SL-08 Finish does not complete the order

- **Persona:** error_user · **Area:** `finish-order` · **Severity:** critical
- **Steps:** complete step one, click *Finish* on the overview.
- **Expected:** *Thank you for your order!*, cart emptied.
- **Actual:** the page stays on the overview. (Today SL-07 already stops error_user one page
  earlier; the area tag keeps this finding detectable on its own once SL-07 is fixed.)
- **Detected by:** *Finishing the order confirms it and empties the cart*.

### SL-09 Catalogue prices are random on every load and disagree with the product page and cart

- **Persona:** visual_user · **Area:** `catalogue-prices` · **Severity:** critical
- **Steps:** log in as visual_user twice; compare the card prices.
- **Expected:** the reference prices ($29.99 for the backpack …), the same on every page.
- **Actual:** different random prices on every load (e.g. backpack $39.50, then $19.40), while
  the product page, the cart and the overview charge the real price. A shopper is shown one
  price and charged another.
- **Detected by:** *Every card shows the product's real price*, *A product page agrees with the
  card that opened it*.
- **Note:** sorting by price still uses the real prices, so the sorting scenarios pass for this
  persona — the assertion compares the ORDER OF NAMES, which is deterministic.

### SL-10 The Backpack card shows the wrong image

- **Persona:** visual_user · **Area:** `catalogue-images` · **Severity:** minor
- **Steps:** log in as visual_user; look at the Backpack card.
- **Expected:** the backpack photo. **Actual:** the placeholder picture.
- **Detected by:** *Every card shows the product's own picture*.

### SL-11 Login and sorting each take about 5 seconds

- **Persona:** performance_glitch_user · **Area:** `response-time` · **Severity:** major
- **Steps:** log in; sort by price.
- **Expected:** within the budgets in `perf-budgets.toml` (login 2.5 s, sort 2 s).
- **Actual:** ~5.1 s each, every time. The interaction timer splits the time into network-busy
  and client time: the network is idle for most of the wait, so the delay is **in the browser**
  (a deliberate client-side delay), not on the server — see [04-execution-and-evidence.md](04-execution-and-evidence.md#performance-evidence).
- **Detected by:** *Logging in stays within its budget*, *Sorting stays within its budget*.
  Functional scenarios still pass: the UI timeout (10 s) is above the delay — a performance
  defect is reported as a performance defect, not as random functional flakiness.

### SL-12 After Reset App State the catalogue still shows Remove buttons until a reload

- **Personas:** all · **Area:** `reset-state` · **Severity:** minor
- **Steps:** add the backpack; open the menu; *Reset App State*.
- **Expected:** empty cart, every card offers *Add to cart*.
- **Actual:** the cart and badge are emptied (that scenario passes), but the backpack card still
  says *Remove* until the page is reloaded; clicking it then does nothing useful.
- **Detected by:** *Reset App State also resets the buttons on the page*.

### SL-14 Checkout accepts an empty Last Name

- **Persona:** error_user · **Area:** `last-name-required` · **Severity:** major
- **Steps:** step one with First Name `Ada`, Last Name empty, Postal Code `10115`; *Continue*.
- **Expected:** *Error: Last Name is required*.
- **Actual:** the overview opens — the order would be placed without a surname.
- **Detected by:** the *Last Name left empty* example of *Each missing detail is refused…*.
- **How it was found:** not by exploration — by the suite. The first run as error_user failed
  this example in an unexpected way; the failure evidence showed the overview page. That is
  what a strict register is for: an unexplained failure is investigated, never waved through.

---

## Retired observations

**SL-13 (never registered) — "After logout, Back shows the products page again".** Seen once
during exploration, after a long session with several reloads. Twelve targeted attempts
(form login and quick login, with and without reload or reset, two personas) all showed the
correct behaviour: Back leads to the login page with *You can only access '/inventory.html'
when you are logged in.* A finding that cannot be reproduced on demand would make the suite
flaky, so it was not registered. The scenario *Back after logging out does not show the
products again* stays as a **regression guard**: it passes today and fails if the behaviour
ever appears for real.
