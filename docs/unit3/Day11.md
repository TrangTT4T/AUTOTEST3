# Unit 3 · Day 11 — Appium Implementation Lab: Prioritised Mobile Workflows and Execution Evidence

| | |
|---|---|
| **Course** | Advanced Automation Test Engineering (ATEST03) — Fast Track |
| **Unit** | Unit 3 — Mobile and Asynchronous-System Testing |
| **Learning outcome** | **LO5** — Implement mobile automation for prioritised Android/iOS workflows using Appium and appropriate synchronization (Bloom **B3: Apply**) |
| **Format** | Assignment/Lab · 150 minutes · **code is the deliverable** |
| **System under test** | Sauce Labs **My Demo App**, Android (`com.saucelabs.mydemoapp.android`) |
| **Starting point** | The Unit 2 project (`Unit2/day7-code/shop-bdd`) |
| **Code** | `Unit3/day11-code/shop-bdd.zip` |
| **Output of the day** | A `MobileStore` and screen objects; the Unit 1 cart scenarios running on the app; P1/P2 mobile workflow tests; a filled **execution-evidence** record (Day 9, §6.3) |

> **How this lab was checked — read this first.** The code was written against **Appium 4.0.0**, **UiAutomator2 driver 9.2.1**, and **Appium Python client 6.1.7**. No Android emulator could run where this lab was prepared, so **nothing in this lab has run on a device yet.** What was verified instead:
> - Every locator was checked against an inventory extracted from the app's own source.
> - The cart scenarios ran offline against the app's real catalogue.
> - Lint, type checks, unit and architecture tests all pass.
> - A real Appium 4 server was started without an Android SDK, and the suite reported every mobile test **BLOCKED** with the server's own reason.
>
> **Your first job in this lab is the first device run.** Part 8 lists exactly what to confirm on it.

---

## How to use this lab

| Badge | Level | After this level you can… |
|---|---|---|
| 🟢 | **Foundation** | Install Appium and an emulator, start a session, and find elements with Appium Inspector |
| 🟡 | **Practitioner** | Build screen objects with strict lookups and explicit waits; automate a full app workflow; collect evidence when it fails |
| 🔴 | **Senior** | Run one BDD specification on web and mobile through the same port. Separate environment problems from product defects. Prove locators without a device. Keep the requirement matrix honest across platforms |

Work through the parts in order. Each one shows the finished code and explains **why** it is written that way. The "Your turn" tasks are the part you write yourself.

### Lab plan (150 min)

| Time | Part |
|---|---|
| 0–20 | Part 0 — Setup: emulator, Appium, the app |
| 20–35 | Part 1 — Reconnaissance and choosing the workflows |
| 35–55 | Part 2 — Locators and screen objects |
| 55–70 | Part 3 — Session, capabilities, reset, and BLOCKED |
| 70–85 | Part 4 — Synchronization |
| 85–110 | Part 5 — The workflows |
| 110–130 | Part 6 — Evidence |
| 130–150 | Part 7 — Platform selection and traceability · Part 8 — First device run and deliverables |

---

## Glossary

| Term | Meaning | Vietnamese |
|---|---|---|
| AVD | Android Virtual Device — an emulator profile created in Android Studio | Thiết bị Android ảo |
| APK | Android app package — the file you install | Gói cài đặt ứng dụng Android |
| `adb` | Android Debug Bridge — the command-line link between your computer and the device | Cầu nối gỡ lỗi Android |
| Screen object | The mobile counterpart of a page object: one class per app screen | Đối tượng màn hình |
| Resource id | The `android:id` of a view, e.g. `cartTV` | Mã định danh tài nguyên |
| Accessibility id | The content description of a view, e.g. `"View cart"` | Mã trợ năng |
| Locator contract | A test that proves every locator exists in the app's layouts, without a device | Hợp đồng locator |
| Deselect | Remove a test from this run (it is not counted at all) — unlike *skip* | Loại khỏi lượt chạy |
| logcat | Android's system and app log | Nhật ký hệ thống Android |

---

## Part 0 — Setup 🟢

### 0.1 What you need

| Piece | Version used here | Why |
|---|---|---|
| Android Studio + an emulator (AVD) | Any recent; a Pixel image with Google APIs, API 34 or 35 | The device |
| Node.js | 22.22.2+ or 24.15+ (Appium 4's requirement) | Appium is a Node.js server |
| Appium server | 4.0.0 | Receives WebDriver commands |
| UiAutomator2 driver | 9.2.1 | Drives Android |
| Appium Python client | 6.1.7 (pinned in `requirements.txt`) | Our tests' side |
| Appium Inspector (desktop app) | Any recent | Find and try locators by hand |
| My Demo App APK | Release **2.3.0** from the Releases page of `saucelabs/my-demo-app-android` on GitHub | The app |

Set the SDK location so that Appium can find `adb`. Add these lines to your shell profile, adjusting the path to wherever Android Studio installed the SDK:

```bash
export ANDROID_HOME="$HOME/Android/Sdk"
```

```bash
export PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"
```

On macOS the default path is `$HOME/Library/Android/sdk`. On Windows it is `%LOCALAPPDATA%\Android\Sdk`; set the variables in *System → Environment Variables*.

### 0.2 Install and check

```bash
npm install -g appium
```

```bash
appium driver install uiautomator2
```

```bash
appium driver doctor uiautomator2
```

`doctor` lists anything still missing (SDK, Java, `adb`). Fix every **required** item before you continue.

Start an emulator from Android Studio's *Device Manager*, or from a terminal with your own AVD name (`emulator -list-avds` shows the names):

```bash
emulator -avd Pixel_8
```

```bash
adb devices
```

You should see one line ending in `device`. If it says `offline` or `unauthorized`, wait for the emulator to finish booting, then run the command again.

### 0.3 The project

```bash
unzip shop-bdd.zip && cd shop-bdd
```

```bash
python -m venv .venv && source .venv/bin/activate
```

```bash
pip install -r requirements-dev.txt
```

```bash
pytest --store fake -n auto --fail-on-uncovered
```

Expected result: `176 passed, 2 skipped`. This offline run already includes the six mobile cart scenarios. They run against the app's catalogue, with no device needed (Part 7 explains how).

### 0.4 First manual session with Appium Inspector

Start the server in one terminal and leave it running:

```bash
appium
```

In Appium Inspector, set *Remote Host* `127.0.0.1`, *Port* `4723`, *Path* `/`, and paste these capabilities. Replace the `app` path with your own; leave it out if the app is already installed:

```json
{
  "platformName": "Android",
  "appium:automationName": "UiAutomator2",
  "appium:deviceName": "Android Emulator",
  "appium:app": "/path/to/my-demo-app.apk",
  "appium:appPackage": "com.saucelabs.mydemoapp.android",
  "appium:appActivity": ".view.activities.SplashActivity",
  "appium:appWaitActivity": "*",
  "appium:autoGrantPermissions": true,
  "appium:language": "en",
  "appium:locale": "US"
}
```

Then do the following and note what you see:
1. Tap a product.
2. Select the *Add To Cart* button and note its `content-desc` and `resource-id`.
3. Note what the cart badge shows **before** you add anything.

You will compare these notes with the code in Part 2 and Part 8.

---

## Part 1 — Reconnaissance and choosing the workflows 🟡 → 🔴

### 1.1 🟡 Read the app before you automate it

On the web shop you explored pages in DevTools. For a native app, the best map is its **source code**, when you have it, and My Demo App's is public. Two small tools read it **statically**, without running the app:

| Tool | Reads | Writes | Used by |
|---|---|---|---|
| `tools/extract_ui_inventory.py` | `res/layout/*.xml` + `AndroidManifest.xml` | `tests/data/mobile_ui_inventory.json` — 29 layouts, every view id and content description | The locator contract test (Part 2.3) |
| `tools/extract_mobile_catalogue.py` | `BaseActivity.populateProductsDb` | `tests/data/mobile_catalogue.json` — 24 products, USD | `FakeStore`, `MobileStore`, and the tests' expected prices |

Both files record their source (`saucelabs/my-demo-app-android af2c830 2026-10-29`). When you install a different build, re-extract from that build's tag, using the commands in the README.

Reading the source also gave **facts the tests depend on**. Each one is marked "confirm on a device" (Part 8):

| Fact (from the source) | Where it matters |
|---|---|
| Prices are shown as `"$ 29.99"` (a space after `$`) in the cart; delivery is `$5.99` | `Money.parse` must accept both formats (unit-tested) |
| Checkout requires a login; `bod@example.com` / `10203040` is the test account | P1 checkout |
| `alice@example.com` is locked out; an empty username shows "Username is required" | P2 login rules |
| **Any non-empty password is accepted** for every other user (`LoginFragment.loginWithEmail`) | A finding: §5.4 |
| Cart and login live in memory, so restarting the app clears them | Test isolation (§3.3) |
| Nothing is charged: it is a demo app | The **whole** checkout can be automated, unlike the web shop, where we stopped before payment |

> 🔴 **Senior habit.** Static reading is cheap and catches whole classes of errors before a device is involved. It cannot prove **behaviour**: timing, rendering, scrolling, and what the app really shows on screen. Treat every fact from the source as a hypothesis until a device run confirms it.

### 1.2 🔴 Which workflows, in which priority

The app is a **different product** from the web shop, so the same requirements map to it differently:

| Priority | Workflow | Requirements | Why this priority | Form |
|---|---|---|---|---|
| **P1** | Add to cart → cart → login → shipping → payment → review → *Checkout Complete* | REQ-03, 04, 07, 08 | The revenue path; one test proves every screen connects | Plain Appium test (`tests/mobile/test_checkout_flow.py`) |
| **P1** | Add one product; the cart and subtotal are right | REQ-03, 04 | Highest-risk rule, already specified in Unit 1 | **Same BDD steps** as the web (`features/mobile_cart.feature`) |
| **P2** | Quantity outline (×2, ×3); several products; remove; change quantity | REQ-04, 05 | Cart arithmetic and editing | Same BDD steps |
| **P2** | Locked-out user; empty username; wrong password | REQ-08 | Security-relevant rules. On the web they are **manual** (CAPTCHA); the app has no CAPTCHA, so here they can be automated | Plain Appium tests (`tests/mobile/test_login.py`) |
| — | Search, sold-out items, information pages, variants | REQ-01, 02, 06, 09 | The app has no such features | Not applicable: the adapter raises `NotSupportedOnPlatformError` |

Why are some workflows BDD and some plain tests? The cart rules are **business behaviour shared by both platforms**, so the same Gherkin specifies both. The checkout and login flows are **app-specific journeys**: writing new Gherkin for them would only describe this one app's screens, so plain tests are clearer.

---

## Part 2 — Locators and screen objects 🟡

### 2.1 Locator rules (from Day 9, Part 3)

1. Use the **accessibility id** where the app has a unique content description (`"View cart"`, `"Tap to add product to cart"`).
2. Otherwise use the **resource id** (`cartTV`, `totalPriceTV`).
3. Do not use `-android uiautomator`.
4. Use XPath **once**, scoped to one cart row.
5. Every locator names the **layout file** it comes from, so a failure points to the source.

**Where locators live:** at the **bottom of each screen class**, after the methods that use them, in a `# --- Locators ---` section. This is the same convention as the web page objects. Methods refer to them by name only.

`framework/adapters/mobile/locators.py` provides the type and three builders:

```python
@dataclass(frozen=True)
class Locator:
    by: str
    value: str
    layout: str  # source layout file (without .xml) the element is defined in

    def as_tuple(self) -> tuple[str, str]:
        return (self.by, self.value)


def by_id(value: str, layout: str) -> Locator:
    """A resource id, e.g. ``cartTV`` (the driver adds the package prefix)."""
    return Locator(AppiumBy.ID, value, layout)


def by_accessibility_id(value: str, layout: str) -> Locator:
    """A content description, e.g. ``"View cart"``."""
    return Locator(AppiumBy.ACCESSIBILITY_ID, value, layout)
```

`ProductScreen` (end of the class, `screens/product.py`):

```python
    def add_to_cart(self, quantity: int = 1) -> None:
        """Set the quantity, tap once, and wait for the evidence: the header badge."""
        before = self.cart_count()
        self.set_quantity(quantity)
        self.tap(self._add_to_cart)
        self.wait_for_cart_count(before + quantity)

    # --- Locators -----------------------------------------------------------------
    _title = by_id("productTV", "fragment_product_detail")  # the product's name
    _price = by_id("priceTV", "fragment_product_detail")
    _plus = by_accessibility_id("Increase item quantity", "fragment_product_detail")
    _minus = by_accessibility_id("Decrease item quantity", "fragment_product_detail")
    _quantity = by_id("noTV", "fragment_product_detail")
    _add_to_cart = by_accessibility_id("Tap to add product to cart", "fragment_product_detail")
```

The header locators (cart, badge, menu) sit at the bottom of the base class `Screen`, because every screen has the header. The one XPath is `CartScreen._line_row_from_title`, which climbs from a line's title to its row.

Note that `productTV` appears in three layouts with three meanings: the catalogue title "Products", the product's name, and the cart title "My Cart". The `layout` field and one class per screen keep them apart.

### 2.2 The base screen: strict lookups

Appium has no Playwright-style *strict mode*, so `find_element` silently returns the **first** match. The base class adds strictness:

```python
    def one(self, locator: Locator, within: WebElement | None = None) -> WebElement:
        """Exactly one match, or an error. Appium has no strict mode (Day 9, 3.4)."""
        root = within if within is not None else self.driver
        matches = root.find_elements(*locator.as_tuple())
        if len(matches) != 1:
            raise AssertionError(f"{locator.value!r} ({locator.layout}) matched {len(matches)} elements")
        return matches[0]
```

The screen objects in `framework/adapters/mobile/screens/` are:

| Screen | Proves it is shown by | Main methods |
|---|---|---|
| `CatalogScreen` | The list, plus the title "Products" | `open_product(name)` (scrolls until found) |
| `ProductScreen` | *Add To Cart* is visible | `read()`, `set_quantity(n)`, `add_to_cart(n)` |
| `CartScreen` | The total **or** "No Items" | `read()`, `remove`, `set_quantity`, `proceed_to_checkout`, `go_shopping` |
| `LoginScreen` | The login button | `log_in`, `password_error`, `username_error` |
| `ShippingScreen` / `PaymentScreen` | Their headings | `submit(Address)` / `submit(Card)` |
| `ReviewScreen` | *Place Order* | `item_count`, `delivery`, `total`, `place_order` |
| `CompleteScreen` | The completion title | `title`, `continue_shopping` |

### 2.3 🔴 The locator contract: prove locators without a device

`tests/unit/test_mobile.py` checks **every** locator against the inventory extracted from the app's layouts:

```python
@pytest.mark.parametrize(("screen", "name", "locator"), LOCATORS, ids=[f"{s}.{n}" for s, n, _ in LOCATORS])
def test_every_locator_exists_in_the_app(screen: str, name: str, locator: Locator) -> None:
    layout = INVENTORY["layouts"].get(locator.layout)
    assert layout is not None, f"{screen}.{name}: no layout {locator.layout!r} in the app"
    if locator.by == AppiumBy.ID:
        assert locator.value in layout, f"{screen}.{name}: id {locator.value!r} not in {locator.layout}"
    elif locator.by == AppiumBy.XPATH:  # structural: every id it mentions must exist in the layout
        ids = re.findall(r"@resource-id, '(\w+)'", locator.value)
        assert ids, f"{screen}.{name}: XPath names no resource id to anchor on"
        assert all(i in layout for i in ids), f"{screen}.{name}: {ids} not all in {locator.layout}"
    else:
        matches = [i for i, e in layout.items() if e["content_description"] == locator.value]
        assert len(matches) == 1, f"{screen}.{name}: {locator.value!r} matches {matches} in {locator.layout}"
```

The test runs in milliseconds, in CI, with no emulator. It catches typos, renamed ids, and accessibility ids that are **not unique** within a layout. It does **not** catch an element that exists but is hidden, off-screen, or rendered differently; only a device run can show those.

### 2.4 Architecture rule: lookups live in screen objects

```python
def test_appium_lookups_live_only_in_screen_objects() -> None:
    offenders: list[str] = []
    for path in _python_files("framework", "tests"):
        rel = _rel(path)
        if rel.startswith(("framework/adapters/mobile/screens/", "tests/unit/")):
            continue
        offenders.extend(
            f"{rel}:{node.lineno} .{node.attr}(...)"
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
            if isinstance(node, ast.Attribute) and node.attr in {"find_element", "find_elements"}
        )
    assert not offenders, "Appium lookups outside screen objects:\n" + "\n".join(offenders)
```

There are also two related rules. Steps may not import `appium` or `selenium`. `time.sleep` is allowed only in `framework/adapters/mobile/waits.py`, inside the polling helper.

Two more rules guard the convention:
- `test_screens_declare_their_locators` fails the build if a method builds a locator, or calls `find_element` with a literal selector.
- The contract test reads every screen's `Locators` section through `ALL_SCREENS` (`screens/__init__.py`), so a new locator is checked as soon as you declare it.

> **Your turn (🟡).** Add `CatalogScreen.product_names()`, which returns the names of the visible tiles. Declare any new locator in the class's Locators section, run the contract test, then use Inspector to check your method on the device.

---

## Part 3 — Session, capabilities, reset, and BLOCKED 🟡 → 🔴

### 3.1 Capabilities: pin what affects results

`framework/adapters/mobile/capabilities.py` builds `UiAutomator2Options`. Values that differ per machine come from options or environment variables. Values that change results are **pinned**:

| Capability | Value | Why |
|---|---|---|
| `appPackage` / `appActivity` | `com.saucelabs.mydemoapp.android` / `.view.activities.SplashActivity` | From `AndroidManifest.xml` |
| `appWaitActivity` | `*` | The splash screen hands over to `MainActivity` |
| `language` / `locale` | `en` / `US` | Texts and the USD format, just as Unit 2 pinned `en-GB` |
| `disableWindowAnimation` | `true` | Fewer timing differences |
| `autoGrantPermissions` | `true` | No permission pop-ups mid-test |
| `newCommandTimeout` | `120` | The server ends abandoned sessions |
| `noReset` | `false` | Start from a clean app data state |

| Option | Environment variable | Default |
|---|---|---|
| `--appium-url` | `SHOP_APPIUM_URL` | `http://127.0.0.1:4723` |
| `--android-app` | `SHOP_ANDROID_APP` | — (the app is already installed) |
| `--android-device` | `SHOP_ANDROID_DEVICE` | `Android Emulator` |
| `--android-avd` | `SHOP_ANDROID_AVD` | — (if set, Appium starts this emulator itself) |

### 3.2 🔴 One session per run, and BLOCKED rather than FAILED

Starting an Appium session installs or launches the app, which takes seconds to a minute. So the framework opens **one session per run** (`scope="session"`) and **restarts the app** before each test.

When the environment is not ready, the error must say so **once** and must not look like a product defect. `framework/adapters/mobile/session.py`:

```python
def start_android_session(settings: Settings) -> WebDriver:
    server_status(settings.appium_url)
    try:
        return webdriver.Remote(settings.appium_url, options=android_options(settings))
    except Exception as error:  # Selenium/Appium wrap many causes in WebDriverException
        first_line = str(error).strip().splitlines()[0] if str(error).strip() else repr(error)
        if is_environment_problem(str(error)):
            raise EnvironmentBlockedError(f"mobile environment not ready: {first_line}") from error
        raise
```

`is_environment_problem` recognises these messages:
- missing SDK
- no connected device
- `adb` not found
- connection refused
- a missing driver

Unit tests prove two things about it: it recognises those messages, and it does **not** misread app problems such as "element could not be located" as environment problems.

`framework/plugins/mobile.py` caches the failure, so the server receives **one** attempt per run instead of one per test:

```python
@pytest.fixture(scope="session")
def mobile_driver(settings: Settings, pytestconfig: pytest.Config) -> Iterator[WebDriver]:
    """One Appium session per run (Day 9, 2.4); each test restarts the app for a known state.

    If the environment is not ready, every mobile test is reported BLOCKED with the reason,
    and the session start is not retried for each test.
    """
    if _SESSION_ERROR in pytestconfig.stash:
        raise pytestconfig.stash[_SESSION_ERROR]
    try:
        driver = start_android_session(settings)
    except EnvironmentBlockedError as error:
        pytestconfig.stash[_SESSION_ERROR] = error
        raise
    log.info("mobile session started: %s", evidence.safe_capabilities(dict(driver.capabilities)))
    driver.implicitly_wait(0)  # explicit waits only (Day 9, 5.2)
    yield driver
    driver.quit()
```

What this looks like with no Appium server running (an actual run):

```
EnvironmentBlockedError: no Appium server at http://127.0.0.1:4723: <urlopen error [Errno 111] Connection refused>

REQ-03  high    Add an available product to the cart              3    0    0    2    0  BLOCKED
REQ-04  high    Cart shows correct items, quantities, subtotal    6    0    0    5    0  BLOCKED
REQ-05  high    Change quantity or remove an item                 4    0    0    2    0  BLOCKED
REQ-07  medium  Proceed from cart to checkout                     2    0    0    1    0  BLOCKED
REQ-08  medium  Sign up and log in                                2    0    0    4    0  BLOCKED
```

With the server running but no Android SDK, the reason changes to `mobile environment not ready: Neither ANDROID_HOME nor ANDROID_SDK_ROOT environment variable was exported…`. That is the exact message seen on Day 9.

### 3.3 A known state for every test

```python
def restart_app(driver: WebDriver) -> None:
    """Known state for the next test: the app keeps cart and login in memory, so a
    process restart clears them (from the source; confirm on a device)."""
    driver.terminate_app(APP_PACKAGE)
    driver.activate_app(APP_PACKAGE)
```

The two common reset strategies cost different amounts:

| Strategy | Cost | Clears |
|---|---|---|
| New session per test | High (reinstall/launch) | Everything |
| **Restart the app process** (chosen) | Low | Whatever lives in memory — cart and login here |
| `mobile: clearApp` (`pm clear`) | Medium | App data on disk too; use it if the app starts persisting the cart |

> 🔴 If the device run shows that a restart does **not** clear the cart, the BDD step "Given a visitor with an empty cart" will fail in the second scenario. Fix it in `restart_app` (add `mobile: clearApp`), **not** in the tests.

---

## Part 4 — Synchronization 🟡 → 🔴

### 4.1 Rule: implicit wait 0, explicit waits for evidence

Appium does not wait for anything by itself (Day 9, Part 5). Mixing implicit and explicit waits makes timeouts unpredictable, so the implicit wait is set to `0`, and every wait is **explicit, for a condition, with a deadline**. `framework/adapters/mobile/waits.py`:

```python
def wait_until(
    read: Callable[[], T],
    done: Callable[[T], bool],
    *,
    timeout: float = 10.0,
    interval: float = 0.1,
    backoff: float = 2.0,
    max_interval: float = 2.0,
) -> T:
    """Poll ``read()`` until ``done(value)`` holds; return it, or raise with the last value (Day 10)."""
    deadline = time.monotonic() + timeout
    value = read()
    while not done(value):
        if time.monotonic() >= deadline:
            raise TimeoutError(f"condition not met within {timeout}s; last value: {value!r}")
        time.sleep(min(interval, max(0.0, deadline - time.monotonic())))  # bounded poll interval
        interval = min(interval * backoff, max_interval)
        value = read()
    return value
```

This is the Day 10 polling pattern: backoff, a cap, a deadline, and **the last value in the error**. A timeout then tells you *what* the app showed, not merely that it took too long.

### 4.2 Wait for the evidence of the action

A tap returns when the finger lifts, not when the app has finished. So after *Add To Cart*, the code waits for the **business evidence**: the header badge showing the new count.

```python
    def add_to_cart(self, quantity: int = 1) -> None:
        """Set the quantity, tap once, and wait for the evidence: the header badge."""
        before = self.cart_count()
        self.set_quantity(quantity)
        self.tap(self._add_to_cart)
        self.wait_for_cart_count(before + quantity)
```

The same pattern appears in `CartScreen.remove` (badge minus that line's quantity) and in `CartScreen.set_quantity` (badge ±1 after every tap).

### 4.3 Scrolling until found

`CatalogScreen.open_product` scrolls until the tile is visible, and **stops when the list cannot scroll further**. `mobile: scrollGesture` returns whether more scrolling is possible:

```python
        for _ in range(max_swipes):
            if found():
                return True
            area = self.visible(container)
            can_scroll = self.driver.execute_script(
                "mobile: scrollGesture", {"elementId": area.id, "direction": "down", "percent": 0.75}
            )
            if not can_scroll:
                return found()
        return found()
```

> ⚠️ **Open question.** The driver's documentation describes `percent` as "0–100". The Android API that the driver forwards it to (`UiObject2.scroll`) takes a fraction from 0 to 1. The code uses `0.75`, following the API. Check it on the device (Part 8) and fix the value if the scroll is tiny or out of range.

---

## Part 5 — The workflows 🟡 → 🔴

### 5.1 🔴 The same Gherkin on two platforms

`features/mobile_cart.feature` uses the **exact step texts** from Unit 1. No new step definitions were written:

```gherkin
@mobile
Feature: Shopping cart in the mobile app
  The Unit 1 cart behaviour, specified with the same steps, for My Demo App (Android).
  The app is a different product with its own catalogue (USD); see Unit 3, Day 11.

  Background:
    Given a visitor with an empty cart

  Rule: Added products appear in the cart with a correct subtotal

    @REQ-03 @REQ-04 @risk-high @smoke
    Scenario: Adding a product in the app puts it in the cart
      Given the visitor is viewing the product "Sauce Labs Backpack"
      When they add the product to the cart
      Then the cart contains 1 "Sauce Labs Backpack"
      And the cart subtotal equals the product price times 1
```

The feature has five more scenarios: a quantity outline (Backpack ×2, Bike Light ×3), several products, remove, and change quantity.

This works because the steps talk to the **Store port**, and `MobileStore` implements that port with screen objects:

```
features/*.feature ── tests/steps/*.py ── Store port ─┬─ FakeStore   (in memory; web or app catalogue)
                                                      ├─ WebStore    (Playwright)
                                                      └─ MobileStore (Appium) ── screen objects
```

A native app has no API to compare the cart against. So `MobileStore.cart()` checks that **three views of the same cart on one screen agree**:

```python
    @staticmethod
    def _check_consistent(cart: Cart, badge: int, items_label: int | None) -> None:
        """Three views of the same cart on one screen must agree (no API to compare with)."""
        problems = []
        lines_total = sum((line.line_total for line in cart.lines), Money.zero(cart.total.currency))
        if cart.lines and lines_total != cart.total:
            problems.append(f"total {cart.total} vs sum of lines {lines_total}")
        if badge != cart.item_count:
            problems.append(f"header badge {badge} vs lines {cart.item_count}")
        if items_label is not None and items_label != cart.item_count:
            problems.append(f"'{items_label} items' label vs lines {cart.item_count}")
        if problems:
            raise CartInconsistencyError("cart screen disagrees with itself: " + "; ".join(problems))
```

Features the app does not have raise `NotSupportedOnPlatformError("My Demo App has no search")` and so on. That is a clear message if someone tags a search scenario `@mobile` by mistake.

> 🔴 **Lesson: currency.** The first offline run of these scenarios failed with `cannot combine GBP and USD`. `Money.zero()` had quietly assumed GBP, the web shop's currency. The fix gave `Catalogue` a `currency`, read from the snapshot, and every empty cart and sum now starts from that currency. **A second platform tests your domain model's hidden assumptions.**

### 5.2 P1: the full checkout journey

`tests/mobile/test_checkout_flow.py` (the middle of the test):

```python
    with mobile_step("Review the cart"):
        cart_screen = CartScreen(app)
        cart_screen.open_cart()
        cart = cart_screen.read()
        assert cart.quantities() == {backpack.name: 2}, cart.describe()
        assert cart.total == backpack.price * 2, cart.describe()
        cart_screen.proceed_to_checkout()

    with mobile_step("Log in with the app's test account"):
        LoginScreen(app).log_in("bod@example.com", "10203040")

    with mobile_step("Enter the shipping address and the payment card"):
        ShippingScreen(app).submit(shipping_address)
        PaymentScreen(app).submit(test_card)

    with mobile_step("Review: items and total include delivery"):
        review = ReviewScreen(app)
        review.wait_until_loaded()
        assert review.item_count() == 2
        assert review.delivery() == Money.parse(DELIVERY, "USD")
        assert review.total() == backpack.price * 2 + review.delivery()
        review.place_order()
```

How to read it:
- **Expected values come from the catalogue**, never from the screen being checked: the product price comes from `mobile_catalogue.json`.
- **The review total is derived**, not hard-coded: 2 × $29.99 + $5.99 = $65.97.
- `mobile_step` names each business step in the log. It is the mobile counterpart of `business_step`; Appium has no trace groups.
- The card number `3258125675687891` is not a real card. It is the number the app's own Espresso test uses. Nothing is charged.

### 5.3 P2: login rules

```python
@covers("REQ-08")
def test_locked_out_user_cannot_log_in(app: WebDriver) -> None:
    login = _to_login(app)
    login.log_in("alice@example.com", "10203040")
    assert login.password_error() == "Sorry this user has been locked out."
```

`test_login_requires_a_username` does the same with an empty username and expects "Username is required".

### 5.4 🔴 The finding: wrong passwords are accepted

From the source, `loginWithEmail` accepts **any non-empty password** for every user except the locked-out one. This is recorded as a **strict xfail** — a tripwire, exactly like defect D-01 on Day 7:

```python
@covers("REQ-08")
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,  # only a failed check is the known defect; anything else must surface
    reason="App behaviour read in its source (LoginFragment.loginWithEmail): any non-empty password "
    "is accepted for any user except alice@example.com. Fine for a demo app; a High security "
    "defect in a real one. strict=True: if the app starts checking passwords, this test XPASSes.",
)
def test_wrong_password_is_rejected(app: WebDriver) -> None:
    login = _to_login(app)
    login.log_in("bod@example.com", "definitely-wrong")
    assert not ShippingScreen(app).is_current(), "logged in with a wrong password"
    assert login.password_error(), "no error message for a wrong password"
```

> 🔴 **Lesson: `raises=AssertionError`.** Without it, the first run with no Appium server reported this test as **xfailed**, which looks like "the known defect, as expected". In fact the test never reached the app. `raises=AssertionError` limits the expected failure to *the check failing*. Any other error, such as an environment block or a missing element, now surfaces as a real failure or as BLOCKED. The same fix was applied to all three xfail tests in the project.

Write the finding in Day 4 format:

| Field | Value |
|---|---|
| Title | Login accepts any non-empty password |
| Severity | High (in a real app: account takeover) · demo app: documented, not fixed |
| Steps | Cart → Proceed to Checkout → user `bod@example.com`, password `definitely-wrong` → Login |
| Expected | An error; still on the login screen |
| Actual | The shipping-address screen opens *(confirm on a device)* |
| Evidence | Source `LoginFragment.loginWithEmail`; after the device run: screenshot and recording |
| Test | `tests/mobile/test_login.py::test_wrong_password_is_rejected` (strict xfail) |

> **Your turn (🟡 → 🔴).** Add a P2 test: after *Checkout Complete*, tapping *Continue Shopping* shows the catalogue, and the cart badge is empty. Use screen objects only, `@covers("REQ-07")`, and `mobile_step`. First predict whether the cart is cleared, by reading `CheckoutCompleteFragment` in the source, then confirm on the device.

---

## Part 6 — Evidence 🟡 → 🔴

### 6.1 What is kept, and when

Every test records the screen. A passing test discards its recording; a failing test keeps **everything** in `reports/mobile/<test name>/`:

| File | Answers | Playwright equivalent |
|---|---|---|
| `screenshot.png` | What the user saw | Screenshot |
| `page_source.xml` | Which elements existed, with ids, texts, `displayed`/`enabled` | DOM snapshot in the trace |
| `logcat.txt` | Crashes, exceptions, app logs (last 300 lines) | Console log |
| `device_info.json` | Model, Android version, screen | Browser/context info |
| `capabilities.json` | What the session asked for and got — **secrets masked** | Context options |
| `recording.mp4` | How the app got there | Trace timeline/video |

```python
@pytest.fixture
def mobile_app(request: pytest.FixtureRequest, mobile_driver: WebDriver) -> Iterator[WebDriver]:
    """The app restarted for this test, recording on; evidence kept only if the test fails."""
    restart_app(mobile_driver)
    mobile_driver.start_recording_screen()
    yield mobile_driver
    folder = Path(request.config.rootpath, "reports", "mobile", re.sub(r"\W+", "_", request.node.name))
    if _failed(request):
        written = evidence.collect(mobile_driver, folder)
        evidence.save_recording(mobile_driver, folder / "recording.mp4")
        log.error("mobile evidence saved in %s: %s", folder, [p.name for p in written])
    else:
        try:
            mobile_driver.stop_recording_screen()  # discard
        except Exception as error:  # noqa: BLE001 - a failed discard must not fail a passing test
            log.warning("could not stop the recording: %r", error)
```

`evidence.collect` saves each file independently: one file that cannot be collected (for example, logcat not enabled) logs a warning and **never hides the original failure**.

The capabilities are masked before they are written. Any key containing `key`, `token`, `password`, `secret`, or `access` becomes `***`. This matters as soon as you run on a device cloud with an access key, and a unit test proves it.

### 6.2 🔴 Fill the execution-evidence record

Copy the template from Day 9 §6.3 for **each** device run. Here is an example of the shape. Replace every `<…>` with the values from your run; do not copy the numbers.

```markdown
# Mobile execution evidence — <2026-11-20-run-1>

| Field | Value |
|---|---|
| Date / time (UTC) | <…> |
| App and build | My Demo App 2.3.0, <apk file name> |
| Platform / OS version | Android <14> |
| Device | <Pixel_8 AVD>, udid <emulator-55xx> |
| Appium / driver / client versions | Appium 4.0.0 / UiAutomator2 9.2.1 / Python client 6.1.7 |
| Capabilities profile | android_options(); effective capabilities in reports/…/capabilities.json |
| Tests run / passed / failed / blocked | <10 / … / … / …> (+ 1 expected xfail) |

## Per test
| Test | Requirement | Result | Class | Evidence files |
|---|---|---|---|---|
| test_customer_completes_checkout_in_the_app | REQ-03,04,07,08 | <PASS> | — | — |
| test_wrong_password_is_rejected | REQ-08 | XFAIL (known) | product | — |
| … | | | | |

## Failures
<failing business step (from the "STEP" log lines), screenshot, page source,
logcat excerpt, recording, Appium server log excerpt, diagnosis, finding (Day 4 format)>
```

For the server log, start Appium with a log file so you can attach an excerpt:

```bash
appium --log appium.log --log-timestamp
```

---

## Part 7 — Platform selection and traceability 🔴

### 7.1 One project, three ways to run

| `--store` | BDD `@web` | BDD `@mobile` | `tests/e2e`, `tests/pages` | `tests/mobile` |
|---|---|---|---|---|
| `fake` | run (web catalogue) | run (app catalogue) | — | — |
| `web` | run | — | run | — |
| `mobile` | — | run | — | run |

In `--store fake`, the `store` fixture picks the **snapshot** from the scenario's tag: `@mobile` scenarios get `FakeStore` loaded with the app's 24 products in USD. That is how the mobile scenarios were proven offline before any device existed. When a step or catalogue fact is wrong, the error appears here first, as it did with the currency bug.

### 7.2 🔴 Lesson: deselect, do not skip

The first version **skipped** web tests in a mobile run. In the requirement matrix, a skip counts as **MANUAL** ("someone checks this by hand"), so the matrix claimed that REQ-01 and REQ-09 were covered manually during a mobile run, which was false. The plugin now **deselects** them: they are not part of this run at all, and the matrix says **NOT RUN**. A summary line says what was removed and why:

```
Platform selection (--store mobile): deselected 22 (scenario not tagged @mobile), 32 (web tests need --store web)
```

In the final code this rule is a pure function in its own plugin, `framework/plugins/selection.py`. Day 12 moved it there and added the events tests:

```python
FOLDER_STORES = {
    "mobile": ("mobile", "mobile tests need --store mobile"),
    "e2e": ("web", "web tests need --store web"),
    "pages": ("web", "web tests need --store web"),
    "events": ("fake", "events tests run with --store fake (local sandbox)"),
}


def deselect_reason(store: str, folder: str, platforms: set[str]) -> str | None:
    """Why a test does not belong to this run, or None. Pure: unit-tested."""
    if folder in FOLDER_STORES:
        needed, reason = FOLDER_STORES[folder]
        return None if store == needed else reason
    if folder == "tests" and platforms:  # a BDD scenario
        if "events" in platforms:
            return None if store == "fake" else "events scenarios run with --store fake (local sandbox)"
        if store == "web" and "web" not in platforms:
            return "scenario not tagged @web"
        if store == "mobile" and "mobile" not in platforms:
            return "scenario not tagged @mobile"
    return None
```

Being pure (no pytest objects in, a string out) is what makes it testable: `tests/unit/test_events.py::test_platform_selection` checks 11 combinations in milliseconds.

The statuses now tell the truth in every run:

| Status | Meaning in a mobile run |
|---|---|
| PASS / FAIL | Ran on the device |
| **BLOCKED** | Could not run: environment (no server, no SDK, no device) |
| **NOT RUN** | Not part of this platform (search, sold-out, information pages) |
| NOT COVERED | No test exists anywhere — `--fail-on-uncovered` fails the build |

### 7.3 🔴 What about iOS?

LO5 says "Android/iOS". The design is ready for iOS, but this lab implements Android only, because iOS needs macOS with Xcode. To add it:
1. Add an `ios_options()` function using `XCUITestOptions`.
2. Add a second locator map. Use the iOS accessibility ids from the iOS app's source, since they differ from Android's.
3. Choose the locator map by platform inside the screen objects.

The Store port, the steps, the feature file, `wait_until`, the evidence policy, and the matrix stay **unchanged**. Write this down as a design note; it is a Day 12 revision question.

---

## Part 8 — First device run and deliverables 🔴

### 8.1 Run

```bash
appium --log appium.log --log-timestamp
```

In a second terminal, from the project folder:

```bash
SHOP_ANDROID_APP=/path/to/my-demo-app.apk pytest tests/test_mobile_cart.py -k "puts_it_in_the_cart" --store mobile -v
```

Start with **one** smoke scenario. When it passes, run everything for the platform:

```bash
pytest --store mobile -v
```

Expected on a healthy device: **9 passed, 1 xfailed** (6 BDD scenarios + checkout + 2 login rules, plus the wrong-password tripwire). Deselected: 54.

### 8.2 Confirm these on the device

These are the points that could not be checked without a device. Tick each one and write what you saw in your evidence record:

| # | Check | If it is different |
|---|---|---|
| 1 | `scrollGesture` with `percent: 0.75` scrolls the catalogue (§4.3) | Try `75`. Also try the list (`Catalog.LIST`) as the container instead of `scrollView` |
| 2 | Restarting the app empties the cart and logs out (§3.3) | Add `mobile: clearApp` to `restart_app` |
| 3 | The cart badge with an empty cart: hidden or empty text? | `cart_count()` already treats both as 0; check that it does |
| 4 | The cart row XPath `./ancestor::*[.//*[contains(@resource-id,'removeBt')]][1]` finds one row per line | Inspect `page_source.xml`; adjust in `CartScreen._row_of` only |
| 5 | Price texts: cart `"$ 29.99"`, review delivery `"$5.99"`, total `"$ 65.97"` | `Money.parse` and its unit test |
| 6 | Wrong password logs in (§5.4) | If it is rejected, the test **XPASSes**: remove the xfail and update the README |
| 7 | `get_log("logcat")` and the screen recording work on your emulator | Evidence warns but never fails; note it |

### 8.3 Deliverables (checked on Day 12)

- [ ] `pytest --store fake -n auto --fail-on-uncovered` green (offline gate, includes the app's scenarios)
- [ ] `ruff check .`, `ruff format --check .`, `mypy`, `python -m framework.review --strict` clean
- [ ] One device run: `pytest --store mobile` with **9 passed, 1 xfailed** — or every difference explained
- [ ] The §8.2 table filled
- [ ] One **filled execution-evidence record** (§6.2), including one deliberately broken test with its evidence folder. For example, change the expected delivery to `"6.99"`, run, diagnose from `reports/mobile/…` only, then revert
- [ ] The wrong-password finding written up (§5.4), with a screenshot from the device
- [ ] Your two "Your turn" tasks (§2.4, §5.4)
- [ ] An iOS design note: what changes and what stays (§7.3)

---

## Common errors

| Error | Meaning | Fix |
|---|---|---|
| `BLOCKED … no Appium server at http://127.0.0.1:4723` | The server is not running, or it is on another port | Start `appium`; or set `SHOP_APPIUM_URL` |
| `BLOCKED … Neither ANDROID_HOME nor ANDROID_SDK_ROOT…` | The server cannot find the SDK | Export `ANDROID_HOME` **in the terminal that starts Appium**, then restart it |
| `BLOCKED … Could not find a connected Android device` | No emulator or phone | `adb devices`; start the AVD, or set `SHOP_ANDROID_AVD` |
| `Could not find a driver for automationName` | The driver is not installed | `appium driver install uiautomator2` |
| `'…' (layout) matched 0 elements` | The screen is not the one you think, or the id changed | Open `page_source.xml`; run the locator contract test |
| `matched 2 elements` | The locator is not unique on this screen | Scope it `within=` a row, or choose a more specific id |
| `TimeoutError: condition not met within 15s; last value: 1` | The badge never reached the expected count | The tap did not register, or the add failed: watch `recording.mp4` |
| `CartInconsistencyError: cart screen disagrees with itself` | Total, lines, badge, or label disagree | A **product** defect candidate: keep the evidence |
| `NotSupportedOnPlatformError: My Demo App has no search` | A web-only scenario was tagged `@mobile` | Remove the tag |
| `XPASS(strict)` on the wrong-password test | The app now rejects wrong passwords | Remove the xfail; update the README's findings |

---

## Self-check (answers below — try first)

1. Why does a timeout in `wait_until` include the **last value**?
2. Why is the implicit wait set to 0?
3. What does the locator contract test prove, and what can it **not** prove?
4. Why does a broken environment produce BLOCKED and not FAILED? Why is the session start not retried for each test?
5. Why restart the app instead of opening a new session for every test?
6. How can the mobile cart scenarios pass in `--store fake`, and what does that prove?
7. Why did skipping web tests in a mobile run make the matrix lie?
8. What did `raises=AssertionError` fix?
9. The app has no API. How does `MobileStore.cart()` still detect a wrong total?
10. What changes and what stays when you add iOS?

<details>
<summary><b>Answer guide</b></summary>

1. The value tells you what the app actually showed, such as "badge stayed at 1". That separates "slow" from "wrong", and you can often diagnose without rerunning.
2. Implicit waits apply to every lookup and combine unpredictably with explicit waits. Strict lookups (`find_elements` counting matches) would also wait the full implicit time whenever the answer is "zero".
3. It proves that every id and accessibility id exists in the layout it claims, and that accessibility ids are unique there. It catches typos and renames without a device. It cannot prove that the element is displayed, reachable, or behaves as expected; that needs a device.
4. Nothing about the app was tested, so FAILED would be a false product signal. One cached attempt keeps the report short, puts the reason in one place, and does not hammer the server with many failing session requests.
5. A session start installs or launches the app and costs seconds to a minute. A process restart is cheap, and it clears the app's in-memory cart and login.
6. The `store` fixture loads `FakeStore` with the app's extracted catalogue (USD) for `@mobile` scenarios. It proves the Gherkin, the steps, and the catalogue facts (names, prices, currency) are consistent. It does not prove the app's UI.
7. The matrix counts skipped tests as MANUAL. So a mobile run claimed that web-only requirements were checked by hand. Deselected tests are not part of the run, so they show NOT RUN.
8. Without it, any error (such as no server) inside the xfail test counted as the expected failure ("xfailed"), hiding an environment block. With it, only a failed check counts as the known defect.
9. It compares three views on the same screen: the total against the sum of the lines, the header badge against the line quantities, and the "n items" label against the lines. Any disagreement raises `CartInconsistencyError`.
10. Changes: capabilities (`XCUITestOptions`), the locator map (iOS accessibility ids), and choosing the platform in the screen objects. Stays: the feature files, steps, Store port, domain model, waits, evidence policy, requirement matrix, and platform selection.
</details>

## Next: Day 12

Topic revision of Units 1–3, then the **asynchronous-system lab** (LO6). You will verify events, retries, duplicates, ordering, timeouts, and recovery, using the polling and correlation techniques from Day 10. The `wait_until` helper from today is reused there.

---

## Verification log

| Check | Result |
|---|---|
| Fresh install from the zip: `pip install -r requirements-dev.txt` | OK |
| `ruff check .` / `ruff format --check .` | All checks passed / 104 files already formatted |
| `mypy --strict` | No issues in 98 source files |
| `python -m framework.review --strict` | OK |
| `pytest --store fake -n auto --fail-on-uncovered` | **176 passed, 2 skipped** (includes the 6 mobile cart scenarios on the app's catalogue) |
| Unit tests | 150 passed: locator contract for every locator, capabilities, environment classification, catalogue facts, `"$ 45.97"` parsing, cart-consistency rules, secret masking, architecture rules |
| `pytest --store mobile`, no Appium server | All 10 mobile tests BLOCKED: "no Appium server at http://127.0.0.1:4723 … Connection refused"; 54 deselected |
| `pytest --store mobile`, Appium 4.0.0 running, no Android SDK | All BLOCKED: "mobile environment not ready: Neither ANDROID_HOME nor ANDROID_SDK_ROOT…"; the server received **1** session request |
| `--store web` collection | 204 of 214 collected; 10 deselected (4 mobile tests, 6 `@mobile` scenarios) |
| Web xfail tripwires, live, after adding `raises=AssertionError` | Still 3 xfailed |
| App facts (locators, catalogue, prices, login rules, delivery) | Read **statically** from `saucelabs/my-demo-app-android` at commit `af2c830` (2026-10-29) |
| **On a device / emulator** | **Not run** — no emulator available here. The §8.2 list is what remains to confirm |
| Appium Inspector, recording, logcat | Not run (they need a device) |
| iOS | Not implemented (needs macOS + Xcode); design note only (§7.3) |
