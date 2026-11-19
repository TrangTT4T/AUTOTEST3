# Unit 1 · Day 1 — Risk-Based Automation Strategy, Testability Analysis, BDD Principles

| | |
|---|---|
| **Course** | Advanced Automation Test Engineering (ATEST03) — Fast Track |
| **Learning outcome** | **LO1** — Evaluate product risk and testability to define an advanced cross-platform automation strategy (Bloom **B5: Evaluate**) |
| **Format** | Concept/Lecture · Virtual · 120 minutes · no code to submit |
| **System under test** | https://sauce-demo.myshopify.com/ (a public Shopify demo store) |
| **Stack for this unit** | Python · `pytest` · `pytest-bdd` (Gherkin) · Playwright for Python (from Day 3) |
| **Output of the day** | A one-page **Automation Strategy** for the store |

> **Site details — checked on Day 3.** This guide was first written from memory. On 2026-11-17 the live store was checked with Playwright (see Day 3, "Site facts"): the product names and prices are correct; **Brown Shades** and **White sandals** are sold out; login and sign-up pages load CAPTCHA scripts. Exercise L1-1 is still worth doing — observing the site yourself is the skill.

---

## How to use this guide

You do not need any testing or BDD background. Each topic climbs three levels:

| Badge | Level | After this level you can… |
|---|---|---|
| 🟢 | **Foundation** (newbie) | Explain the idea in your own words with an everyday example |
| 🟡 | **Practitioner** | Apply it to the demo store step by step |
| 🔴 | **Advanced** | Make and defend decisions, spot weak designs, connect it to the whole strategy |

Read every 🟢 section first. Stop at each **Checkpoint**: if you cannot answer it, re-read before moving on. The lecture time plan (120 min):

| Time | Part |
|---|---|
| 0–15 | Part 0 — Testing basics |
| 15–45 | Part 1 — Risk |
| 45–65 | Part 2 — Testability |
| 65–100 | Part 3 — BDD |
| 100–120 | Part 4 — Putting it together (advanced) |

---

## Glossary

Come back here whenever a word is unclear.

| Term | Meaning | Vietnamese |
|---|---|---|
| Test case | Steps + expected result that check one thing | Ca kiểm thử |
| Automation | A program performs the test instead of a person | Tự động hóa |
| Regression | Re-testing old features after a change, to catch things that broke | Kiểm thử hồi quy |
| Risk | The chance that something goes wrong × how bad it would be | Rủi ro |
| Likelihood | How likely a failure is | Khả năng xảy ra |
| Impact | How much damage a failure causes | Mức độ ảnh hưởng |
| Testability | How easy it is to test something reliably | Khả năng kiểm thử được |
| Flaky test | A test that sometimes passes, sometimes fails, with no code change | Test chập chờn |
| Locator / selector | The address a test uses to find an element on the page | Bộ định vị phần tử |
| BDD | Behaviour-Driven Development: agree on behaviour using examples | Phát triển hướng hành vi |
| Gherkin | The plain-English format for BDD examples (`Given/When/Then`) | Ngôn ngữ Gherkin |
| Scenario | One concrete example of one behaviour | Kịch bản |
| Feature file | A `.feature` file holding scenarios about one capability | File đặc tả tính năng |
| Step definition | Code that runs when a Gherkin step is executed | Định nghĩa bước |
| Tag | A label like `@smoke` on a scenario, used to select and trace | Nhãn |
| Traceability | Being able to link a requirement ↔ test ↔ result | Khả năng truy vết |
| Stakeholder | Anyone who cares about the product (business, dev, tester, user) | Bên liên quan |

---

## Part 0 — Testing basics you need first 🟢

### 0.1 What is a test?

A test compares **what the system does** with **what it should do**. Every test case has three parts:

| Part | Example on the store |
|---|---|
| **Precondition** (starting state) | The cart is empty |
| **Steps** (actions) | Open "Grey jacket", click *Add to Cart* |
| **Expected result** | The cart shows 1 × Grey jacket, subtotal = jacket price |

If the actual result differs from the expected result, the test **fails** and you have found a possible defect.

### 0.2 Manual vs automated

| | Manual testing | Automated testing |
|---|---|---|
| Who runs it | A person | A program |
| Good at | Exploring, judging look and feel, new features | Repeating the same checks quickly and exactly |
| Bad at | Repeating 200 checks every day without mistakes | Noticing things nobody told it to check |
| Cost | Pay every time you run it | Pay once to build, then pay to **maintain** |

Key idea: automation is **not free**. Every automated test is code that must be written, fixed when the site changes, and investigated when it fails.

### 0.3 Test layers (the test pyramid)

```
          /\        UI / end-to-end   — few, slow, fragile, closest to the real user
         /  \
        /----\      API / service     — more, fast, stable
       /      \
      /--------\    Unit              — many, very fast (written by developers)
```

A check at a lower layer is cheaper and more stable. A check at the UI layer is more realistic. You will choose between them in Part 1.

> **Checkpoint 0.** Write one manual test case for "search for *jacket*" with precondition, steps, and expected result. Name one thing automation would do better than you here, and one thing you would do better.

---

## Part 1 — Risk-based automation strategy

### 1.1 🟢 The idea

You cannot test everything — there is never enough time. So you test **where failure would hurt most**.

Everyday example: at an airport, security checks every bag (high impact if missed), but nobody checks whether the café's coffee is hot. Same budget logic.

**Risk = Likelihood × Impact**

- **Likelihood**: how likely is it to break? (complex logic, frequent changes → more likely)
- **Impact**: if it breaks, how bad is it? (money lost, user blocked → very bad)

### 1.2 🟢 Scoring scale

Use 1, 3, or 5 at first (2 and 4 are fine once you are confident).

| Score | Likelihood | Impact |
|---|---|---|
| 1 | Simple, rarely changes | Cosmetic; users barely notice |
| 3 | Some logic, changes sometimes | Feature degraded; a workaround exists |
| 5 | Complex, many inputs, changes often | Money lost, user blocked, wrong data |

| Risk score | Level | What it usually means |
|---|---|---|
| 15–25 | **High** | Test deeply, automate first, run on every change |
| 8–14 | **Medium** | Automate the main paths, run regularly |
| 1–7 | **Low** | Light check or manual exploration |

### 1.3 🟡 Sample requirements (used for the whole unit)

You do not have official requirements, so we use these. They describe what the store **should** do.

| ID | Requirement |
|---|---|
| REQ-01 | A visitor can search products by keyword and see matching results |
| REQ-02 | A visitor can open a product page and see name, price, and availability |
| REQ-03 | A visitor can add an available product to the cart |
| REQ-04 | The cart shows correct line items, quantities, and subtotal |
| REQ-05 | A visitor can change quantity or remove an item, and the subtotal updates |
| REQ-06 | A sold-out product cannot be added to the cart |
| REQ-07 | A visitor can proceed from the cart to checkout |
| REQ-08 | A visitor can sign up and log in |
| REQ-09 | Static pages (About Us, Blog) load and are reachable from navigation |

### 1.4 🟡 Worked example: scoring REQ-04 step by step

Think aloud like this for every requirement:

1. **What could go wrong?** The subtotal is wrong, or a quantity is wrong.
2. **Likelihood?** The cart combines prices × quantities × several products, and themes and discount apps often change it → **4**.
3. **Impact?** A customer is charged the wrong amount, or loses trust and leaves → **5**.
4. **Score** = 4 × 5 = **20 → High**.

### 1.5 🟡 Full risk register

| Req | What could go wrong | L | I | Score | Level |
|---|---|---|---|---|---|
| REQ-04 | Wrong subtotal or quantity in cart | 4 | 5 | 20 | High |
| REQ-05 | Subtotal not updated after edit/remove | 4 | 4 | 16 | High |
| REQ-03 | Add to cart fails or adds the wrong variant | 3 | 5 | 15 | High |
| REQ-07 | Cannot reach checkout | 2 | 5 | 10 | Medium |
| REQ-06 | A sold-out item can be bought | 2 | 5 | 10 | Medium |
| REQ-01 | Search returns wrong or no results | 3 | 3 | 9 | Medium |
| REQ-08 | Cannot sign up or log in | 2 | 4 | 8 | Medium |
| REQ-02 | Wrong price or name shown | 2 | 4 | 8 | Medium |
| REQ-09 | A static page is broken | 1 | 2 | 2 | Low |

Seen as a heat map (requirements placed by their scores):

```
Impact 5 |          REQ-06,07      REQ-03          REQ-04
Impact 4 |          REQ-02,08                      REQ-05
Impact 3 |                         REQ-01
Impact 2 | REQ-09
         +----------------------------------------------------
           L=1       L=2            L=3             L=4
```

Top-right = test first. Bottom-left = test last.

### 1.6 🔴 From risk to an automation decision

Risk tells you what **matters**. It does not yet tell you what to **automate**. Ask four questions:

| Question | Automate when… | Example |
|---|---|---|
| **Risk** | High or Medium | REQ-04 yes, REQ-09 probably not |
| **Repetition** | It must be re-checked on every release | Cart: every release. Sign-up page design: rarely |
| **Stability** | The feature is not redesigned every week | A brand-new page → wait until it settles |
| **Testability** | You can control inputs and see results (Part 2) | Checkout payment → no; we must not pay |

**Is it worth it? A simple return-on-investment check:**

```
Manual cost   = minutes per manual run × runs per year
Automation    = minutes to build + minutes to maintain per year
Automate if     Manual cost  >  Automation cost
```

Example for the "add to cart" check: 5 min manual × 100 runs = 500 min/year. Automation: 120 min build + 120 min maintenance = 240 min/year → worth it. A check run twice a year is usually not.

**A high-risk feature with poor testability is never simply skipped.** Pick one:

1. **Improve testability** — ask developers for a test account or stable `data-testid` attributes.
2. **Test at another layer** — check cart totals through an API instead of the screen.
3. **Keep it manual on purpose** — and record it as a known gap (tag `@manual`) so it stays visible.

### 1.7 🔴 Choose the cheapest layer that still catches the risk

| Layer | Speed | Use it for on this store |
|---|---|---|
| Unit | Fastest | Not available — we do not own the store's code |
| API / JSON | Fast | Product data and cart contents (Shopify stores usually expose `/products.json` and `/cart.js` — verify) |
| UI end-to-end | Slowest | One full user journey per critical requirement |

Advanced habit: prove **one** journey end-to-end through the browser, then cover the many variations (40 products × quantities) at the faster layer.

### 1.8 🔴 Risk changes — keep the register alive

Re-score when:

- A **defect** is found in an area → raise its likelihood.
- A feature is **changed or redesigned** → raise likelihood for a while.
- An area has been **stable for many releases** → you may lower it.
- The **business** changes (a sale season makes checkout even more critical) → raise impact.

Also run tests **by risk**: high-risk on every change, medium nightly, low before a release. Tags make this possible (Part 4).

> **Checkpoint 1.** Score REQ-01 yourself without looking at the table. If your score differs, explain in one sentence why. Then answer: why is REQ-07 only Medium even though its impact is 5?

---

## Part 2 — Testability analysis

### 2.1 🟢 The idea

**Testability** = how easy it is to test something **reliably**.

Everyday example: a car with a dashboard (speed, fuel, warning lights) is easy to check. A car with no dashboard can still be driven, but you only discover a problem when it stops. Software is the same: if you cannot **set it up** and **see what happened**, testing is slow and unreliable.

### 2.2 🟡 Five dimensions, applied to the store

| Dimension | Question to ask | On this store (expected — verify) | What we do about it |
|---|---|---|---|
| **Controllability** | Can I put the system in the state I need? | Partial. No admin access: we cannot create products or change stock | Use existing products; build the cart through the site itself |
| **Observability** | Can I clearly see the result? | Good. Cart, prices, messages are visible; JSON endpoints likely exist | Check the screen for the journey, JSON for exact numbers |
| **Isolation** | Do tests disturb each other? | Good. The cart lives in each browser session | A fresh browser session per scenario |
| **Determinism** | Same input → same result every time? | Medium. It is a shared public site; prices and products can change without notice | Never hard-code prices; read them from the site during the test |
| **Automation access** | Is anything blocking a robot? | Poor for login and checkout: CAPTCHA and bot protection are likely; we must never pay | Stop at "checkout page reached"; keep account flows manual |

### 2.3 🔴 Locators: the testability that decides maintenance cost

A test finds buttons and texts using **locators**. If the locator breaks every time the design changes, the suite becomes expensive. Preferred order (Playwright for Python shown):

| Priority | Locator type | Example | Why |
|---|---|---|---|
| 1 | Role + accessible name | `page.get_by_role("button", name="Add to Cart")` | Matches what a user sees; survives redesigns |
| 2 | Label / visible text | `page.get_by_label("Quantity")` | Readable, fairly stable |
| 3 | Test id | `page.get_by_test_id("cart-subtotal")` | Very stable, but needs developers to add it |
| 4 | CSS / XPath | `page.locator("#AddToCart .btn-primary")` | Last resort; breaks with theme changes |

### 2.4 🔴 Flakiness — the enemy of trust

A **flaky** test fails sometimes for no real reason. Developers then stop trusting failures, and real bugs slip through. Common causes on a site like this:

| Cause | Example | Prevention (you will build these on Day 3) |
|---|---|---|
| Timing | Clicking before the button is ready | Wait for a condition, never `sleep(3)` |
| Shared state | Two tests share one cart | Fresh browser context per scenario |
| Changing data | Price changed overnight | Read values at runtime |
| Third-party interference | Pop-ups, bot checks | Handle or avoid those flows |

### 2.5 🔴 Risk × testability: the decision grid

| | **Good testability** | **Poor testability** |
|---|---|---|
| **High risk** | Automate first (REQ-03, 04, 05) | Improve testability, change layer, or manual-on-purpose (REQ-07 partly) |
| **Low risk** | Small, cheap check (REQ-09) | Leave to exploratory testing |

> **Checkpoint 2.** For REQ-06 (sold-out cannot be added): which dimension is weakest, and what happens to your test if the store restocks the item tomorrow?

---

## Part 3 — BDD principles

### 3.1 🟢 The problem BDD solves

A business person writes: *"The cart must show the right total."*
- The developer builds: total **before** shipping.
- The tester checks: total **including** shipping.
- The customer expects: total **including tax**.

Everyone read the same sentence and understood something different. The bug is in the **conversation**, not the code.

**BDD (Behaviour-Driven Development)** fixes this by agreeing on **concrete examples** *before* building:

> *Given the cart is empty, when I add one Grey jacket at £55, then the subtotal shows £55, and shipping is not included yet.*

Now there is nothing to misunderstand. These examples are then **automated**, so the agreement is checked forever.

Two things BDD is **not**:
- Not a tool. Cucumber, SpecFlow, and `pytest-bdd` only *automate* the examples.
- Not only for testers. The value comes from business, development, and testing agreeing together.

### 3.2 🟢 From test case to Given / When / Then

Take the test case from Part 0 and translate it:

| Test case part | Gherkin keyword | Example |
|---|---|---|
| Precondition | **Given** | Given a visitor with an empty cart |
| Action | **When** | When they add "Grey jacket" to the cart |
| Expected result | **Then** | Then the cart contains 1 "Grey jacket" |

```gherkin
Scenario: Adding a product puts it in the cart
  Given a visitor with an empty cart
  When they add "Grey jacket" to the cart
  Then the cart contains 1 "Grey jacket"
```

That is a real, valid Gherkin scenario. On Day 2 you will make it run.

### 3.3 🟡 All the Gherkin keywords you need

| Keyword | Meaning |
|---|---|
| `Feature` | The capability being described (one per file) |
| `Rule` | One business rule inside the feature; groups its scenarios |
| `Scenario` | One concrete example |
| `Given` / `When` / `Then` | Starting state / the action / the expected outcome |
| `And` / `But` | Continue the previous step type |
| `Background` | `Given` steps shared by every scenario in the file |
| `Scenario Outline` + `Examples` | One scenario run with several rows of data |
| `@tag` | A label for selecting and tracing scenarios |
| `"""` / `\| table \|` | Multi-line text / a table of data inside a step |
| `#` | Comment |

A full example using most of them:

```gherkin
@web
Feature: Shopping cart
  Visitors collect products in a cart before checkout.

  Background:
    Given a visitor with an empty cart

  Rule: The subtotal is the sum of price × quantity

    @REQ-04 @risk-high @smoke
    Scenario: One product
      Given the visitor is viewing the product "Grey jacket"
      When they add the product to the cart
      Then the cart subtotal equals the product price times 1

    @REQ-04 @risk-high @regression
    Scenario Outline: Several of the same product
      Given the visitor is viewing the product "<product>"
      When they add the product to the cart <times> times
      Then the cart subtotal equals the product price times <times>

      Examples:
        | product     | times |
        | Grey jacket | 2     |
        | Noir jacket | 3     |
```

The `Scenario Outline` runs **twice**, once per row in `Examples`, with `<product>` and `<times>` replaced.

### 3.4 🟡 Declarative vs imperative — the most important style rule

**Imperative** (describes clicks — weak):

```gherkin
Scenario: Add to cart
  Given I open "https://sauce-demo.myshopify.com/"
  When I click the "Grey jacket" image
  And I click the button with id "add"
  And I click the link "My Cart"
  Then the element ".cart-item" contains "Grey jacket"
```

**Declarative** (describes behaviour — strong):

```gherkin
Scenario: Adding an available product puts it in the cart
  Given the visitor is viewing the product "Grey jacket"
  When they add the product to the cart
  Then the cart contains 1 "Grey jacket"
```

| | Imperative | Declarative |
|---|---|---|
| Can a business person read it? | Barely | Yes |
| Survives a redesign? | No — ids and links change | Yes |
| Works for web **and** mobile? | No — mentions web elements | Yes — names no UI element |
| Where do the clicks go? | In the scenario | In the code behind the steps (Day 2) |

Quick test: **if the sentence would still be true on a phone app, it is declarative.**

### 3.5 🟡 Six rules for a good scenario

| # | Rule | Bad | Good |
|---|---|---|---|
| 1 | One behaviour, one `When` | When they add a jacket and remove it and search | Split into 3 scenarios |
| 2 | Business language | When I click `#add` | When they add the product to the cart |
| 3 | Independent | Scenario 2 needs the cart left by scenario 1 | Each scenario sets up its own `Given` |
| 4 | Concrete | Given some product | Given the product "Grey jacket" |
| 5 | Short | 15 steps | About 3–6 steps |
| 6 | No volatile hard-coded data | Then the subtotal is £55.00 | Then the subtotal equals the product price times 1 |

### 3.6 🔴 The three BDD practices

| Practice | Who | Activity | Result |
|---|---|---|---|
| **Discovery** | "Three Amigos": business, developer, tester | Talk through examples before building | Shared understanding, rules, questions |
| **Formulation** | Usually tester + business | Write the examples in Gherkin | `.feature` files |
| **Automation** | Tester / developer | Connect each step to code | Executable specification |

Most failed BDD projects skip **Discovery** and only do Automation. They end up with Gherkin that nobody reads — just slower tests.

### 3.7 🔴 Example Mapping (how Discovery works)

Take one requirement and fill four kinds of cards in 25 minutes:

| Card | Colour (traditional) | Meaning |
|---|---|---|
| Story | Yellow | The requirement |
| Rule | Blue | A business rule inside it |
| Example | Green | A concrete case illustrating a rule |
| Question | Red | Something nobody can answer yet |

Worked example for **REQ-05** (change quantity or remove an item):

```
[Story] REQ-05: change quantity or remove an item; the subtotal updates

[Rule] Changing quantity updates the subtotal
   [Example] 1 Grey jacket → set quantity 3 → subtotal = 3 × price
   [Example] 3 Grey jackets → set quantity 1 → subtotal = 1 × price

[Rule] Removing an item removes only that item
   [Example] Grey + Noir in cart → remove Grey → only Noir remains, subtotal = Noir price
   [Example] Only Grey in cart → remove Grey → cart is empty, subtotal = 0

[Rule] Quantity 0 counts as removal
   [Example] 1 Grey jacket → set quantity 0 → item disappears

[Question] Is there a maximum quantity per item?
[Question] What happens if the quantity box gets "-1" or "abc"?
```

How to read the result:
- Each **Rule** becomes a `Rule:` block in the feature file; each **Example** becomes a scenario.
- Many **Questions** → the requirement is not ready to build or automate.
- More than about 4 **Rules** → the requirement is too big; split it.

### 3.8 🔴 When BDD is (and is not) worth it

| Worth it | Not worth it |
|---|---|
| Business rules people misunderstand (prices, discounts, eligibility) | Purely technical checks (a page returns HTTP 200) |
| Several teams or platforms share the same behaviour | One developer, no business readers, simple UI |
| You need living documentation and traceability | Throw-away prototype |

On this course, BDD's strongest value is **traceability** and **cross-platform reuse**, which Part 4 builds.

> **Checkpoint 3.** Rewrite this imperative scenario declaratively: *"Given I go to /search, When I type 'jacket' in input#q and press Enter, Then I see div.product-card elements"*.

---

## Part 4 — Putting it together: the automation strategy 🔴

### 4.1 Traceability through tags

Tags connect every scenario to its requirement and its risk level, so a report can say *"REQ-04: 4 scenarios, all passed"*.

| Tag family | Values | Purpose |
|---|---|---|
| Requirement | `@REQ-01` … `@REQ-09` | Which requirement it proves |
| Risk | `@risk-high`, `@risk-medium`, `@risk-low` | Run order and priority |
| Suite | `@smoke` (minutes, every change), `@regression` (full, nightly) | When it runs |
| Platform | `@web`, `@api`, `@mobile` | Where it runs |
| Status | `@manual` | A known gap that stays visible in reports |

### 4.2 Cross-platform design

Declarative scenarios are what make one specification work on several platforms:

```
            cart.feature  (one set of scenarios, declarative)
                    │
            step definitions  (call a neutral "Store" interface)
          ┌─────────┼──────────┐
     WebStore   ApiStore   MobileStore
    (Unit 1–2)             (Unit 3)
```

| Layer | Shared across platforms? |
|---|---|
| Feature files | Yes |
| Step definitions | Mostly — they only call the interface |
| Store implementations (page objects) | No — one per platform |

### 4.3 Automation scope decision

| Req | Risk | Testability | Decision | Layer | Tags |
|---|---|---|---|---|---|
| REQ-03, 04, 05 | High | Good | Automate first | UI journey + API for variations | `@risk-high @smoke` |
| REQ-06 | Medium | Medium (needs a sold-out product to exist) | Automate; skip with a clear message if none is found | UI | `@risk-medium @regression` |
| REQ-01, 02 | Medium | Good | Automate | UI + API data check | `@risk-medium @regression` |
| REQ-07 | Medium | Partial | Automate up to "checkout page reached", never pay | UI | `@risk-medium @smoke` |
| REQ-08 | Medium | Poor (CAPTCHA) | Manual; revisit if a test account is provided | — | `@manual` |
| REQ-09 | Low | Good | One link-check scenario | UI | `@risk-low` |

### 4.4 Entry and exit criteria

| | Criteria |
|---|---|
| **Entry** (ready to automate) | Requirement has examples; no open red Question cards; site area is stable |
| **Exit** (unit done) | All `@risk-high` scenarios automated and passing; every requirement has ≥ 1 scenario or a `@manual` tag with a reason; zero flaky failures in 3 consecutive runs |

### 4.5 Your one-page strategy template

```
1. Scope & system under test     — what is in/out, which site, which browsers
2. Risk register                 — table from 1.5 (your scores)
3. Testability assessment        — table from 2.2 + mitigations
4. Automation scope decision     — table from 4.3
5. Layers & tools                — pytest-bdd, Playwright, API checks
6. Tag taxonomy & run plan       — which tags run when
7. Entry / exit criteria         — from 4.4
8. Known gaps & residual risk    — what is manual, and why that is acceptable
```

---

## Common newbie mistakes

| Mistake | Why it hurts | Instead |
|---|---|---|
| "Automate everything" | Huge maintenance, slow suite | Automate by risk × testability |
| Scoring every risk High | Nothing is prioritized | Force a spread; justify every 5 |
| Clicks and ids in Gherkin | Breaks on redesign, unreadable | Declarative steps |
| Hard-coded prices | Fails when data changes | Compare with values read at runtime |
| Tests that depend on each other | One failure cascades | Each scenario sets up its own state |
| Hiding manual gaps | False sense of coverage | `@manual` tag + reason in the strategy |

---

## Exercises (your Day 1 output)

**🟢 Level 1**
1. **Verify the site (15 min).** Browse the store and correct anything in this guide that is wrong: product names, which product is sold out, whether sign-up/login shows a CAPTCHA, whether `https://sauce-demo.myshopify.com/products.json` opens in your browser.
2. Write three manual test cases (precondition, steps, expected result) for REQ-01, REQ-03, REQ-06.

**🟡 Level 2**
3. Re-score the risk register. Change at least two scores and justify each in one sentence.
4. Convert your three test cases into **declarative** Gherkin scenarios with tags (`@REQ-xx`, `@risk-*`, `@smoke`/`@regression`, `@web`).

**🔴 Level 3**
5. Do an Example Map for **REQ-06** (sold-out): rules, two examples per rule, questions.
6. Fill the **one-page strategy template** (4.5). This is your Day 1 deliverable.

---

## Self-check (answers below — try first)

1. Checkout (REQ-07) has the highest business impact but is only partly automated. Defend that decision.
2. A teammate wants all 40 cart variations tested through the UI. What do you propose instead?
3. Prices changed overnight and ten scenarios failed. Which scenario rule was broken, and how do you fix the design?
4. Why does a declarative scenario make a cross-platform strategy possible, when an imperative one does not?
5. Is BDD still worth it if no business person ever reads the feature files? Argue both sides.

<details>
<summary><b>Answer guide</b></summary>

1. Impact is 5, but testability is poor: payment must not be completed and bot protection is likely. Automating up to "checkout page reached" covers the part we control; the payment step stays a documented manual check with a stated residual risk. Spending effort on a test that cannot run reliably would reduce trust in the suite.
2. One or two UI journeys prove the screen works end-to-end. The 40 variations check the same calculation, so run them at the API/JSON layer — faster, more stable, same risk coverage.
3. Rule 6 (no volatile hard-coded data). Read the price from the product page during the test and assert *subtotal = price × quantity*.
4. A declarative step names a behaviour ("add the product to the cart"), not a web element. The same step can call a web, API, or mobile implementation behind one interface. An imperative step names `#add`, which only exists on the web page.
5. *For:* traceability by tags, readable reports, a shared vocabulary between testers and developers, reuse across platforms. *Against:* the extra Gherkin layer costs time; without Discovery conversations you lose BDD's main benefit and could write plain pytest tests instead. A strong answer says which benefit you actually rely on.
</details>

## Next: Day 2

How `pytest-bdd` turns these scenarios into running tests: project structure, step definitions, hooks, tags, and reports — built step by step, starting from zero Python testing knowledge.
