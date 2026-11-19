# Unit 2 · Day 5 — Playwright Architecture, Browser Contexts, Locators, Fixtures, Assertions, Isolation

| | |
|---|---|
| **Course** | Advanced Automation Test Engineering (ATEST03) — Fast Track |
| **Unit** | Unit 2 — Playwright End-to-End Automation |
| **Learning outcome** | **LO3** — Build reliable Playwright suites using fixtures, isolation, tracing, network control, and parallel execution (Bloom **B3: Apply**) |
| **Format** | Concept/Lecture · Virtual · 120 minutes · **no code to produce** |
| **System used in examples** | https://sauce-demo.myshopify.com/ and the Unit 1 framework |
| **Output of the day** | Understanding of the six concepts, and your one-page **Playwright test design notes** (end of this document) |

Code appears only as short illustrations (one to three lines) where the syntax *is* the concept. Writing code is the job of Day 7 (lab).

> **How the facts here were checked.** Every behaviour described in this lecture — what Playwright waits for, what a locator matches, what an option changes — was confirmed by running it with Playwright 1.63 / pytest-playwright 0.10 while preparing the course. Part 8 lists four results that surprised us.

---

## How to use this lecture

| Badge | Level | After this level you can… |
|---|---|---|
| 🟢 | **Foundation** | Explain browser → context → page, read a role-based locator, and say why `expect` is used |
| 🟡 | **Practitioner** | Choose locators, waits, and assertions that do not flake; configure contexts and fixtures |
| 🔴 | **Senior** | Reason about what Playwright waits for and what it cannot, and design isolation that survives parallel runs |

### Lecture plan (120 min)

| Time | Part |
|---|---|
| 0–10 | Part 0 — From Unit 1 to Unit 2 |
| 10–30 | Part 1 — Architecture |
| 30–50 | Part 2 — Browser contexts |
| 50–75 | Part 3 — Locators |
| 75–90 | Part 4 — Actions and automatic waiting |
| 90–105 | Part 5 — Assertions |
| 105–115 | Part 6 — Fixtures · Part 7 — Isolation |
| 115–120 | Part 8 — Lessons and the stability checklist |

---

## Glossary

| Term | Meaning | Vietnamese |
|---|---|---|
| Driver | The Node.js process Playwright's Python library talks to; it controls the browsers | Tiến trình điều khiển |
| Browser | One running browser program (Chromium, Firefox, WebKit) | Trình duyệt |
| Browser context | An isolated, incognito-like profile inside a browser: own cookies, storage, cache | Ngữ cảnh trình duyệt |
| Page | One tab in a context | Trang / tab |
| Locator | A recipe to find elements, evaluated again every time it is used | Bộ định vị |
| Accessible name | The name assistive technology announces for an element (from its text, label, or `aria-label`) | Tên truy cập |
| Strict mode | An action needs exactly one matching element | Chế độ nghiêm ngặt |
| Actionability | Checks made before acting: visible, stable, enabled, receives events… | Khả năng thao tác |
| Web-first assertion | `expect(...)`: retries until the condition holds or times out | Khẳng định có chờ |
| Fixture | A pytest function that prepares (and cleans up) what a test needs | Fixture |
| Fixture scope | How long a fixture's value lives: function, module, session | Phạm vi fixture |
| Factory fixture | A fixture that returns a function, so a test can create several objects | Fixture nhà máy |
| Storage state | Cookies and localStorage saved to a file, to start a context already "logged in" | Trạng thái lưu trữ |
| Device emulation | A context that imitates a phone: size, user agent, touch | Giả lập thiết bị |
| Flaky test | A test that passes and fails without any code change | Test chập chờn |

---

## Part 0 — From Unit 1 to Unit 2 🟢

### 0.1 Two kinds of test, one set of page objects

| | Unit 1: BDD scenarios | Unit 2: Playwright tests |
|---|---|---|
| Written in | Gherkin + step definitions | Plain Python + pytest |
| Talks to | The `Store` port | Page objects, or Playwright directly |
| Best for | Business behaviour, traceability to requirements | Technical end-to-end checks: page contracts, browsers, network control, timing |

Both use the **same page objects**, so when the shop changes, a locator is fixed in one place for both.

### 0.2 The six concepts of today, in one picture

```
            ┌────────────── fixtures (Part 6) prepare and clean up ──────────────┐
            │                                                                     │
 Browser ──▶ Context (Part 2) ──▶ Page ──▶ Locator (Part 3) ──▶ Action (Part 4) ──▶ Assertion (Part 5)
 (Part 1)    one per test                   "which element?"     "do it, safely"     "is it right?"
            │                                                                     │
            └──────────── isolation (Part 7): nothing leaks between tests ─────────┘
```

---

## Part 1 — Architecture 🟢 → 🔴

### 1.1 🟢 Three processes

```
┌──────────────────┐   pipe    ┌──────────────────────┐  browser protocol   ┌──────────────┐
│ your pytest test │ ────────▶ │ Playwright driver    │ ──────────────────▶ │ Chromium /   │
│ (Python library) │ ◀──────── │ (Node.js, bundled)   │ ◀────────────────── │ Firefox /    │
└──────────────────┘           └──────────────────────┘                     │ WebKit       │
                                                                             └──────────────┘
```

| Piece | Comes from | Key point |
|---|---|---|
| Python library | `pip install playwright` | Your code; every call is a message to the driver |
| Driver (Node.js) | Bundled in the same package | Translates commands and controls the browsers |
| Browsers | `playwright install chromium` | Built for **that exact Playwright version** — upgrade one without the other and the browser is "not found". Pin the version |

Everyday picture: you (the test) give instructions to an interpreter (the driver), who speaks each browser's own language.

### 1.2 🟡 The object tree

```
Playwright
└── BrowserType (chromium | firefox | webkit)
    └── Browser                       expensive: start once per test session
        └── BrowserContext            cheap: one per test — the isolation unit
            └── Page                  a tab
                ├── Frame             the page and its iframes
                └── Locator           a recipe to find elements, evaluated on use
```

**The cost model** explains the whole fixture design (Part 6): starting a browser takes hundreds of milliseconds; creating a context takes a few. So: **one browser per session, one context per test**.

### 1.3 🔴 What really happens on `click()`

1. **Resolve** the locator against the page as it is *now*.
2. **Strict check:** exactly one element, or an error.
3. **Actionability checks**, retried until they pass or time out: attached, visible, stable (not moving), enabled, and **receives events** (nothing on top of it).
4. Scroll into view and click in the middle.
5. If the click starts a navigation, wait for it to begin.

This built-in waiting is why Playwright is less flaky than tools without it. It is not magic: it waits for **the element** to be usable, not for **your application's business work** (for example, the server finishing saving the cart). Part 4 shows the difference.

### 1.4 🔴 Not everything goes through the browser

`page.request` (calling an API from a test) is performed by the **driver**, not by the browser. In this course's test environment, the browser could reach the shop while `page.request` could not, because they use different network paths. That is why the Unit 1 framework calls the shop's JSON endpoints *from inside the page*: same network, same cookies as the user. When something works in the browser but not in an API call, ask **which process made the call**.

> **Checkpoint 1.** Why one browser per session but one context per test?

---

## Part 2 — Browser contexts 🟢 → 🔴

### 2.1 🟢 A context is an incognito window

Two contexts in the same browser share **nothing**: no cookies, no localStorage, no cache, no logged-in session.

On the shop: Alice adds a jacket in her context; Bob, in another context of the same browser, opens the cart and sees it empty. Each test gets a new context, so **every test starts with an empty cart without any clean-up code** — the reason the Unit 1 framework never needed to "clear the cart".

### 2.2 🟡 What a context can pretend to be

| Option | Example value | Use |
|---|---|---|
| `base_url` | `https://sauce-demo.myshopify.com` | Write `goto("/cart")` instead of full URLs |
| `viewport` | 390 × 844 | Responsive layouts |
| `locale` | `en-GB` | Language, number and date formats |
| `timezone_id` | `Europe/London` | Dates and times on the page |
| `geolocation` + `permissions` | London, `["geolocation"]` | "Stores near me" features |
| `color_scheme` | `dark` | Dark mode |
| `storage_state` | `state.json` | Start already logged in (§2.4) |
| `extra_http_headers` | `X-Test-Run: nightly` | Mark test traffic for the server team |
| `offline` | `True` | Offline behaviour |
| Device descriptor | "iPhone 13" | Size + user agent + touch + mobile mode |

**Pin what your results depend on.** A British shop tested from a Vietnamese laptop and from a US cloud runner would format dates and numbers differently. A senior setup fixes `locale` and `timezone_id` for every test once (pytest-playwright's `browser_context_args` fixture), and lets a single test override them when it is *about* another locale:

```python
@pytest.mark.browser_context_args(locale="vi-VN", timezone_id="Asia/Ho_Chi_Minh")
```

### 2.3 🟡 Device emulation — useful, but not a phone

A context created from `playwright.devices["iPhone 13"]` has the iPhone's screen size, user agent, and touch support. It is still a desktop browser engine: real devices are Unit 3 (Appium). Use emulation for **layout and responsive behaviour**, not for device-specific bugs.

### 2.4 🔴 Storage state: log in once, reuse safely

A context's cookies and localStorage can be **saved to a file** and **loaded into a new context**. On the shop, a cart saved this way reappears in a brand-new context.

The pattern for sites with login:

```
session fixture:  log in once ──▶ save state.json
every test:       NEW context from state.json ──▶ already logged in, still isolated
```

Each test still gets its *own* context (isolation kept) but skips the slow, CAPTCHA-prone login. Compare with Part 7's anti-pattern: *sharing one context* also "remembers the login", but every test then changes the same state.

### 2.5 🔴 Several users in one test

Some behaviours need two people at once: "Bob does not see Alice's cart", "an admin's change appears for a customer". pytest-playwright's `new_context` fixture creates as many contexts as a test needs, and closes (and records evidence for) all of them afterwards. The Unit 1 framework wraps it as a factory, so a test reads `alice, bob = new_shop(), new_shop()`.

> **Checkpoint 2.** Storage state and a shared context both "remember" a session. Why is one good practice and the other an anti-pattern?

---

## Part 3 — Locators 🟢 → 🔴

### 3.1 🟢 The priority order, with reasons

| Priority | Locator | Why |
|---|---|---|
| 1 | `get_by_role(role, name=...)` | Matches what users and screen readers perceive; survives redesigns |
| 2 | `get_by_label`, `get_by_placeholder`, `get_by_text`, `get_by_alt_text`, `get_by_title` | Visible and user-facing |
| 3 | `get_by_test_id` | A stable contract with developers (`data-testid`) |
| 4 | CSS / XPath | Last resort — and only inside a small, scoped area |

```python
page.get_by_role("button", name="Add to Cart")
```

### 3.2 🟡 The accessible name is not always the visible text

A button showing only "×" but marked `aria-label="Close dialog"` is found by `name="Close dialog"`, **not** by `name="×"`. The shop's cart remove link is the opposite case: its name really is "x", which says nothing — a testability and accessibility defect (Day 3).

How to see names the way Playwright does: the accessibility snapshot (Day 3, Part 2) or the Inspector's "Pick locator" button (`PWDEBUG=1`).

### 3.3 🟡 Three matching rules that surprise beginners

| Rule | Example | Consequence |
|---|---|---|
| Names match **substrings** by default | `name="Add"` also matches "Add to Cart" | Use `exact=True` when a shorter name is contained in a longer one |
| **Strict mode** for actions | Clicking a locator that matches 2 buttons | Error "strict mode violation" — Playwright refuses to guess. This is a feature |
| Role locators ignore **hidden** elements; CSS does not | The shop's hidden mini-cart duplicates every cart row | Role locators see 1 button; CSS sees 2 and trips strict mode |

### 3.4 🟡 Labels only work when they are linked

`get_by_label("Email address")` finds an input only if the `<label>` is linked to it (`for=` / wrapping). The shop's registration form has unlinked labels **and** duplicated ids, so its page object had to fall back to the inputs' `name` attributes — and the defect was reported. A locator that is hard to write is often a bug report waiting to be filed.

### 3.5 🔴 Scope, filter, chain

The professional way to reach "the button of *this* product":

```
all articles ──filter(has = heading "Noir jacket")──▶ one card ──get_by_role("button")──▶ its button
```

| Tool | Keeps… |
|---|---|
| `.filter(has=…)` | elements that contain a match |
| `.filter(has_not=…)` | elements that do not contain a match |
| `.filter(has_text=…)` | elements containing a text |
| `.filter(visible=True)` | visible elements only |
| `outer.get_by_role(…)` | searches inside `outer` only (chaining) |
| `.first`, `.nth(i)` | by position — fragile; use only when order **is** the behaviour |

This is exactly how the Unit 1 cart page object finds the row of one product and then its unlabeled quantity box: a weak locator made safe by a tiny search area.

### 3.6 🔴 Locators are lazy; `or_` needs care

- A locator is a **recipe**, not an element. It is evaluated each time it is used, so it never goes "stale" after a reload, and it can be created before the element exists.
- `a.or_(b)` matches whichever appears ("Saved" or "Error"). If **both** can be visible together, an action on it is a strict-mode violation — Day 3 hit this on the empty cart page (heading *and* empty message).

> **Checkpoint 3.** Describe, in words, a locator for "the Add to Cart button of the product priced £60.00" that uses no CSS.

---

## Part 4 — Actions and automatic waiting 🟡 → 🔴

### 4.1 🟡 What each action waits for

| Action | Waits until the element is… |
|---|---|
| `click`, `dblclick`, `tap` | attached, visible, stable, **receives events**, enabled |
| `hover` | attached, visible, stable, receives events |
| `fill`, `clear` | attached, visible, enabled, **editable** |
| `check`, `uncheck` | attached, visible, stable, receives events, enabled |
| `select_option` | attached, visible, enabled |
| `inner_text`, `input_value`, `count`, `is_visible` | **does not wait for a value** — reads it once |

### 4.2 🟡 Reading a timeout error

When an action times out, the error's **call log** names the check that failed:

| Message in the log | Meaning |
|---|---|
| `element is not visible` | Hidden, zero size, or off-screen |
| `element is not enabled` | Disabled — often waiting for user input first |
| `element is not stable` | Still animating |
| `<div id="overlay"> intercepts pointer events` | Something is on top (loading screen, cookie banner, modal) |
| `strict mode violation` | Your locator matches several elements |

That line is usually the whole diagnosis. Read it before changing anything.

### 4.3 🔴 `force=True` turns a real problem into a silent pass

`force=True` skips the actionability checks. On a disabled "Sold Out" button, a forced click raises **no error and does nothing** — a test could "click" a button no user can use and pass while the feature is broken. Treat `force=True` as a review finding unless a comment proves it is needed.

### 4.4 🔴 What automatic waiting cannot know

Playwright waits for **elements**. It cannot know that your application is still saving, recalculating, or loading data. Day 3's Add to Cart proved it: the button was clickable again immediately, while the server had not finished — and a test that waited for "the network to go quiet" read the cart too early.

| Wait for… | Tool |
|---|---|
| A server's answer | `expect_response(...)` around the action |
| A navigation | `wait_for_url(...)` |
| A visible outcome | `expect(locator).to_have_text(...)` and friends |
| **Never** | `time.sleep`, `wait_for_timeout` — too long on fast days, too short on slow days |

### 4.5 🟡 Timeouts

| Timeout | Default | Advice |
|---|---|---|
| Actions (`click`, `fill`…) | 30 s | The Unit 1 framework uses 15 s; one global value, changed only with a reason |
| Navigation (`goto`, `wait_for_url`) | same as actions | — |
| Assertions (`expect`) | 5 s | Raise per assertion when a step is known to be slow |

A **short** timeout on one call is fine for proving that something does *not* happen. A **long** global timeout hides slowness and makes failures take minutes.

---

## Part 5 — Assertions 🟢 → 🔴

### 5.1 🟢 `assert` takes a photo; `expect` watches

| | `assert locator.inner_text() == "Saved"` | `expect(locator).to_have_text("Saved")` |
|---|---|---|
| Reads | once | again and again, up to 5 s |
| If the text is still "Saving…" | fails | waits until "Saved" |
| Result | flaky | stable |

**Rule:** anything on the page is checked with `expect`. Plain `assert` is for values that can no longer change — a returned object, a parsed JSON, a total you already read into a `Money`.

### 5.2 🟡 The assertions you will use most

| Category | Assertions |
|---|---|
| Text | `to_have_text` (whole text), `to_contain_text` (part); both accept regular expressions |
| State | `to_be_visible` / `to_be_hidden`, `to_be_enabled` / `to_be_disabled`, `to_be_checked`, `to_be_editable`, `to_be_focused` |
| Form values | `to_have_value`, `to_have_values` |
| Attributes | `to_have_attribute`, `to_have_class`, `to_have_id`, `to_have_css` |
| Lists | `to_have_count` |
| Page | `expect(page).to_have_url(...)`, `to_have_title(...)` |
| API | `expect(response).to_be_ok()` |
| Negation | `not_to_…` — **waits** for the negative state |

### 5.3 🔴 Three traps

| Trap | Why it fails | Instead |
|---|---|---|
| `assert not locator.is_visible()` | Checks once; passes even if the element appears 100 ms later | `expect(locator).to_be_hidden()` |
| A hard-coded value that the site may change (a price, a tax line) | Fails when the data changes, not when the feature breaks | Compare with data read at runtime, or check a rule (Part 8) |
| No message on an important assertion | "expected 1, got 0" says nothing about the business meaning | `expect(cart, "cart should hold one item").to_have_text("1")` |

### 5.4 🔴 Several facts, one report

Sometimes one failure should not hide the others: a page shows five facts and you want to know **all** that are wrong. Two ways:

| Way | How | Use for |
|---|---|---|
| Soft assertions | `expect.soft(locator).to_have_text(...)` — the test continues; at the end it fails once, listing every failed check (needs pytest-playwright 0.7.3 or newer) | Several **page** facts checked in one place |
| Collect and assert once | Gather mismatches into a list, then one `assert` with all of them — as the Unit 1 cart check compares quantities, total, and header count | Facts already read into **domain objects** |

Checked with Playwright 1.63 and pytest-playwright 0.10: a test with two failing `expect.soft` checks ran to its last line, then failed with both errors reported together.

Use soft assertions for **checks**, never for **preconditions**: if "the cart page opened" fails, every later check is noise.

*(Correction: an earlier version of this lecture said Python Playwright had no soft assertions. That was wrong; it was found while preparing Day 10.)*

> **Checkpoint 5.** Which can flake: (a) `assert page.title() == "About"` right after clicking a link; (b) `expect(page).to_have_title("About")`; (c) `assert cart.total == expected` where `cart` was already read into an object?

---

## Part 6 — Fixtures 🟡 → 🔴

### 6.1 🟡 What pytest-playwright provides

| Fixture | Scope | What it is |
|---|---|---|
| `playwright` | session | The Playwright instance |
| `browser` | session | One launched browser for the whole run |
| `browser_type_launch_args` | session | Launch options: headed, slow motion, channel |
| `browser_context_args` | session | Default options for **every** context — override it to pin locale, time zone, viewport |
| `new_context` | function | **Factory**: extra contexts; all closed and recorded after the test |
| `context` | function | One fresh context per test |
| `page` | function | One fresh page in that context |
| `base_url` | session | From configuration or `--base-url` |

Command-line options you will use: `--browser chromium|firefox|webkit` (repeatable), `--headed`, `--slowmo 300`, `--device "iPhone 13"`, `--tracing`, `--video`, `--screenshot`, `--output`.

### 6.2 🟡 What the Unit 1 framework adds on top

| Fixture | Scope | Purpose |
|---|---|---|
| `settings` | session | Options and environment variables, read once |
| `live_catalogue` | session | Product data read once per run |
| `shop` | function | Every page object for the test's page |
| `new_shop` | function | Factory: extra isolated shoppers |
| `store` | function | The BDD port (fake or web) |

### 6.3 🔴 Choosing a scope

| Question | If yes |
|---|---|
| Does it hold state that a test can change (cookies, cart, page)? | **function** |
| Is it expensive and read-only (browser, catalogue, settings, a test server)? | **session** |
| Does a long-lived fixture need a short-lived one? | Not allowed — pytest refuses (`ScopeMismatch`) |

### 6.4 🔴 Factory fixtures

A fixture's value is created once per test. When a test needs **several** of something (two shoppers, three carts), the fixture returns a **function** that builds them. Building it on `new_context` means clean-up, traces, and screenshots come for free.

---

## Part 7 — Isolation 🔴

### 7.1 Four levels

| Level | Means | How it is achieved |
|---|---|---|
| Browser state | No cookies, storage, or cache shared between tests | A new context per test |
| Data | Each test creates the data it needs | API setup, generated test data, data chosen at runtime |
| Order | Any test can run first, last, or alone | No test depends on another's leftovers |
| Parallel | Tests can run at the same time | No shared files, ports, or accounts between tests |

### 7.2 The anti-pattern

A "convenient" session-scoped `page` fixture means one context for the whole run:

```
test A adds 1 item   → cart shows 1
test B adds 1 item   → cart shows 2   ← same test, different result, depending on what ran before
```

That is a flaky test **created by design**. With a context per test, B shows 1 whatever runs before it.

### 7.3 Proving isolation

Isolation is a claim until three runs agree:

| Run | Tool | Expectation |
|---|---|---|
| Repeated | `pytest-repeat` (`--count 3`) | Same results every time |
| Parallel | `pytest-xdist` (`-n 4`) | Same results |
| Random order | `pytest-randomly` | Same results with any seed |

All three were used to check this course's examples before the lecture.

---

## Part 8 — Lessons and the stability checklist 🔴

### 8.1 Four surprises found while preparing this lecture

| What happened | Cause | Lesson |
|---|---|---|
| A context set to `Asia/Ho_Chi_Minh` reported its zone as `Asia/Saigon` | Chromium reports the ICU canonical name of the zone | Check the **effect** (UTC+7), not the spelling |
| iPhone emulation showed a page 980 px wide, not 390 px | The page had no `<meta name="viewport">`; mobile browsers then lay out at 980 px | Emulation is faithful — including to pages that are not responsive. A real finding on a real site |
| An API call from the test could not reach the shop while the browser could | `page.request` runs in the driver, outside the browser's network path | Know which process makes each call (§1.4) |
| The checkout's "Including £18.33 in taxes" line disappeared between two runs (not because of locale: en-GB and en-US looked the same) | Shopify's checkout content varies | Volatile data: check it only when present, and as a rule (VAT = total ÷ 6), never as a fixed amount |

### 8.2 Stability and maintainability checklist

Use it for every Playwright test from Day 7 on, and in Day 8's review:

| # | Check |
|---|---|
| 1 | Locators are role/label-based; CSS only scoped inside a page object |
| 2 | No `.nth()` / `.first` unless the order **is** the behaviour |
| 3 | Every page fact is checked with `expect`, not `assert` |
| 4 | Every action that changes server state waits for its evidence (response, URL, or visible outcome) |
| 5 | No `sleep`, `wait_for_timeout`, `force=True`, or raised global timeouts without a written reason |
| 6 | Each test creates its own data and context; nothing depends on order |
| 7 | Volatile data (prices, stock, tax lines) is read at runtime or checked as a rule |
| 8 | Extra contexts come from `new_context` / a factory (cleaned up and recorded) |
| 9 | Context options that affect results (locale, time zone, viewport) are explicit |
| 10 | The suite passes repeated, in parallel, and in random order |

---

## Your output: Playwright test design notes (one page)

Fill this in after the lecture. Day 7's lab is built on it.

| Topic | Your decision and the reason |
|---|---|
| Default context options (locale, time zone, viewport) | |
| Fixture scopes (what is session, what is function) | |
| Locator rules (priority, when CSS is allowed) | |
| Waiting rules (what to wait for after each kind of action) | |
| Assertion rules (`expect` vs `assert`, volatile data) | |
| How you will prove isolation | |
| Two questions you still have | |

---

## Self-check (answers below — try first)

1. Name the three processes involved when a Python test clicks a button.
2. Why is the browser session-scoped but the context function-scoped?
3. A button shows "×" and has `aria-label="Close dialog"`. Which `name` finds it?
4. A click times out. Where do you look first?
5. Why is `force=True` dangerous?
6. Give two things automatic waiting does **not** wait for, and how to wait for them.
7. When is a plain `assert` correct in a Playwright test?
8. Storage state vs a shared context: which is good practice, and why?
9. Why pin `locale` and `timezone_id` for every test?

<details>
<summary><b>Answer guide</b></summary>

1. The Python test (sends commands), the Playwright driver in Node.js (translates and controls), the browser (executes).
2. A browser is slow to start and holds no test state by itself; a context holds cookies and storage, so each test needs its own — and contexts are cheap.
3. `name="Close dialog"` — the accessible name comes from `aria-label`, not from the glyph.
4. The call log in the error: it names the failed check ("not visible", "not enabled", "… intercepts pointer events", "strict mode violation").
5. It skips the actionability checks, so a test can "click" something no user can click and pass while the feature is broken.
6. The server finishing its work (`expect_response`), and navigation to a specific page (`wait_for_url`); also text that appears later (`expect(...).to_have_text`). Never a fixed sleep.
7. For values that no longer change: return values, objects already read, parsed JSON.
8. Storage state: each test loads a *copy* into a *new* context, so every test starts from the same known state. A shared context is the *same* state changed by every test, so results depend on order.
9. So dates, number formats, and language do not depend on the machine or the CI region; one test can still override them when it is about another locale.
</details>

## Next: Day 6

Tracing, network interception (mocking and blocking requests), authentication state, parallel execution, and reporting patterns.
