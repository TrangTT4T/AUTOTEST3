# Unit 5 · Day 20 — Mock Project (2/4): Framework and BDD Scenarios

| | |
|---|---|
| **Course** | Advanced Automation Test Engineering (ATEST03) — Fast Track |
| **Unit** | Unit 5 — Mock Project Design and Implementation |
| **Session** | Assignment/Lab, part 2 of 4 · **120 min** |
| **Learning outcomes** | **LO2** BDD specifications with maintainable steps, hooks, tags, reporting and traceable evidence (B3) · **LO3** reliable Playwright suites: fixtures, isolation, tracing, network control, parallel execution (B3) · **LO5** synchronisation on mobile-sized, touch targets (B3) |
| **Code** | `mock-project/` — `swaglabs/`, `features/`, `tests/` |
| **Output today** | A framework that runs the 46 scenarios for any persona, with tag rules, strict expected failures, evidence and traceability |

---

## Plan for today (120 min)

| Time | Block | Level |
|---|---|---|
| 0–15 | 1. Project skeleton and the layer rules | 🟢 |
| 15–40 | 2. Domain types and page objects (selectors at the bottom) | 🟢→🟡 |
| 40–65 | 3. Features, tags and steps | 🟡 |
| 65–90 | 4. Fixtures, isolation, network control, evidence | 🟡→🔴 |
| 90–110 | 5. The plugins: tag rules, strict expected failures, traceability | 🔴 |
| 110–120 | 6. Run it for every persona, self-check | 🔴 |

---

## 1. 🟢 Project skeleton and the layer rules

```bash
cd mock-project
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt        # pinned: pytest 9.2, pytest-bdd 9.0.1, playwright 1.63 ...
playwright install --with-deps chromium
pytest --collect-only -q                   # 46 tests collected
```

```
features/*.feature        WHAT is tested (business language, tags)
tests/steps/*_steps.py    HOW a sentence maps to actions — talks only to the SwagLabs facade
swaglabs/app.py           SwagLabs: page objects, session/cart shortcuts, timing, waiting
swaglabs/pages/*.py       one class per page; selectors at the BOTTOM; methods return domain values
swaglabs/domain.py        Money, Catalogue, Cart, OrderSummary, SortOrder — the oracles
swaglabs/plugins/*.py     thin pytest glue; the logic is in pure modules next to them
```

Why layers? When Swag Labs renames a `data-test`, exactly **one** line changes (in a page
object). When a business rule changes (tax becomes 10 %), one data file changes. Steps never
change for either. The rules are not a wish — `tests/unit/test_architecture.py` fails the build
if a selector is written outside the Locators section, if a step imports Playwright or touches
`.page`, or if anyone sleeps for a fixed time.

---

## 2. 🟢→🟡 Domain types and page objects

### 2.1 Money is not a float

```python
>>> 0.1 + 0.2
0.30000000000000004
```

A shop computes money; floats cannot represent cents exactly. `swaglabs/domain.py` uses
`Decimal`, rounded **half-up** to the cent (the way shops round, unlike Python's default
banker's rounding):

```python
@dataclass(frozen=True, order=True)
class Money:
    amount: Decimal

    def __init__(self, amount: Decimal | str | int) -> None:
        ...
        object.__setattr__(self, "amount", value.quantize(CENT, rounding=ROUND_HALF_UP))

    @classmethod
    def parse(cls, text: str) -> Self:
        """The amount in a label such as ``'$29.99'`` or ``'Item total: $47.97'``."""
```

The overview oracle then computes what the page **must** show, independently of the page:

```python
summary = OrderSummary.expected_for([Money("29.99"), Money("9.99")], Decimal("0.08"))
assert summary == OrderSummary(Money("39.98"), Money("3.20"), Money("43.18"))
```

### 2.2 The reference catalogue (the oracle)

`swaglabs/data/catalogue.json` holds the six products recorded from `standard_user`: id, name,
price and the stable start of the image file name (the rest is a build hash that changes on
every deployment of the site — matching the whole name would break on their next release):

```python
def shows_image(self, src: str) -> bool:
    """True when an <img src> is this product's picture (whatever the build hash)."""
    file_name = src.rsplit("/", 1)[-1]
    return file_name.split("-1200x", 1)[0] == self.image
```

### 2.3 A page object, end to end

```python
class InventoryPage(BasePage):
    PATH = "/inventory.html"

    def wait_until_loaded(self) -> None:
        expect(self.list).to_be_visible()

    def read_cards(self) -> list[Card]:
        selectors = {"name": self._card_name, "price": self._card_price, "image": self._card_image}
        rows = self.find(self._card).evaluate_all(_READ_CARDS, selectors)
        return [Card(r["name"], Money.parse(r["price"]), r["image"]) for r in rows]

    def add(self, product: Product) -> None:
        self.find(self._add.format(slug=product.slug)).click()

    def expect_in_cart(self, product: Product) -> None:
        """The card's button turned into Remove: the add was accepted."""
        expect(self.find(self._remove.format(slug=product.slug))).to_be_visible()

    # --- Locators -------------------------------------------------------------
    _list = "[data-test='inventory-list']"
    _card = "[data-test='inventory-item']"
    _card_name = "[data-test='inventory-item-name']"
    _card_price = "[data-test='inventory-item-price']"
    _card_image = "img.inventory_item_img"
    _sort = "[data-test='product-sort-container']"
    _add = "[data-test='add-to-cart-{slug}']"
    _remove = "[data-test='remove-{slug}']"
```

What to notice:

| Detail | Why |
|---|---|
| Selectors at the **bottom**, after the methods | The course convention: methods first (what the page does), selectors last (how it is found); one place to update |
| `_add` is a template (`{slug}`) | Six products, one selector; the slug comes from the domain (`Product.slug`) |
| `read_cards` uses **one** `evaluate_all` | Six cards × three reads = 18 round trips → 1. And a single snapshot cannot "tear" if the page re-renders between reads |
| `wait_until_loaded` | `open()` returns only when the page is usable; every page defines its own proof |
| Returns `Card` with `Money` | Steps compare business values, never scraped strings |
| `expect_in_cart` after `add` | The click is not the result; the button turning into *Remove* is. For problem_user's three broken products, this is where the test fails — with an `AssertionError` |

### 2.4 A single-page-app trap

Clicking a card changes the URL **before** React has replaced the catalogue. If you read
`[data-test=inventory-item-name]` right after the URL changes, you get six names (strict-mode
violation) — we hit exactly this during exploration. The fix is to wait for something that only
the **new** page has:

```python
def wait_until_loaded(self) -> None:          # ProductPage
    self.page.wait_for_url(f"**{self.PATH}?id=*")
    expect(self.back_button).to_be_visible()
```

### 2.5 Verified input

```python
def fill_verified(self, field: Locator, value: str) -> None:
    field.fill(value)
    expect(field, f"the field should keep the text {value!r}").to_have_value(value, timeout=INPUT_SETTLE_MS)
```

Typing is synchronous in the browser: if the value is not in the field within 2 s it will never
be. For problem_user (Last Name text jumps into First Name) and error_user (Last Name stays
empty) the failure now says **which field** lost the text, instead of a puzzling "Error: Last
Name is required" two steps later.

---

## 3. 🟡 Features, tags and steps

### 3.1 A feature file

```gherkin
Feature: Shopping cart
  As a shopper
  I want the cart to hold exactly what I chose
  So that I pay for the right things

  Background:
    Given I am logged in

  @smoke @risk-high @REQ-SL-07
  Scenario: Adding products updates the badge and the cart
    When I add "Sauce Labs Backpack" to the cart
    And I add "Sauce Labs Bike Light" to the cart
    Then the cart badge shows 2
    And the cart holds exactly:
      | product               | quantity | price  |
      | Sauce Labs Backpack   | 1        | $29.99 |
      | Sauce Labs Bike Light | 1        | $9.99  |

  @regression @risk-high @REQ-SL-07 @area-add-any-product
  Scenario: Every product can be added from the catalogue
    When I add every product to the cart
    Then the cart badge shows 6
    And the stored cart holds every product
```

### 3.2 The tag vocabulary

| Tag | Meaning | Rule (checked at collection) |
|---|---|---|
| `@REQ-SL-xx` | requirement(s) the scenario covers | ≥ 1, each must exist in `requirements.toml` |
| `@risk-high/medium/low` | risk band | exactly 1, equal to the highest band of its requirements |
| `@smoke` / `@regression` | suite | exactly 1 |
| `@area-<name>` | behaviours the scenario depends on | each must be declared in `findings.toml [areas]` |
| `@persona-independent` | logs in with its own explicit users | runs only in the `standard_user` job |
| `@phone` | phone-sized touch context | becomes a `browser_context_args` marker |
| `@manual` | not automated (documented) | needs only a requirement |

### 3.3 Area tags on **Examples** — precision matters

The checkout validation outline has four rows. Two of them type into Last Name, two do not.
problem_user and error_user break Last Name, so only those two rows may be expected to fail:

```gherkin
  @regression @risk-high @REQ-SL-09
  Scenario Outline: Each missing detail is refused with its own message
    When I enter first name "<first>", last name "<last>" and postal code "<postal>"
    And I continue
    Then I stay on the checkout information page
    And I see the checkout error "<error>"

    Examples: Nothing typed
      | first | last | postal | error                         |
      |       |      |        | Error: First Name is required |

    @area-last-name-required
    Examples: Last Name left empty
      | first | last | postal | error                        |
      | Ada   |      | 10115  | Error: Last Name is required |

    @area-last-name-entry
    Examples: Last Name typed
      | first | last     | postal | error                          |
      |       | Lovelace | 10115  | Error: First Name is required  |
      | Ada   | Lovelace |        | Error: Postal Code is required |
```

pytest-bdd 9 turns Examples tags into marks on each generated test, so the expectation is
attached to exactly the rows it belongs to.

> 🔴 **War story: how SL-14 was found.** The first version had *Last Name left empty* in the
> untagged block. The run as error_user failed that row — not with a timeout, with a different
> assertion: the page had moved on to the **overview**. error_user's checkout accepts an empty
> Last Name! That is a new defect (SL-14, `@area-last-name-required`), found by the suite, not
> by exploration. A strict register forces this: an unexplained failure is investigated, never
> waved through as "probably the known one".

### 3.4 Steps talk to one facade

```python
@when(parsers.parse('I add "{name}" to the cart'))
def add_to_cart(shop: SwagLabs, name: str) -> None:
    product = shop.catalogue.by_name(name)
    inventory = shop.inventory()
    with shop.perf.measure("add-to-cart"):
        inventory.add(product)
        inventory.expect_in_cart(product)
```

- No Playwright import, no selector, no `page`: a UI change never touches a step.
- Empty Examples cells (`""`) need a regex parser: `parse`'s `{}` needs at least one character.

```python
DETAILS = parsers.re(
    r'I enter first name "(?P<first>[^"]*)", last name "(?P<last>[^"]*)" and postal code "(?P<postal>[^"]*)"'
)
```

- Feature files never contain the password. `(valid)` and `(empty)` are tokens a step resolves:

```python
def _value(shop: SwagLabs, token: str) -> str:
    """Feature files never contain the password: ``(valid)`` stands for it, ``(empty)`` for ''."""
    return {VALID: shop.settings.password, EMPTY: ""}.get(token, token)
```

---

## 4. 🟡→🔴 Fixtures, isolation, network control, evidence

### 4.1 One fresh browser context per test

```python
@pytest.fixture
def shop(request, page, settings, catalogue) -> Iterator[SwagLabs]:
    """The application under test, in a FRESH browser context (pytest-playwright's ``page``)."""
    page.set_default_timeout(settings.ui_timeout_ms)
    monitor = BrowserMonitor()
    monitor.attach(page.context)
    perf = PerfRecorder(monitor, test=request.node.nodeid)
    app = SwagLabs(page, settings, catalogue, monitor, perf)
    request.node.stash[SHOP_KEY] = app
    yield app
    request.node.user_properties.append((PERF_PROPERTY, [m.as_dict() for m in perf.measurements]))
```

A fresh context = fresh cookies and localStorage. No test can see another test's session or
cart, so the order of tests does not matter and `pytest -n 4` is safe.

### 4.2 Arrange through state, act through the UI (ADR-4)

```python
def start_session(self) -> InventoryPage:
    self.page.context.add_cookies(
        [{"name": SESSION_COOKIE, "value": self.settings.persona.value, "url": self.settings.base_url}]
    )
    return self.inventory().open()

def seed_cart(self, products: Iterable[Product]) -> None:
    ids = [p.id for p in products]
    self.page.evaluate("([key, ids]) => localStorage.setItem(key, JSON.stringify(ids))", [CART_STORAGE_KEY, ids])
    self.page.reload()
```

| Benefit | Example |
|---|---|
| Speed | no login form in 40 scenarios |
| Independence | the checkout scenarios do not depend on *Add to cart*, which problem_user breaks |
| Honest timing | performance_glitch_user's 5-second login does not slow every scenario |

**The guard** — shortcuts rot when the product changes. One scenario logs in through the form
and checks it set exactly the cookie the shortcut sets:

```gherkin
  @regression @risk-high @REQ-SL-01 @REQ-SL-03
  Scenario: The quick-login shortcut creates the same session as the login form
    Given I am on the login page
    When I log in as the persona under test
    Then the session cookie is the one the quick-login shortcut sets
```

### 4.3 Network control

```python
ALLOWED_HOSTS = frozenset({"www.saucedemo.com", "fonts.googleapis.com", "fonts.gstatic.com"})

def attach(self, context: BrowserContext) -> None:
    # A predicate matcher: only foreign requests are routed; the shop's own go straight through.
    context.route(self._is_foreign, self._abort)
    context.on("page", self._watch)
```

Why block? Swag Labs reports JavaScript errors to a third-party tracker. Our fault personas
produce errors *on purpose*; sending them would pollute a vendor's data and make our timing
depend on a service we do not test. Every blocked host is counted and saved in the evidence.
The monitor also records **dialogs** (and dismisses them — an unhandled `alert()` would freeze
the page) and **console errors**.

### 4.4 Evidence when a step fails

`pytest_bdd_step_error` writes, under `reports/evidence/<test>/`:

| File | Content |
|---|---|
| `<step>.png` | full-page screenshot |
| `<step>.html` | the page's HTML, password masked |
| `<step>.json` | scenario, step, persona, error, URL, console errors, dialogs, blocked hosts |

Plus Playwright's own `trace.zip` (`--tracing=retain-on-failure`) under `reports/artifacts/` —
open it with `playwright show-trace` to replay every action with DOM snapshots and network.

---

## 5. 🔴 The plugins

### 5.1 Tag rules — the risk analysis made executable

`swaglabs/plugins/registry.py` loads both registers, registers every `REQ-*` and `area-*` tag as
a marker (`--strict-markers` then rejects typos), and checks every scenario:

```python
def pytest_collection_modifyitems(config, items):
    ...
    for item in scenarios:
        tags = {marker.name for marker in item.iter_markers()}
        problems += [f"{item.name}: {p}" for p in tag_problems(tags, registry, areas)]
    if problems:
        raise pytest.UsageError("Tag rules broken:\n  " + "\n  ".join(problems))
```

`tag_problems` is a **pure function** in `swaglabs/requirements.py`, unit-tested with every
broken rule. The plugin only adapts pytest to it.

### 5.2 Strict expected failures from the register

```python
@pytest.hookimpl(trylast=True)  # after the tag rules have accepted the scenarios
def pytest_collection_modifyitems(config, items):
    persona = Persona.parse(str(config.getoption("persona")))
    ...
        if "persona-independent" in names and persona is not Persona.STANDARD:
            drop.append(item)
            continue
        expected = register.expected_failures(persona, area_tags(names))
        if expected:
            reason = "; ".join(f"{f.id} {f.title}" for f in expected)
            item.add_marker(pytest.mark.xfail(strict=True, raises=AssertionError, reason=reason))
            for finding in expected:
                item.add_marker(pytest.mark.known_defect(finding.id))
    if drop:
        config.hook.pytest_deselected(items=drop)
```

Deselected (not skipped): a skipped test would show as MANUAL in the matrix — a lie.

### 5.3 Traceability and the run record

`swaglabs/plugins/reporting.py` classifies each result (an xfail report says "skipped"; we
count it as **known-defect**, never as manual), and on the xdist controller writes:

```
reports/traceability.md / .json   requirement → scenarios → passed/failed/known-defect/manual → status
reports/perf.md / .json           timings (Day 21)
reports/run.json                  persona, browser, versions, commit, outcome counts, duration
reports/log-<worker>.jsonl        JSON log lines, password masked
reports/manifest.json             SHA-256 of every file (written last)
```

Status precedence: **FAIL > KNOWN DEFECT > PASS > MANUAL**, NOT RUN, NOT COVERED. The worst
outcome wins: one known defect makes a requirement "not met", however many tests pass.

### 5.4 With pytest-xdist, data must travel in the report

Workers are separate processes. A module-level list filled on a worker is invisible to the
controller that writes the reports. Everything the controller needs goes into
`report.user_properties` — measurements at teardown, known-defect ids at call — which xdist
serialises back to the controller.

### 5.5 Testing the test framework

How do you know the plugins work? `tests/unit/test_plugins.py` builds a tiny project in a
sandbox (pytester) — two scenarios, one finding — and asserts the outcomes:

```python
def test_a_fixed_defect_turns_the_run_red(project):
    write_steps(project, "pass")
    result = project.runpytest("--persona", "problem_user")
    result.assert_outcomes(failed=1, skipped=1, deselected=1)
    result.stdout.fnmatch_lines(["*XPASS(strict)*SL-01*"])

def test_a_different_kind_of_failure_is_never_hidden(project):
    write_steps(project, "raise RuntimeError('our own bug')")
    result = project.runpytest("--persona", "problem_user")
    result.assert_outcomes(failed=1, skipped=1, deselected=1)
```

One subtlety: pytest-playwright wraps every test in a soft-assertion scope, which cannot nest
inside the outer run's scope — the sandbox switches it off with `-p no:playwright` (it needs no
browser anyway). The unit and plugin tests reach **98 % branch coverage** of the framework (the
gate is 90 %).

---

## 6. 🔴 Run it for every persona

```bash
pytest tests/test_scenarios.py -n 4                                  # standard_user
pytest tests/test_scenarios.py -n 4 --persona problem_user -rx       # -rx lists the expected failures
pytest tests/test_scenarios.py -n 4 --persona error_user -rx
pytest tests/test_scenarios.py -n 4 --persona visual_user -rx
pytest tests/test_scenarios.py -n 4 --persona performance_glitch_user -rx
pytest tests/test_scenarios.py -n 4 --device "Pixel 7"
```

Expected results (Chromium, 2026-11-24):

| Run | Passed | Known defects (xfail) | Deselected | Skipped (manual) | Wall time |
|---|---:|---:|---:|---:|---:|
| standard_user | 44 | 1 (SL-12) | 0 | 1 | ~31 s |
| problem_user | 21 | 16 | 8 | 1 | ~55 s |
| error_user | 23 | 14 | 8 | 1 | ~54 s |
| visual_user | 32 | 5 | 8 | 1 | ~30 s |
| performance_glitch_user | 34 | 3 | 8 | 1 | ~100–110 s |
| standard_user, Pixel 7 | 44 | 1 | 0 | 1 | ~34 s |

Read `reports/traceability.md` after each run. For problem_user you should see REQ-SL-04, 05,
06, 07, 09, 10, 11, 12, 14 as **KNOWN DEFECT** — and nothing as FAIL.

---

## Lab tasks — Day 20

| # | Task | Done when |
|---|---|---|
| L20.1 | Implement `Money`, `Catalogue`, `OrderSummary` with unit tests (rounding half-up, the live overview values). | `pytest tests/unit/test_domain.py` green |
| L20.2 | Page objects for login, inventory, product, cart, checkout (selectors at the bottom). | Architecture tests green |
| L20.3 | Feature files for REQ-SL-01…12 with full tags; steps through the facade. | `pytest --collect-only -q --fail-on-uncovered` exits 0 |
| L20.4 | `shop` fixture with network allow-list; evidence on step failure. | A deliberately broken step leaves `.png`, `.html`, `.json` |
| L20.5 | Findings plugin; run every persona. | No FAIL in any persona; the expected-failure list matches the register |
| L20.6 | **Break it on purpose**: remove one persona from a finding and run that persona; then fix the register again. | You have seen a FAIL and an XPASS(strict) with your own eyes |

---

## Self-check

1. Why does `read_cards` use one `evaluate_all` instead of a loop of `inner_text()` calls?
2. After clicking a product card, why is `wait_for_url` alone not enough?
3. What is the risk of the cookie-login shortcut, and how is it controlled?
4. Why must an expected failure be limited to `AssertionError`?
5. Why are `@persona-independent` scenarios *deselected* in other persona jobs rather than skipped?
6. How do measurements recorded on an xdist worker reach the report written by the controller?
7. In the checkout outline, why do the area tags sit on **Examples** blocks?

<details>
<summary>Answers</summary>

1. One round trip instead of eighteen, and one consistent snapshot: the page cannot re-render between reads of the same card.
2. In a single-page app the URL changes before the new view is rendered; the old catalogue is still in the DOM. Wait for an element that only the new page has (the *Back to products* button).
3. It depends on the shop's internals (cookie name and value). A contract scenario logs in through the form and checks it set exactly that cookie, so the shortcut cannot silently drift.
4. So that only the known kind of failure is "expected". A timeout, a crash or a bug in our own code must still turn the run red; otherwise a known defect would hide new problems.
5. A skip would be counted as MANUAL in the traceability matrix, which is false. Deselected tests are simply not part of that run (NOT RUN in that column of the merged matrix).
6. Through `report.user_properties`, which pytest-xdist serialises from worker to controller; the controller's `pytest_runtest_logreport` collects them.
7. Because only some rows depend on the broken behaviour (typing into Last Name). Tagging the whole outline would make the other rows XPASS(strict) for the faulty personas.
</details>

---

## Verification log

| Check | Result |
|---|---|
| `ruff check .`, `ruff format --check .`, `mypy` (strict) on `mock-project/` | clean (48 source files) |
| `pytest tests/unit --cov` | 124 passed; branch coverage 98.4 % (gate 90 %) |
| `pytest --collect-only -q --fail-on-uncovered` | 46 tests; gate passes |
| Live runs per persona (table in section 6) | Run on 2026-11-24 against www.saucedemo.com, Chromium 1243 headless, 4 workers; all exit 0 |
| Firefox / WebKit | WebKit full suite run inside the container image: all scenarios pass. Firefox could not be run in this sandbox (its TLS-inspecting proxy is not trusted by Playwright's Firefox); it runs in the CI matrix |
