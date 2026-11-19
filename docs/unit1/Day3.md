# Unit 1 · Day 3 — BDD Implementation Lab: A Senior-Level Framework on the Real Store

| | |
|---|---|
| **Course** | Advanced Automation Test Engineering (ATEST03) — Fast Track |
| **Learning outcome** | **LO2** — Implement BDD specifications with maintainable steps, hooks, tags, reporting, and traceable evidence (Bloom **B3: Apply**) |
| **Format** | Assignment/Lab · Hybrid · 150 minutes · **code is the deliverable** |
| **System under test** | https://sauce-demo.myshopify.com/ — the real store, in a real browser |
| **Stack** | Python 3.11+ · `pytest` · `pytest-bdd` · `pytest-playwright` · `pytest-xdist` · `ruff` · `mypy` (all pinned) |
| **Starting point** | The Day 2 project (`day2-code/shop-bdd.zip`) |
| **Finished project** | `day3-code/shop-bdd.zip` — senior-level reference framework with README and CI |
| **Output of the day** | Executable specifications for all 9 requirements on a layered framework (domain model, port, page objects, API client), governed by a requirement registry, with failure evidence, a traceability matrix, quality gates, and CI |

> **What was verified, and how.** See the **Verification log** at the end. In short: every site fact was observed on the live store; the final code passed **all 20 automated scenarios and all 20 page-object tests against the live store** (one test is the expected `xfail` documenting a shop defect), with every cart read cross-checked against the shop's cart data; it passes offline and in parallel; lint, formatting, and strict type checks are clean; 48 unit tests cover the framework's own logic; every guard was tested by breaking things on purpose. The CI workflow is validated but was not run on GitHub.

---

## How to use this lab

Day 2 built the framework on a pretend store. Today has two halves:

1. **Make it work** on the real store (Parts 0–2): drive a browser, study the real pages, and learn what the real world adds — timing, hidden elements, missing labels, and a site that pushes back.
2. **Make it senior** (Parts 3–9): the architecture, governance, diagnostics, reliability, and quality gates that a team can rely on for years.

| Badge | Level | After this level you can… |
|---|---|---|
| 🟢 | **Foundation** | Drive a browser with Playwright, find elements, make one real scenario pass |
| 🟡 | **Practitioner** | Explain and extend a layered framework: domain model, port, page objects, typed steps |
| 🔴 | **Senior** | Govern traceability, separate environment failures from defects, design for low load, keep the framework itself under quality gates and CI |

### Lab plan (150 min)

| Time | Task | Level | Part |
|---|---|---|---|
| 0–15 | Setup; run quality gate and offline suite | 🟢 | 0 |
| 15–35 | First Playwright script; locators and waits | 🟢 | 1 |
| 35–50 | Reconnaissance: study the real pages | 🟡 | 2 |
| 50–85 | Read the architecture: domain, port, page objects, API, orchestrator | 🟡 | 3 |
| 85–100 | Wiring and specifications; "Your turn" tasks | 🟡 | 4–5 |
| 100–120 | Governance: registry, tag rules, traceability, coverage gate | 🔴 | 6 |
| 120–135 | Evidence and reliability: break a test, investigate from evidence only | 🔴 | 7–8 |
| 135–150 | Quality gates and CI | 🔴 | 9 |

**Core** (must finish): Parts 0–5 and both "Your turn" tasks.
**Stretch**: Parts 6–9 in depth. The reference code is complete — the goal is to **understand and extend it**, not to type 1,500 lines in 150 minutes.

---

## Site facts (observed on the live store)

These replace the "from memory" assumptions of Day 1 and Day 2. Day 1's guesses were correct.

| Fact | Observed |
|---|---|
| Products (7) | Grey jacket £55.00 · Noir jacket £60.00 (Size S/M/L × Color Blue/Red) · Striped top £50.00 · Black heels £45.00 · Bronze sandals £39.99 · **Brown Shades £20.00 — sold out** · **White sandals £25.00 — sold out** |
| Sold-out product page | Button **"Sold Out"**, disabled |
| Add to Cart | Stays on the product page; sends `POST /cart/add.js` in the background (AJAX); header link changes to **"My Cart (N)"** |
| Cart page `/cart` | One row per product variant; quantity text box with **no label**; remove link with text **"x"**; heading **"Total £X"**; buttons **Update** and **Check Out** |
| Hidden mini-cart | Every page contains a hidden copy of the cart rows with the **same element ids** |
| Search | Header search box → `/search?type=product&q=…`; heading "Search Results"; "No results found for …" |
| Product URLs | Usually the name in lower case, but **"Black heels" lives at `/products/flower-print-jeans`** |
| JSON endpoints | `/products.json` (sent as `application/json`) and `/cart.js`, `/cart/add.js` (valid JSON, but sent as **`text/javascript`**) |
| Checkout | "Check Out" leads to `/checkouts/…`, title "Checkout - Sauce Demo", with sections Contact, Delivery, Payment |
| Login / Sign up | Pages load hCaptcha/reCAPTCHA scripts → stay manual (REQ-08) |
| Bot protection | After a burst of automated visits, Cloudflare replaces pages with *"Your connection needs to be verified before you can proceed"* |

---

## Glossary (new terms)

| Term | Meaning | Vietnamese |
|---|---|---|
| Browser context | A private, isolated browser session (own cookies, own cart) — like an incognito window | Phiên trình duyệt độc lập |
| Page | One tab inside a context | Tab |
| Locator | A recipe for finding an element; looked up again every time it is used | Bộ định vị |
| Auto-wait | Playwright waits for an element to be visible, enabled, and stable before acting | Tự động chờ |
| Web-first assertion | `expect(...)` that retries until true or a timeout | Khẳng định có chờ |
| Strict mode | A locator used for an action must match exactly one element | Chế độ nghiêm ngặt |
| AJAX | The page talks to the server in the background without reloading | Gọi nền |
| Headless | Browser runs without a visible window | Chạy không giao diện |
| Trace | A recording of a test: every action, screenshot, network call | Bản ghi vết |
| Bot protection | A service (here Cloudflare) that blocks traffic it thinks is automated | Chống bot |
| Base URL | The site address that relative paths like `/cart` are joined to | URL gốc |
| xdist | pytest plugin that runs tests in parallel processes (`-n 4`) | Chạy song song |
| Page object | A class that owns the selectors and waits of one page | Đối tượng trang |
| Domain model | Typed classes for the business concepts (Money, Cart) | Mô hình nghiệp vụ |
| Port / adapter | An interface (port) and the ways of fulfilling it (adapters: fake, web, mobile) | Cổng / bộ chuyển đổi |
| Pure function | Output depends only on input; no files, network, or pytest — easy to unit-test | Hàm thuần |
| Linter / type checker | Tools that find bugs without running the code (`ruff`, `mypy`) | Công cụ phân tích tĩnh |
| CI | Continuous Integration: checks run automatically on every change | Tích hợp liên tục |
| Coverage gate | A check that fails the build when a requirement has no scenario | Cổng kiểm soát độ phủ |

---

## Part 0 — Setup 🟢

Unzip `day3-code/shop-bdd.zip`, create and activate a virtual environment (Day 2 §0.1), then:

```bash
pip install -r requirements-dev.txt
```

```bash
playwright install chromium
```

`requirements-dev.txt` installs the pinned runtime set (`requirements.txt`) plus `ruff` and `mypy`:

```
pytest==9.2.0
pytest-bdd==9.0.1
pytest-playwright==0.10.0
playwright==1.63.0
pytest-xdist==3.8.0
ruff==0.17.5
mypy==2.4.1
```

Prove everything works **before** touching the network — exactly what CI does:

```bash
ruff check . && ruff format --check . && mypy
```

```bash
pytest --store fake -n auto --fail-on-uncovered
```

```
68 passed, 22 skipped
```

That is 48 unit tests of the framework itself plus the 20 automated scenarios on the in-memory store. Skipped: the 2 `@manual` account scenarios, and the 20 page-object tests, which need the live shop (Part 10).

---

## Part 1 — Playwright for beginners 🟢

### 1.1 Three objects to remember

```
Browser  ──▶  Context (private session: own cookies, own cart)  ──▶  Page (a tab)
```

pytest-playwright creates a **new context for every test**. That is why every scenario starts with an empty cart, without any clean-up code (Day 1, isolation).

### 1.2 Your first script

Save as `first_script.py` (outside the project folder) and run `python first_script.py`. A browser window opens and you can watch it work.

```python
from playwright.sync_api import sync_playwright, expect

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)       # headless=True: no window
    context = browser.new_context()                    # a fresh, private "incognito" session
    page = context.new_page()                          # one tab

    page.goto("https://sauce-demo.myshopify.com/products/grey-jacket")

    # 1. Find elements the way a user sees them
    title = page.locator("[itemprop='name']")
    add_button = page.get_by_role("button", name="Add to Cart")

    print("Product:", title.inner_text())
    print("Price:  ", page.locator("#product-price").inner_text())

    # 2. Act, and wait for the server to confirm
    with page.expect_response(lambda r: "/cart/add" in r.url):
        add_button.click()

    # 3. Check: web-first assertion, retries until true or 5 s timeout
    expect(page.get_by_role("link", name="My Cart (1)")).to_be_visible()
    print("Cart link now says:", page.get_by_role("link", name="My Cart (1)").inner_text())

    browser.close()
```

Expected output:

```
Product: Grey jacket
Price:   £55.00
Cart link now says: My Cart (1)
```

### 1.3 Locators — how to find elements

Same priority as Day 1 §2.3, now with real examples from this store:

| Priority | Method | Real example on this store |
|---|---|---|
| 1 | `get_by_role(role, name=...)` | `page.get_by_role("button", name="Add to Cart")` |
| 2 | `get_by_label` / `get_by_text` / `get_by_placeholder` | `page.get_by_text("No results found for")` |
| 3 | Stable attribute | `page.locator("[itemprop='name']")` — a schema.org attribute that themes keep for search engines |
| 4 | CSS id / class | `page.locator("#cart .row")` — only when nothing better exists |

**Two facts beginners often miss:**

- A locator is a *recipe*, not an element. It is looked up again every time you use it, so it never goes stale after a page reload.
- `get_by_role` only sees elements that are **visible** to users (in the accessibility tree). CSS locators also see **hidden** elements. On this store, that difference matters (Part 2).

### 1.4 Actions, waits, and assertions

| You write | Playwright does |
|---|---|
| `button.click()` | Waits until the button is visible, enabled, and not moving, then clicks |
| `box.fill("jacket")` | Waits until the box is editable, then replaces its text |
| `expect(x).to_be_visible()` | Checks again and again for up to 5 s |
| `expect(x).to_have_text("Grey jacket")` | Same, for text |
| `with page.expect_response(...)` | Waits for a specific network answer from the server |

**Never use `time.sleep(3)`.** It is too long when the site is fast (slow suite) and too short when it is slow (flaky test). Always wait for a **condition**.

### 1.5 Discover locators with the recorder (not run while preparing this guide)

```bash
playwright codegen https://sauce-demo.myshopify.com
```

A browser opens. Click around and Playwright writes the code, choosing role-based locators where it can. Use it to **learn** locators, not to produce your framework: recorded code is imperative and repetitive, which is exactly what the layers from Day 2 avoid.

> **Checkpoint 1.** Why does the script wait for the `/cart/add` response instead of just checking the cart link right after the click?

---

## Part 2 — Reconnaissance: study the pages before coding 🟡

Professional automation starts by **observing**, not typing. Two tools:

1. **Accessibility snapshot** — shows what `get_by_role` can see:
   ```python
   print(page.locator("body").aria_snapshot())
   ```
2. **Browser DevTools** (F12) → Elements and Network tabs.

The real product page, as `get_by_role` sees it (trimmed):

```yaml
- heading "Grey jacket" [level=1]
- heading "£55.00" [level=2]
- combobox:
  - option "Grey jacket" [selected]
- button "Add to Cart"
```

A sold-out product:

```yaml
- heading "Brown Shades" [level=1]
- heading "£20.00" [level=2]
- button "Sold Out" [disabled]
```

The cart page:

```yaml
- heading "My Cart" [level=1]
- heading "Noir jacket - M / Blue" [level=3]
- text: £60.00
- textbox: "1"            # ← quantity box: no name!
- text: £60.00
- link "x"                # ← remove link: the name is just "x"
- heading "Grey jacket - Grey jacket" [level=3]
- ...
- heading "Total £115.00" [level=2]
- button "Update"
- button "Check Out"
```

### 2.1 Six testability findings (each one shapes the code)

| # | Finding | Evidence | Design decision |
|---|---|---|---|
| 1 | **Add to Cart is AJAX** | The URL does not change; `POST /cart/add.js` runs in the background | Wait for that response after every click (§2.2) |
| 2 | **Hidden duplicate mini-cart** with the **same ids** | `#updates_611945025` matches 2 elements → strict mode error (§2.3) | Scope every cart locator to `#cart`; prefer role locators, which ignore hidden elements |
| 3 | **Quantity box has no label**; remove link is named "x" | Accessibility snapshot above | Find the row by its product heading, then use a CSS locator **inside that row only** |
| 4 | **URL ≠ product name** | "Black heels" → `/products/flower-print-jeans` | Never build URLs from names; look them up in `/products.json` |
| 5 | **CAPTCHA** on login and sign-up | hCaptcha/reCAPTCHA scripts in the page | REQ-08 stays `@manual` (Day 1 decision confirmed) |
| 6 | **Bot protection** under load | Cloudflare verification page | Detect it, report it separately, keep load low (Part 8) |

Findings 2 and 3 are **testability defects** worth reporting to the site's developers: a label on the quantity box and unique ids would make the site more accessible *and* more testable.

### 2.2 Finding 1 in detail: the `networkidle` trap

A tempting way to wait after clicking "Add to Cart":

```python
button.click()
page.wait_for_load_state("networkidle")   # "wait until the network is quiet"
```

Result observed on the live store, clicking twice:

```
after 1st click: cart.js item_count = 1
after 2nd click: cart.js item_count = 1    ← wrong, should be 2
```

Why: `wait_for_load_state` waits for a page **load state**, which happens once per page load. After the first time, it returns **immediately**, so the test reads the cart before the second add has finished. It passes on a fast day and fails on a slow day — a classic flaky test.

The fix — wait for the exact event that proves the action finished:

```python
with page.expect_response(lambda r: "/cart/add" in r.url) as info:
    button.click()
assert info.value.ok
```

Observed: `add 1 → count 1`, `add 2 → count 2`, `add 3 → count 3`.

### 2.3 Finding 2 in detail: strict mode

```python
page.locator("#updates_611945025").fill("3")
```

```
Error: strict mode violation: locator("#updates_611945025") resolved to 2 elements
```

Playwright refuses to guess which of two elements you meant. That is a feature: without it, the test might type into the hidden mini-cart and pass or fail for the wrong reason. Fix: `page.locator("#cart")…` — search only inside the visible cart.

> **Checkpoint 2.** `get_by_role("button", name="Check Out")` finds exactly one element, although the hidden mini-cart also contains a "Check Out" button. Why?

---

## Part 3 — From a working class to a senior architecture 🟡 → 🔴

### 3.1 Why "it works" is not the finish line

A first version of this lab put everything in one `WebStore` class: selectors, waits, JSON calls, bot detection, and cart caching. It passed 15 of 15 scenarios live. A senior reviewer would still reject it:

| Smell in the first version | Why it hurts on a real team | Senior version |
|---|---|---|
| One 200-line class does everything | Every change touches the same file; hard to review and test | **Page objects** per page, an **API client**, a **guard**, a thin **orchestrator** |
| Steps pass `dict`s (`product["price"]`) | Typos found only at runtime; no editor help | **Typed domain objects** (`Product`, `Cart`, `Money`) |
| Blocked runs found by searching error text | Rename the message and the report silently lies | Classified by **exception type** |
| Tags checked by hand in review | A forgotten tag breaks traceability unnoticed | **Requirement registry** + automatic tag rules |
| Matrix only shows what ran | A requirement with no scenario is invisible | Matrix lists **every** requirement, `NOT COVERED` included, plus a CI **coverage gate** |
| UI numbers trusted as shown | A page showing a wrong total but the right data passes | **Cross-layer check**: cart page vs cart JSON on every read |
| `print()` for diagnostics | Lost in parallel runs, no timestamps | **Logging**, plus evidence files per failing step |
| No checks on the framework code | Framework bugs look like product bugs | **ruff**, **mypy --strict**, **unit tests** for framework logic, **CI** |

Everything in this part is in `day3-code/shop-bdd.zip`. You are not expected to type it all in 150 minutes: read it in this order, run it, then do the "Your turn" tasks.

### 3.2 The architecture map

```
features/*.feature            WHAT: business behaviour, tagged with requirement + risk
        │
tests/steps/*.py              GLUE: thin, typed steps; call the Store port only
        │
framework/ports.py            Store protocol  ◀── the only API steps may use
        │
        ├── framework/adapters/fake.py          in-memory, fed by tests/data/catalogue_snapshot.json
        └── framework/adapters/web/
              store.py        orchestration + cross-layer consistency check
              api.py          shop JSON endpoints, called inside the page (same cookies)
              guard.py        bot-check / outage detection
              diagnostics.py  console errors + failed shop requests, kept for failures
              shop.py         Shop facade: one entry point to every page object (+ API)
              components/     header, main menu, mini-cart, product grid, breadcrumb
              pages/          page objects: the ONLY place with selectors and waits
        │
framework/domain.py           Money, Catalogue, Product, Cart, OrderSummary, ...: immutable typed values
framework/testdata.py         builders: unique_email(), new_customer()
framework/plugins/            pytest plugins: fixtures, tag rules, evidence, traceability
requirements.toml             requirement registry: ids, titles, risk (single source of truth)
```

**Layer rules** (they are also in the project README and are checked on Day 4):

1. Feature files contain no selectors, URLs, or clicks.
2. Steps call only `Store` methods and assert on domain objects. No Playwright imports.
3. Selectors and waits live only in `framework/adapters/web/pages/`.
4. Every wait waits for proof (a server response, a URL, a visible element). No `sleep`.
5. Money is `Money` (Decimal). Never float.
6. Volatile data (prices, sold-out products) is read at runtime, never hard-coded.
7. Logic in plugins lives in pure functions with unit tests; hooks only adapt.

This is the **ports and adapters** pattern: the steps depend on a *port* (an interface), and each way of reaching the shop is an *adapter*. Unit 3 adds a mobile adapter without touching features or steps.

### 3.3 The domain model: typed, immutable values

`framework/domain.py` describes the shop's concepts. Everything above the adapters speaks this language.

```python
@dataclass(frozen=True, order=True)
class Money:
    """An exact amount of money. Never use float for money."""

    amount: Decimal
    currency: str = "GBP"
```

`Money.parse("£1,055.00")`, `Money.from_minor_units(5500)` (the cart JSON counts pence), `+`, and `* quantity` are all exact. Adding GBP to USD raises an error instead of producing nonsense.

```python
@dataclass(frozen=True)
class Cart:
    """An immutable snapshot of the cart at one moment."""

    lines: tuple[CartLine, ...]
    total: Money
```

| Design choice | Why |
|---|---|
| `frozen=True` | A snapshot cannot be changed by accident halfway through a scenario |
| `Cart.quantity_of(name)` sums all variants | "2 Noir jackets" may be 1 × S + 1 × M |
| `Cart.describe()` | Readable failure messages: `expected 3 x Grey jacket, cart: 1 x Grey jacket (Grey jacket); total £55.00` |
| `Catalogue.by_name` raises `DataUnavailableError` listing real names | A typo in a feature file explains itself |

### 3.4 The port

`framework/ports.py` — the contract every adapter must fulfil:

```python
@runtime_checkable
class Store(Protocol):
    # --- catalogue -------------------------------------------------------
    def open_product(self, name: str) -> Product: ...
    def catalogue_price(self, name: str) -> Money: ...
    def catalogue_data(self) -> Catalogue: ...
    def catalogue_listing(self) -> list[ProductCard]: ...
    def find_sold_out_product(self) -> str | None: ...
    def search(self, keyword: str) -> list[str]: ...

    # --- cart ------------------------------------------------------------
    def add(self, name: str, quantity: int = 1) -> None: ...
    def add_variant(self, name: str, variant: str, quantity: int = 1) -> None: ...
    def try_add(self, name: str) -> bool: ...
    def prefill(self, items: Mapping[str, int]) -> None: ...
    def set_quantity(self, name: str, quantity: int) -> None: ...
    def remove(self, name: str) -> None: ...
    def cart(self) -> Cart: ...

    # --- navigation ------------------------------------------------------
    def go_to_checkout(self) -> str: ...
    def checkout_summary(self) -> OrderSummary: ...
    def open_menu_page(self, link: str) -> str: ...
    def open_latest_article(self) -> tuple[str, str]: ...  # (title in the list, title on the page)
    def open_missing_page(self) -> tuple[int | None, str]: ...  # (HTTP status, page title)
```

Reading the cart is now **one** method returning a snapshot (`cart()`), instead of separate `quantity()`, `item_count()`, `subtotal()` calls that each reloaded the page.

### 3.5 Page objects: selectors and waits in one place

Every page object follows one contract, defined in `framework/adapters/web/pages/base.py`:

```python
    def open_path(self, path: str) -> Self:
        response = self.page.goto(path)
        self.last_status = response.status if response else None
        ensure_not_blocked(self.page, self.last_status)
        self.wait_until_loaded()
        return self

    def wait_until_loaded(self) -> None:
        """Override: wait for the element that proves this page is ready."""
```

So "opened" always means: navigated, **checked for a bot page**, and **proved ready**. No caller can forget either step.

| Page object | Owns |
|---|---|
| `HomePage` | `/`; ready when the search box is visible |
| `Header` | Search box, "My Cart (N)" link, main menu (present on every page) |
| `ProductPage` | Title, price, Add to Cart, Sold Out |
| `CartPage` | Rows, quantity boxes, remove links, total, Update, Check Out |
| `SearchResultsPage` | Result titles |
| `CheckoutPage` | Read-only: proves checkout loaded, never enters data |

Part 10 extends this list to every page of the shop.

**`ProductPage.add_to_cart`** — the `networkidle` lesson from §2.2, now living in exactly one place:

```python
    def add_to_cart(self, times: int = 1) -> None:
        """Click Add to Cart and wait for the server to confirm every click.

        Add to Cart is AJAX. A load-state wait (e.g. "networkidle") returns
        at once on an already-loaded page, so it cannot prove the add finished.
        """
        for _ in range(times):
            response = self.click_add_to_cart()
            if not response.ok:
                raise AssertionError(f"add to cart failed: HTTP {response.status}")

    def click_add_to_cart(self) -> Response:
        """Click once and return the server's answer, whatever it is (for error-handling tests)."""
        with self.page.expect_response(lambda r: "/cart/add" in r.url) as response:
            self.add_button.click()
        return response.value
```

> 🔴 **Why `raise AssertionError` and not `assert` in framework code?** Python removes `assert` statements when it runs with `-O`. A check written with `assert` inside a page object would then **silently disappear**, and a failed Add to Cart would pass. Tests may use `assert` (pytest rewrites and reports them); framework code raises explicitly. The linter enforces this (ruff rule `S101`, allowed only under `tests/`).

**Locators are declared, not called.** Each page object and component lists its selectors as string constants in a `# --- Locators ---` section at the **bottom of the class**. Methods use only those names; a selector that depends on data is a template filled with `.format(...)`. An architecture test (`test_page_objects_declare_their_locators`) fails the build if a page object calls `get_by_role(...)` or writes a selector inline. Playwright reads these strings directly:
- CSS (`#cart`);
- `role=` (`role=button[name='Add to Cart']`, `role=heading[level=3]`);
- `text=`;
- `>>` for "inside".

The full list is in `framework/adapters/web/selectors.py`.

**`CartPage`** — findings 2 and 3 from §2.1 (hidden duplicate mini-cart, unlabeled quantity box):

```python
    def _rows(self) -> Locator:
        return self.root.locator(self._row).filter(has=self.find(self._row_title))

    def _rows_for(self, name: str) -> Locator:
        handle = self._catalogue.by_name(name).handle
        return self._rows().filter(has=self.find(self._row_product_link.format(handle=handle)))
    ...

    # --- Locators -------------------------------------------------------------
    _root = "#cart"
    _heading = "role=heading[level=1][name='My Cart']"
    _empty_message = "text=It appears that your cart is currently empty!"
    ...
    # Rows (inside _root): a row is a product line when it has a level-3 heading.
    _row = ".row"
    _row_title = "role=heading[level=3]"
    _row_product_link = "h3 a[href$='/products/{handle}']"
    _row_quantity = "input[name='updates[]']"
    _row_remove_link = "role=link[name='x']"
```

1. `self.root` is `#cart` (`_root`): only the **visible** cart.
2. A row is identified by its product **link** (`/products/<handle>`), not by heading text. Heading text such as "Grey jacket - Grey jacket" is theme formatting; the link is data. That also handles "Black heels" → `flower-print-jeans`.
3. The unlabeled quantity box is then found **inside that one row**: a weak CSS locator made safe by a tiny search area.

### 3.6 The API client: setup fast, judge the body

`framework/adapters/web/api.py` calls the shop's JSON endpoints with `fetch()` **inside the page**, so requests carry the page's cookies: the cart set up through the API is the cart the UI shows.

```python
        result = self._page.evaluate(_FETCH, [method, path, body])
        # Judge the body, not the Content-Type header: this shop sends valid
        # JSON from /cart.js and /cart/add.js labelled "text/javascript".
        if result["json"] is None:
            raise EnvironmentBlockedError(f"{method} {path} returned HTTP {result['status']} without JSON")
        if result["status"] >= 400:
            raise AssertionError(f"{method} {path} failed: HTTP {result['status']} {result['json']}")
        return result["json"]
```

Two outcomes, two meanings: HTML instead of JSON = the environment blocked us; JSON with an error status = the shop refused, which is a real failure.

### 3.7 The orchestrator and the cross-layer check

`framework/adapters/web/store.py` combines page objects and API, and adds a guarantee the first version lacked:

```python
    def cart(self) -> Cart:
        if self._cart is None:
            page = self._open_cart_page()
            ui_cart = page.read()
            data_cart = self.api.cart()
            self._check_consistent(ui_cart, data_cart, page.header_count())
            self._cart = ui_cart
        return self._cart
```

Every cart read compares **three** sources: the cart page rows and total, the shop's cart JSON, and the "My Cart (N)" header. If they disagree, the scenario fails with a precise message:

```
CartInconsistencyError: cart page disagrees with cart data: total: page £100.00 vs data £110.00
```

`CartInconsistencyError` is an `AssertionError`: a disagreement is a **product defect**, not an environment problem. The snapshot is cached until something changes the cart (`add`, `prefill`, `set_quantity`, `remove` reset it), so three `Then` steps cost one page load.

### 3.8 The fake, fed by real data

`FakeStore` no longer invents products. It loads `tests/data/catalogue_snapshot.json`, a trimmed recording of the live `/products.json`, so offline runs use the real 7 products, real prices, and the real 2 sold-out items:

```python
    @classmethod
    def from_snapshot(cls, path: Path = DEFAULT_SNAPSHOT) -> FakeStore:
        return cls(Catalogue.from_products_json(json.loads(path.read_text(encoding="utf-8"))))
```

Unit tests state the store facts the scenarios depend on (`Black heels` lives at `flower-print-jeans`; `Brown Shades` and `White sandals` are sold out). If the live shop changes, re-record the snapshot and those tests tell you which assumptions broke.

> **Your turn (🟡).** Open `framework/adapters/web/pages/cart.py` and explain, line by line, how `remove_all` handles a product that has two variants in the cart. Then find the one line that waits for the server.

---

## Part 4 — Wiring: configuration and fixtures 🟡

### 4.1 `pyproject.toml` replaces `pytest.ini`

One file configures pytest, ruff, and mypy. The pytest part:

```toml
[tool.pytest.ini_options]
minversion = "8.3"
testpaths = ["tests"]
pythonpath = ["."]
bdd_features_base_dir = "features"
base_url = "https://sauce-demo.myshopify.com"
requirements_registry = "requirements.toml"
addopts = [
    "--strict-markers",
    "--strict-config",
    "-ra",
    "--screenshot=only-on-failure",
    "--tracing=retain-on-failure",
    "--output=reports/artifacts",
]
```

| Setting | Why |
|---|---|
| `--strict-config` | A typo in a config key is an error, not silently ignored |
| `filterwarnings = ["error", ...]` | Any new warning fails the run, so deprecations are fixed before they break you. The one known warning from a third-party plugin is explicitly ignored, with a comment saying why |
| `log_level`, `log_format` | Each step and store action is logged with a timestamp (Part 7) |

Dependencies are **pinned** to the exact versions this suite was verified with (`requirements.txt`, `requirements-dev.txt`). "It worked yesterday" problems caused by a silent library upgrade cannot happen.

### 4.2 Settings: option > environment variable > default

`framework/config.py` adds three options. Each also reads an environment variable, which is how CI systems usually pass settings:

| Option | Environment variable | Default |
|---|---|---|
| `--store web\|fake` | `SHOP_STORE` | `web` |
| `--ui-timeout <ms>` | `SHOP_UI_TIMEOUT_MS` | `15000` |
| `--fail-on-uncovered` | — | off |

They are read once into a frozen `Settings` object; nothing else reads options directly.

### 4.3 Fixtures

`framework/plugins/fixtures.py`:

```python
@pytest.fixture
def store(request: pytest.FixtureRequest, settings: Settings) -> Iterator[Store]:
    """The Store adapter for this scenario. A new one (and a new cart) every time."""
    if settings.store == "fake":
        yield FakeStore.from_snapshot()
        return

    page = request.getfixturevalue("page")  # pytest-playwright: fresh browser context per test
    page.set_default_timeout(settings.ui_timeout_ms)
    diagnostics = BrowserDiagnostics(settings.base_url)
    diagnostics.attach(page)
    yield WebStore(page, request.getfixturevalue("live_catalogue"), diagnostics)
    # No clean-up request: the browser context (and its cart) is discarded by pytest-playwright.
```

- The fixture is typed as the **port** (`Store`), so steps cannot reach adapter internals.
- The browser is requested lazily: `--store fake` never starts one.
- `live_catalogue` has `scope="session"`: `/products.json` is read once per run (per parallel worker).

### 4.4 `conftest.py` is a table of contents

```python
pytest_plugins = [
    "framework.plugins.fixtures",
    "framework.plugins.tags",
    "framework.plugins.evidence",
    "framework.plugins.traceability",
    "tests.steps.cart_steps",
    "tests.steps.catalogue_steps",
    "tests.steps.navigation_steps",
]
```

No logic. Each plugin has one responsibility and can be read, tested, and reused alone.

### 4.5 Run it

```bash
pip install -r requirements-dev.txt
```

```bash
pytest --store fake -n auto
```

```bash
pytest tests/test_*.py -m smoke --headed
```

```bash
pytest tests/test_*.py -m "not manual"
```

`pytest` with no path also runs `tests/unit` (the framework's own tests). `tests/test_*.py` selects only the BDD scenarios.

---

## Part 5 — Specifications for every requirement 🟡

### 5.1 Feature files

The Gherkin is unchanged from the first version of this lab — the specification did not need to change when the architecture did.

| File | Requirements | Scenarios |
|---|---|---|
| `cart.feature` | REQ-03, 04, 05, 06 | Add one product · Subtotal follows quantity (outline × 2) · Several products · Remove one keeps others · Change quantity · Sold-out cannot be added |
| `catalogue.feature` | REQ-01, 02 | Keyword search · Unknown word finds nothing · Product page matches catalogue (outline × 3) |
| `checkout.feature` | REQ-07 | Proceeding from the cart reaches checkout |
| `navigation.feature` | REQ-09 | Main menu opens an information page (outline × 2) |
| `account.feature` | REQ-08 | Sign up · Log in — both `@manual`, reason (CAPTCHA) written in the feature description |

The new cart rules:

```gherkin
  Rule: Changing the cart updates the subtotal

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

    # (excerpt: the second REQ-05 scenario, "Changing the quantity updates the subtotal", is omitted here)

  Rule: Sold-out products cannot be bought

    @REQ-06 @risk-medium @regression
    Scenario: A sold-out product cannot be added to the cart
      Given the visitor is viewing a sold-out product
      When they try to add the product to the cart
      Then the product is not added
      And the cart has 0 items in total
```

### 5.2 Typed, thin steps

From `tests/steps/cart_steps.py`:

```python
@given(parsers.parse('the visitor is viewing the product "{name}"'), target_fixture="product")
def viewing_product(store: Store, name: str) -> Product:
    return store.open_product(name)


@given("the cart contains these products:")
def cart_prefilled(store: Store, datatable: list[list[str]]) -> None:
    store.prefill(_table_to_items(datatable))  # setup through the fastest reliable layer
```

```python
@then(parsers.parse('the cart contains {quantity:d} "{name}"'))
def cart_contains(store: Store, quantity: int, name: str) -> None:
    cart = store.cart()
    assert cart.quantity_of(name) == quantity, f"expected {quantity} x {name}, cart: {cart.describe()}"
```

The pattern of every step: **one call to the port, then (in `Then`) one assertion with a message that shows the whole cart**. A failure reads like a bug report, not like `assert 0 == 1`.

### 5.3 A deliberate refactor, protected by tests

Compared with Day 2, the **step texts and feature files are unchanged**, but the step *bodies* changed: `product["name"]` became `product.name`, and `store.quantity(...)` became `store.cart().quantity_of(...)`. This is the normal life of a framework: the interface was improved once, on purpose, and the offline suite proved nothing broke within a second of each change. That is the real value of `--store fake`.

### 5.4 Data chosen at runtime, checks written as properties

- **Sold-out product:** the step asks the catalogue for *any* sold-out product, and skips with a clear reason if the shop restocks everything. Nothing is hard-coded.
- **Search:** "at least 2 results" and "every result mentions *jacket*" are **properties** of a correct result. A new jacket tomorrow does not break the test — and should not.
- **Prices:** always compared with the catalogue price read during the run (REQ-02 compares UI price with `/products.json`).

> **Your turn (🟡).** Add a scenario for REQ-04: "Adding two different products gives the sum of their prices". Use only existing steps. Run it with `--store fake` first, then live.

---

## Part 6 — Governance: registry, tag rules, traceability 🔴

### 6.1 The requirement registry

`requirements.toml` is the single source of truth for requirement IDs, titles, and risk levels (from the Day 1 risk register):

```toml
[REQ-04]
title = "Cart shows correct items, quantities, subtotal"
risk = "high"
```

Markers `@REQ-01` … `@REQ-09` are registered **from this file**, so an unknown tag such as `@REQ-99` is rejected by `--strict-markers` at once.

### 6.2 Tag rules as a pure function

`framework/requirements.py` holds the rules; it imports nothing from pytest:

```python
def tag_problems(tags: Iterable[str], registry: Mapping[str, Requirement]) -> list[str]:
```

| Rule | Example of a broken tag set |
|---|---|
| ≥ 1 `@REQ-xx`, each in the registry | no requirement tag |
| Exactly 1 `@risk-*`, equal to the **highest** risk of its requirements | `@REQ-01 @risk-high` (registry says medium) |
| Exactly 1 of `@smoke` / `@regression` | neither, or both |
| ≥ 1 platform tag | no `@web` |
| `@manual` scenarios need no risk or suite tag | — |

Because it is a pure function, 10 unit tests cover it in milliseconds. The plugin only feeds it each scenario's tags. Real output when two scenarios were broken on purpose:

```
ERROR: Tag rules broken:
  test_searching_for_an_unknown_word_finds_nothing: @risk-high but registry says medium for ['REQ-01']
  test_product_page_matches_the_catalogue[Grey jacket]: needs exactly one of @smoke/@regression, found []
  test_product_page_matches_the_catalogue[Noir jacket]: needs exactly one of @smoke/@regression, found []
  test_product_page_matches_the_catalogue[Striped top]: needs exactly one of @smoke/@regression, found []
```

### 6.3 Lesson: a guard that never fires is worse than none

The first version of this plugin recognised scenarios through an attribute (`__scenario__`) that older pytest-bdd versions put on test functions. **pytest-bdd 9 no longer does.** The plugin therefore found zero scenarios, checked nothing, and the run stayed green — even with broken tags. Only a deliberate negative test (break a tag, expect a failure) revealed it.

The fix reads tags through pytest **markers** (a public API) and adds a fail-loud guard:

```python
def _is_scenario(item: pytest.Item) -> bool:
    # pytest-bdd gives every scenario test this parameter. If a future version
    # stops doing so, the guard below fails the run loudly instead of letting
    # the tag rules silently check nothing.
    return "_pytest_bdd_example" in getattr(item, "fixturenames", ())
```

If BDD test modules are collected but no scenario is recognised, the run stops with an explanation. Senior rule: **every validator gets a test that proves it can fail.**

### 6.4 The traceability matrix

Two inputs, combined by pure functions in `framework/traceability.py`:

1. **Declared** — the feature files, parsed with the official Gherkin parser: which scenarios claim which requirement.
2. **Executed** — each test report's requirement markers and outcome class.

Real output of the final live run:

```
=========================== Requirement traceability ===========================
Req     Risk    Title                                          Decl Pass Fail Blck  Man  Status
REQ-01  medium  Search products by keyword                        2    2    0    0    0  PASS
REQ-02  medium  Product page shows name, price, availability      2    4    0    0    0  PASS
REQ-03  high    Add an available product to the cart              2    2    0    0    0  PASS
REQ-04  high    Cart shows correct items, quantities, subtotal    3    4    0    0    0  PASS
REQ-05  high    Change quantity or remove an item                 2    2    0    0    0  PASS
REQ-06  medium  Sold-out product cannot be added                  2    2    0    0    0  PASS
REQ-07  medium  Proceed from cart to checkout                     2    2    0    0    0  PASS
REQ-08  medium  Sign up and log in                                2    0    0    0    0  NOT RUN
REQ-09  low     Information pages reachable from navigation       3    4    0    0    0  PASS
================= 20 passed, 2 deselected in 77.75s (0:01:17) ==================
```

(`Decl` counts scenarios as written; an outline counts once but runs once per example row, which is why REQ-02 shows 2 declared and 4 passed (the outline runs for 3 products). REQ-08 is `NOT RUN` because that run used `-m "not manual"`; a full run shows `MANUAL`.)

| Status | Meaning |
|---|---|
| `PASS` | Has scenarios, all executed ones passed |
| `FAIL` | At least one product defect |
| `BLOCKED` | Environment stopped at least one scenario, none failed |
| `MANUAL` | Only manual scenarios |
| `NOT RUN` | Has scenarios, none selected in this run |
| `NOT COVERED` | **No scenario at all** — invisible in the first version |

Written also to `reports/traceability.csv` and `reports/traceability.md` (renders as a table on GitHub).

### 6.5 The coverage gate

Add a requirement to the registry without writing a scenario:

```toml
[REQ-10]
title = "Apply a discount code"
risk = "high"
```

```bash
pytest --store fake --fail-on-uncovered
```

```
REQ-10  high    Apply a discount code                             0    0    0    0    0  NOT COVERED
Coverage gate failed - no scenarios for: ['REQ-10']
```

Exit code 1. CI runs with this option, so "we agreed a requirement but nobody specified it" cannot merge unnoticed.

---

## Part 7 — Evidence and diagnosability 🔴

A senior framework answers "what happened?" without rerunning anything. Verified with one scenario broken on purpose (expected title "Wrong title"):

### 7.1 Logs: the story of the scenario

```
------------------------------ Captured log call -------------------------------
02:30:44 INFO  shop.bdd: SCENARIO Main menu opens an information page  tags=['REQ-09', 'regression', 'risk-low']
02:30:44 INFO  shop.bdd:   When the visitor opens "About Us" from the main menu
02:30:44 INFO  shop.web: open menu page 'About Us'
02:30:46 INFO  shop.bdd:   Then a page titled "Wrong title" is shown
02:30:46 ERROR shop.bdd: FAILED STEP: Then a page titled "Wrong title" is shown -> AssertionError("expected a title containing 'Wrong title', got 'About Us – Sauce Demo'...")
```

Two loggers: `shop.bdd` (business steps) and `shop.web` (what the adapter did). pytest shows them only for failing tests, so passing runs stay quiet.

### 7.2 Files

```
reports/
├── evidence/test_main_menu_opens_an_information_page_About_Us_Wrong_title/
│   ├── Then_a_page_titled_Wrong_title_is_shown.png    # screen at the failing business step
│   └── Then_a_page_titled_Wrong_title_is_shown.json   # step, error, URL, browser clues
├── artifacts/tests-test-navigation-py-test-main-menu-…/
│   ├── test-failed-1.png
│   └── trace.zip                                      # playwright show-trace <file>
├── traceability.csv
└── traceability.md
```

The JSON file:

```json
{
  "scenario": "Main menu opens an information page",
  "step": "Then a page titled \"Wrong title\" is shown",
  "error": "AssertionError(\"expected a title containing 'Wrong title', got 'About Us – Sauce Demo' ...\")",
  "url": "https://sauce-demo.myshopify.com/pages/about-us",
  "console_errors": ["..."],
  "failed_requests": []
}
```

`BrowserDiagnostics` records browser console errors and **the shop's own** failed requests (status ≥ 400) during the scenario. Third-party analytics noise is ignored, and repeated messages are counted (`"... (x14)"`) instead of repeated. During this lab the console list held only messages caused by the test environment's network, which is exactly why this evidence is kept as *clues*, not as test failures.

---

## Part 8 — Reliability engineering 🔴

### 8.1 Environment failures are not product defects

During this lab, the store's Cloudflare protection replaced pages with *"Your connection needs to be verified"* twice. Without special handling, one run reported 15 failures — 15 bogus bugs.

The senior design classifies by **exception type**, not by message text:

```python
@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[None]
) -> Generator[None, pytest.TestReport, pytest.TestReport]:
    report = yield
    if call.excinfo is not None and call.excinfo.errisinstance(EnvironmentBlockedError):
        report.user_properties.append((OUTCOME_KEY, "blocked"))
    return report
```

The label travels **inside the test report**, which parallel workers send to the main process, so classification also works with `-n 4`.

Where `EnvironmentBlockedError` comes from:

| Detector | Trigger |
|---|---|
| `guard.ensure_not_blocked` (every page open) | HTTP 403/429/503, or a bot-check text such as "connection needs to be verified" |
| `StoreApi._call` | The body is not JSON |
| `live_catalogue` fixture | `/products.json` is not JSON |

**The false alarm.** An earlier detector decided "blocked" when the `Content-Type` header did not contain `json`. On a live run, 3 scenarios were reported Blocked while the scenarios between them passed. Checking the real responses showed why:

```
/cart/add.js    200  text/javascript; charset=utf-8   {"items":[{"id":611945025, ...
/cart.js        200  text/javascript; charset=utf-8   {"token":"...
/products.json  200  application/json; charset=utf-8  {"products":[...
```

Valid JSON, labelled as JavaScript. The fix: judge the **body**. Lesson: a classifier that is too eager hides real failures as surely as a missing one invents fake ones. When only one code path is "blocked" and its neighbours pass, suspect the detector first.

> **Never try to get around bot protection** (fake user agents, CAPTCHA solvers, rotating IPs). It is the site owner's security control. On a site you own, ask for a test environment or an allow-list. On a site you do not own, reduce your load and accept the limit.

### 8.2 Design for low load

| Technique | Where | Saving per scenario |
|---|---|---|
| Catalogue read once per run | `live_catalogue`, `scope="session"` | 1 request |
| Cart snapshot cached until the cart changes | `WebStore.cart()` | up to 3 page loads |
| Setup through the API | `prefill` | several page loads |
| No clean-up request | new browser context = new cart | 1 request |
| Serial live runs | CI `live` job; README | avoids bursts |

### 8.3 Parallel runs

```bash
pytest --store fake -n auto
```

`-n auto` uses one worker per CPU core. The Day 2 traceability plugin printed an **empty** table in parallel runs, because it stored tags during collection, which happens only inside workers. The current plugin reads everything from reports. Parallel runs are for offline and owned environments — never for a shared third-party site.

### 8.4 Flakiness checklist (used on Day 4)

| Question | This framework |
|---|---|
| Any `sleep`? | None |
| Waiting for proof that an action finished? | `expect_response` after add/update/remove; `wait_for_url` after navigation; `wait_until_loaded` on every page |
| Locators unique and scoped? | Role locators; CSS only inside `#cart` rows identified by product link |
| Fresh state per scenario? | New browser context per test |
| Volatile data hard-coded? | No |
| Environment problems separated? | `BLOCKED` status by exception type |
| Automatic retries? | Not used on purpose: retries turn a 1-in-5 failure into "green" and hide timing bugs |

### 8.5 Exit criterion: three consecutive green runs

```bash
pytest tests/test_*.py -m "not manual"
```

Three times, a few minutes apart. A run that is `BLOCKED` counts neither way: wait and rerun.

---

## Part 9 — Quality gates for the framework itself 🔴

Test code is production code for the team that depends on it. It gets the same gates.

### 9.1 Static checks

```bash
ruff check .
```

```bash
ruff format --check .
```

```bash
mypy
```

| Tool | Catches |
|---|---|
| `ruff check` | Bugs and bad patterns (unused imports, mutable class defaults, ambiguous characters, too-long lines, naming) |
| `ruff format` | Style debates — the formatter decides |
| `mypy --strict` | A step passing a `str` where `Money` is expected, a missing return, an untyped function |

Examples ruff found in this project: exceptions not ending in `Error` (renamed to `EnvironmentBlockedError` etc.), and an invisible EN DASH in a page title (now written as `–` so a reader can see it).

### 9.2 Unit tests for the framework

`tests/unit/` — 48 tests, under 0.1 s, no browser:

| File | Proves |
|---|---|
| `test_money.py` | Parsing "£1,055.50", pence, exact arithmetic, currency mixing refused |
| `test_catalogue_and_cart.py` | Snapshot facts (sold-out items, Black heels' URL), cart maths across variants |
| `test_tag_rules.py` | Every tag rule fires, including "highest risk wins" |
| `test_traceability.py` | Each status, `NOT COVERED`, Gherkin scanning of rules and feature-level tags |
| `test_cart_consistency.py` | Each kind of UI/data disagreement raises `CartInconsistencyError` |
| `test_fake_store.py` | The fake implements the port and behaves like Shopify (quantity 0 removes the line) |
| `test_diagnostics.py` | Repeated console messages are counted |
| `test_testdata.py` | Generated e-mails are unique and undeliverable; builders accept overrides |

How framework bugs were actually caught while building this project: a **negative test** exposed the silent tag validator (§6.3); a **code review** before the first run caught that the first coverage gate read a flag set in the terminal summary, which pytest prints *after* `pytest_sessionfinish` — so the gate could never fire; and a unit test failed because its own regex treated `(1)` as a group (tests are code too).

### 9.3 Continuous integration

`.github/workflows/ci.yml` defines two jobs:

| Job | When | Steps |
|---|---|---|
| `quality` | Every push and pull request | ruff · format check · mypy · `pytest --store fake -n auto --fail-on-uncovered` · upload reports |
| `live` | `main`, nightly at 03:17 UTC, or on demand | `playwright install --with-deps chromium` · smoke on push / full regression nightly, **serial** · upload reports (kept 14 days) |

Design decisions: the slow, network-dependent live job runs only after `quality` passes and never on every pull request, which keeps load on the third-party site low; reports are uploaded even when tests fail (`if: always()`), because that is when you need them.

---

## Part 10 — The page-object library: every page, ready for Unit 2 🟡 → 🔴

The BDD scenarios need only part of the shop. Unit 2 (Playwright end-to-end) needs **all** of it. The library now covers every page and every shared part of the page, verified against the live shop by its own tests.

### 10.1 Components: parts that appear on many pages

`framework/adapters/web/components/`:

| Component | Where | Main methods |
|---|---|---|
| `Header` | Every page | `search(keyword)`, `cart_count()`, `expect_cart_count(n)`, `go_to_log_in()`, `go_to_sign_up()` |
| `MainMenu` | Every page | `names()`, `open(name)` — Home, Catalog, Blog, About Us |
| `MiniCart` | Drawer behind "My Cart (N)" | `open()`, `read()`, `remove(name)` |
| `ProductGrid` | Home, catalogue, search | `read()` → `ProductCard`s (name, price, sold out, handle), `open(name)` |
| `Breadcrumb` | Most pages | `trail()` → `["Home", "Products"]`, `current()` |

Every page object gets `header`, `menu`, and `breadcrumb` from `BasePage`, plus `last_status` (HTTP status of the last `open`) and `page_title()`.

Two lessons from building them:

- **The header number lags.** Right after the server confirms Add to Cart, the header still says `My Cart (0)`; JavaScript updates it a moment later. So the component offers `expect_cart_count(n)`, a web-first assertion that waits, next to `cart_count()`, which reads once:

```python
    def expect_cart_count(self, count: int) -> None:
        """Wait until the header shows ``count``.

        After Add to Cart the server answers first and the header text is
        updated a moment later, so a one-off read can still see the old number.
        """
        expect(self.cart_link).to_have_text(f"My Cart ({count})")
```

- **Shared parsing lives once.** The cart page and the mini-cart use the same row markup, so both call `components/cart_rows.py: read_rows(...)`.

### 10.2 Pages

| `shop.` | Page object | Main methods |
|---|---|---|
| `home()` | `HomePage` | `open()`, `featured_products()` |
| `catalog()` | `CatalogPage` | `open()`, `products()`, `open_product(name)` |
| `open_product(name)` / `product()` | `ProductPage` | `read()`, `option_names()`, `select_variant(v)`, `add_to_cart(n)`, `is_sold_out()` |
| `cart()` | `CartPage` | `open()`, `read()`, `is_empty()`, `set_quantity()`, `remove_all()`, `continue_shopping()`, `check_out()` |
| `mini_cart()` | `MiniCart` | `open()`, `read()`, `remove(name)` |
| `search()` | `SearchResultsPage` | `open_for(keyword)`, `results()`, `titles()`, `has_no_results()` |
| `checkout()` | `CheckoutPage` | `wait_until_loaded()`, `order_summary()` — read-only |
| `content()` | `ContentPage` | `open_page(handle)`, `heading_text()` |
| `blog()` / `article()` | `BlogPage` / `ArticlePage` | `article_list()`, `open_article(title)`, `heading_text()`, `author()` |
| `login()` | `LoginPage` | `fill_credentials()`, `sign_in()`, `errors()`, `show_password_recovery()`, `hide_password_recovery()` |
| `register()` | `RegisterPage` | `fill_form(customer)`, `register(customer)` |
| `not_found()` | `NotFoundPage` | `open_missing(path)`, `is_shown()` |
| `api` | `StoreApi` | `add_lines(...)`, `cart()` — fast setup and data-layer checks |

**Choosing a variant** proves the page picked the right one, using the variant id from the catalogue:

```python
    def select_variant(self, variant: Variant) -> None:
        """Choose a variant through the option boxes, then prove the page picked the right id.

        Variant titles list option values in option order: "L / Red" = Size L, Color Red.
        """
        values = variant.title.split(" / ")
        selects = self.option_selects.all()
        if len(selects) != len(values):
            raise AssertionError(f"{len(selects)} option boxes for variant {variant.title!r}")
        for select, value in zip(selects, values, strict=True):
            select.select_option(value)
        expect(self.selected_variant_id).to_have_value(str(variant.id))
```

**Reading the checkout summary** uses the accessible tables Shopify renders ("Shopping cart", "Cost summary") — subtotal, total, and the included UK VAT — without typing anything into the checkout.

**Account pages are complete but never submitted on the public shop.** `sign_in`, `request_password_reset`, and `register` would hit CAPTCHA, send real e-mail, or create real accounts on someone else's store. One wrong-password attempt during reconnaissance returned to the login page with no visible message — consistent with CAPTCHA interception, and the reason REQ-08 stays manual. The methods are ready for an owned test environment; test data comes from builders:

```python
def new_customer(**overrides: str) -> Customer:
    values = {
        "first_name": "Test",
        "last_name": "Customer",
        "email": unique_email(),
        "password": f"Pw-{secrets.token_urlsafe(12)}",
    }
    values.update(overrides)
    return Customer(**values)
```

`unique_email()` returns addresses at `example.com`, a domain reserved for documentation, so mail is never delivered to a real person.

### 10.3 The `Shop` facade and the `shop` fixture

```python
@pytest.fixture
def shop(page: Page, live_catalogue: Catalogue, settings: Settings) -> Shop:
    """Every page object, for plain Playwright tests (Unit 2): ``shop.catalog().open()``."""
    page.set_default_timeout(settings.ui_timeout_ms)
    return Shop(page, live_catalogue)
```

A plain Playwright test then reads like this (from `tests/pages/test_cart_pages.py`):

```python
def test_checkout_summary_matches_the_cart(shop: Shop) -> None:
    shop.page.goto("/cart")
    shop.api.add_lines([(_variant(shop, "Grey jacket"), 2)])
    shop.cart().open().check_out()
    summary = shop.checkout().order_summary()
    assert summary.quantities() == {"Grey jacket": 2}
    assert summary.subtotal == summary.total == Money(Decimal("110.00"))
    # Tax display is volatile: one run showed "Including £18.33 in taxes", a later one an
    # empty "Taxes" row. No requirement covers it, so check it only when it is shown:
    # then it must be the UK VAT (20 %) included in the total, i.e. total / 6.
    if summary.included_tax is not None:
        assert summary.included_tax == Money(summary.total.amount / 6)
```

The first version asserted a fixed `£18.33`. It failed on a later live run because the checkout no longer showed the tax line. No requirement covers tax display, so the test now checks the **rule** (VAT is total / 6) whenever the line is shown, instead of one observed value.

`WebStore` (the BDD adapter) is now built on the same `Shop`, so BDD and plain Playwright tests share one set of page objects.

### 10.4 Page-object tests: proof, and the starting point for Unit 2

`tests/pages/` holds 20 plain pytest-playwright tests, at least one per page object. They are skipped offline and run nightly in CI.

Their first live run found **four problems** before any scenario used those pages — **three bugs in the page objects** and **one new shop defect** (duplicated ids):

| Found by a page-object test | Cause | Fix |
|---|---|---|
| Strict-mode violation on the empty cart | Empty cart shows both "My Cart" and the empty message, so `heading.or_(message)` matched 2 elements | Wait for the heading, which both states show |
| Strict-mode violation on `#first_name` | **Shop defect:** `<div id="first_name">` wraps `<input id="first_name">` — duplicated ids | Locate inputs by their unique `name` |
| Breadcrumb read `["Home"]` only | Only "Home" carries schema.org markup; the current page is a plain link | Read all links inside `#breadcrumb` |
| "Continue Shopping" not found on an empty cart | The link text differs: "« Continue Shopping" vs "Continue Shopping" | Match the common end of the name |

### 10.5 A known defect as a tripwire: strict `xfail`

The mini-cart drawer is rendered when the page loads and **is not refreshed after an AJAX Add to Cart** (the header number is). That is a shop defect. The test that describes the correct behaviour is kept, and marked:

```python
@pytest.mark.xfail(
    strict=True,
    reason="Known shop defect (2026-11-18): the mini-cart is not refreshed after an AJAX add. "
    "strict=True: if the shop fixes it, this test fails as XPASS and must be updated.",
)
def test_mini_cart_updates_without_a_page_load(shop: Shop) -> None:
```

- While the defect exists, the run is green and the report lists it as `xfailed` — documented, not forgotten.
- If the shop fixes it, the test passes **unexpectedly**, and `strict=True` turns that into a failure: the team is told to remove the marker. A plain `skip` would hide the fix forever.

### 10.6 New BDD scenarios on the new pages

| Feature | Scenario | Requirement |
|---|---|---|
| `cart.feature` | Adding a chosen variant puts exactly that variant in the cart | REQ-03 |
| `catalogue.feature` | The catalogue lists every product and labels the sold-out ones | REQ-02, REQ-06 |
| `checkout.feature` | The order summary matches the cart | REQ-07 |
| `navigation.feature` | The latest blog article opens from the blog | REQ-09 |
| `navigation.feature` | An unknown address shows the not-found page | REQ-09 |

The catalogue scenario is a **cross-layer** check: every card's name and price must equal `/products.json`, and the "Sold Out" labels must match exactly the products with no available variant.

> **Your turn (🔴).** Write a page-object test that adds two different products through their product pages, opens the cart page, and asserts that `shop.cart().read()` equals `shop.api.cart()`. Then explain why the two can legitimately differ in `variant` text, and what you compare instead.

---

## Lab deliverables — senior Definition of Done (checked on Day 4)

- [ ] `ruff check .`, `ruff format --check .`, `mypy` all clean
- [ ] `pytest --store fake -n auto --fail-on-uncovered` green (unit + offline BDD)
- [ ] `pytest tests/test_*.py -m smoke` green against the live store
- [ ] `pytest tests/pages` green against the live store (1 `xfailed` = the known mini-cart defect)
- [ ] Traceability shows every requirement; none `NOT COVERED`
- [ ] Layer rules (§3.2) hold: no selector outside `pages/`, no Playwright import in steps
- [ ] Your two "Your turn" tasks done, each with a scenario or unit test
- [ ] One failure investigated from evidence only (log + PNG + JSON + trace), without rerunning
- [ ] Three consecutive live runs recorded (pass / fail / blocked)
- [ ] Testability defects listed for the shop's developers (Part 2.1, findings 2–3)

---

## Appendix A — Project tree and responsibilities

```
shop-bdd/
├── README.md                     architecture, conventions, commands
├── pyproject.toml                pytest, ruff, mypy configuration
├── requirements.txt              runtime dependencies (pinned)
├── requirements-dev.txt          + ruff, mypy (pinned)
├── requirements.toml             requirement registry
├── conftest.py                   plugin list only
├── .github/workflows/ci.yml      quality + live jobs
├── features/                     5 feature files (Gherkin)
├── framework/
│   ├── domain.py                 Money, Variant, CatalogueItem, Catalogue, Product, CartLine, Cart,
│   │                             ProductCard, OrderSummary, ArticleSummary, Customer
│   ├── testdata.py               unique_email, new_customer
│   ├── errors.py                 FrameworkError, EnvironmentBlockedError, DataUnavailableError, CartInconsistencyError
│   ├── ports.py                  Store protocol
│   ├── config.py                 options + Settings
│   ├── requirements.py           registry loading + tag rules (pure)
│   ├── traceability.py           Gherkin scan + matrix (pure)
│   ├── adapters/
│   │   ├── fake.py               FakeStore
│   │   └── web/
│   │       ├── store.py          WebStore (orchestrator)
│   │       ├── api.py            StoreApi
│   │       ├── guard.py          ensure_not_blocked
│   │       ├── diagnostics.py    BrowserDiagnostics
│   │       ├── shop.py           Shop facade
│   │       ├── components/       header, main_menu, mini_cart, product_grid, breadcrumb, cart_rows
│   │       └── pages/            base, home, catalog, product, cart, search, checkout,
│   │                             content, blog (+ article), account (login, register), not_found
│   └── plugins/
│       ├── fixtures.py           settings, live_catalogue, store
│       ├── tags.py               markers from registry, @manual, tag rules
│       ├── evidence.py           step logging, failure screenshot + JSON
│       └── traceability.py       outcome classes, matrix, coverage gate
└── tests/
    ├── test_*.py                 bind feature files
    ├── steps/                    cart, catalogue, navigation steps
    ├── unit/                     48 framework unit tests
    ├── pages/                    20 page-object tests (live shop; basis for Unit 2)
    └── data/catalogue_snapshot.json
```

## Appendix B — Command cheat-sheet

| Goal | Command |
|---|---|
| Quality gate (as CI) | `ruff check . && ruff format --check . && mypy` |
| Unit + offline BDD, parallel, coverage gate | `pytest --store fake -n auto --fail-on-uncovered` |
| Only the framework's unit tests | `pytest tests/unit` |
| Smoke on the live store, watch it | `pytest tests/test_*.py -m smoke --headed --slowmo 300` |
| Page-object tests (live) | `pytest tests/pages` |
| Everything automated, live | `pytest tests/test_*.py -m "not manual"` |
| One requirement | `pytest -m REQ-05` |
| Longer timeouts on a slow network | `SHOP_UI_TIMEOUT_MS=30000 pytest tests/test_*.py -m smoke` |
| Another browser | `pytest tests/test_*.py --browser firefox` |
| Open a failure recording | `playwright show-trace reports/artifacts/<folder>/trace.zip` |
| Reports for CI and dashboards | add `--cucumberjson=reports/cucumber.json --junitxml=reports/junit.xml` |

## Appendix C — Common errors

| Error | Meaning | Fix |
|---|---|---|
| `Executable doesn't exist ... run playwright install` | Browser not downloaded | `playwright install chromium` |
| `Tag rules broken: ...` | A scenario's tags break the rules (§6.2) | Fix the tags; the message lists every problem |
| `'REQ-12' not found in markers configuration option` | Requirement not in the registry | Add it to `requirements.toml` |
| `Coverage gate failed - no scenarios for: [...]` | Registered requirement without a scenario | Write one, or remove it from the registry |
| `DataUnavailableError: no product named 'X'; the store has: [...]` | Feature file names a product that does not exist | Use a name from the list |
| `EnvironmentBlockedError: bot protection at ...` | Cloudflare verification page | Not a bug. Wait 10–30 min, run fewer tests, serially |
| `CartInconsistencyError: cart page disagrees with cart data: ...` | UI and data disagree | A product defect: report it with the evidence folder |
| `strict mode violation: ... resolved to 2 elements` | Locator matches several elements | Scope it in the page object |
| `Timeout ... exceeded` | Element or response never came | Open the trace; check the evidence PNG — wrong page? blocked? renamed? |

---

## Self-check (answers below — try first)

1. Why is `wait_for_load_state("networkidle")` after "Add to Cart" a flaky wait on this store, and what replaces it?
2. The cart page heading says "Grey jacket - Grey jacket". Why does `CartPage` identify rows by the product **link** instead?
3. `WebStore.cart()` reads the page **and** the cart JSON. What kind of defect does that catch that a UI-only check misses?
4. Why is `CartInconsistencyError` an `AssertionError`, while `EnvironmentBlockedError` is not?
5. The tag-rule plugin once checked nothing and stayed green. What made the bug visible, and what prevents a repeat?
6. Why are `tag_problems` and `build_matrix` pure functions, separate from the pytest hooks?
7. Three scenarios are Blocked, but the scenarios between them passed. What do you suspect, and how do you check?
8. Why does the CI `live` job run serially, only after `quality`, and not on every pull request?
9. Which files would change to add a `MobileStore` in Unit 3, and which must not?

<details>
<summary><b>Answer guide</b></summary>

1. A load state is reached once per page load; after the first add the page is already "idle", so the wait returns at once and the test reads the cart too early. `expect_response` for `/cart/add` waits for the server's confirmation of *this* click.
2. Heading text is theme formatting and can change with a template edit; the link carries the product handle, which is data. The handle also maps correctly when the URL differs from the name ("Black heels" → `flower-print-jeans`).
3. A page that renders numbers different from the shop's real cart (wrong total, missing line, stale header count). A UI-only check would compare the page with itself and pass.
4. A disagreement is a product defect, so it must count as a failed test (`FAIL`). A bot check is the environment, so it gets its own class (`BLOCKED`) and must not be filed as a bug.
5. A deliberate negative test: break a tag, expect the run to fail. It did not fail. Now tags are read through public markers, and a guard stops the run if BDD modules are collected but no scenario is recognised.
6. Pure functions can be unit-tested in milliseconds with any input, without starting pytest sessions or browsers. Hooks then only adapt pytest's data to them, so most logic is proven before any scenario runs.
7. Real blocking affects everything after it starts. Blocked results mixed with passes on one shared code path point to the detector or that path. Check what the endpoint returns (status, content type, body) — here it was `text/javascript`.
8. It hits a shared third-party site: parallel or frequent runs look like an attack and trigger bot protection. Running after `quality` avoids wasting live runs on code that does not even pass lint and unit tests.
9. New: `framework/adapters/mobile/` (screen objects + a `MobileStore` implementing the `Store` port) and a branch in the `store` fixture. Unchanged: feature files, step definitions, domain model, plugins.
</details>

## Next: Day 4 — Review

Review your framework (and a classmate's) for maintainability, traceability, and duplication, using the layer rules (§3.2), the anti-pattern list from Day 2 §8.2, the flakiness checklist (§8.4), the Definition of Done above, and a scoring rubric.

---

## Verification log

| Check | Result |
|---|---|
| Site facts table | Observed on the live store with Playwright, 2026-11-17 |
| `first_script.py` | Ran headless against the live store: printed `Grey jacket`, `£55.00`, `My Cart (1)` |
| `networkidle` trap and `expect_response` fix | Observed live (§2.2) |
| Strict mode violation on duplicate ids | Observed live (§2.3) |
| Catalogue snapshot | Recorded from the live `/products.json`, 2026-11-18 |
| `ruff check`, `ruff format --check`, `mypy --strict` | Clean (64 source files) |
| Unit tests | 48 passed |
| `pytest --store fake -n auto --fail-on-uncovered` | 68 passed (48 unit + 20 BDD), 22 skipped (2 manual + 20 live-only page tests), exit 0 |
| Tag rules, broken on purpose | Run stopped (exit 4) with the 4 problems shown in §6.2; unknown `@REQ-99` rejected by `--strict-markers` |
| Silent tag-rule bug (pytest-bdd 9) | Reproduced, fixed, guard added (§6.3) |
| Coverage gate with an extra `REQ-10` | Exit 0 without the option, exit 1 with it; message shown in §6.5 |
| Blocked vs failed, parallel (`-n 2`), simulated | Simulated bot check → REQ-01 `BLOCKED`; injected cart bug → REQ-03/04/05 `FAIL` |
| Live run, final code (`pytest tests/test_*.py -m "not manual"`) | **20 passed in 78 s**, every cart read cross-checked against the cart JSON (output in §6.4) |
| Live page-object tests (`pytest tests/pages`) | **19 passed, 1 xfailed** (the known mini-cart defect) in 47 s |
| Page-object reconnaissance (Part 10) | Home, catalogue, variants, mini-cart, blog, article, login, register, recovery form, 404, checkout summary observed live on 2026-11-18; one wrong-password login attempt (no message shown); no registration, no password reset, no payment data ever submitted |
| Rate limiting during Part 10 | One run got HTTP 429 on the 404 scenario → correctly reported `BLOCKED`; rerun after a pause passed |
| Failure evidence, live (one scenario broken on purpose) | Log, step PNG + JSON, Playwright PNG + trace all created (Part 7) |
| Fresh install from `requirements-dev.txt` | ruff, mypy, and the CI `quality` pytest command all pass |
| CI workflow | YAML validated, every job step listed; the `quality` commands run locally. **Not run on GitHub** |
| Earlier live history | First draft: 8 passed then blocked by Cloudflare; detector false alarm (`text/javascript`) found and fixed; both kept as lessons (Part 8.1) |
| Library versions | Python 3.13; pytest 9.2.0, pytest-bdd 9.0.1, pytest-playwright 0.10.0, Playwright 1.63.0, pytest-xdist 3.8.0, ruff 0.17.5, mypy 2.4.1 (all pinned) |
| Not run here | `playwright codegen`, `show-trace`, `--headed`, Firefox (need a desktop session) |
