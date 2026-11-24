# Unit 5 · Day 19 — Mock Project (1/4): Discovery, Risk and Strategy

| | |
|---|---|
| **Course** | Advanced Automation Test Engineering (ATEST03) — Fast Track |
| **Unit** | Unit 5 — Mock Project Design and Implementation |
| **Session** | Assignment/Lab, part 1 of 4 · **120 min** (of the unit's 480 lab minutes) |
| **Learning outcomes** | **LO1** Evaluate product risk and testability for a cross-platform strategy (B5) · start of **LO9** (design decisions you will defend on Day 22) |
| **Product under test** | Swag Labs — https://www.saucedemo.com (a public demo shop by Sauce Labs) |
| **Code** | `Unit5/unit5-code/swaglabs-mock-project.zip` → `mock-project/` (also in the course repository) |
| **Output today** | Exploration notes per persona · `requirements.toml` · risk register · first `findings.toml` · ADR list |

> **Scope note — no AWS.** The official brief says "integrated AWS automation mock project
> (ECS/Fargate, Device Farm, S3, CloudWatch)". This project keeps every *learning outcome* but
> replaces each AWS part with something you can run without a cloud account: containers on
> GitHub-hosted runners instead of Fargate, browser/device emulation instead of Device Farm,
> CI artifacts with a SHA-256 manifest instead of S3, JSON logs and timing reports instead of
> CloudWatch. Day 21 and `docs/04-execution-and-evidence.md` show the exact mapping, and Day 22
> shows how the same image would move to AWS unchanged.

> **Rules of engagement (third-party site).** Swag Labs belongs to someone else.
> 1. Use only the demo accounts printed on its login page. Never type real personal data.
> 2. No load or stress tests — ever. Single-user timings only.
> 3. Do not try to bypass anything (there is no CAPTCHA here; if one appears, stop).
> 4. Keep parallelism modest (the CI pipeline uses at most 32 browsers for about two minutes).

---

## Plan for today (120 min)

| Time | Block | Level |
|---|---|---|
| 0–15 | 1. What a mock project is, and how it is marked | 🟢 |
| 15–55 | 2. Explore the product, persona by persona (charters) | 🟢→🟡 |
| 55–80 | 3. From observations to requirements and risks | 🟡 |
| 80–105 | 4. Testability assessment → architecture decisions | 🔴 |
| 105–120 | 5. Strategy one-pager, self-check | 🔴 |

---

## 1. 🟢 What a mock project is

A mock project is a **small, complete delivery**: you are the test engineer of a product, and at
the end you hand over working automation **and** the reasoning behind it. Four days, four slices:

| Day | Slice | Main LOs |
|---|---|---|
| 19 | Discovery: product, risks, testability, strategy | LO1, LO9 |
| 20 | Framework and BDD scenarios in Playwright | LO2, LO3, LO5 |
| 21 | Asynchronous behaviour, performance, containers, CI, evidence | LO4, LO6, LO7, LO8 |
| 22 | Topic revision (240 min) + evidence pack and design defense | LO1–LO9 |

How a reviewer reads your project — keep this in mind from the first minute:

1. **Is every test there for a reason?** A test without a requirement and a risk is a cost.
2. **Can a test fail?** A suite that cannot fail proves nothing. You will *show* failures.
3. **Is a result trustworthy?** No flakiness, isolated tests, evidence for every failure.
4. **Can you defend each decision?** "Because the tutorial did it" is not a reason.

---

## 2. 🟢→🟡 Explore the product, persona by persona

### 2.1 The product in five minutes

Open https://www.saucedemo.com. The login page lists six usernames and **one shared password**
(it is printed right there — that is why our code calls it "public demo data", Day 20).

```
Login ─► Products (6 cards, sort menu) ─► Product page
   │            │ Add to cart / Remove        │
   │            ▼                              │
   │         Cart ─► Checkout: Your Information ─► Overview (item total, tax, total) ─► Complete
   │
   └─ Menu: All Items · Dynamic Catalog (Spinner, Lazy Load, Slider) · About · Logout · Reset App State
```

### 2.2 Personas are a gift: a ready-made fault-injection matrix

| Username | What the site says about it | What we will find |
|---|---|---|
| `standard_user` | works | (almost) everything works |
| `locked_out_user` | cannot log in | a clear error message |
| `problem_user` | "has problems" | images, sorting, buttons, product links, form fields |
| `performance_glitch_user` | "is slow" | two specific actions take ~5 s |
| `error_user` | "throws errors" | JavaScript alerts, broken buttons, broken checkout |
| `visual_user` | "looks wrong" | random prices (!), a wrong image, layout shifts |

**Key insight (write it in your notes):** the same shop with six behaviours means one test suite
can be run six times, and the differences *are* the findings. A scenario that passes for
`standard_user` and fails for `problem_user` is proven to be able to fail. That is how we will
show, on Day 22, that our tests have teeth.

### 2.3 Exploratory charters

A **charter** is a one-line mission with a time box. It keeps exploration focused and makes it
reviewable. Use this template for each persona:

```
Charter:  Explore <area> as <persona> with <resources/technique> to discover <information>.
Time box: 8 minutes.
Notes:    what I did · what I saw · questions · possible defects (with exact steps)
```

Suggested charters (one per persona, 8 minutes each):

| # | Charter |
|---|---|
| C1 | Explore the **whole purchase** as `standard_user` with DevTools open, to learn the pages, the data the app stores, and the expected values (prices, tax). |
| C2 | Explore **catalogue and cart** as `problem_user`, adding and removing **every** product, to discover which buttons, links and images misbehave. |
| C3 | Explore **sorting and checkout** as `error_user`, to discover errors and where the journey breaks. |
| C4 | Explore **prices and images** as `visual_user`, comparing the card, the product page, the cart and the overview. |
| C5 | Explore **timing** as `performance_glitch_user` with the DevTools Network panel, to find which actions are slow and whether the network is involved. |

### 2.4 What to look at in DevTools (testability evidence)

| Look at | Where | What we learned |
|---|---|---|
| Elements | right-click → Inspect | almost every element has a `data-test` attribute (`data-test="add-to-cart-sauce-labs-backpack"`) |
| Application → Cookies | after login | one cookie `session-username` = the persona name: the whole session |
| Application → Local Storage | after adding to cart | `cart-contents` = `[4,0]`: the cart is a list of product ids |
| Network | while logging in / sorting | no API calls: the catalogue is built into the app; errors are reported to a third-party tracker (`*.backtrace.io`) |
| Console | as `error_user` | JavaScript errors when buttons are clicked |

These five facts decide half of the architecture (section 4). Write them down with screenshots.

### 2.5 What our exploration found (compare with yours)

| Persona | Observation | Reproducible? |
|---|---|---|
| problem_user | all card images are the same dog picture | yes |
| problem_user | sorting does nothing | yes |
| problem_user, error_user | *Add to cart* does nothing for Bolt T-Shirt, Fleece Jacket, Test.allTheThings() T-Shirt | yes — but **only** for those three: a test that adds only the backpack never sees it |
| problem_user, error_user | *Remove* on the catalogue does nothing (on the cart page it works) | yes |
| problem_user | clicking the Backpack card opens the Fleece Jacket (`?id=5` instead of 4) | yes |
| problem_user | typing a last name changes the **first** name field | yes |
| error_user | sorting shows `alert("Sorting is broken! …")` | yes |
| error_user | Last Name stays empty; *Finish* does nothing | yes |
| visual_user | catalogue prices are **random on every load**; cart charges the real price | yes |
| visual_user | the Backpack card shows the wrong picture | yes |
| performance_glitch_user | login ~5 s, sorting ~5 s, everything else normal | yes |
| all | after *Reset App State* the cards still say *Remove* until a reload | yes |
| standard_user | once, after logout, *Back* showed the products page again | **no** — 12 targeted retries never reproduced it |

> 🔴 **Reproducibility rule.** A finding goes into the register only with steps that reproduce
> it on demand. The last row was *seen* once and never again in 12 controlled attempts (form
> login and cookie login, with and without reload and reset, two personas). We keep a scenario
> that would catch it (a regression guard) but we do **not** register it as a known defect —
> a defect that comes and goes would make the suite flaky and teach the team to ignore red.
> `docs/03-findings.md` → *Retired observations* records the decision.

---

## 3. 🟡 From observations to requirements and risks

### 3.1 Requirements: what must be true

Exploration tells you what the product **does**; requirements say what it **must do**. Write
them as short, testable statements with an id. Our registry has 16:

```toml
# mock-project/requirements.toml (excerpt)
[REQ-SL-07]
title = "Any product can be added to and removed from the cart"
risk = "high"

[REQ-SL-10]
title = "The order overview shows the right subtotal, 8 % tax and total"
risk = "high"

[REQ-SL-13]
title = "Dynamic catalogue content loads asynchronously and settles correctly"
risk = "medium"
```

Notice the wording of REQ-SL-07: "**Any** product". The exploration showed that "the first
product" works for every persona; writing "a product" would let a test pass that misses SL-04.
**Requirements written after exploration are sharper than requirements written before it.**

### 3.2 Risk = likelihood × impact

| Score band | Range | Meaning for the suite |
|---|---|---|
| high | 15–25 | `@smoke` candidates; covered on every browser; release-blocking |
| medium | 8–14 | `@regression`; covered on the main browser |
| low | 1–7 | `@regression` or manual |

Score a risk by asking two questions with evidence, not gut feeling:

- **Likelihood (1–5):** how complex is it, how often does it change, did exploration find
  defects here? (Cart: 4 — three personas break it.)
- **Impact (1–5):** what happens to the customer or the business? (Wrong amount charged: 5.)

| Risk | L | I | Score | Requirement |
|---|---|---|---|---|
| Wrong items or amounts in the cart | 4 | 5 | 20 high | REQ-SL-07 |
| Order with wrong/missing customer data | 4 | 4 | 16 high | REQ-SL-09 |
| Wrong amount charged | 3 | 5 | 15 high | REQ-SL-10 |
| Wrong price or picture shown | 4 | 3 | 12 medium | REQ-SL-04 |
| Slow interactions | 3 | 4 | 12 medium | REQ-SL-14 |
| Reset leaves stale state | 2 | 2 | 4 low | REQ-SL-12 |

The full register (14 risks) is in `docs/01-strategy.md`. The **band** goes into
`requirements.toml`, and from Day 20 on the framework refuses any scenario whose `@risk-*` tag
does not equal the band of its requirements. The risk analysis is therefore not a document that
rots in a folder: it is **executable**.

### 3.3 Scope — and saying "no" with a reason

| Out of scope | Reason |
|---|---|
| Load and stress tests | not our system; load on a third party is abuse (Unit 4 did load on our own sandbox) |
| Visual pixel comparison (REQ-SL-16) | needs approved baselines per browser × viewport and a review workflow; without them it is noise → `@manual` |
| Payment | there is none; real payment data is never entered anywhere |
| Native app | Swag Labs is a web app; mobile = phone-sized browser (native Appium was Unit 3) |
| Security testing of the site | not authorised on a third-party site; we secure **our pipeline** instead |

A senior engineer's scope section is as much about what is *not* tested, and why, as about what
is. Each "no" is a decision you will defend on Day 22.

### 3.4 Findings register — first draft

Each reproducible defect becomes a register entry. The fields are chosen for what the framework
will do with them on Day 20:

```toml
# mock-project/findings.toml (excerpt)
[areas]
add-any-product = "Every product (not only the first few) can be added from the catalogue"
sorting = "Choosing a sort order re-orders the catalogue without errors"

[SL-04]
title = "Add to cart does nothing for three of the six products"
personas = ["problem_user", "error_user"]
area = "add-any-product"
requirement = "REQ-SL-07"
severity = "critical"
```

- **personas** — who shows it. **area** — *which behaviour* it breaks (not which test!).
- Scenarios will declare the behaviours they depend on with `@area-<name>` tags.
- When the suite runs as an affected persona, every scenario with that area must fail with an
  assertion — a **strict expected failure**. Day 20 builds this.

Why "area" and not "test name"? Because tests get renamed and split, but the behaviour they
depend on does not. The join "persona × area" stays correct when the suite grows.

---

## 4. 🔴 Testability assessment → architecture decisions

A testability assessment asks: *what makes this product easy or hard to test automatically,
and what will we do about it?* Each row ends in a decision.

| Aspect | Observation | Decision (ADR) |
|---|---|---|
| **Control** — can we put the system into a state quickly? | Session = one cookie; cart = `localStorage["cart-contents"]` | Arrange through state, act through the UI (ADR-4). Log in by setting the cookie; seed the cart in storage. Guarded by a **contract scenario** that proves the login form sets exactly that cookie. |
| **Observation** — can we see what happened? | Only the browser: DOM, storage, network, console | A browser monitor that records requests, console errors and dialogs; evidence on every failed step (Day 20). |
| **Oracles** — how do we know the right answer? | No API with the truth | A **recorded reference catalogue** (`swaglabs/data/catalogue.json`) and computed expectations: sort orders, 8 % tax with `Decimal` rounding (ADR-5). |
| **Determinism** | `visual_user` prices are random; the slider rotates by itself; lazy tiles load when visible | Assert deterministic properties: the *order of names* after sorting, the slider's *invariant* and *history*, tile *numbering*. Never a single racy snapshot. |
| **Locators** | stable `data-test` on nearly everything | Page objects use `data-test`; ARIA roles where they carry meaning (`role=button[name='Open Menu']`, the spinner's `role=status`). |
| **Isolation** | Third-party error tracker, Google Fonts | Network allow-list: only the shop and its fonts (Day 20). |
| **Variability** | six personas, three browser engines, phones | Persona as a **run dimension** (ADR-2): one persona per run, the CI matrix runs them in parallel. |

### 4.1 Why personas are a run dimension, not a scenario parameter (ADR-2)

Option A — every scenario is an outline over the five personas:

```gherkin
Scenario Outline: Every product can be added
  Given I am logged in as "<persona>"
  ...
  Examples:
    | persona                 |
    | standard_user           |
    | problem_user            |   # expected to fail - how do we say that here?
```

Option B — `pytest --persona problem_user` runs the **whole** suite as one persona, and the
findings register decides what is expected to fail.

| | A: outline | B: run dimension |
|---|---|---|
| Scenario text | mixes "what must work" with "who is broken" | only "what must work" |
| Expected failures | per example row, hand-maintained in every feature | one register, joined by area |
| Parallelism | inside one job | one CI job per persona, side by side |
| Adding a persona | edit every outline | one matrix line |

We chose B. The price: the release view needs to *merge* the runs — a small tool on Day 21
(`python -m swaglabs.matrix`).

### 4.2 Strict expected failures — the semantics we commit to

| Outcome when run as an affected persona | Meaning | Run |
|---|---|---|
| fails with `AssertionError` | the defect is still there | green; matrix says **KNOWN DEFECT** |
| passes | the defect was fixed (or the test is wrong) | **red** (`XPASS(strict)`) → update the register |
| fails with anything else (timeout, our own bug) | a *different* problem | **red** |

Why not `skip`? A skip hides the defect and never notices the fix. Why not a plain failure?
A build that is always red trains people to stop looking. Strict xfail is the only option that
keeps both information and attention.

### 4.3 Cross-platform strategy

| Dimension | Values | Where |
|---|---|---|
| Persona | 5 runnable personas | CI matrix, Chromium |
| Browser engine | Chromium, Firefox, WebKit | CI matrix, `standard_user` |
| Device | Pixel 7 emulation; phone-sized touch context for `@phone` scenarios | CI matrix + every run |
| Test level | unit/plugin tests (no browser) → BDD scenarios → merged quality matrix | every push |

Why not every persona on every browser (5 × 3 = 15 jobs)? The personas inject **application**
faults, which do not depend on the browser engine. Browser coverage matters for the behaviour
that *should* work — that is `standard_user`. 8 jobs give the same information as 15 at about
half the cost. (A panel question on Day 22.)

---

## 5. 🔴 The strategy one-pager

Write a one-page strategy (ours: `docs/01-strategy.md`). Required sections:

1. Product and context (who owns it; what we can and cannot see)
2. Scope and out-of-scope **with reasons**
3. Risk register (L, I, score, requirement, mitigation)
4. Testability assessment with decisions
5. Approach: levels, cross-platform matrix, selection (`@smoke`/`@regression`), known-defect policy
6. Entry and exit criteria
7. How each learning outcome is met

**Exit criteria example (release view):** no FAIL in any run; every high-risk requirement PASS
for `standard_user` on all three browsers; every KNOWN DEFECT has an owner and a decision.

---

## Lab tasks — Day 19

| # | Task | Done when |
|---|---|---|
| L19.1 | Run charters C1–C5 (8 min each). Record notes, DevTools screenshots of the cookie and `cart-contents`. | Five charter notes with exact steps for every suspected defect |
| L19.2 | Retry every suspected defect at least 3 times, from a fresh browser. | Each observation marked reproducible / not reproducible |
| L19.3 | Write `requirements.toml` (≥ 12 requirements, with risk band). | Each requirement is one testable sentence |
| L19.4 | Write the risk register (L, I, score, mitigation). | Every requirement's band follows from a scored risk |
| L19.5 | Draft `findings.toml`: areas + one entry per reproducible defect. | Every entry has personas, area, requirement, severity |
| L19.6 | List your ADRs (title + one-line decision): at least personas, oracle, state set-up, strict xfail, container base, CI platform. | Six ADR stubs |
| L19.7 | Write the strategy one-pager. | Seven sections present |

**Check your work against ours** in `mock-project/requirements.toml`, `findings.toml` and
`docs/01-strategy.md` — differences are fine if you can argue them.

---

## Self-check

1. Why is "A product can be added to the cart" a weaker requirement than "Any product can be added"?
2. Give two reasons not to register a defect you saw only once.
3. What does a findings entry's *area* refer to, and why not to a test name?
4. A strict expected failure passes. What happened, and what must you do?
5. Why do we not run all five personas on all three browsers?
6. Which two facts found in DevTools allow a fast, isolated test set-up, and what guards that shortcut?

<details>
<summary>Answers</summary>

1. Exploration showed that the first products work for every persona while three others fail for two personas. "A product" is satisfied by the backpack alone, so a test written from it would miss SL-04. "Any" forces a scenario that adds every product.
2. A defect that does not reproduce makes its scenario flaky (sometimes XPASS → red, sometimes XFAIL), and flaky red teaches people to ignore red. It also cannot be fixed or verified by a developer without steps. Keep a regression guard instead.
3. A behaviour of the product ("every product can be added"). Tests are renamed, split and merged; the behaviour they depend on stays. The framework joins persona × area at collection time.
4. The defect is gone (fixed, or the site changed) — or the test no longer exercises the behaviour. The run goes red on purpose: investigate, then update `findings.toml` (remove the persona or the finding) and the findings report.
5. Personas inject application faults that do not depend on the browser engine. Browser coverage is needed for behaviour that should work (standard_user). 8 jobs give the same information as 15 at about half the cost.
6. The session is one cookie (`session-username`) and the cart is `localStorage["cart-contents"]`. A contract scenario proves the login form sets exactly that cookie, so the shortcut cannot silently drift from reality.
</details>

---

## Verification log

| Check | Result |
|---|---|
| Persona behaviours in section 2.5 | Re-checked with scripted Playwright sessions on 2026-11-24: every "yes" row reproduced; the Back-after-logout row did not reproduce in 12 attempts |
| DevTools facts (cookie, `cart-contents`, `data-test`, third-party tracker) | Confirmed by script: cookie `session-username`, `cart-contents` = `[4,2]` after adding Backpack and Onesie, requests to `events.backtrace.io` / `submit.backtrace.io` |
| `requirements.toml`, `findings.toml` | Loaded and validated by the project's unit tests (`tests/unit/test_registers.py`, `test_rules.py`) |
| Tax example | 8 % of $29.99 = $2.3992 → $2.40; total $32.39 — matches the live overview |
