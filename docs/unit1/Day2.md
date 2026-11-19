# Unit 1 · Day 2 — BDD Framework Architecture: Features, Steps, Hooks, Tags, Reporting

| | |
|---|---|
| **Course** | Advanced Automation Test Engineering (ATEST03) — Fast Track |
| **Learning outcome** | **LO2** — Implement BDD specifications with maintainable steps, hooks, tags, reporting, and traceable evidence (Bloom **B3: Apply**) |
| **Format** | Concept/Lecture · Virtual · 120 minutes · code is studied, not submitted |
| **System under test** | https://sauce-demo.myshopify.com/ — today replaced by an in-memory **FakeStore**, so everything runs offline |
| **Stack** | Python 3.10+ · `pytest` · `pytest-bdd` (tested with pytest 9.2 and pytest-bdd 9.0.1) |
| **Output of the day** | A one-page **Framework Design** + a working offline project you understand line by line |
| **Companion code** | `day2-code/shop-bdd.zip` — the finished project from this guide |

> **What was tested.** Every code block and every output shown here was run with pytest-bdd 9.0.1 on Python 3.13, against the FakeStore. Nothing in Day 2 runs against the live site. The Playwright evidence options in section 5.4 were verified later, during the Day 3 live runs.

---

## How to use this guide

Day 1 was about *what* to test. Day 2 is about *how a BDD framework is built*. You will build a small project in seven stages, running it after each one.

| Badge | Level | After this level you can… |
|---|---|---|
| 🟢 | **Foundation** | Run pytest, write a fixture, make your first scenario pass |
| 🟡 | **Practitioner** | Write parameterized steps, share data between steps, use tables, outlines, hooks, and tags |
| 🔴 | **Advanced** | Structure a layered framework, enforce tag rules, produce traceability evidence, review a framework for maintainability |

**Why use a FakeStore today?** Learning BDD and learning browser automation at the same time is two hard things at once. The FakeStore behaves like a tiny shop in memory. On Day 3 you swap it for a real Playwright implementation — and the feature files and steps stay the same. That swap is itself the advanced lesson.

Lecture time plan (120 min). Doing all the follow-along stages yourself takes about 2–3 extra hours.

| Time | Part |
|---|---|
| 0–20 | Part 0 — Python & pytest prerequisites |
| 20–30 | Part 1 — How a BDD framework works |
| 30–45 | Part 2 — Your first executable scenario |
| 45–70 | Part 3 — Step definitions |
| 70–80 | Part 4 — Organizing the framework |
| 80–90 | Part 5 — Hooks |
| 90–100 | Part 6 — Tags |
| 100–115 | Part 7 — Reporting & traceability |
| 115–120 | Part 8 — Maintainability rules |

---

## Glossary

| Term | Meaning | Vietnamese |
|---|---|---|
| Virtual environment (venv) | A private folder of Python packages for one project | Môi trường ảo |
| `pip` | Python's package installer | Trình cài gói |
| pytest | The most popular Python test runner | Bộ chạy test |
| Assertion (`assert`) | A line that fails the test if a condition is false | Câu khẳng định |
| Fixture | A function that prepares something a test needs (and cleans up after) | Fixture / dữ liệu dựng sẵn |
| Decorator (`@something`) | A label placed above a function that gives it a special role | Decorator |
| Step definition | A Python function linked to one Gherkin step text | Định nghĩa bước |
| Glue code | All step definitions together: the "glue" between Gherkin and the system | Mã kết nối |
| Hook | A function the framework calls automatically at a certain moment | Hook |
| Marker | pytest's name for a tag; used to select tests with `-m` | Marker |
| Page object / Store object | A class that hides how to talk to the system (selectors, URLs) | Page object |
| Interface (Protocol) | A list of methods every implementation must offer | Giao diện |
| Living documentation | Feature files + reports that always reflect current behaviour | Tài liệu sống |

---

## Part 0 — Python & pytest prerequisites 🟢

### 0.1 Set up a project folder

Install Python 3.10 or newer from python.org. Then, in a terminal:

**Windows (PowerShell):**

```bash
mkdir shop-bdd
```

```bash
cd shop-bdd
```

```bash
py -m venv .venv
```

```bash
.venv\Scripts\activate
```

**macOS / Linux:**

```bash
mkdir shop-bdd && cd shop-bdd
```

```bash
python3 -m venv .venv
```

```bash
source .venv/bin/activate
```

Then, on both:

```bash
pip install pytest pytest-bdd
```

Your prompt now starts with `(.venv)`. Activate it again each time you open a new terminal.

### 0.2 The only Python you need today

| Concept | Example | What it means |
|---|---|---|
| Function | `def add(a, b): return a + b` | A named, reusable block of code |
| Dictionary | `{"name": "Grey jacket", "price": 55}` | Key → value pairs |
| f-string | `f"Hello {name}"` | Text with values inserted |
| Decorator | `@given("a visitor with an empty cart")` | A **label** above a function. Here it tells pytest-bdd: *"when you see this sentence in a feature file, run the function below"* |
| `assert` | `assert total == 55` | Stop the test with a failure if the condition is false |
| `yield` | see 0.4 | "Pause here, let the test run, then continue" |

### 0.3 pytest in 5 minutes

Create `test_basics.py`:

```python
def add(a, b):
    return a + b


def test_add():
    assert add(2, 3) == 5
```

Run:

```bash
pytest -v
```

```
test_basics.py::test_add PASSED
```

Rules pytest follows: files named `test_*.py`, functions named `test_*`. Change `5` to `6` and run again to see what a failure looks like — reading failure messages is a core skill.

### 0.4 Fixtures — the most important pytest idea

A **fixture** prepares something a test needs. A test asks for it simply by naming it as a parameter.

Add to `test_basics.py`:

```python
import pytest


@pytest.fixture
def cart():
    print("\n[setup] create an empty cart")
    items = []
    yield items                       # the test runs here
    print("\n[teardown] throw the cart away")


def test_new_cart_is_empty(cart):     # "cart" = ask pytest for the fixture
    assert cart == []


def test_cart_can_hold_an_item(cart):
    cart.append("Grey jacket")
    assert len(cart) == 1
```

```bash
pytest -v -s
```

```
[setup] create an empty cart
PASSED
[teardown] throw the cart away
[setup] create an empty cart
PASSED
[teardown] throw the cart away
```

Three things to notice:
1. Each test got its **own new cart** → tests cannot disturb each other (isolation, Day 1 §2.2).
2. Code after `yield` is **teardown**; it runs even when the test fails.
3. You never call `cart()` yourself. pytest sees the parameter name and provides it.

pytest-bdd is built entirely on this mechanism. If fixtures make sense, BDD will too.

> **Checkpoint 0.** What would go wrong if `cart` were a global list shared by both tests and the second test ran first?

---

## Part 1 — How a BDD framework works 🟢

### 1.1 The big picture

```
features/cart.feature          tests/test_cart.py              tests/steps/cart_steps.py
┌────────────────────┐        ┌───────────────────┐           ┌──────────────────────────┐
│ Scenario: ...      │ ─────▶ │ scenarios(...)    │           │ @given("a visitor ...")  │
│   Given a visitor… │        │ turns each        │  matches  │ def empty_cart(store):   │
│   When they add …  │        │ scenario into a   │ ────────▶ │ @when("they add ...")    │
│   Then the cart …  │        │ pytest test       │  by text  │ def add_product(store):  │
└────────────────────┘        └───────────────────┘           └────────────┬─────────────┘
                                                                           │ uses fixtures
                                                              ┌────────────▼─────────────┐
                                                              │ store  (FakeStore today, │
                                                              │ Playwright on Day 3)     │
                                                              └──────────────────────────┘
```

Restaurant analogy:
- **Feature file** = the customer's order, in plain words.
- **Step definitions** = the recipes. Each recipe is found by the exact name of the dish.
- **Fixtures** = the kitchen equipment, set up before cooking and cleaned after.
- **Store object** = the cook's hands: the only part that touches the real ingredients.

Rules to remember:
- One **scenario** becomes one **pytest test**.
- One **Gherkin step** runs one **Python function**, found by matching its **text**.
- Everything shared between steps travels through **fixtures**.

### 1.2 🟡 Cucumber and SpecFlow use the same ideas

The syllabus names Cucumber/SpecFlow. You will meet them in jobs, so learn the mapping:

| Concept | Cucumber (Java/JS) | SpecFlow (C#) | pytest-bdd (Python) |
|---|---|---|---|
| Specification | `.feature` (Gherkin) | `.feature` | `.feature` — identical syntax |
| Step definition | `@Given` / `Given()` | `[Given]` | `@given` |
| Shared state between steps | World / dependency injection | ScenarioContext | pytest fixtures, `target_fixture` |
| Before/after hooks | `@Before` / `@After` | `[BeforeScenario]` | fixture with `yield`, `pytest_bdd_*` hooks |
| Tags | `@tag`, `--tags` | `@tag` | `@tag` → marker, `-m` |
| Step parameters | Cucumber expressions `{int}` | regex / expressions | `parsers.parse("{qty:d}")` |
| Report | Cucumber JSON / HTML | LivingDoc | `--cucumberjson`, JUnit XML |

---

## Part 2 — Your first executable scenario 🟢 (Stage 1)

### 2.1 Create the files

```
shop-bdd/
├── pytest.ini
├── conftest.py
├── features/
│   └── cart.feature
├── support/
│   ├── __init__.py        (empty file)
│   └── store.py
└── tests/
    └── test_cart.py
```

**`pytest.ini`** — tells pytest where things are:

```ini
[pytest]
testpaths = tests
bdd_features_base_dir = features
```

**`features/cart.feature`** — the scenario from Day 1 §3.2:

```gherkin
Feature: Shopping cart

  Scenario: Adding a product puts it in the cart
    Given a visitor with an empty cart
    When they add "Grey jacket" to the cart
    Then the cart contains 1 "Grey jacket"
```

**`support/store.py`** — the FakeStore (a pretend shop in memory):

```python
from decimal import Decimal


class FakeStore:
    """An in-memory stand-in for the real web store."""

    PRICES = {
        "Grey jacket": Decimal("55.00"),
        "Noir jacket": Decimal("60.00"),
    }

    def __init__(self):
        self.lines = {}  # product name -> quantity

    def open_product(self, name):
        return {"name": name, "price": self.PRICES[name]}

    def add(self, name, qty=1):
        self.lines[name] = self.lines.get(name, 0) + qty

    def quantity(self, name):
        return self.lines.get(name, 0)

    def item_count(self):
        return sum(self.lines.values())

    def subtotal(self):
        return sum((self.PRICES[n] * q for n, q in self.lines.items()), Decimal("0"))

    def clear_cart(self):
        self.lines.clear()
```

**`conftest.py`** — pytest loads this file automatically; fixtures here are available everywhere:

```python
import pytest
from support.store import FakeStore


@pytest.fixture
def store():
    s = FakeStore()
    yield s
    s.clear_cart()
```

**`tests/test_cart.py`** — binds the feature file and defines the three steps:

```python
from pytest_bdd import scenarios, given, when, then

scenarios("cart.feature")   # every scenario in the file becomes a test


@given("a visitor with an empty cart")
def empty_cart(store):
    assert store.item_count() == 0


@when('they add "Grey jacket" to the cart')
def add_grey_jacket(store):
    store.add("Grey jacket")


@then('the cart contains 1 "Grey jacket"')
def cart_has_one_grey_jacket(store):
    assert store.quantity("Grey jacket") == 1
```

### 2.2 Run it

```bash
pytest -v
```

```
tests/test_cart.py::test_adding_a_product_puts_it_in_the_cart PASSED     [100%]
============================== 1 passed in 0.01s ===============================
```

The test name was generated from the scenario name. Your first executable specification works.

### 2.3 Break it on purpose

Change the `When` line in the feature file to `When they put "Grey jacket" in the basket` and run again:

```
StepDefinitionNotFoundError: Step definition is not found: When "they put "Grey jacket" in the basket".
Line 5 in scenario "Adding a product puts it in the cart" ...
```

Lesson: steps are matched by **exact text**. The feature file and the code must agree word for word. Change it back.

> **Checkpoint 2.** Why does `empty_cart` receive `store` as a parameter, and where does that value come from?

---

## Part 3 — Step definitions 🟡

### 3.1 Parameters (Stage 2)

Stage 1 has a problem: the step only works for "Grey jacket". A second product would need copy-pasted functions. Use **parameters** instead.

Add a second scenario to `cart.feature`:

```gherkin
  Scenario: Adding a different product
    Given a visitor with an empty cart
    When they add "Noir jacket" to the cart
    Then the cart contains 1 "Noir jacket"
```

Replace the steps in `tests/test_cart.py`:

```python
from pytest_bdd import scenarios, given, when, then, parsers

scenarios("cart.feature")


@given("a visitor with an empty cart")
def empty_cart(store):
    assert store.item_count() == 0


@when(parsers.parse('they add "{name}" to the cart'))
def add_product(store, name):
    store.add(name)


@then(parsers.parse('the cart contains {qty:d} "{name}"'))
def cart_contains(store, qty, name):
    assert store.quantity(name) == qty
```

```
tests/test_cart.py::test_adding_a_product_puts_it_in_the_cart PASSED
tests/test_cart.py::test_adding_a_different_product PASSED
```

How `parsers.parse` works: `{name}` captures text into a parameter called `name`. `{qty:d}` captures a **number** and converts it to an `int`.

| Pattern | Matches | Python value |
|---|---|---|
| `{name}` | any text | `str` |
| `{qty:d}` | `3` | `int` 3 |
| `{price:f}` | `55.5` | `float` 55.5 |
| `{word:w}` | one word (letters/digits) | `str` |

Rarely needed: `parsers.re(r'...(?P<name>...)')` for regular expressions (optional words, alternatives).

### 3.2 Passing data between steps with `target_fixture` (Stage 3)

Often a `Given` creates something that later steps need. Example: "the visitor is viewing the product X" → the `When` step needs to know *which* product.

```python
@given(
    parsers.parse('the visitor is viewing the product "{name}"'),
    target_fixture="product",          # the return value becomes a fixture called "product"
)
def viewing_product(store, name):
    return store.open_product(name)    # {"name": "Grey jacket", "price": Decimal("55.00")}


@when("they add the product to the cart")
def add_once(store, product):          # ask for "product" like any fixture
    store.add(product["name"])
```

If you use `When they add the product to the cart` **without** the `Given` that creates `product`, pytest tells you:

```
E       fixture 'product' not found
```

That error always means: *"a step needs data that no earlier step provided."*

### 3.3 `Background` — shared starting steps

Every cart scenario begins with an empty cart. Instead of repeating it:

```gherkin
Feature: Shopping cart
  Visitors collect products in a cart before checkout.

  Background:
    Given a visitor with an empty cart

  Scenario: Adding an available product puts it in the cart
    Given the visitor is viewing the product "Grey jacket"
    When they add the product to the cart
    Then the cart contains 1 "Grey jacket"
    And the cart subtotal equals the product price times 1
```

`Background` runs before **each** scenario in the file. Keep it to 1–3 steps; readers forget what is hidden there.

### 3.4 `Scenario Outline` — one scenario, many data rows

```gherkin
  Scenario Outline: Subtotal follows quantity
    Given the visitor is viewing the product "<product>"
    When they add the product to the cart <times> times
    Then the cart contains <times> "<product>"
    And the cart subtotal equals the product price times <times>

    Examples:
      | product     | times |
      | Grey jacket | 2     |
      | Noir jacket | 3     |
```

Steps it needs:

```python
@when(parsers.parse("they add the product to the cart {times:d} times"))
def add_many(store, product, times):
    store.add(product["name"], times)


@then(parsers.parse("the cart subtotal equals the product price times {qty:d}"))
def subtotal_is_price_times(store, product, qty):
    assert store.subtotal() == product["price"] * qty
```

pytest creates **one test per row**:

```
test_subtotal_follows_quantity[Grey jacket-2] PASSED
test_subtotal_follows_quantity[Noir jacket-3] PASSED
```

Notice the subtotal check never hard-codes "£110". It compares with the product's own price — Day 1 rule 6.

### 3.5 Data tables — a list inside one step

```gherkin
  Scenario: Cart with several products
    When they add these products to the cart:
      | product     | quantity |
      | Grey jacket | 1        |
      | Noir jacket | 2        |
    Then the cart has 3 items in total
```

pytest-bdd gives the table to a parameter named exactly **`datatable`**, as a list of rows (the header row first, all values as text):

```python
@when("they add these products to the cart:")
def add_table(store, datatable):
    header, *rows = datatable          # header = ["product", "quantity"]
    for row in rows:
        item = dict(zip(header, row))  # {"product": "Grey jacket", "quantity": "1"}
        store.add(item["product"], int(item["quantity"]))   # convert text → int


@then(parsers.parse("the cart has {total:d} items in total"))
def total_items(store, total):
    assert store.item_count() == total
```

### 3.6 Choosing the right construct

| Construct | Use it for | Avoid when |
|---|---|---|
| Parameter `{name}` | Same step, different values | — |
| `target_fixture` | A `Given` produces data later steps use | You could just pass the value as a parameter |
| `Background` | 1–3 `Given` steps every scenario needs | It grows long or only some scenarios need it |
| `Scenario Outline` | Same behaviour, different data | Rows describe *different behaviours* → separate scenarios |
| Data table | Several items in one step | A single value would do |

All four constructs together = **Stage 3**: 4 tests passing.

```
test_adding_an_available_product_puts_it_in_the_cart PASSED
test_subtotal_follows_quantity[Grey jacket-2] PASSED
test_subtotal_follows_quantity[Noir jacket-3] PASSED
test_cart_with_several_products PASSED
```

> **Checkpoint 3.** The Outline creates two tests. Does the `Background` run once in total, or once per test? Why does that matter for isolation?

---

## Part 4 — Organizing the framework 🟡 → 🔴 (Stage 4)

### 4.1 Why structure matters

A framework with 5 scenarios can live in one file. A framework with 300 cannot. The goal is: **each kind of change touches exactly one place**.

| Change | Should only touch |
|---|---|
| A business rule changes | `features/` |
| A new step phrasing | `tests/steps/` |
| The site's theme / selectors change | `support/` (the store object) |
| A new platform (mobile in Unit 3) | A new store class in `support/` |
| Reporting or run settings | `conftest.py`, `pytest.ini` |

### 4.2 The layered layout

```
shop-bdd/
├── pytest.ini                 # settings, registered tags
├── conftest.py                # fixtures, hooks, plugin list
├── features/
│   └── cart.feature           # WHAT — business behaviour only
├── tests/
│   ├── __init__.py
│   ├── test_cart.py           # binds the feature file (2 lines)
│   └── steps/
│       ├── __init__.py
│       └── cart_steps.py      # glue — thin steps, no selectors
├── support/
│   ├── __init__.py
│   ├── interface.py           # the Store contract
│   ├── store.py               # FakeStore (today), WebStore (Day 3)
│   └── traceability.py        # report plugin (Part 7)
└── reports/                   # generated, never committed
```

| Layer | Knows about | Must NOT know about |
|---|---|---|
| Feature files | Business behaviour | Python, selectors, URLs |
| Step definitions | Gherkin text, the Store interface | Selectors, URLs, waits |
| Store implementations | Selectors, URLs, waits, API calls | Gherkin |

### 4.3 Moving steps out of the test file

`tests/test_cart.py` shrinks to:

```python
from pytest_bdd import scenarios

scenarios("cart.feature")
```

All step functions move to `tests/steps/cart_steps.py` (same code as Part 3). Then load that module once, in `conftest.py`:

```python
pytest_plugins = [
    "tests.steps.cart_steps",
]
```

Now any feature file can reuse those steps — no copy-pasting between test files.

### 4.4 🔴 The Store interface — the cross-platform contract

```python
# support/interface.py
from decimal import Decimal
from typing import Protocol


class Store(Protocol):
    """What every store implementation must offer: fake, web, or mobile."""

    def open_product(self, name: str) -> dict: ...
    def add(self, name: str, qty: int = 1) -> None: ...
    def quantity(self, name: str) -> int: ...
    def item_count(self) -> int: ...
    def subtotal(self) -> Decimal: ...
    def clear_cart(self) -> None: ...
```

Steps only ever call these six methods. So:
- **Today**: the `store` fixture returns `FakeStore()`.
- **Day 3**: it returns `WebStore(page)`, which does the same six things with Playwright clicks.
- **Unit 3**: `MobileStore(driver)` with Appium.

Feature files and steps never change. This is the *cross-platform strategy* from Day 1 §4.2, now as real code.

### 4.5 🔴 Why `Decimal` for money

```python
>>> 0.1 + 0.2
0.30000000000000004
```

Floats cannot store most decimal fractions exactly, so `assert subtotal == 0.3` can fail on correct data. `Decimal("0.10") + Decimal("0.20") == Decimal("0.30")` is exact. Always use `Decimal` (or whole pence as `int`) for money.

---

## Part 5 — Hooks 🟡 → 🔴

### 5.1 Setup and teardown = a fixture with `yield`

You already know this from Part 0:

```python
@pytest.fixture
def store():
    s = FakeStore()
    yield s          # the scenario runs here
    s.clear_cart()   # teardown: runs even if the scenario failed
```

Fixture **scope** controls how often it runs:

| Scope | Runs | Use for |
|---|---|---|
| `function` (default) | Once per scenario | Anything with state: cart, browser page — **use this** |
| `session` | Once per whole run | Read-only things: configuration, base URL |

Sharing a stateful fixture across scenarios (`scope="session"` for the cart) is the classic cause of "passes alone, fails in the suite".

### 5.2 pytest-bdd hooks

Put these functions in `conftest.py`. pytest-bdd calls them automatically at the moment their name describes.

| Hook | Called when | Typical use |
|---|---|---|
| `pytest_bdd_before_scenario` | Before each scenario | Log the name and tags |
| `pytest_bdd_after_scenario` | After each scenario | Attach evidence |
| `pytest_bdd_before_step` / `pytest_bdd_after_step` | Around each step | Timing, step logs |
| `pytest_bdd_step_error` | A step raised an error | Record what failed and why |
| `pytest_bdd_apply_tag` | A tag is turned into a marker | Give a tag special behaviour (Part 6) |

```python
def pytest_bdd_before_scenario(request, feature, scenario):
    print(f"\n[START] {scenario.name}  tags={sorted(scenario.tags)}")


def pytest_bdd_step_error(request, feature, scenario, step, step_func,
                          step_func_args, exception):
    print(f"\n[FAILED STEP] {step.keyword} {step.name}")
    print(f"[REASON] {exception!r}")
```

### 5.3 See the hooks catch a bug

Introduce a bug in `add_once` (replace `store.add(product["name"])` with `pass`) and run `pytest -s -m smoke`:

```
[START] Adding an available product puts it in the cart  tags=['REQ-03', 'REQ-04', 'risk-high', 'smoke']
[FAILED STEP] Then the cart contains 1 "Grey jacket"
[REASON] AssertionError("assert 0 == 1\n +  where 0 = quantity('Grey jacket') ...")
```

The report names the **business step** that failed, not just a line of Python. That is BDD's debugging advantage. Fix the bug again.

### 5.4 🔴 Evidence on failure (Day 3 preview — not run today)

With a real browser, `pytest-playwright` collects evidence without any custom hook:

```bash
pytest --screenshot only-on-failure --tracing retain-on-failure --output reports/artifacts
```

### 5.5 🔴 Hook discipline

- Hooks are for **infrastructure** (browser, logging, evidence). Never hide **business** setup in a hook: if a reader of the scenario needs to know about it, it must be a visible `Given`.
- Teardown must be safe after a failure (the cart might be half-filled).

---

## Part 6 — Tags 🟡 → 🔴

### 6.1 Tags become markers; markers select tests

Tags on a `Feature` apply to all its scenarios; tags on a `Scenario` apply to that one.

```bash
pytest -m smoke
```

```bash
pytest -m "risk-high and not manual"
```

```bash
pytest -m "REQ-04"
```

Output on the full project:

| Command | Result |
|---|---|
| `pytest` | 4 passed, 1 skipped |
| `pytest -m smoke` | 1 passed, 4 deselected |
| `pytest -m "risk-high"` | 4 passed, 1 deselected |
| `pytest -m "not manual"` | 4 passed, 1 deselected |

### 6.2 Register every tag

Add `--strict-markers` and a list of allowed tags to `pytest.ini`:

```ini
[pytest]
testpaths = tests
bdd_features_base_dir = features
addopts = --strict-markers
markers =
    web: runs in a browser
    api: runs against JSON endpoints
    mobile: runs on a phone or emulator
    smoke: fast critical checks, run on every change
    regression: full suite, run nightly
    manual: not automated, documented gap
    risk-high: risk score 15-25
    risk-medium: risk score 8-14
    risk-low: risk score 1-7
```

Now a typo such as `@smok` stops the run immediately:

```
'smok' not found in `markers` configuration option
```

Without `--strict-markers`, `@smok` is silently accepted and the scenario quietly drops out of your smoke suite.

Register `@REQ-01` … `@REQ-09` in code instead of nine lines (in `conftest.py`):

```python
def pytest_configure(config):
    for n in range(1, 10):
        config.addinivalue_line("markers", f"REQ-{n:02d}: covers requirement REQ-{n:02d}")
```

### 6.3 🔴 Give a tag behaviour: `@manual`

A manual scenario is still written in Gherkin, so the gap is documented — but it must not run:

```gherkin
  Rule: Account flows stay manual

    @REQ-08 @manual
    Scenario: Visitor signs up for an account
      Given the visitor is on the sign-up page
      When they register with a new email address
      Then they are logged in to their new account
```

```python
def pytest_bdd_apply_tag(tag, function):
    if tag == "manual":
        pytest.mark.manual(function)  # keep the tag so -m "not manual" works
        pytest.mark.skip(reason="Manual check - see strategy document")(function)
        return True                   # "I handled this tag"
    return None                       # every other tag: default behaviour
```

Its steps do not need step definitions, because a skipped scenario never looks them up.

**Trap:** when this hook returns `True`, pytest-bdd no longer adds the `manual` marker itself. Without the `pytest.mark.manual(function)` line, `-m "not manual"` would quietly select nothing to exclude. (This exact bug appeared while preparing this guide.)

### 6.4 🔴 Tag taxonomy (from Day 1 §4.1)

| Family | Values | Rule |
|---|---|---|
| Requirement | `@REQ-01` … `@REQ-09` | At least one per scenario |
| Risk | `@risk-high` / `@risk-medium` / `@risk-low` | Exactly one, except `@manual` |
| Suite | `@smoke` / `@regression` | Exactly one, except `@manual` |
| Platform | `@web` / `@api` / `@mobile` | At least one (usually on the `Feature`) |
| Status | `@manual` | Optional |

Exercise L3-2 turns these rules into code that fails the run when they are broken.

---

## Part 7 — Reporting & traceability 🔴

### 7.1 Four kinds of report

| Report | Command | For whom |
|---|---|---|
| Gherkin in the terminal | `pytest --gherkin-terminal-reporter -vv` | You, while developing |
| Cucumber JSON | `pytest --cucumberjson=reports/cucumber.json` | Dashboards, traceability tools |
| JUnit XML | `pytest --junitxml=reports/junit.xml` | CI systems (GitHub Actions, Jenkins) |
| HTML | plugins `pytest-html` or `allure-pytest-bdd` | Managers and stakeholders |

Gherkin terminal output:

```
Feature: Shopping cart
  Rule: Added products appear in the cart with a correct subtotal
        Scenario: Adding an available product puts it in the cart
            Given a visitor with an empty cart
            Given the visitor is viewing the product "Grey jacket"
            When they add the product to the cart
            Then the cart contains 1 "Grey jacket"
            And the cart subtotal equals the product price times 1
        PASSED
```

### 7.2 The gap you must know about

Skipped scenarios (our `@manual` ones) are **left out of the Cucumber JSON**. They appear in JUnit XML as "skipped", but JUnit XML has no tags. So neither built-in report can show "REQ-08 is a manual gap". If you build a traceability matrix from Cucumber JSON only, manual gaps silently disappear — exactly the false sense of coverage Day 1 warned about.

### 7.3 A traceability plugin

The fix: a small pytest plugin that reads each test's `REQ-*` markers and its outcome (including skips), then prints a matrix and saves a CSV.

```python
# support/traceability.py
"""Prints a requirement traceability matrix at the end of every run."""
import csv
from collections import defaultdict
from pathlib import Path

_requirements = {}  # test id -> ["REQ-03", ...]
_outcomes = {}      # test id -> "passed" / "failed" / "skipped"


def pytest_collection_modifyitems(session, config, items):
    for item in items:
        _requirements[item.nodeid] = sorted(
            m.name for m in item.iter_markers() if m.name.startswith("REQ-")
        )


def pytest_runtest_logreport(report):
    if report.when == "call" or (report.when == "setup" and not report.passed):
        _outcomes[report.nodeid] = report.outcome


def pytest_terminal_summary(terminalreporter):
    matrix = defaultdict(lambda: {"passed": 0, "failed": 0, "skipped": 0})
    for test_id, reqs in _requirements.items():
        outcome = _outcomes.get(test_id)
        if outcome is None:  # deselected with -m, not run
            continue
        for req in reqs:
            matrix[req][outcome] += 1

    rows = [
        [req, sum(c.values()), c["passed"], c["failed"], c["skipped"]]
        for req, c in sorted(matrix.items())
    ]
    header = ["Requirement", "Scenarios", "Passed", "Failed", "Skipped/Manual"]

    terminalreporter.section("Requirement traceability")
    terminalreporter.write_line("{:<12} {:>9} {:>7} {:>7} {:>15}".format(*header))
    for row in rows:
        terminalreporter.write_line("{:<12} {:>9} {:>7} {:>7} {:>15}".format(*row))

    out = Path("reports")
    out.mkdir(exist_ok=True)
    with open(out / "traceability.csv", "w", newline="") as f:
        csv.writer(f).writerows([header, *rows])
```

How it works, in plain words:
1. **After collection**, remember which `REQ-*` tags each test has.
2. **After each test**, remember whether it passed, failed, or was skipped. (A skip happens during *setup*, so setup results are recorded too.)
3. **At the end**, count per requirement, print the table, write `reports/traceability.csv`.

Register it in `conftest.py`:

```python
pytest_plugins = [
    "tests.steps.cart_steps",
    "support.traceability",
]
```

Every run now ends with:

```
=========================== Requirement traceability ===========================
Requirement  Scenarios  Passed  Failed  Skipped/Manual
REQ-03               1       1       0               0
REQ-04               4       4       0               0
REQ-08               1       0       0               1
```

This table answers Day 1's key questions: *which requirements are covered, did they pass, and what is knowingly not automated?* Requirements missing from the table (REQ-01, 02, 05, 06, 07, 09) have **no scenarios yet** — that is your Day 3 to-do list.

---

## Part 8 — Maintainability rules & anti-patterns 🔴

### 8.1 Rules for steps

| Rule | Why |
|---|---|
| **Thin steps**: one or two lines calling `store` | Logic lives in one place; steps stay readable |
| **No selectors or URLs in steps** | A redesign must not touch step files |
| **State through fixtures**, never global variables | Scenarios stay independent and can run in parallel |
| **Assertions only in `Then`** | A failure points to a behaviour, not a setup detail |
| **One phrasing per action** | "add the product" and "put the product" as two steps is duplication |
| **Parameterize instead of copying** | `{qty:d} "{name}"` covers every product and quantity |
| **Compare with values read at runtime** | `price × qty`, never a hard-coded `£55.00` |

### 8.2 Anti-patterns (Day 4 reviews against this list)

| Anti-pattern | How to recognise it | Fix |
|---|---|---|
| Imperative scenarios | Steps mention clicks, ids, URLs | Rewrite declaratively (Day 1 §3.4) |
| Step explosion | Many near-identical step functions | Parameterize; agree on one phrasing |
| Fat steps | Selectors, loops, waits inside step functions | Move into the store object |
| Hidden setup | Business state created in a hook | Make it a visible `Given` |
| Shared state | Passes alone, fails in the suite | Function-scoped fixtures |
| Hard-coded volatile data | Fails when the store changes a price | Read at runtime |
| Untraceable scenarios | No `@REQ-*` tag | Enforce the taxonomy (Exercise L3-2) |
| Float money | Rounding failures on correct data | `Decimal` |

---

## Appendix A — The finished project

The complete project is in `day2-code/shop-bdd.zip` (verified in a fresh virtual environment: **4 passed, 1 skipped**). Run it:

```bash
pip install -r requirements.txt
```

```bash
pytest -v
```

Files not already shown in full above:

**`features/cart.feature`**

```gherkin
@web
Feature: Shopping cart
  Visitors collect products in a cart before checkout.

  Background:
    Given a visitor with an empty cart

  Rule: Added products appear in the cart with a correct subtotal

    @REQ-03 @REQ-04 @risk-high @smoke
    Scenario: Adding an available product puts it in the cart
      Given the visitor is viewing the product "Grey jacket"
      When they add the product to the cart
      Then the cart contains 1 "Grey jacket"
      And the cart subtotal equals the product price times 1

    @REQ-04 @risk-high @regression
    Scenario Outline: Subtotal follows quantity
      Given the visitor is viewing the product "<product>"
      When they add the product to the cart <times> times
      Then the cart contains <times> "<product>"
      And the cart subtotal equals the product price times <times>

      Examples:
        | product     | times |
        | Grey jacket | 2     |
        | Noir jacket | 3     |

  Rule: Several products can be added at once

    @REQ-04 @risk-high @regression
    Scenario: Cart with several products
      When they add these products to the cart:
        | product     | quantity |
        | Grey jacket | 1        |
        | Noir jacket | 2        |
      Then the cart has 3 items in total

  Rule: Account flows stay manual

    @REQ-08 @manual
    Scenario: Visitor signs up for an account
      Given the visitor is on the sign-up page
      When they register with a new email address
      Then they are logged in to their new account
```

**`conftest.py`**

```python
import pytest
from support.store import FakeStore

pytest_plugins = [
    "tests.steps.cart_steps",
    "support.traceability",
]


# ---------- Fixtures ----------
@pytest.fixture
def store():
    s = FakeStore()
    yield s          # the scenario runs here
    s.clear_cart()   # teardown: runs even if the scenario failed


# ---------- Tags ----------
def pytest_configure(config):
    for n in range(1, 10):
        config.addinivalue_line("markers", f"REQ-{n:02d}: covers requirement REQ-{n:02d}")


def pytest_bdd_apply_tag(tag, function):
    if tag == "manual":
        pytest.mark.manual(function)  # keep the tag so -m "not manual" works
        pytest.mark.skip(reason="Manual check - see strategy document")(function)
        return True
    return None


# ---------- Hooks ----------
def pytest_bdd_before_scenario(request, feature, scenario):
    print(f"\n[START] {scenario.name}  tags={sorted(scenario.tags)}")


def pytest_bdd_step_error(request, feature, scenario, step, step_func,
                          step_func_args, exception):
    print(f"\n[FAILED STEP] {step.keyword} {step.name}")
    print(f"[REASON] {exception!r}")
```

**`tests/steps/cart_steps.py`**

```python
from pytest_bdd import given, when, then, parsers


@given("a visitor with an empty cart")
def empty_cart(store):
    assert store.item_count() == 0


@given(
    parsers.parse('the visitor is viewing the product "{name}"'),
    target_fixture="product",
)
def viewing_product(store, name):
    return store.open_product(name)


@when("they add the product to the cart")
def add_once(store, product):
    store.add(product["name"])


@when(parsers.parse("they add the product to the cart {times:d} times"))
def add_many(store, product, times):
    store.add(product["name"], times)


@when("they add these products to the cart:")
def add_table(store, datatable):
    header, *rows = datatable
    for row in rows:
        item = dict(zip(header, row))
        store.add(item["product"], int(item["quantity"]))


@then(parsers.parse('the cart contains {qty:d} "{name}"'))
def cart_contains(store, qty, name):
    assert store.quantity(name) == qty


@then(parsers.parse("the cart subtotal equals the product price times {qty:d}"))
def subtotal_is_price_times(store, product, qty):
    assert store.subtotal() == product["price"] * qty


@then(parsers.parse("the cart has {total:d} items in total"))
def total_items(store, total):
    assert store.item_count() == total
```

## Appendix B — Common errors and fixes

| Error message | Meaning | Fix |
|---|---|---|
| `StepDefinitionNotFoundError: Step definition is not found: When "..."` | No step function matches this text | Check spelling word for word; check the steps module is in `pytest_plugins` |
| `fixture 'product' not found` | A step needs data no earlier step provided | Add the `Given` that has `target_fixture="product"` |
| `'smok' not found in markers configuration option` | Tag not registered (typo?) | Fix the tag or add it to `pytest.ini` |
| `no tests ran` | `scenarios(...)` missing, or file not named `test_*.py` | Check `tests/test_*.py` calls `scenarios("x.feature")` |
| `ModuleNotFoundError: No module named 'support'` | Python cannot find your folders | Run `pytest` from the project root (where `conftest.py` is); keep the `__init__.py` files |
| `FileNotFoundError ... .feature` | Wrong feature path | Paths in `scenarios()` are relative to `bdd_features_base_dir` |

---

## Exercises (your Day 2 output)

**🟢 Level 1**
1. Build Stages 0–2 yourself by typing the code (do not copy-paste — typing is how you learn it). Make each one pass, then break it on purpose and read the error.
2. Add a scenario "Adding Noir jacket twice gives 2 Noir jackets" using only existing steps.

**🟡 Level 2**
3. Add **REQ-05**: "Removing one product keeps the others". You need a `remove(name)` method in `FakeStore`, a `Given` that pre-fills the cart from a table, and a `When` that removes. Tag it correctly.
4. Write the **step catalogue** for the three Day 1 scenarios you wrote: each distinct step text and its parameters. Merge any two steps that mean the same thing.

**🔴 Level 3**
5. Add a `remove` method to the `Store` interface, and list the six other methods a `WebStore` will need on Day 3 — with no selectors yet, just names and what each returns.
6. **Enforce the tag taxonomy**: add a hook so that `pytest` refuses to run if any scenario lacks a `@REQ-*` tag, or lacks a `@risk-*` tag (unless it is `@manual`).
7. Fill your one-page **Framework Design**: folder layout, Store interface, step catalogue, hook plan, tag taxonomy, report plan.

<details>
<summary><b>Solution — Exercise 3 (verified: 5 passed, 1 skipped)</b></summary>

`support/store.py` — add to `FakeStore`:

```python
    def remove(self, name):
        self.lines.pop(name, None)
```

`features/cart.feature` — new rule before the manual one:

```gherkin
  Rule: Removing a product updates the cart

    @REQ-05 @risk-high @regression
    Scenario: Removing one product keeps the others
      Given the cart contains these products:
        | product     | quantity |
        | Grey jacket | 1        |
        | Noir jacket | 2        |
      When they remove "Grey jacket" from the cart
      Then the cart contains 0 "Grey jacket"
      And the cart contains 2 "Noir jacket"
      And the cart has 2 items in total
```

`tests/steps/cart_steps.py` — add:

```python
@given("the cart contains these products:")
def cart_prefilled(store, datatable):
    add_table(store, datatable)          # reuse, don't duplicate


@when(parsers.parse('they remove "{name}" from the cart'))
def remove_product(store, name):
    store.remove(name)
```

The traceability table now shows a `REQ-05` row.
</details>

<details>
<summary><b>Solution — Exercise 6 (verified)</b></summary>

Add to `conftest.py`:

```python
RISK_TAGS = {"risk-high", "risk-medium", "risk-low"}


def pytest_collection_modifyitems(config, items):
    problems = []
    for item in items:
        names = {m.name for m in item.iter_markers()}
        if not any(n.startswith("REQ-") for n in names):
            problems.append(f"{item.name}: missing a @REQ-xx tag")
        if "manual" not in names and not names & RISK_TAGS:
            problems.append(f"{item.name}: missing a @risk-* tag")
    if problems:
        raise pytest.UsageError("Tag rules broken:\n  " + "\n  ".join(problems))
```

Remove the tags from one scenario and run `pytest`:

```
ERROR: Tag rules broken:
  test_removing_one_product_keeps_the_others: missing a @REQ-xx tag
  test_removing_one_product_keeps_the_others: missing a @risk-* tag
```

This only works for `@manual` scenarios because the `pytest_bdd_apply_tag` hook keeps the `manual` marker (§6.3).
</details>

---

## Self-check (answers below — try first)

1. A step needs the product chosen by an earlier step. How does the data get there, and why not a global variable?
2. `@smok` is typed by mistake. What happens with and without `--strict-markers`?
3. Where does a CSS selector belong, and what breaks if it sits in a step function?
4. When is `Scenario Outline` the wrong choice?
5. Your Cucumber JSON report shows no scenario for REQ-08, yet REQ-08 has a `@manual` scenario. Why, and how did this guide solve it?
6. Which should be a hook and which a `Given`: "launch the browser", "a visitor with an empty cart"? Justify.
7. On Day 3 the FakeStore becomes a Playwright WebStore. Which folders change, and which must not?

<details>
<summary><b>Answer guide</b></summary>

1. The `Given` returns it with `target_fixture="product"`; later steps ask for `product` as a parameter. A global would survive into the next scenario, so tests would depend on run order and break in parallel runs.
2. With it: the run stops with `'smok' not found in markers`. Without it: `@smok` is silently accepted, and the scenario drops out of `-m smoke` without anyone noticing.
3. In the store object under `support/`. In a step, a theme change forces edits in many step files, and the step can no longer run on mobile.
4. When the rows describe different behaviours (e.g. one row is "sold out → error" and another is "in stock → added"). Those are different rules; write separate scenarios so each failure has a clear meaning.
5. pytest-bdd leaves skipped scenarios out of Cucumber JSON, and JUnit XML has no tags. The `support/traceability.py` plugin reads markers and outcomes directly, so skipped/manual scenarios are counted.
6. "Launch the browser" is infrastructure → a fixture/hook. "A visitor with an empty cart" is business state the reader must know → a visible `Given`.
7. Only `support/` (a new WebStore class) and the `store` fixture in `conftest.py`. `features/` and `tests/steps/` must not change — that proves the layering works.
</details>

## Next: Day 3 — the lab

Write `WebStore` with Playwright against the live store, make the cart scenarios pass in a real browser, add scenarios for the uncovered requirements, and produce screenshots, traces, and the traceability report as evidence.
