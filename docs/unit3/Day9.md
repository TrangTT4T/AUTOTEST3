# Unit 3 · Day 9 — Appium Architecture, Capabilities, Locators, Gestures, Synchronization, Mobile Evidence

| | |
|---|---|
| **Course** | Advanced Automation Test Engineering (ATEST03) — Fast Track |
| **Unit** | Unit 3 — Mobile and Asynchronous-System Testing |
| **Learning outcome** | **LO5** — Implement mobile automation for prioritised Android/iOS workflows using Appium and appropriate synchronization (Bloom **B3: Apply**) |
| **Format** | Concept/Lecture · Virtual · 120 minutes · no code to produce (short illustrations only) |
| **Sample application** | Sauce Labs **My Demo App** (Android; an iOS version exists) — see Part 0.3 |
| **Output of the day** | Your one-page **mobile test design notes** and an **execution-evidence template** you will fill on Day 11 |

> **How the facts here were checked.** Appium **4.0.0** (current release), the **UiAutomator2 driver 9.2.1**, and the **Appium Python client 6.1.7** were installed while preparing this lecture. Their documentation and source were read, the server was started, and a session request was sent to observe the architecture's path. No emulator was available, so **nothing ran on a device**: every behaviour that needs one is marked *(confirm on Day 11)*. iOS command names were checked in the XCUITest driver 13.1.1 package.

---

## How to use this lecture

Unit 2 automated a browser. Unit 3 automates **apps on phones**. Many ideas carry over — layers, page objects, waiting for evidence, isolation — but three things change sharply: **there is no automatic waiting**, the **session is expensive**, and **the device itself** becomes part of what can fail.

| Badge | Level | After this level you can… |
|---|---|---|
| 🟢 | **Foundation** | Explain how a Python test reaches an app on a phone; read capabilities and locators |
| 🟡 | **Practitioner** | Choose locators, gestures, and waits that do not flake; collect mobile evidence |
| 🔴 | **Senior** | Design sessions, synchronization, and evidence for a cross-platform suite that reuses the Unit 1 architecture |

### Lecture plan (120 min)

| Time | Part |
|---|---|
| 0–10 | Part 0 — From web to mobile; the sample app |
| 10–30 | Part 1 — Architecture |
| 30–45 | Part 2 — Capabilities and sessions |
| 45–70 | Part 3 — Locators |
| 70–85 | Part 4 — Gestures and device actions |
| 85–105 | Part 5 — Synchronization |
| 105–115 | Part 6 — Mobile evidence |
| 115–120 | Part 7 — Fitting mobile into our framework |

---

## Glossary

| Term | Meaning | Vietnamese |
|---|---|---|
| Native app | Built with the platform's own UI toolkit (Android views/Compose, iOS UIKit/SwiftUI) | Ứng dụng gốc |
| Hybrid app | A native shell showing web content in a WebView | Ứng dụng lai |
| Appium server | The Node.js program that receives test commands and routes them to a driver | Máy chủ Appium |
| Driver | The Appium plugin for one platform: UiAutomator2 (Android), XCUITest (iOS), … | Trình điều khiển |
| Capabilities | Key–value settings that describe the session you want (platform, device, app) | Khả năng / cấu hình phiên |
| Session | One connection from a test to one app on one device | Phiên |
| Emulator / simulator | A virtual Android device / a virtual iOS device on a Mac | Máy ảo |
| Accessibility id | An element's accessibility label (Android content description, iOS accessibility identifier) | Mã truy cập |
| Page source | The XML tree of the current screen | Mã nguồn màn hình |
| Gesture | Touch movement: tap, swipe, scroll, long press, pinch, drag | Cử chỉ |
| Implicit / explicit wait | A global "retry finding for N seconds" / a wait for one specific condition | Chờ ngầm / chờ tường minh |
| Idle state | The moment the app's UI stops changing; UiAutomator waits for it before acting | Trạng thái rảnh |
| Logcat | Android's system and app log | Nhật ký Android |
| Appium Inspector | A desktop tool to view an app's element tree and try locators | Công cụ soi phần tử |

---

## Part 0 — From web to mobile 🟢

### 0.1 What changes

| Topic | Web with Playwright (Unit 2) | Mobile with Appium (Unit 3) |
|---|---|---|
| Waiting | Automatic actionability waits | **None by default** — you design every wait (Part 5) |
| Starting a test | New browser context: milliseconds | New session: installs/launches the app and an automation server on the device — **much slower**; often reused (Part 2.4) |
| Isolation | Free (context per test) | Must be designed: reset the app, clear data, or reinstall |
| Locators | Accessibility tree of a web page | Accessibility tree of native UI (different per platform) |
| Interaction | Mouse/keyboard | Touch gestures, on-screen keyboard, system dialogs, back button |
| Network control | Built-in routes and mocks | **None for native apps** — use backend checks, test environments, or a proxy |
| Evidence | Trace, screenshot, video | Screenshot, page source XML, screen recording, device log, server log |
| Platforms | One engine per browser | Android **and** iOS, many OS versions and screen sizes |

### 0.2 Three kinds of mobile app

| Kind | Example | How Appium sees it |
|---|---|---|
| Native | A shopping app built in Kotlin or Swift | Native elements in the `NATIVE_APP` context |
| Hybrid | A native shell showing an HTML checkout | `NATIVE_APP` plus one or more `WEBVIEW_…` contexts; switch context to use web locators |
| Mobile web | The Shopify shop in a phone's Chrome | A browser session (Playwright's device emulation covers layout; real mobile browsers need Appium) |

### 0.3 The sample application

The syllabus requires a sample mobile application. This course uses **Sauce Labs My Demo App**:

| Fact | Value | Source |
|---|---|---|
| Android package | `com.saucelabs.mydemoapp.android` | `app/build.gradle` in `saucelabs/my-demo-app-android` |
| Minimum / target Android SDK | 21 / 31 | same file |
| Latest release | 2.3.0 (APK attached to the GitHub release) | the repository's Releases page |
| iOS version | Repository `saucelabs/my-demo-app-ios` | not inspected for this lecture |

Why this app: it is a **shopping app** — products, cart, checkout — like the Unit 1–2 shop, built **for** test automation practice, and available on both platforms. The Unit 1 design (feature files → `Store` port → adapters) therefore carries over: Day 11 adds a mobile adapter instead of starting again.

Screen names and accessibility ids of the app are **not** quoted in this lecture: they must be read from the installed app with Appium Inspector on Day 11. Example locators below are marked as illustrations.

---

## Part 1 — Architecture 🟢 → 🔴

### 1.1 🟢 Five hops from your test to the app

```
┌─────────────┐  W3C WebDriver   ┌───────────────┐       ┌────────────────────┐        ┌──────────────────────┐      ┌─────┐
│ Python test │ ── HTTP/JSON ──▶ │ Appium server │ ────▶ │ Driver             │ ─────▶ │ On-device automation │ ───▶ │ App │
│ (client)    │ ◀─────────────── │ (Node.js)     │ ◀──── │ UiAutomator2 (And.)│ ◀───── │ UiAutomator2 server  │ ◀─── │     │
└─────────────┘                  └───────────────┘       │ XCUITest (iOS)     │  adb / │ WebDriverAgent (iOS) │      └─────┘
                                                          └────────────────────┘  Xcode  └──────────────────────┘
```

| Hop | What it is | Installed with |
|---|---|---|
| Client | `Appium-Python-Client` (built on Selenium) | `pip install Appium-Python-Client` |
| Server | Appium 4 | `npm install -g appium` (needs Node `^22.22.2`, `^24.15`, or `>=26`) |
| Driver | One per platform, installed **separately** | `appium driver install uiautomator2` / `appium driver install xcuitest` |
| Platform tools | Android SDK + `adb`; for iOS, macOS with Xcode | Android Studio / Xcode |
| On-device server | Installed on the device by the driver at session start | automatic |

### 1.2 🟡 Watching the path in the server log

Starting Appium 4 and requesting a UiAutomator2 session on a machine **without** an Android SDK printed (trimmed):

```
[Appium] Welcome to Appium v4.0.0
[Appium] Attempting to find matching driver for automationName 'UIAutomator2' and platformName 'Android'
[Appium] The 'uiautomator2' driver was installed and matched caps.
[AppiumDriver] Appium v4.0.0 creating new AndroidUiautomator2Driver (v9.2.1) session
```

and the client received:

```
WebDriverException: Neither ANDROID_HOME nor ANDROID_SDK_ROOT environment variable was exported.
```

Each line is one hop: the server picked the driver **from the capabilities** (`automationName` + `platformName`), the driver started, and the driver failed at the next hop because it could not reach Android's tools. Reading the server log hop by hop is the first diagnostic skill of Unit 3.

### 1.3 🟡 Compared with Playwright

| | Playwright (Unit 2) | Appium (Unit 3) |
|---|---|---|
| Protocol | Private, between library and driver | W3C WebDriver (HTTP) — any language, any client |
| Server | Bundled driver process | Separate server, drivers as plugins |
| Target | Browsers it downloads itself | Real devices, emulators, simulators, device clouds |
| Speed of a new test | Context in milliseconds | Session start is heavy (app + on-device server) |

### 1.4 🔴 Where the test can run

| Target | Strength | Weakness |
|---|---|---|
| Android emulator / iOS simulator | Free, scriptable, resettable | Not real hardware (camera, sensors, performance) |
| Real device on your desk | Real behaviour | One at a time, manual upkeep |
| Device cloud (e.g. AWS Device Farm — LO7, Unit 4) | Many real devices, parallel | Cost, queue time, network latency |

### 1.5 🟡 Appium Inspector

A desktop app that opens a session through the same server and shows the screen, the **element tree**, each element's attributes, and lets you try a locator before writing code. It is the mobile version of Unit 1's accessibility snapshot. Day 11 starts with it.

> **Checkpoint 1.** The server log says "driver matched caps" but the session fails. Which hops are already proven to work, and where do you look next?

---

## Part 2 — Capabilities and sessions 🟢 → 🔴

### 2.1 🟢 Capabilities describe the session

W3C capabilities are a JSON object. Standard keys stand alone (`platformName`); Appium's keys carry the vendor prefix `appium:`. The Python client builds them through **options** classes:

```python
options = UiAutomator2Options()
options.app = "/apps/my-demo-app-2.3.0.apk"
options.no_reset = False
```

which becomes (checked with client 6.1.7):

```
{'automationName': 'UIAutomator2', 'platformName': 'Android', 'appium:app': '/apps/my-demo-app-2.3.0.apk', 'appium:noReset': False}
```

Note that the client sends `automationName` **without** the `appium:` prefix; Appium accepts both spellings. The table below uses the prefixed form you will see in documentation.

### 2.2 🟡 The capabilities you will use

| Capability | Android example | iOS example | Purpose |
|---|---|---|---|
| `platformName` | `Android` | `iOS` | Chooses the platform |
| `appium:automationName` | `UiAutomator2` | `XCUITest` | Chooses the driver |
| `appium:platformVersion` | `15` | `18.0` | OS version |
| `appium:deviceName` / `appium:udid` / `appium:avd` | emulator name, device id | simulator name, device id | Which device |
| `appium:app` | path or URL of an `.apk` | path or URL of an `.app`/`.ipa` | Install this build |
| `appium:appPackage` + `appium:appActivity` | `com.saucelabs.mydemoapp.android` + launch activity | — | Start an already-installed app |
| `appium:bundleId` | — | the app's bundle id | Start an installed iOS app |
| `appium:noReset` / `appium:fullReset` | `true` / `false` | same | How much state to keep between sessions |
| `appium:autoGrantPermissions` | `true` | — | Skip Android permission dialogs |
| `appium:language` / `appium:locale` | `en` / `GB` | same | Pin language like Unit 2 pinned `en-GB` |
| `appium:newCommandTimeout` | `120` | same | Seconds of client silence before the server ends the session |
| `appium:disableWindowAnimation` | `true` | — | Remove animations (Part 5) |

### 2.3 🔴 Capability design

- **One profile per target** (Android emulator, iOS simulator, cloud device), chosen by a command-line option — the same idea as `--store web|fake`.
- **Never hard-code device ids or cloud keys**; read them from the environment (Unit 2, Day 6).
- **Pin what affects results**: language, locale, OS version, app build.
- **Record the effective capabilities in every report** (Part 6): "it failed on Android 15 emulator with build 2.3.0" is half the diagnosis.

### 2.4 🔴 Sessions are expensive: the isolation trade-off

Unit 2 gave every test a fresh context almost for free. A mobile session installs or launches the app and the on-device server, so one session per test can dominate the run time. The options:

| Strategy | Isolation | Speed | Use when |
|---|---|---|---|
| New session per test, `fullReset` | Strongest | Slowest | Few tests, or flows that change device state |
| Session per test file/class, **reset app data between tests** (terminate, clear data, relaunch) | Good | Medium | The usual choice |
| One session for the whole run | Weak — Unit 2's anti-pattern | Fastest | Only for read-only smoke checks |

Whatever you choose, the Day 5 rule still holds: **each test must start from a known state**. On mobile, that state is created deliberately (reset, deep link, API setup), not received for free.

### 2.5 🟡 Parallel sessions

The UiAutomator2 driver documentation lists what must be **unique per parallel session**: `udid` (real device) or `avd` (emulator), `systemPort`, and — when recording video or using web views — `mjpegServerPort` and `chromedriverPort`. One Appium server can run several sessions at once (the documentation calls this preferable to one server per session).

---

## Part 3 — Locators 🟢 → 🔴

### 3.1 🟢 Strategies (UiAutomator2, from the driver documentation)

| Strategy | Python | Maps to (Android) | Driver's speed rating |
|---|---|---|---|
| `accessibility id` | `AppiumBy.ACCESSIBILITY_ID` | content description | ⭐⭐⭐⭐⭐ |
| `id` | `AppiumBy.ID` | resource id | ⭐⭐⭐⭐⭐ |
| `class name` | `AppiumBy.CLASS_NAME` | widget class | ⭐⭐⭐⭐⭐ |
| `-android uiautomator` | `AppiumBy.ANDROID_UIAUTOMATOR` | `UiSelector` expression | ⭐⭐⭐⭐ |
| `xpath` | `AppiumBy.XPATH` | the page-source XML | ⭐⭐⭐ |

iOS adds `-ios predicate string` (`AppiumBy.IOS_PREDICATE`) and `-ios class chain` (`AppiumBy.IOS_CLASS_CHAIN`); accessibility id maps to the accessibility identifier.

### 3.2 🟡 Priority, mapped to Unit 2

| Priority | Mobile | Web equivalent | Why |
|---|---|---|---|
| 1 | Accessibility id | `get_by_role(name=…)` / test id | Works on **both** platforms; also makes the app accessible |
| 2 | `id` (Android resource id) / iOS predicate on a stable attribute | `get_by_test_id` | Stable, fast, one platform |
| 3 | Class chain (iOS) | Scoped CSS | Structural, scoped |
| 4 | XPath | XPath | Slowest; breaks with layout changes |

```python
driver.find_element(AppiumBy.ACCESSIBILITY_ID, "<accessibility id>")  # illustration
```

### 3.3 🔴 Two warnings from the driver documentation

1. **`-android uiautomator` has an expiry date.** The UiAutomator2 driver's README warns that Google is deprecating and will remove `UiSelector`, `UiScrollable`, `UiObject`, and `UiCollection`, which "will render all `-android uiautomator`-based locators invalid". Do not build new suites on them — including the popular `UiScrollable().scrollIntoView(...)` trick. Scroll with gestures instead (Part 4).
2. **XPath reads the page source**, which is regenerated for each lookup: slow on big screens, and coupled to the layout.

### 3.4 🔴 There is no strict mode

Playwright refuses to act when a locator matches two elements. Appium's `find_element` simply returns the **first** match. A duplicated label (a hidden copy, a list item) is clicked silently. Senior screen objects protect themselves:

```python
matches = driver.find_elements(AppiumBy.ACCESSIBILITY_ID, label)
assert len(matches) == 1, f"{label!r} matched {len(matches)} elements"
```

### 3.5 🟡 Testability, again

The Unit 1 shop had unlabeled inputs and duplicate ids (Days 3 and 7). Mobile apps have the same problems: icon buttons without accessibility labels, ids generated at build time, identical rows. Ask developers for **accessibility labels on every interactive element** — it is both a testability and an accessibility requirement, and the cheapest fix for brittle locators.

---

## Part 4 — Gestures and device actions 🟡 → 🔴

### 4.1 🟡 Three levels of interaction

| Level | Use for | Example |
|---|---|---|
| Element actions | Tap, type, clear | `element.click()`, `element.send_keys("…")` |
| Driver gesture commands | Swipe, scroll, long press, drag, pinch, fling | `driver.execute_script("mobile: swipeGesture", {...})` |
| W3C Actions (touch pointer) | Anything custom: multi-finger, curves, precise timing | Selenium `ActionBuilder` with a touch `PointerInput` |

### 4.2 🟡 Gesture commands

| Gesture | Android (UiAutomator2 9.2.1) | iOS (XCUITest 13.1.1) |
|---|---|---|
| Tap | `mobile: clickGesture` | `mobile: tap` |
| Double tap | `mobile: doubleClickGesture` | `mobile: doubleTap` |
| Long press | `mobile: longClickGesture` | `mobile: touchAndHold` |
| Swipe | `mobile: swipeGesture` | `mobile: swipe` |
| Scroll | `mobile: scrollGesture` | `mobile: scroll` |
| Fling | `mobile: flingGesture` | — |
| Drag | `mobile: dragGesture` | `mobile: dragFromToForDuration` |
| Pinch | `mobile: pinchOpenGesture` / `mobile: pinchCloseGesture` | `mobile: pinch` |

```python
can_scroll_more = driver.execute_script(
    "mobile: scrollGesture",
    {"elementId": product_list.id, "direction": "down", "percent": 0.75},  # see the note below
)
```

From the driver source: `swipeGesture` and `scrollGesture` require `direction` and `percent`, and accept `elementId` **or** an area (`left`, `top`, `width`, `height`) plus `speed`. `scrollGesture` **returns whether more scrolling is possible** — the building block for "scroll until the element appears" without the deprecated `UiScrollable`.

> **A documentation conflict, kept as a lesson.** The driver's code comments describe `percent` as "0-100", while the Android UiAutomator API it forwards to takes a fraction (0.75 = 75 %). When two sources disagree, **measure on the device** *(confirm on Day 11)* and write the answer in your design notes.

### 4.3 🟡 Device actions you will need

| Need | Android (UiAutomator2) |
|---|---|
| Open a screen directly (like `page.goto`) | `mobile: deepLink` (iOS: `mobile: deepLink`) |
| Back button | `mobile: pressKey` with the Android back key code |
| App state | `mobile: queryAppState`, `mobile: activateApp`, `mobile: terminateApp`, `mobile: clearApp` |
| Keyboard | `driver.hide_keyboard()`, `mobile: isKeyboardShown` |
| Permissions | `mobile: changePermissions`, `mobile: getPermissions` |
| System alerts | `mobile: acceptAlert`, `mobile: dismissAlert` (iOS: `mobile: alert`) |
| Network on/off | `mobile: setConnectivity` / `mobile: getConnectivity` |

### 4.4 🔴 Gesture rules

- Scroll **inside a container element** (`elementId`), not by screen coordinates: coordinates break on a different screen size.
- Prefer driver gesture commands over hand-built W3C actions: they are maintained by the driver team and tuned for the platform.
- After any gesture that changes the screen, **wait for the evidence** (Part 5) — a swipe returns when the finger lifts, not when the list has settled.
- Deep links are the mobile equivalent of Unit 1's API setup: reach the screen under test directly instead of tapping through five screens.

---

## Part 5 — Synchronization 🟡 → 🔴

### 5.1 🟢 The biggest difference from Playwright

Playwright waited for actionability on every action. Appium **does not**: `find_element` searches **once**, and fails immediately if the element is not there yet. Every wait is your design.

### 5.2 🟡 Implicit vs explicit waits

| | Implicit wait | Explicit wait |
|---|---|---|
| Set with | `driver.implicitly_wait(5)` — global | `WebDriverWait(driver, 10).until(condition)` — per need |
| Waits for | An element to **exist** | **Any** condition: visible, clickable, text, count, your own function |
| Problem | Hides slowness everywhere; makes "element should be absent" checks wait the full time | More code — so put it in screen objects |

**Rule:** implicit wait **0**, explicit waits inside screen objects. Mixing both produces unpredictable total wait times.

```python
WebDriverWait(driver, 10).until(EC.visibility_of_element_located((AppiumBy.ACCESSIBILITY_ID, label)))
```

### 5.3 🔴 Waiting for the app to be idle

Before searching for an element, UiAutomator waits for the UI to become **idle** (the driver documents this as `waitForIdleTimeout`, a setting). Two consequences:

- An app with **continuous animation** (a spinner, a carousel) never becomes idle: every lookup waits the full idle timeout. Lower the setting for that screen (`driver.update_settings({"waitForIdleTimeout": 100})`) or disable animations (`appium:disableWindowAnimation`).
- Idle is not the same as **done**: a list can be idle and still empty because data is loading. Wait for **business evidence** (§5.4).

### 5.4 🔴 Waiting for evidence, the mobile way

Unit 2's rule — wait for the evidence of the action — still applies, but native apps offer no network interception. The evidence is on the screen or in the backend:

| After… | Wait for… |
|---|---|
| Tapping "Add to cart" | The cart badge to show the new count (custom condition on its text) |
| Opening a screen | Its unique, visible element (the screen object's "loaded" check — Unit 1's `wait_until_loaded`) |
| A gesture | The target element visible, or `scrollGesture` returning "no more scrolling" |
| A background operation | The backend state through an API, when the test environment allows it |
| Never | `time.sleep` — the Unit 1 architecture test still applies |

A custom condition is just a function:

```python
WebDriverWait(driver, 10).until(lambda d: cart_badge_count(d) == expected)
```

### 5.5 🟡 Timeouts that exist on mobile

| Timeout | Where | Meaning |
|---|---|---|
| Explicit wait | Your screen objects | How long one condition may take |
| `waitForIdleTimeout` | Driver setting | How long to wait for UI idle before each lookup |
| `newCommandTimeout` | Capability | Session ends after this many seconds without a command |
| Session start / app install | Driver capabilities | Slow devices may need more time — raise only with evidence |

---

## Part 6 — Mobile evidence 🟡 → 🔴

### 6.1 🟡 What to collect

| Evidence | How (Python client 6.1.7) | Answers |
|---|---|---|
| Screenshot | `driver.get_screenshot_as_file(path)` | What the user saw |
| Page source | `driver.page_source` (XML) | Which elements existed, with attributes — the mobile "DOM snapshot" |
| Screen recording | `driver.start_recording_screen()` / `stop_recording_screen()` (Base64 video) | Timing, animations, gestures |
| Device log | `driver.get_log("logcat")` (Android) | Crashes, exceptions, app warnings |
| Device information | `mobile: deviceInfo` | Model, OS, screen — for the report |
| Appium server log | The server's `--log` file | Which hop failed (Part 1.2) |
| Capabilities and versions | From the session | Reproducing the run |

### 6.2 🔴 Evidence on failure, at the business step

The Unit 1 framework saved a screenshot and a JSON file at the failing **business step**. The mobile adapter on Day 11 does the same: screenshot, page source, and a logcat excerpt per failing step, plus a recording per failing test. Recordings cost time and storage: keep them **on failure** only, as with Playwright traces.

### 6.3 Execution-evidence template (required material)

Copy and fill one per run on Day 11:

```markdown
# Mobile execution evidence — <run id>

| Field | Value |
|---|---|
| Date / time (UTC) | |
| App and build | My Demo App <version>, <apk/ipa file name> |
| Platform / OS version | Android <x> / iOS <x> |
| Device | <emulator/simulator name or model>, udid <masked> |
| Appium / driver / client versions | Appium 4.0.0 / UiAutomator2 9.2.1 / Python client 6.1.7 |
| Capabilities profile | <profile name>; effective capabilities attached (secrets removed) |
| Tests run / passed / failed / blocked | |

## Per test
| Test | Requirement | Result | Class (product / test / environment / framework) | Evidence files |
|---|---|---|---|---|

## Failures
For each failure: failing business step, screenshot, page source, logcat excerpt,
recording, server-log excerpt, diagnosis, and the finding written in Day 4 format.
```

---

## Part 7 — Fitting mobile into our framework 🔴

### 7.1 The Unit 1 design pays off

```
features/*.feature  (unchanged Gherkin)
        │
tests/steps/*.py    (unchanged steps)
        │
Store port ─────────┬── FakeStore      (in memory)
                    ├── WebStore       (Playwright, Unit 1–2)
                    └── MobileStore    (Appium, Day 11) ── screen objects (one locator map per platform)
```

Day 1 promised that declarative scenarios would run on mobile. On Day 11, a `--store mobile` option selects a `MobileStore` built from **screen objects** — page objects for app screens — with the same contract: open a product, add it, read the cart into the same `Cart` domain object.

### 7.2 What transfers and what does not

| Transfers unchanged | Must be rebuilt for mobile |
|---|---|
| Feature files, step definitions, domain model, traceability, tag rules, review tool | Screen objects (locators, gestures, waits) |
| Failure classes (product / test / environment / framework) | Session management and reset strategy |
| "Wait for evidence", "no sleep", evidence-per-step | Evidence collection (page source, logcat, recording) |
| Requirement registry | Which scenarios apply to the app (it is a different product — Day 11 maps them) |

### 7.3 Prerequisites for Day 11 (prepare before the lab)

| Item | Note |
|---|---|
| Android Studio with one emulator (or an Android phone with USB debugging) | iOS needs a Mac with Xcode |
| Node.js 22.22.2+ (or 24.15+) and Appium 4 with the UiAutomator2 driver | `appium driver install uiautomator2` |
| Appium Inspector | For reading the app's real locators |
| My Demo App APK 2.3.0 | From the GitHub release |
| Python packages | `Appium-Python-Client` in the course project |

---

## Your output: mobile test design notes (one page)

| Topic | Your decision and the reason |
|---|---|
| Target devices and OS versions (emulator, real, cloud) | |
| Capability profiles and where secrets come from | |
| Session strategy and how each test reaches a known state | |
| Locator priority; what you will ask developers to add | |
| Gesture approach (driver commands vs W3C actions); scrolling without `UiScrollable` | |
| Waiting rules (implicit 0; explicit waits in screen objects; idle settings) | |
| Evidence collected on failure | |
| Open question to confirm on Day 11 (e.g., the `percent` scale) | |

---

## Self-check (answers below — try first)

1. Name the five hops from a Python test to the app on Android.
2. How does the Appium server choose a driver?
3. Why are mobile sessions usually reused across several tests, and what must you then do between tests?
4. Which locator strategy works on both Android and iOS, and why is it also good for users?
5. Why should a new Android suite avoid `-android uiautomator` locators?
6. What happens in Appium when a locator matches two elements, and how do screen objects protect against it?
7. Why is "implicit wait 0, explicit waits in screen objects" the recommended rule?
8. An app shows a permanent loading animation and every lookup is slow. What is likely happening, and what do you change?
9. Which mobile evidence plays the role of Playwright's DOM snapshot?
10. What must change, and what stays the same, when the Unit 1 features run on the mobile app?

<details>
<summary><b>Answer guide</b></summary>

1. Python client → Appium server → driver (UiAutomator2) → on-device automation server (installed through `adb`) → app.
2. From the capabilities: `platformName` plus `appium:automationName` must match an installed driver (the log says "driver … matched caps").
3. Starting a session installs/launches the app and the on-device server, which is slow. Between tests you must restore a known state: terminate and relaunch, clear app data, or navigate by deep link to a clean starting point.
4. Accessibility id. It is the label screen readers announce, so adding it makes the app accessible as well as testable.
5. The driver documentation warns that Google is deprecating and will remove `UiSelector`/`UiScrollable`, which will make those locators invalid.
6. `find_element` returns the first match silently. Screen objects use `find_elements` and assert exactly one match where ambiguity is possible.
7. Implicit waits apply everywhere (hiding slowness and slowing "absent" checks) and combine unpredictably with explicit waits; explicit waits in screen objects wait for exactly the right condition.
8. UiAutomator waits for the UI to become idle before each lookup; a never-ending animation means it waits the full idle timeout every time. Lower `waitForIdleTimeout` for that screen and/or disable animations.
9. The page source (XML) at the failing step.
10. Stays: feature files, steps, domain model, traceability, failure classes, evidence policy. Changes: a `MobileStore` with screen objects, session and reset strategy, mobile evidence collection, and a mapping of which scenarios the app supports.
</details>

## Next: Day 10

Asynchronous-system testing concepts: WebSocket, queues, event correlation, polling, retries, and eventual consistency.

---

## Verification notes

| Check | Result |
|---|---|
| Appium | 4.0.0 installed; requires Node `^22.22.2 \|\| ^24.15.0 \|\| >=26.0.0`; server started and reported `ready` |
| UiAutomator2 driver | 9.2.1 installed with `appium driver install uiautomator2`; README and source read for capabilities, strategies, speed ratings, gestures, settings, parallel capabilities, and the UiSelector deprecation warning |
| Session request without Android SDK | Server matched the driver; client received the `ANDROID_HOME` error shown in §1.2 |
| Appium Python client | 6.1.7 (with Selenium 4.53.0): `AppiumBy` strategies, `UiAutomator2Options` / `XCUITestOptions` output, recording, `get_log`, `page_source`, `update_settings`, `hide_keyboard`, touch pointer input all present |
| XCUITest driver | 13.1.1 package inspected for iOS command names (§4.2) |
| My Demo App | Package id, SDK levels, and latest release read from GitHub |
| **Not run (no emulator)** | Any on-device behaviour: gestures, waits, idle timing, recordings, logcat, the app's screens and locators, the `percent` scale |
