# Unit 2 · Day 7 — Playwright Implementation Lab: Prioritised End-to-End Workflows

| | |
|---|---|
| **Course** | Advanced Automation Test Engineering (ATEST03) — Fast Track |
| **Unit** | Unit 2 — Playwright End-to-End Automation |
| **Learning outcome** | **LO3** — Build reliable Playwright suites using fixtures, isolation, tracing, network control, and parallel execution (Bloom **B3: Apply**) |
| **Format** | Assignment/Lab · Hybrid · 150 minutes · **code is the deliverable** |
| **System under test** | https://sauce-demo.myshopify.com/ — live, in a real browser |
| **Starting point** | The Unit 1 framework (`Unit1/day4-code/shop-bdd.zip`) |
| **Finished project** | `day7-code/shop-bdd.zip` — adds `tests/e2e/`, network helpers, `business_step` tracing, `@covers`, and the `new_shop` fixture |
| **Output of the day** | Prioritised end-to-end tests that pass on the live shop, a trace you can read, one documented product defect, and three recorded runs |

> **What was verified.** Every test in this guide ran against the live shop twice with identical results (**8 passed, 2 xfailed**, about 61 s each). The trace grouping, the network behaviour, and the product defect in Part 4 were observed directly. The project passes `ruff`, `mypy --strict`, the BDD review, 79 unit tests, and the offline BDD suite in a fresh environment. See the Verification log.

---

## How to use this lab

Days 5–6 explained the concepts. Today you apply them to the real shop: choose **which** workflows deserve an end-to-end test, write them with page objects and fixtures, control the network to test what normal browsing cannot reach, and read the evidence a trace gives you.

| Badge | Level | After this level you can… |
|---|---|---|
| 🟢 | **Foundation** | Run the e2e suite, read one test, open its trace |
| 🟡 | **Practitioner** | Write a workflow test with business steps, observe a request, simulate a failure |
| 🔴 | **Senior** | Prioritise workflows by risk and test layer, turn a failure simulation into a defect report with a tripwire, and prove stability |

### Lab plan (150 min)

| Time | Task | Part |
|---|---|---|
| 0–15 | Setup; run the existing suites | 0 |
| 15–30 | Choose and prioritise the workflows | 1 |
| 30–70 | The P1 purchase journey | 2–3 |
| 70–100 | Network control: observe a request, simulate failures | 4 |
| 100–125 | Tracing: record, read, diagnose a broken test | 5 |
| 125–140 | Traceability and CI priorities | 6 |
| 140–150 | Stability runs and deliverables | 7 |

**Core:** Parts 0–4 and one "Your turn" task. **Stretch:** Parts 5–7 and the remaining tasks.

---

## Part 0 — Setup 🟢

Unzip `day7-code/shop-bdd.zip`, create and activate a virtual environment (Unit 1, Day 2 §0.1), then:

```bash
pip install -r requirements-dev.txt
```

```bash
playwright install chromium
```

Offline gate first (no shop traffic):

```bash
pytest --store fake -n auto
```

Expected: `99 passed, 34 skipped` — 79 unit tests and 20 BDD scenarios pass; the skipped tests are the 2 manual scenarios and the 32 browser tests that need the live shop.

Then the new end-to-end tests, live and **serially** (Day 6: never parallel against a third-party site):

```bash
pytest tests/e2e -v
```

```
test_visitor_finds_a_product_by_search_and_sees_catalogue_details PASSED
test_sold_out_product_cannot_be_bought PASSED
test_two_shoppers_have_separate_carts PASSED
test_selected_variant_is_what_the_server_receives PASSED
test_failed_add_to_cart_leaves_the_cart_unchanged[chromium-500] PASSED
test_failed_add_to_cart_leaves_the_cart_unchanged[chromium-503] PASSED
test_customer_can_retry_after_a_failed_add_to_cart[chromium-http-500] XFAIL
test_customer_can_retry_after_a_failed_add_to_cart[chromium-network] XFAIL
test_shop_works_with_third_party_scripts_silenced PASSED
test_customer_buys_two_products_up_to_checkout PASSED
8 passed, 2 xfailed in 60.83s
```

The two `XFAIL` results are expected: they describe a shop defect found in this lab (Part 4.3).

---

## Part 1 — Choose the workflows 🟡 → 🔴

### 1.1 🟡 End-to-end tests are expensive — choose them on purpose

An end-to-end test is the slowest and most fragile kind (Unit 1, Day 1 §0.3). It earns its place when **only a full journey** can catch the risk: several pages, real server state, real data flowing from one step to the next.

| Question | If yes → e2e candidate |
|---|---|
| Is the risk High (Day 1 register)? | Money, cart, checkout |
| Does the failure appear only **between** pages or components? | Variant chosen on one page → line on the cart page → checkout summary |
| Is it **not** already covered at a cheaper layer? | BDD scenarios and page-object tests already cover single pages |
| Does it need network control the other layers cannot do? | Server errors, request contents |

### 1.2 🔴 The decision for this shop

| Workflow | Risk (Day 1/4) | Already covered by | Decision | Priority |
|---|---|---|---|---|
| Catalogue → variant → search → cart → change quantity → checkout summary | High (REQ-03/04/05/07) | Each step separately (BDD, page tests); **not the journey** | Automate as one journey | **P1** — every change |
| The variant chosen is what the server receives | High (REQ-03) | Cart contents only (the *result*) | Automate: observe the request | **P1** |
| Search → product details match the catalogue | Medium (REQ-01/02) | BDD search; page test | Automate: short journey across pages | P2 — nightly |
| A sold-out product cannot reach the cart | Medium (REQ-06) | BDD scenario | Automate: cheap, checks the server cart too | P2 |
| Two shoppers' carts are separate | High (REQ-04) + isolation | Not covered | Automate with `new_shop` | P2 |
| Add to Cart fails on the server | High (REQ-03/04) | Impossible without network control | Automate with `simulate_failure` | P2 |
| Information pages, 404 | Low (REQ-09) | BDD scenarios + page tests | **Do not duplicate** at e2e level | — |
| Sign up / log in | Medium (REQ-08) | Manual (CAPTCHA) | **Cannot** automate on the public shop | — |

The last two rows matter as much as the first six: a senior suite is defined as much by what it **does not** test at the expensive layer.

> **Your turn (🟢).** Add one row: "A customer adds the same product twice from two different pages (search result and catalogue)." Decide its priority and justify it in one sentence.

---

## Part 2 — Anatomy of an end-to-end test 🟡

### 2.1 The P1 purchase journey

`tests/e2e/test_purchase_journey.py`:

```python
@covers("REQ-01", "REQ-02", "REQ-03", "REQ-04", "REQ-05", "REQ-07")
def test_customer_buys_two_products_up_to_checkout(shop: Shop) -> None:
    noir = shop.catalogue.by_name("Noir jacket")
    sandals = shop.catalogue.by_name("Bronze sandals")

    with business_step(shop.page, "Browse the catalogue and open Noir jacket"):
        shop.catalog().open().open_product("Noir jacket")
        product = shop.product()
        product.wait_until_loaded()
        expect(product.price).to_have_text(str(noir.price))

    with business_step(shop.page, "Choose M / Red and add it to the cart"):
        product.select_variant(noir.variant("M / Red"))
        product.add_to_cart()
        product.header.expect_cart_count(1)

    with business_step(shop.page, "Find sandals with the search box and add two"):
        product.header.search("sandals")
        shop.search().open_result("Bronze sandals")
        sandals_page = shop.product()
        sandals_page.wait_until_loaded()
        sandals_page.add_to_cart(2)
        sandals_page.header.expect_cart_count(3)

    with business_step(shop.page, "Review the cart"):
        cart = shop.cart().open().read()
        assert cart.quantities() == {"Noir jacket": 1, "Bronze sandals": 2}, cart.describe()
        assert ("Noir jacket", "M / Red") in {(line.name, line.variant) for line in cart.lines}
        assert cart.total == noir.price + sandals.price * 2, cart.describe()
        assert shop.api.cart().quantities() == cart.quantities(), "cart page and cart data disagree"

    with business_step(shop.page, "Reduce the sandals to one"):
        shop.cart().set_quantity("Bronze sandals", 1)
        cart_page = shop.cart().open()
        cart = cart_page.read()
        assert cart.total == noir.price + sandals.price, cart.describe()

    with business_step(shop.page, "Proceed to checkout and compare the order summary"):
        cart_page.check_out()
        summary = shop.checkout().order_summary()
        assert summary.quantities() == cart.quantities()
        assert summary.subtotal == cart.total
```

### 2.2 How to read it — the rules it follows

| Rule (Day 5/6 checklist) | Where |
|---|---|
| Steps named in business language | Six `business_step` blocks: the trace and the log read like the workflow |
| Data from the shop, not hard-coded | Prices from `shop.catalogue`; expected totals **computed** (`noir.price + sandals.price * 2`) |
| Page facts through `expect` | `expect(product.price)`, `header.expect_cart_count(...)` — the header number updates after the server answers |
| Values already read through `assert` | `cart` is a `Cart` object read once; plain `assert` is right |
| Wait for evidence of server work | `add_to_cart()` waits for each `/cart/add.js` response |
| Cross-layer check | The cart page is compared with the shop's cart data (`shop.api.cart()`) |
| No selectors in the test | Only page objects (enforced by the architecture tests) |
| Messages that explain | `cart.describe()` in assertion messages shows the whole cart on failure |

### 2.3 One long journey, or many short tests?

| Long journey (this test) | Short tests (BDD, page tests) |
|---|---|
| Catches failures **between** steps (variant lost on the way to the cart) | Pinpoint which page broke |
| One failure hides the later steps | Independent results |
| Slow (22 s here) | Fast |

A suite needs both. Keep journeys **few** and at the **top** priority, and let the short tests explain the failure when a journey breaks.

> **Your turn (🟡).** Add a step "Remove the Noir jacket" before checkout, using `shop.cart().remove_all(...)`, and adjust the checkout assertions. Run only this test: `pytest tests/e2e -k buys_two`.

---

## Part 3 — Fixtures for end-to-end tests 🟡

### 3.1 What each e2e test receives

```
settings ──┐
browser ───┼─▶ context ──▶ page ──▶ shop (page objects + api)
           │      │
           │      └─▶ silenced  (autouse: third-party telemetry answered with 204)
live_catalogue ─────────────────▶ shop.catalogue
new_context ──▶ new_shop (factory: extra shoppers, each in its own context)
```

### 3.2 `tests/e2e/conftest.py`

```python
@pytest.fixture(autouse=True)
def _live_only(settings: Settings) -> None:
    if settings.store == "fake":
        pytest.skip("end-to-end tests need the live shop (run without --store fake)")


@pytest.fixture(autouse=True)
def silenced(_live_only: None, context: BrowserContext) -> Counter[str]:
    """Third-party requests answered with 204 in this test's context, counted per host."""
    return silence_third_parties(context)
```

- `silenced` **depends on** `_live_only`, so an offline run skips before any browser starts.
- It is `autouse`, so no e2e test can forget it, and it **returns** the counter, so a test can ask for it as evidence (Part 4.4).

### 3.3 Several shoppers in one test

```python
@covers("REQ-04")
def test_two_shoppers_have_separate_carts(new_shop: Callable[..., Shop]) -> None:
    alice, bob = new_shop(), new_shop()
    for shopper in (alice, bob):
        silence_third_parties(shopper.page.context)

    with business_step(alice.page, "Alice adds a Grey jacket"):
        product = alice.open_product("Grey jacket")
        product.add_to_cart()
        product.header.expect_cart_count(1)

    with business_step(bob.page, "Bob's cart is still empty"):
        assert bob.cart().open().is_empty()
        assert bob.api.cart().item_count == 0
```

The extra contexts come from `new_shop` (built on pytest-playwright's `new_context`), so they are closed and recorded like the main one. They are not the default `context`, so the autouse fixture does not reach them — the test silences them itself.

---

## Part 4 — Network control 🟡 → 🔴

### 4.1 🟡 Observe: is the right variant sent?

The cart shows the *result* of adding a product. It cannot show whether the browser sent the **variant the customer chose** — a different variant at the same price would look identical in many checks. Reconnaissance showed what the theme sends:

```
POST /cart/add.js   content-type: application/x-www-form-urlencoded   body: id=7805236929
```

(7805236929 is "Noir jacket — M / Red" in `/products.json`.) So the test watches the request, without changing anything:

```python
@pytest.mark.p1
@covers("REQ-03")
def test_selected_variant_is_what_the_server_receives(shop: Shop) -> None:
    variant = shop.catalogue.by_name("Noir jacket").variant("L / Red")
    product = shop.open_product("Noir jacket")
    product.select_variant(variant)

    with shop.page.expect_request(ADD_TO_CART) as request:  # observe only: nothing is mocked
        product.add_to_cart()

    assert parse_qs(request.value.post_data or "")["id"] == [str(variant.id)]
```

### 4.2 🟡 Simulate: what happens when Add to Cart fails?

No amount of normal browsing makes the shop's server return an error. A route can (Day 6, Part 2). Before writing a test, **observe** — the lab's reconnaissance on the live shop:

| Simulated failure | Button afterwards | Message to the customer | Cart on the server |
|---|---|---|---|
| HTTP 500 | Turns into **"Sold Out"**, disabled | none | unchanged (0) |
| Network failure (`abort`) | "Add to Cart", but **disabled** | none | unchanged (0) |
| After reloading the page | "Add to Cart", enabled | — | unchanged (0) |

Two very different facts are in that table:

1. **Safety holds:** a failed add never puts anything in the cart. That is a property to protect with a normal, passing test.
2. **The customer experience is broken:** a temporary server problem is presented as "Sold Out", and the customer cannot retry without reloading. That is a **product defect**.

The helper:

```python
def simulate_failure(target: BrowserContext | Page, url: str, status: int | None = 500) -> None:
    """Make matching requests fail: with an HTTP ``status``, or (``status=None``) like a broken network."""

    def fail(route: Route) -> None:
        if status is None:
            route.abort()
        else:
            route.fulfill(status=status, content_type="application/json", body=f'{{"status": {status}}}')

    target.route(url, fail)
```

The safety test:

```python
@pytest.mark.p2
@covers("REQ-03", "REQ-04")
@pytest.mark.parametrize("status", [500, 503])
def test_failed_add_to_cart_leaves_the_cart_unchanged(shop: Shop, status: int) -> None:
    product = shop.open_product("Grey jacket")

    with business_step(shop.page, f"The server answers Add to Cart with HTTP {status}"):
        simulate_failure(shop.page, ADD_TO_CART, status=status)
        assert product.click_add_to_cart().status == status

    with business_step(shop.page, "Nothing was added"):
        product.header.expect_cart_count(0)
        assert shop.api.cart().item_count == 0
```

`click_add_to_cart()` is a new page-object method that clicks once and returns the server's answer **whatever it is**; `add_to_cart()` now uses it and insists on success. Note what is mocked: only the **failure**. The success path of `/cart/add.js` stays real in every other test — the "live twin" rule from Day 6.

### 4.3 🔴 The defect, as a tripwire

The expected behaviour is written as a test, and marked as a known defect:

```python
@pytest.mark.p2
@pytest.mark.xfail(
    strict=True,
    reason="Shop defect (2026-11-18): after a failed Add to Cart the button stays disabled "
    "(after HTTP 500 it even reads 'Sold Out') and no message is shown, so the customer cannot retry.",
)
@pytest.mark.parametrize("failure", ["http-500", "network"], ids=["http-500", "network"])
def test_customer_can_retry_after_a_failed_add_to_cart(shop: Shop, failure: str) -> None:
    product = shop.open_product("Grey jacket")
    simulate_failure(shop.page, ADD_TO_CART, status=500 if failure == "http-500" else None)

    product.add_button.click()

    expect(product.add_button, "the customer must be able to try again").to_be_enabled(timeout=5000)
```

- The test states the **requirement**, not the current behaviour. It fails today, so it is reported as `XFAIL`.
- `strict=True`: the day the shop fixes the defect, the test passes, the run **fails** as `XPASS(strict)`, and someone removes the marker. The defect cannot be fixed (or reappear) silently.
- Why `to_be_enabled` works here: the theme disables the button on click; the correct behaviour would enable it again after the error. Waiting up to 5 s for that is a fair, deterministic definition of "can retry".

The defect report, in Day 4's format:

> **D-01 (High, product) — A failed Add to Cart is shown as "Sold Out" and blocks retrying.** *Observation:* when `/cart/add.js` fails, no message is shown; after HTTP 500 the button changes to a disabled "Sold Out"; after a network failure it stays disabled. *Evidence:* `tests/e2e/test_network_control.py::test_customer_can_retry_after_a_failed_add_to_cart` (both cases `XFAIL`), trace in `reports/artifacts/`. *Impact:* customers believe an available product is sold out during a brief server problem; lost sales. *Recommendation:* on error, re-enable the button and show "Could not add to cart, please try again". *Cart integrity is not affected* (`test_failed_add_to_cart_leaves_the_cart_unchanged` passes).

### 4.4 🔴 Isolation from third parties

```python
def silence_third_parties(target: BrowserContext | Page) -> Counter[str]:
    """Answer telemetry and third-party scripts with an empty 204. Returns a live count per host."""
    silenced: Counter[str] = Counter()

    def answer(route: Route) -> None:
        silenced[urlsplit(route.request.url).netloc] += 1
        route.fulfill(status=204, body="")

    target.route(THIRD_PARTY, answer)
    return silenced
```

- `204`, not `abort`: Day 6 measured that aborting made the shop's telemetry retry (74 requests instead of 65).
- The danger of any block list is blocking **the shop itself**. A unit test guards it: `/cart/add.js`, `/cart.js`, `/products.json`, product, search, and checkout URLs must never match `THIRD_PARTY` (`tests/unit/test_e2e_helpers.py`).
- `test_shop_works_with_third_party_scripts_silenced` proves the shop still works and that something really was silenced.

> **Your turn (🔴).** Write `test_failed_cart_page_load_shows_an_error`: make `**/cart` (the page) answer HTTP 503 and observe what the customer sees. Decide, as in §4.2, which part is a safety property and which part (if any) is a defect.

---

## Part 5 — Tracing 🟡 → 🔴

### 5.1 Business steps in the trace

```python
@contextmanager
def business_step(page: Page, title: str) -> Iterator[None]:
    log.info("STEP %s", title)
    page.context.tracing.group(title)
    try:
        yield
    finally:
        page.context.tracing.group_end()
```

- In the **log** each step appears as `STEP …` (shown by pytest for failing tests).
- In the **trace** the actions are grouped under the step title. When tracing is off, grouping does nothing (checked), so the helper is always safe to use.

### 5.2 Record and open a trace

```bash
pytest tests/e2e -m p1 -k buys_two --tracing on
```

```bash
playwright show-trace reports/artifacts/tests-e2e-test-purchase-journey-py-test-customer-buys-two-products-up-to-checkout-chromium/trace.zip
```

What the recorded trace contained (checked by reading the file): **195 actions**, grouped under the six steps —

1. Browse the catalogue and open Noir jacket
2. Choose M / Red and add it to the cart
3. Find sandals with the search box and add two
4. Review the cart
5. Reduce the sandals to one
6. Proceed to checkout and compare the order summary

The file was **9.8 MB** for one 23-second test — the concrete reason CI uses `retain-on-failure` (already set in `pyproject.toml`) rather than `on`.

### 5.3 🔴 Exercise: diagnose from the trace only

1. Break the journey on purpose: change `noir.variant("M / Red")` to `noir.variant("L / Red")` in step 2 but keep `("Noir jacket", "M / Red")` in step 4.
2. Run it. It fails in "Review the cart".
3. Without reading the test code, open the trace: find the failing step group, the **after** snapshot of the cart page, and the `POST /cart/add.js` request in the Network panel (its body shows which variant id was sent).
4. Write one sentence: is this a product defect, a test defect, or an environment problem? (Answer: a test defect — the test chose one variant and expected another.)
5. Undo the change.

---

## Part 6 — Traceability and CI priorities 🔴

### 6.1 E2E evidence in the requirement matrix

`@covers(...)` adds requirement markers to a plain test, so the Unit 1 traceability matrix counts it next to the BDD scenarios:

```python
def covers(*requirement_ids: str) -> Callable[[F], F]:
    def apply(test: F) -> F:
        for requirement_id in requirement_ids:
            test = getattr(pytest.mark, requirement_id)(test)
        return test

    return apply
```

The ids are registered markers (from `requirements.toml`), so a typo like `REQ-3` fails the run. The matrix printed after `pytest tests/e2e`:

```
REQ-01  medium  Search products by keyword                        2    2    0    0    0  PASS
REQ-02  medium  Product page shows name, price, availability      2    2    0    0    0  PASS
REQ-03  high    Add an available product to the cart              2    4    0    0    0  PASS
REQ-04  high    Cart shows correct items, quantities, subtotal    3    4    0    0    0  PASS
REQ-05  high    Change quantity or remove an item                 2    1    0    0    0  PASS
REQ-06  medium  Sold-out product cannot be added                  2    1    0    0    0  PASS
REQ-07  medium  Proceed from cart to checkout                     2    1    0    0    0  PASS
REQ-08  medium  Sign up and log in                                2    0    0    0    0  NOT RUN
REQ-09  low     Information pages reachable from navigation       3    0    0    0    0  NOT RUN
```

("Decl" still counts only Gherkin scenarios; "Pass" now includes e2e tests. REQ-09 is `NOT RUN` here because, by the decision in §1.2, no e2e test covers it.)

### 6.2 Priorities become CI schedules

| Marker | Meaning | CI `live` job |
|---|---|---|
| `p1` | Must pass on every change | On push to `main`: `-m "smoke or p1"` |
| `p2` | Important, slower or narrower | Nightly, with everything else: `-m "not manual"` |
| `e2e` | Any end-to-end workflow | Select all: `pytest tests/e2e` |

---

## Part 7 — Stability and deliverables 🔴

### 7.1 Results

| Run | Result | Duration |
|---|---|---|
| Live run 1 | 8 passed, 2 xfailed | 60.8 s |
| Live run 2 (60 s later) | 8 passed, 2 xfailed | 62.4 s |
| BDD smoke after the page-object change | 2 passed | 13.3 s |

Slowest tests (run 1): purchase journey 22.0 s; the two retry tests 6.2 s each (they wait the full 5 s for a button that never comes back — by design); two shoppers 4.6 s; search journey 4.2 s.

Your Day 1 exit criterion asks for **three** consecutive green runs; record your third. A `BLOCKED` run (bot protection, HTTP 429) does not count either way — wait and rerun.

### 7.2 Deliverables (checked on Day 8)

- [ ] `pytest --store fake -n auto` green (offline gate)
- [ ] `pytest tests/e2e` green on the live shop: all `PASSED`, exactly 2 `XFAIL`, no `XPASS`
- [ ] Your workflow priority table (§1.2) with the row from "Your turn"
- [ ] At least one new e2e test from a "Your turn" task, with `business_step` and `@covers`
- [ ] One trace opened and a broken test diagnosed from the trace alone (§5.3)
- [ ] Defect D-01 written up (§4.3), plus anything your own simulation found
- [ ] Three live runs recorded (pass / fail / blocked) with durations
- [ ] Day 5 + Day 6 checklist (items 1–16) ticked for every test you wrote

---

## Common errors

| Error | Meaning | Fix |
|---|---|---|
| `SKIPPED ... end-to-end tests need the live shop` | You ran with `--store fake` | Run without it |
| `AssertionError: add to cart failed: HTTP 500` | `add_to_cart()` insists on success; a route made it fail | Use `click_add_to_cart()` in failure tests |
| `XPASS(strict)` | A known defect seems fixed | Check the shop; if fixed, remove the `xfail` and update the README's defect table |
| `strict mode violation` in a new test | A locator matches several elements | Add or fix the method in the page object, not in the test |
| `EnvironmentBlockedError: bot protection` | Cloudflare check / rate limit | Not a defect: wait 10–30 min, run serially, fewer tests |
| `'REQ-3' not found in markers` | Typo in `@covers` | Use the ids from `requirements.toml` |

---

## Self-check (answers below — try first)

1. Why are information pages (REQ-09) deliberately **not** in the e2e suite?
2. What does `test_selected_variant_is_what_the_server_receives` prove that reading the cart does not?
3. In the failure tests, what is mocked and what is never mocked? Why does that matter?
4. Why are the safety property and the customer-experience requirement two separate tests?
5. Why `strict=True` on the xfail?
6. Why does `silenced` depend on `_live_only`?
7. Why is the trace kept only on failure in CI?
8. The journey test fails at "Review the cart". Which tests help you find out which page broke?

<details>
<summary><b>Answer guide</b></summary>

1. Their risk is low and they are already covered by BDD scenarios and page-object tests; an e2e duplicate would add cost and fragility without new information.
2. That the browser sent the **chosen variant's id** to the server. A different variant at the same price could produce a cart that passes most checks.
3. Only the failing `/cart/add.js` answer is mocked, inside the failure tests. The successful path is never mocked anywhere, so every other test still proves the real behaviour — mocks without a live twin can drift from reality unnoticed.
4. One must pass (cart integrity is protected today); the other describes a defect that exists today. Mixing them would either hide the defect or make a protected property look broken.
5. So that a fix (or any change in behaviour) turns the run red and forces someone to update the test; a plain xfail would let the change go unnoticed.
6. So that an offline run skips the test before the browser and context are created.
7. One 23-second trace was 9.8 MB; keeping traces for every passing test costs disk and time for no benefit.
8. The BDD cart scenarios and the page-object tests (`tests/pages`): they test each page on its own, so the one that fails points to the page.
</details>

## Next: Day 8

Topic revision, then reliability and maintainability patterns: failure analysis, flaky-test control, tracing diagnostics, and maintainability criteria.

---

## Verification log

| Check | Result |
|---|---|
| Reconnaissance: `/cart/add.js` request | `POST`, form-encoded, body `id=<variant id>` |
| Reconnaissance: Add to Cart with HTTP 500 / network failure | As in §4.2 (button "Sold Out"/disabled; no message; server cart 0) |
| `tracing.group` with tracing off | No error |
| `pytest tests/e2e`, live run 1 | 8 passed, 2 xfailed, 60.8 s |
| `pytest tests/e2e`, live run 2 | 8 passed, 2 xfailed, 62.4 s |
| Trace of the journey (`--tracing on`) | 195 actions, 6 groups with the step titles, 9.8 MB |
| BDD smoke after refactoring `add_to_cart` | 2 passed |
| Fresh install: ruff, format, `mypy --strict`, BDD review `--strict` | Clean (77 source files) |
| Fresh install: `pytest --store fake -n auto --fail-on-uncovered` | 99 passed (79 unit + 20 BDD), 34 skipped |
| Unit tests for the new helpers | 13 (third-party pattern matches telemetry and never the shop's own URLs; `covers`) |
| Architecture tests | Pass: e2e tests use page objects only |
| CI workflow | Live job now runs `tests/e2e` (`smoke or p1` on push, everything nightly); YAML validated; **not run on GitHub** |
| Not run here | `playwright show-trace` UI, `--headed` (need a desktop); the §5.3 and "Your turn" exercises are for you |
