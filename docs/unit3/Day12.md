# Unit 3 · Day 12 — Topic Revision (Mobile), then the Asynchronous-System Lab

| | |
|---|---|
| **Course** | Advanced Automation Test Engineering (ATEST03) — Fast Track |
| **Unit** | Unit 3 — Mobile and Asynchronous-System Testing |
| **Session A** | Topic Revision · Guides/Review · Virtual · **60 min** · **LO5** (mobile automation with Appium) |
| **Session B** | Asynchronous-system lab: verify events, retries, duplicates, ordering, timeout, and recovery behaviour · Assignment/Lab · Hybrid · **150 min** · **LO6** (Bloom **B4: Analyze**) |
| **Code** | `Unit3/day12-code/shop-bdd.zip` — **the whole Unit 3 project**: everything from Units 1–2, the Day 11 mobile code, and today's asynchronous-system code |
| **Output of the day** | Session A: quiz answers, an evidence-diagnosis drill, a peer review of your Day 11 code, and your device-run debrief. Session B: the fault-injection tests, a filled **async execution-evidence** record (Day 10, §7.3), and three findings in Day 4 format |

> **How this lab was checked.** Everything in Session B ran here for real: the sandbox (a real HTTP and WebSocket server in its own process), all 20 asynchronous tests (in parallel and serially, eight repeated runs), the fixed-build validation, and a fresh install from the zip. Every output quoted below was copied from those runs. Two limits:
> - The broker is the sandbox's own **in-memory** broker. It implements the delivery semantics Day 10 described (acknowledgements, visibility timeout, retries, dead-letter queue), but it is not Kafka, RabbitMQ, or SQS.
> - The mobile part of the project still has **not run on a device** (Day 11). Session A's debrief is where you bring in your own device results.

---

## How to use this day

| Badge | Level | After this level you can… |
|---|---|---|
| 🟢 | **Foundation** | Explore an asynchronous system by hand: send a command, follow its events, read the delivery journal |
| 🟡 | **Practitioner** | Write tests that wait for outcomes instead of time, filter by correlation id, inject one fault, and check the business effect |
| 🔴 | **Senior** | Analyse why a test passed. Check "exactly once" only after the system has gone quiet. Use invariants over a time window. Prove that each defect test fails only because of its defect |

---

# Session A — Topic Revision: Mobile Automation (LO5) · 60 min

| Time | Activity |
|---|---|
| 0–10 | A.1 One-page map: from Day 9's concepts to Day 11's code |
| 10–30 | A.2 Quiz (12 questions) |
| 30–45 | A.3 Evidence-diagnosis drill |
| 45–60 | A.4 Peer review of Day 11 code · A.5 Device-run debrief |

## A.1 One-page map

| Day 9 concept | Where it lives in the code (Day 11) | The rule to remember |
|---|---|---|
| Client → Appium server → driver → device | `framework/adapters/mobile/session.py` | One session per run; restart the app between tests |
| Capabilities | `capabilities.py` (`UiAutomator2Options`) | Pin what changes results (language, locale, animations); machine values come from options |
| Locators | At the bottom of each screen class (`# --- Locators ---`), checked by a contract test against the app's layouts | Accessibility id, then resource id; XPath once, scoped; strict `one()` |
| Gestures | `Screen.scroll_until` (`mobile: scrollGesture`) | Stop when the list cannot scroll any further, then report clearly |
| Synchronization | `framework/waiting.py` (`wait_until`), implicit wait 0 | Wait for **business evidence** (the cart badge), never for time |
| Evidence | `mobile/evidence.py`, `mobile_app` fixture | Screenshot, page source, logcat, device info, masked capabilities, recording — kept on failure |
| Fitting into the framework | `MobileStore` implements the Store port | The same Gherkin runs on web, mobile, and in-memory stores |
| Honest reporting | `EnvironmentBlockedError`, platform deselection | BLOCKED is not FAIL; deselected (NOT RUN) is not MANUAL |

## A.2 Quiz (answers below — try first)

1. Name the four hops from a Python test to a tap on the device.
2. Which **two** capabilities did the project pin because they change results, and why?
3. `find_element` returns the first of two matches. What does the framework do instead, and why?
4. Why is the implicit wait set to `0`?
5. After *Add To Cart*, what does the test wait for, and why not for the button to be clickable again?
6. `scrollGesture` returns `False`. What does `scroll_until` conclude?
7. A run without an Appium server: what status do the tests get, and how many session attempts reach the server?
8. Why was the mobile catalogue checked offline in `--store fake` before any device existed? Which bug did that find?
9. Why does the wrong-password test carry `raises=AssertionError`?
10. In a `--store mobile` run, the web-only requirements show **NOT RUN**. Why not **MANUAL**?
11. Which locator problems can the locator contract test catch, and which can it not?
12. What would change, and what would stay, if you added iOS?

<details>
<summary><b>Answer guide</b></summary>

1. Python client → (W3C WebDriver over HTTP) → Appium server → UiAutomator2 driver → the on-device UiAutomator2 server → the app.
2. `language`/`locale` (texts and the `$` format) and `disableWindowAnimation` (timing). Also accepted: `autoGrantPermissions`, so no pop-ups appear mid-test.
3. `Screen.one()` counts the matches and raises unless there is exactly one: Appium has no strict mode, and "the first match" silently taps the wrong element.
4. Implicit waits apply to every lookup and combine unpredictably with explicit waits. A strict "zero matches" check would also wait the full implicit time.
5. The header badge showing the new count: that is the business evidence that the add finished. A clickable button only proves that the UI is ready again.
6. The list is at its end: it returns whether the item is visible now, and the caller raises "not found in the catalogue".
7. BLOCKED, with the reason "no Appium server at …". One attempt: the session error is cached for the run.
8. To prove the Gherkin, the steps, and the catalogue facts without a device. It found the hidden assumption `Money.zero()` = GBP (the error "cannot combine GBP and USD").
9. So that only a failed check counts as the known defect. Without it, an environment block inside the test showed up as "xfailed".
10. Skipped tests count as MANUAL ("checked by hand"), which would be false. Deselected tests are simply not part of this run.
11. It can catch: typos, renamed ids, and accessibility ids that are not unique within a layout. It cannot catch: elements that are hidden, off-screen, not yet rendered, or behave differently. Those need a device.
12. Changes: `XCUITestOptions`, an iOS locator map, choosing the platform in the screen objects. Stays: features, steps, the port, the domain model, waits, the evidence policy, the matrix.
</details>

## A.3 Evidence-diagnosis drill

For each excerpt (these are example messages in the framework's real formats), decide:
1. the **class** — product, test, environment, or framework;
2. the **next step**.

| # | Excerpt |
|---|---|
| 1 | `EnvironmentBlockedError: mobile environment not ready: Neither ANDROID_HOME nor ANDROID_SDK_ROOT environment variable was exported.` |
| 2 | `AssertionError: 'cartTV' (menu_header_layout) matched 0 elements`, and `page_source.xml` shows `nameET` and `passwordET` |
| 3 | `TimeoutError: condition not met within 15.0s; last value: 1` after `add_to_cart(2)`; `recording.mp4` shows a single tap on *Add To Cart* and the quantity selector still at 1 |
| 4 | `CartInconsistencyError: cart screen disagrees with itself: total $ 29.99 vs sum of lines $ 59.98` |
| 5 | `[XPASS(strict)] App behaviour read in its source …` on `test_wrong_password_is_rejected` |

<details>
<summary><b>Answer guide</b></summary>

1. **Environment.** Export `ANDROID_HOME` in the terminal that starts Appium, then restart Appium. It is not a defect, and no ticket is needed.
2. **Test (or flow).** The app is on the login screen, so the test is not where it thinks it is: either a login is required at this point or an earlier step failed. Fix the navigation in the screen object or the test, not the locator.
3. **Test, probably.** `set_quantity` did not reach 2 before the tap. Check that `PLUS` really increments on this device, and check the quantity text format. If the "+" tap registers but the number does not change, it is a product defect candidate; watch the video frame by frame.
4. **Product** defect candidate: the screen contradicts itself. Keep the evidence folder, confirm manually, and write it up in Day 4 format.
5. **Product behaviour changed**, which is good news. Confirm that a wrong password is now rejected, then remove the xfail and update the README findings. The tripwire did its job.
</details>

## A.4 Peer review of Day 11 code — checklist

Swap projects with a partner. For each ✘, write a finding in Day 4 format.

| # | Check | ✔/✘ |
|---|---|---|
| 1 | No `find_element(s)` outside `framework/adapters/mobile/screens/` (architecture test green) | |
| 2 | Every new locator names its layout and passes the contract test | |
| 3 | No `sleep`; every wait is for a condition, with a deadline and the last value in the error | |
| 4 | Every action that changes state waits for its business evidence (badge, screen, text) | |
| 5 | Expected values come from the catalogue or a calculation, never from the screen under test | |
| 6 | Each test starts from a known state (app restart) and needs no other test | |
| 7 | Environment errors give BLOCKED with a reason; app errors are never classified as environment errors | |
| 8 | Evidence folder complete on failure; capabilities masked | |
| 9 | `@covers` on every workflow test; the matrix shows the right status | |
| 10 | xfails are strict and `raises=AssertionError`, with a reason that names the finding | |

## A.5 Device-run debrief

Bring your Day 11 §8.2 table. For each row, say what you saw and what you changed:

| # | Check from Day 11 | What you saw | Change made (file) |
|---|---|---|---|
| 1 | `scrollGesture` percent `0.75` scrolls the catalogue | | |
| 2 | An app restart empties the cart and logs out | | |
| 3 | Empty-cart badge: hidden or empty text | | |
| 4 | The cart row XPath finds one row per line | | |
| 5 | Price formats `$ 29.99` / `$5.99` / `$ 65.97` | | |
| 6 | Wrong password logs in | | |
| 7 | logcat and the recording work | | |

> **Two numbers changed in today's code; this is expected, not a regression.**
> - A `--store mobile` run now deselects **74** tests, not 54: the 20 new asynchronous tests run only with `--store fake`.
> - The matrix now has a **KNOWN DEFECT** status (§B7.4). On a device, the wrong-password tripwire makes REQ-08 show KNOWN DEFECT instead of being hidden among the passes.

---

# Session B — Asynchronous-System Lab (LO6) · 150 min

## Lab plan

| Time | Part |
|---|---|
| 0–15 | B0 — Setup and the system under test |
| 15–30 | B1 — Reconnaissance: explore the system by hand |
| 30–50 | B2 — Test architecture: flows, correlation, push and pull |
| 50–75 | B3 — Exactly once: duplicates, lost acks, resubmits, **timeouts** |
| 75–90 | B4 — Ordering and invariants |
| 90–105 | B5 — Retries, the dead-letter queue, poison messages, redrive |
| 105–120 | B6 — Recovery: reconnect and worker outage |
| 120–140 | B7 — Evidence, known defects, and proving the tests themselves |
| 140–150 | B8 — Deliverables |

What the syllabus asks for, and where each item is covered:

| Syllabus | Tests (`tests/events/`, `features/order_events.feature`) |
|---|---|
| **Events** | Every test follows the pushed status events; the journal lists every delivery |
| **Retries** | `test_transient_gateway_failure_is_retried_with_backoff`, `test_failing_message_is_dead_lettered_then_redriven` |
| **Duplicates** | `test_duplicate_payment_message_charges_once`, `test_lost_acknowledgement_does_not_charge_twice`, `test_resubmitted_order_creates_one_order`, `test_repeated_updates_are_shown_once` |
| **Ordering** | `test_late_packed_update_does_not_undo_shipped` (D-12-02), `test_a_disturbed_order_does_not_disturb_another` |
| **Timeout** | `test_payment_retried_after_gateway_timeout_charges_once` (D-12-01) |
| **Recovery** | `test_status_stream_catches_up_after_a_reconnect` (D-12-03), `test_order_completes_once_after_a_worker_outage`, the redrive test |

## Glossary (new today)

| Term | Meaning | Vietnamese |
|---|---|---|
| Sandbox | A small, controllable copy of a system, made for testing | Môi trường thử nghiệm cô lập |
| Journal | The sandbox's record of every delivery and its result | Nhật ký giao nhận |
| Visibility timeout | How long the broker waits for an ack before delivering again | Thời gian chờ xác nhận |
| Redrive | Sending dead-lettered messages back for processing | Đưa lại thư lỗi vào xử lý |
| Quiescence | The system has gone quiet: no new activity for a set period | Trạng thái lắng |
| Oracle validation | Proving that a test fails for the right reason and passes when the defect is fixed | Kiểm chứng phép thử |

---

## B0 — Setup and the system under test 🟢

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

Expected result: `236 passed, 2 skipped, 5 xfailed`. The 5 xfails are the three known defects below: two are detected by both a plain test and a BDD scenario. Two new dependencies were added: `aiohttp` 3.14.5, which runs the sandbox's server, and `websockets` 17.4, which the tests use as a client. Using a different library on each side means that the protocol is exercised by two independent implementations.

### The system: an order-fulfilment back end (`sandbox/`)

```
POST /orders ──202 Accepted──▶ test
     │
     └─▶ OrderPlaced ─▶ [payments] ─▶ payment gateway ─▶ OrderPaid ─▶ [fulfilment] ─▶ OrderPacked ─▶ OrderShipped
                                                                                  │
every event ─▶ [projector] ─▶ read model  GET /orders/{id}                         │
                         └──▶ WebSocket frames  /ws?correlation_id=…&since=…  ◀───┘
```

| Property | Value | From Day 10 |
|---|---|---|
| Delivery | At-least-once: ack after the handler; redelivery after a **0.6 s** visibility timeout | §1.3 |
| Retries | Transient errors: backoff **0.2 s, 0.4 s**, **3** attempts, then the DLQ. Permanent errors (malformed): DLQ at once | §4.2 |
| Ordering | Each subscription processes its messages one at a time; retries and held messages can still reorder them | §5.1 |
| Consistency target | Every status change visible within **2 s** (requirement REQ-13) | §5.4 |
| Faults | `POST /admin/faults`, **scoped to one correlation id** | §6.3 |

Four new requirements were added to `requirements.toml`. The coverage gate and the tag rules apply to them like to every other requirement:

| Id | Risk | Requirement |
|---|---|---|
| REQ-10 | high | Each order is charged and processed exactly once |
| REQ-11 | high | Order status never goes backwards |
| REQ-12 | medium | Failing messages are retried, then dead-lettered |
| REQ-13 | medium | Status visible within 2 s, also after reconnect |

> **Why a sandbox in the repository?** The syllabus asks for a "WebSocket/message-queue sandbox". It lives in `sandbox/` and is the **system under test**, not test code. An architecture test forbids `framework/` and `tests/` from importing it: the tests may only reach it over HTTP and WebSocket, exactly as they would reach a real service.

---

## B1 — Reconnaissance: explore the system by hand 🟢 → 🟡

Start the sandbox in one terminal:

```bash
python -m sandbox --port 8765 --build release
```

In a second terminal, place an order with a fault: the payment gateway answers after 0.8 s, which is later than the worker's 0.5 s timeout.

```bash
curl -s -X POST localhost:8765/admin/faults -H 'Content-Type: application/json' -d '{"kind":"gateway_slow","correlation_id":"T-1","seconds":0.8}'
```

```bash
curl -s -X POST localhost:8765/orders -H 'Content-Type: application/json' -d '{"correlation_id":"T-1","idempotency_key":"k-1","items":[{"sku":"A","quantity":2,"unit_price":"29.99"}]}'
```

```bash
curl -s "localhost:8765/deliveries?correlation_id=T-1"
```

```bash
curl -s "localhost:8765/payments?correlation_id=T-1"
```

What a run like this recorded (`deliveries.txt` and `payments.json` from the evidence folder, real output):

```
  0.034s projector  OrderPlaced  seq 1 #1 first                -> applied
  0.535s payments   OrderPlaced  seq 1 #1 first                -> failed (payment gateway timeout after 0.5s; retry in 0.2s)
  0.756s payments   OrderPlaced  seq 1 #2 retry                -> applied
  0.756s projector  OrderPaid    seq 2 #1 first                -> applied
  0.807s projector  OrderPacked  seq 3 #1 first                -> applied
  0.858s fulfilment OrderPaid    seq 2 #1 first                -> applied
  0.858s projector  OrderShipped seq 4 #1 first                -> applied
```

```
"idempotency_key": "pay-O-00001-9c2602", "amount": "59.98", "at": 0.755
"idempotency_key": "pay-O-00001-940fd9", "amount": "59.98", "at": 0.835
```

**Analyse it (Day 10, §7.2).** The order reached `shipped` and every delivery reads "applied", yet the customer was charged **twice**:
- The first attempt timed out at 0.535 s, but the gateway's call **continued** and charged at 0.835 s: the "late answer".
- The retry charged again at 0.755 s with a **different idempotency key**, so the gateway could not recognise it as a repeat.

This is defect **D-12-01**. Note what found it: the status looked fine, and only the **business effect** (the charges) showed the defect.

> **Your turn (🟢).** Try `{"kind":"duplicate","correlation_id":"T-2","subscription":"payments","event_type":"OrderPlaced"}` with a new order, then read the journal. Which line shows that the copy was recognised? Try a list endpoint without `correlation_id`: what does it answer, and why is that a good design for a shared test environment?

---

## B2 — Test architecture 🟡 → 🔴

### B2.1 Layers

```
features/order_events.feature ── tests/steps/order_event_steps.py ─┐
tests/events/*.py ──────────────────────────────────────────────────┤
                                                                     ▼
                         framework/events/flow.py   OrderFlow (one business flow)
                           ├── client.py            HTTP (urllib, no proxy), every read filtered by correlation id
                           ├── stream.py            WebSocket (websockets 17), background reader + condition variable
                           ├── oracles.py           backwards, repeated, redelivered, gaps — pure, unit-tested
                           ├── findings.py          known defects and the builds they are in
                           └── evidence.py          per-flow files + the run's evidence record
                         framework/plugins/events.py  one sandbox process per xdist worker, flow fixtures
                         framework/waiting.py         wait_until · holds_for · wait_until_stable
                                                                     │ HTTP + WebSocket only
                                                                     ▼
                                                         sandbox/  (system under test)
```

Two architecture tests guard these layers:
- `test_the_sandbox_is_a_black_box`: nothing in `framework/` or `tests/` imports `sandbox`.
- `test_events_tests_use_the_flow_not_the_wire`: tests and steps never import `urllib`, `websockets`, or `aiohttp`. They talk to `OrderFlow` only.

### B2.2 One flow, one correlation id, subscribed before acting

The `flow` fixture creates an `OrderFlow` with a unique correlation id. Its format is `T-<run>-<worker>-<test>-<hash>`, for example `T-e3684d-master-test-duplicate-payment-message-charges-o-5cc4`. The fixture also **subscribes to the live status before the test does anything** (push, not pull: Day 10, §3.4):

```python
    def follow(self) -> None:
        """Subscribe to the live status before anything happens (push, not pull)."""
        self.stream.connect()

    def inject(self, fault: Fault) -> None:
        self.client.inject(self.correlation_id, fault)
        self.faults.append(fault)

    def place(self, items: Sequence[Item] = DEFAULT_ITEMS, idempotency_key: str | None = None) -> str:
        key = idempotency_key or f"{self.correlation_id}-order"
        self.placed_at = time.monotonic()
        self.order_id, _ = self.client.place_order(self.correlation_id, items, key)
        return self.order_id
```

Faults are scoped to the correlation id. Each pytest-xdist worker starts its **own** sandbox process on a free port (`--port 0`, which prints `SANDBOX READY http://…`). Together, these two facts make parallel runs safe.

### B2.3 Three ways to wait — each for a different question

| Question | Helper | Example |
|---|---|---|
| "Has it happened yet?" (**push**) | `StatusStream.wait_for_status` — a condition variable, no polling interval | The customer sees `shipped` |
| "Has it happened yet?" (**pull**) | `wait_until(read, done, timeout)` (Day 10) | The read model shows `placed`; the DLQ has 1 entry |
| "Does it **stay** true?" (invariant over a window) | `holds_for(read, condition, duration)` | No second charge while the late answer arrives |
| "Has it **stopped** happening?" (quiescence) | `wait_until_stable(read, quiet, timeout)` | Only then judge "exactly once" (§B7.3) |

Every timeout comes from the system's published numbers (`GET /config`), never from a guess. Examples: `consistency_target` (2 s), `retry_budget` (0.2 + 0.4 + 3 × 0.5 = 2.1 s), and `quiet_period` (0.6 + 0.4 = 1.0 s).

---

## B3 — Exactly once 🟡 → 🔴 (REQ-10)

### B3.1 Duplicate delivery and a lost acknowledgement

```python
@covers("REQ-10")
def test_lost_acknowledgement_does_not_charge_twice(flow: OrderFlow) -> None:
    """Ack lost after a successful payment: redelivered after the visibility timeout; still one charge."""
    flow.inject(Fault.lose_ack("payments", "OrderPlaced"))
    flow.place()
    flow.wait_for_status("shipped")

    first, again = flow.wait_for_deliveries("payments", "OrderPlaced", count=2)
    assert (first.result, first.detail) == ("applied", "acknowledgement lost"), first.describe()
    assert (again.reason, again.result) == ("redelivery (no ack)", "ignored: duplicate"), again.describe()
    assert again.at - first.at >= flow.info.visibility_timeout * 0.9, (
        "redelivered before the visibility timeout"
    )
    assert len(flow.charges()) == 1, flow.charges()
```

The test reads like Day 10's patterns:
- It injects **one** fault, on its own flow.
- It waits for the **evidence** that the fault played out (two deliveries), not for a time.
- It checks the **business effect**: one charge.
- It checks the **mechanism** too: the redelivery came after the visibility timeout, and the copy was ignored.

`test_resubmitted_order_creates_one_order` covers the same risk one layer up. The client's HTTP request is repeated, for example after a lost response, and the idempotency key on `POST /orders` must prevent a second order.

### B3.2 🔴 The timeout test, and D-12-01

```python
@covers("REQ-10")
@pytest.mark.known_defect("D-12-01")
def test_payment_retried_after_gateway_timeout_charges_once(flow: OrderFlow) -> None:
    """Gateway answers after the worker gave up and retried: the late answer must not add a charge."""
    late = flow.info.gateway_timeout + 0.3
    flow.inject(Fault.gateway_slow(seconds=late))
    flow.place()
    flow.wait_for_status("shipped", timeout=flow.info.consistency_target + flow.info.retry_budget)

    payments = flow.deliveries("payments", "OrderPlaced")
    assert [d.result for d in payments] == ["failed", "applied"], [d.describe() for d in payments]
    assert "timeout" in payments[0].detail
    # The first call is still running inside the gateway; watch until its answer has surely arrived.
    charges = holds_for(flow.charges, lambda c: len(c) <= 1, duration=late)
    assert len(charges) == 1, charges
```

Why `holds_for` and not a plain check after `shipped`? When `shipped` arrives (~0.86 s), the late first charge may not have landed yet (0.835 s here, but it depends on timing). A check at that moment could pass by luck. `holds_for` watches the invariant "at most one charge" for the full window in which the late answer can arrive, and fails at the first violation.

The cause, in the sandbox's payments worker (read **after** the test found the defect, as a developer would):

```python
        key = f"pay-{event.order_id}"
        if self.config.has("per-attempt-payment-key"):
            key = f"{key}-{uuid.uuid4().hex[:6]}"
```

A new key per attempt makes every retry look like a new payment. The fix is one stable key per order (`pay-O-00001`), which is exactly what the `fixed` build does.

| Field (Day 4 format) | D-12-01 |
|---|---|
| Title | A payment retried after a gateway timeout charges the customer twice |
| Severity | **Critical**: money taken twice; customer harm, refunds, chargebacks |
| Steps | Gateway answers after 0.8 s (worker timeout 0.5 s) → place an order |
| Expected | One charge (REQ-10) |
| Actual | Two charges with different idempotency keys (`pay-O-00001-9c2602`, `pay-O-00001-940fd9`) |
| Evidence | `reports/events/test_payment_retried_after_gateway_timeout_charges_once/` (`deliveries.txt`, `payments.json`, `sandbox_log.txt`) |
| Recommendation | One idempotency key per order, reused on every attempt; a gateway that honours it |

---

## B4 — Ordering and invariants 🟡 → 🔴 (REQ-11)

```python
@covers("REQ-11")
@pytest.mark.known_defect("D-12-02")
def test_late_packed_update_does_not_undo_shipped(flow: OrderFlow) -> None:
    """'packed' reaches the read model after 'shipped': what the customer sees never goes backwards."""
    flow.inject(Fault.deliver_after("projector", "OrderPacked", after_type="OrderShipped"))
    flow.place()
    flow.wait_for_status("shipped")
    flow.wait_for_deliveries("projector", "OrderPacked", 1, where=lambda d: d.reason.startswith("released"))

    seen = flow.statuses()
    assert oracles.backwards(seen) == [], f"the customer saw {seen}"
    view = flow.view()
    assert view is not None
    assert view.status == "shipped", view
    assert oracles.backwards(view.history) == [], view.history
```

The journal of the failing run (real output):

```
  0.741s projector  OrderPacked  seq 3 #1 first                -> held (until OrderShipped is delivered)
  0.791s projector  OrderShipped seq 4 #1 first                -> applied
  0.791s projector  OrderPacked  seq 3 #1 released after OrderShipped -> applied
```

The read model applied sequence 3 **after** sequence 4, so the customer saw `shipped → packed`. That is the pattern of row 7 in Day 10's dataset, reproduced on purpose. With the fix, the same delivery is recorded as `ignored: stale (sequence 3 < version 4)`. Note also that the test waits for the **released** delivery before judging the final state: without that wait, it could pass before the late message had even arrived.

Two protected properties (they pass in both builds):
- **Repeated updates:** every event is delivered twice to the projector; each status is shown once, in order.
- **Isolation:** two customers at once, faults on one of them only. Each sees only its own, complete, ordered statuses, and the calm order has no repeat deliveries at all.

> **Your turn (🟡 → 🔴).** Write `test_late_paid_does_not_undo_packed`: hold `OrderPaid` at the projector until `OrderPacked`. First predict what the customer will see in the `release` build, then run the test. Is it the same defect or a new one? How do you decide?

---

## B5 — Retries, DLQ, poison messages, redrive 🟡 → 🔴 (REQ-12)

| Test | Fault | Oracle (real result) |
|---|---|---|
| `test_transient_gateway_failure_is_retried_with_backoff` | gateway 503 ×2 | Deliveries `first/failed`, `retry/failed`, `retry/applied`; gaps ≥ 0.2 s and ≥ 0.4 s (a lower bound only, never "exactly"); one charge |
| `test_failing_message_is_dead_lettered_then_redriven` | gateway 503 ×3 | DLQ entry with `attempts == 3`; **no** charge; the read model **stays** `placed` (`holds_for`); after the outage, a redrive leads to `shipped` and exactly one charge, and the DLQ is empty |
| `test_malformed_message_is_parked_at_once_and_blocks_nothing` | another producer publishes an `OrderPlaced` with `items: []` | DLQ after **1** attempt (permanent error: no pointless retries; Day 10 §7.2 answer 5); the next customer's order still completes |

Why a **lower** bound on the backoff gaps? On a loaded CI machine, delays only grow. An upper bound ("exactly 0.2 s") makes the test flaky without telling you anything about the product. The upper bound that matters is the **business** one: the whole flow must finish within `consistency_target + retry_budget`.

---

## B6 — Recovery 🔴 (REQ-13)

### B6.1 Reconnect, and D-12-03

```python
@covers("REQ-13")
@pytest.mark.known_defect("D-12-03")
def test_status_stream_catches_up_after_a_reconnect(flow: OrderFlow) -> None:
    """Connection lost after 'paid'; the updates sent meanwhile arrive after reconnecting, none missing."""
    flow.inject(Fault.drop_connection(after_status="paid"))
    flow.place()
    flow.stream.wait_disconnected(timeout=flow.info.consistency_target)
    flow.wait_for_view_status("shipped")  # the system moved on while the customer was offline

    reconnected_at = time.monotonic()
    flow.stream.reconnect()
    flow.wait_for_status("shipped", measured_from=reconnected_at)
    assert flow.statuses() == ALL_STATUSES
```

The stream reconnects with `since=<last frame received>` (here 2). The `release` build replays from `since + 2`, so the customer gets `placed, paid, shipped` and never sees `packed`. The test is deterministic because it waits for the **read model** to reach `shipped` before reconnecting, so the gap always contains two missed updates.

### B6.2 Worker outage

`test_order_completes_once_after_a_worker_outage` stops the fulfilment worker, places an order, and checks two things:
1. The order reaches `paid` and **stays** there for 0.5 s (`holds_for`): no progress, and no loss.
2. After the restart, `shipped` arrives **once**: fulfilment applied `OrderPaid` exactly once, and there is exactly one charge.

The time to `shipped` is measured from the restart (about 0.1 s in the runs here).

> This test stops a worker for the **whole** sandbox. That is safe only because every pytest worker has its own sandbox. The docstring says so; with a shared `--sandbox-url`, run such tests serially.

---

## B7 — Evidence, known defects, and proving the tests 🔴

### B7.1 The execution-evidence record — written on every run

`reports/events/evidence.md` follows Day 10's template (§7.3), with one row per test, passed or not. An excerpt from a real run:

```
| Test | Correlation id | Fault | Oracle | Result | Measured convergence (s) | Attempts seen | Duplicates seen | Charges |
| test_exactly_once::test_duplicate_payment_message_charges_once | T-e3684d-master-test-duplicate-payment-message-charges-o-5cc4 | duplicate OrderPlaced -> payments | Payment message delivered twice: one charge; the copy is recorded as ignored. | PASS | 0.124 | 2 | 1 | 1 |
| test_exactly_once::test_payment_retried_after_gateway_timeout_charges_once | T-e3684d-master-test-payment-retried-after-gateway-timeo-a32c | gateway_slow 0.8s | Gateway answers after the worker gave up and retried: the late answer must not add a charge. | XFAIL D-12-01 | 0.826 | 2 | 0 | 2 |
| test_failures::test_transient_gateway_failure_is_retried_with_backoff | T-e3684d-master-test-transient-gateway-failure-is-retrie-20dd | gateway_fail x2 | Gateway fails twice, then works: 3 attempts, growing gaps, one charge. | PASS | 0.725 | 3 | 0 | 1 |
```

Failed and known-defect flows also get a folder `reports/events/<test>/` containing `deliveries.txt`, `deliveries.json`, `events.json`, `frames.json`, `order.json`, `payments.json`, `dlq.json`, `faults.json`, and `sandbox_log.txt` (only the log lines with this flow's correlation id).

### B7.2 Known defects: marked, strict, and limited

```python
            if finding is not None:
                item.add_marker(
                    pytest.mark.xfail(
                        strict=True,
                        raises=AssertionError,  # only the documented failure counts; anything else surfaces
                        reason=f"{finding.id} ({finding.severity}): {finding.title} [build {build}]",
                    )
                )
```

How the mechanism works:
- A test declares `@pytest.mark.known_defect("D-12-01")`; a BDD scenario uses the tag `@defect-D-12-02`.
- The register (`framework/events/findings.py`) records the builds each defect is present in, and the xfail applies only to those builds.
- `raises=AssertionError` comes from the Day 11 lesson: a timeout or an unreachable sandbox inside a known-defect test must surface as an error, never as "expected".
- Unit tests check that every mark is registered, that every finding is detected by at least one test, and that each finding names a test that exists.

**The tripwire, checked.** If a defect disappears while the register still lists it, the test XPASSes and the run fails. This was checked by temporarily listing D-12-01 as present in the `fixed` build:

```
[XPASS(strict)] D-12-01 (Critical): A payment retried after a gateway timeout charges the customer twice [build fixed]
REQ-10  high    Each order is charged and processed exactly on    2    3    1    0    0    0  FAIL
1 failed, 3 passed in 2.98s
```

### B7.3 🔴 Oracle validation: prove each defect test fails only because of its defect

A test that fails against the defective build proves little on its own; it might fail for another reason. So the same 20 tests also run against the **fixed** build, where they must all pass:

```bash
pytest --store fake tests/events tests/test_order_events.py -n auto --sandbox-build fixed
```

```
REQ-10  high    Each order is charged and processed exactly on    2   12    0    0    0    0  PASS
REQ-11  high    Order status never goes backwards                 1    4    0    0    0    0  PASS
REQ-12  medium  Failing messages are retried, then dead-letter    1    4    0    0    0    0  PASS
REQ-13  medium  Status visible within 2 s, also after reconnec    2    5    0    0    0    0  PASS
20 passed in 3.51s
```

Each defect test therefore fails with the defect and passes without it, and nothing else differs between the two builds. CI runs this validation as a separate step after the main gate.

> 🔴 **Lesson: a pass that proved nothing — found by reading the evidence record.** In the first version of this lab, the BDD scenario "lost acknowledgement" passed, but its evidence row said **Attempts seen 1, Duplicates seen 0**. The fault had **not played out yet**: the redelivery comes 0.6 s after the lost ack, and the step "they were charged exactly once" had already checked at about 0.12 s. The test was green and would have stayed green even if redelivery charged twice. The fix: judge "exactly once" only after the flow has **gone quiet** for longer than any pending redelivery or retry could take.
>
> ```python
> def charged_once(flow: OrderFlow) -> None:
>     flow.settle()  # judge "once" only after every redelivery and retry could have happened
>     charges = flow.charges()
>     assert len(charges) == 1, f"{len(charges)} charges: {charges}"
> ```
>
> After the fix, the same row reads **Attempts seen 2, Duplicates seen 1, Charges 1**. The rule: **for every fault test, check in the evidence that the fault actually happened.** A fault that never fired is a test that tested nothing.

### B7.4 🔴 Lesson: an expected failure is not "manual"

In the requirement matrix, a pytest xfail report has the outcome "skipped", so known defects were first counted in the **Man** (manual) column, and REQ-10 showed **PASS**. That hid a Critical defect behind a green status. The matrix now has its own column and status:

```
Req     Risk    Title                                          Decl Pass Fail Dfct Blck  Man  Status
REQ-10  high    Each order is charged and processed exactly on    2   11    0    1    0    0  KNOWN DEFECT
REQ-11  high    Order status never goes backwards                 1    2    0    2    0    0  KNOWN DEFECT
REQ-12  medium  Failing messages are retried, then dead-letter    1    4    0    0    0    0  PASS
REQ-13  medium  Status visible within 2 s, also after reconnec    2    3    0    2    0    0  KNOWN DEFECT
```

The status precedence is FAIL > KNOWN DEFECT > BLOCKED > PASS > MANUAL > NOT RUN; the worst outcome decides. The change applies to the whole project: the web xfails from Unit 2 and the mobile wrong-password tripwire are now also reported as KNOWN DEFECT.

---

## B8 — Deliverables (checked at the start of Unit 4)

- [ ] `pytest --store fake -n auto --fail-on-uncovered`: `236 passed, 2 skipped, 5 xfailed` (plus your own tests)
- [ ] The same events tests with `--sandbox-build fixed`: all pass
- [ ] `ruff check .`, `ruff format --check .`, `mypy`, `python -m framework.review --strict`: all clean
- [ ] B1 exploration notes: your journal of one hand-made fault, analysed in Day 10's style
- [ ] Your "Your turn" test (§B4), with its prediction written **before** the run
- [ ] **Your own async execution-evidence record**: `reports/events/evidence.md` from your run, plus, for each XFAIL row, a two-line diagnosis written from its evidence folder only
- [ ] Findings D-12-01, D-12-02, and D-12-03 in Day 4 format (D-12-01 is done above; write the other two yourself)
- [ ] For every fault test you wrote: evidence that the fault fired (attempts or duplicates seen > the baseline)
- [ ] Your async test design notes from Day 10, updated with what changed after this lab

---

## Common errors

| Error | Meaning | Fix |
|---|---|---|
| `BLOCKED … the events sandbox did not start within 20s` | `aiohttp` is missing, or the sandbox crashed at start | `pip install -r requirements.txt`; read `reports/events/sandbox-<worker>.log` |
| `BLOCKED … order-events system unreachable` | `--sandbox-url` points to nothing | Start `python -m sandbox --port 8765`, or drop the option |
| `--sandbox-url runs build 'fixed' but --sandbox-build says 'release'` | The known-defect marks would be wrong | Pass the matching `--sandbox-build` |
| `HTTP 400 … correlation_id is required` | A read without a correlation id | Always read through `OrderFlow` |
| `TimeoutError: status 'shipped' not seen within 2.0s; frames so far: [...]; stream disconnected` | The flow stopped, or the stream dropped | Read `deliveries.txt`: which subscription stopped, and with what result? |
| `TimeoutError: still changing after …` | The flow never went quiet (a redelivery loop?) | A product defect candidate: look for an event delivered again and again |
| `unknown defect 'D-12-9'` | A typo in a `known_defect` mark or `@defect-` tag | Use an id registered in `findings.py` |
| `XPASS(strict)` | A known defect is gone in this build | Confirm, then update `findings.py` and the README |
| All events tests deselected | Run without `--store fake` | `pytest --store fake tests/events` |

---

## Self-check (answers below — try first)

1. The order reached `shipped` and every delivery says "applied". How could the customer still have been charged twice?
2. Why do faults carry a correlation id?
3. Why does the timeout test use `holds_for` after `shipped`, instead of checking the charges once?
4. When is it valid to say "exactly once", and how does the framework wait for that moment?
5. Why lower bounds on backoff gaps, and which upper bound matters?
6. A malformed message reached the DLQ after one attempt. Why is that correct, when a gateway 503 gets three?
7. How does the reconnect test make sure the gap really contains missed updates?
8. What does running the tests against the `fixed` build prove?
9. Why must a known defect not count as "manual" in the matrix?
10. Where in this lab did reading the evidence find a problem that the pass/fail result hid?

<details>
<summary><b>Answer guide</b></summary>

1. A late answer. The first gateway call timed out for the worker, but it still completed and charged. The retry used a new idempotency key, so the gateway charged again. Status oracles cannot see this; only the business effect (charges) can.
2. So that parallel tests, and other users of a shared environment, never receive each other's faults; each test disturbs only its own flow.
3. The late charge can land after `shipped`. A single check can pass by luck; the invariant has to hold over the whole window in which the late answer may arrive.
4. Only after no redelivery, retry, or late answer can still be pending. `settle()` waits until deliveries, charges, and frames have not changed for the quiet period (visibility timeout + the longest backoff).
5. Delays only grow under load, so an exact or upper bound on a gap makes the test flaky. The upper bound that matters is the business one: the flow completes within the consistency target plus the retry budget.
6. A malformed message is a permanent error: retrying it cannot succeed and only delays the messages behind it. A 503 is transient.
7. It waits until the read model shows `shipped` before reconnecting, so `packed` and `shipped` are always sent while the customer is offline.
8. That each defect test fails because of its defect and for no other reason: with the defect fixed and everything else identical, every test passes.
9. An xfail means "the requirement is not met, and we know it". Counting it as manual (or under PASS) shows a Critical defect as green.
10. Two places. The evidence row "Attempts seen 1" exposed a lost-ack scenario that passed before the fault had fired (§B7.3). The matrix showed REQ-10 as PASS while it had a Critical known defect (§B7.4).
</details>

## Next: Unit 4

AWS (LO7–LO9). The project is ready for it: the order-events sandbox has the same shape as a queue-and-worker service in the cloud (for example SQS with a dead-letter queue, and Lambda consumers). The oracles, correlation ids, and evidence record from today carry over unchanged.

---

## Verification log

| Check | Result |
|---|---|
| Fresh install from `day12-code/shop-bdd.zip` (`pip install -r requirements-dev.txt`) | OK (adds `aiohttp` 3.14.5, `websockets` 17.4) |
| `ruff check .` / `ruff format --check .` | All checks passed / 134 files already formatted |
| `mypy` (strict, now including `sandbox/`) | No issues in 128 source files |
| `python -m framework.review --strict` | 0 problems. The first draft had a "several-whens" smell in the reconnect scenario; fixed with a Given step |
| `pytest --store fake -n auto --fail-on-uncovered` | **236 passed, 2 skipped, 5 xfailed**, 6.7 s |
| Unit tests | 195 passed (45 new: oracles, waits, correlation ids, faults, platform selection, findings register, traceability precedence) |
| Events tests, `release` build, `-n auto`, 8 consecutive runs | 15 passed, 5 xfailed every time (3.1–3.5 s) |
| Events tests, `release` build, serial | 15 passed, 5 xfailed, 7.0 s |
| Events tests, `fixed` build | 20 passed (oracle validation) |
| External sandbox (`--sandbox-url`), `fixed` build, serial | 20 passed; build mismatch correctly refused (3 errors with the message above) |
| Tripwire: D-12-01 wrongly listed for `fixed` | `XPASS(strict)` → FAIL, REQ-10 FAIL |
| `--store web` collection | 249 of 279 collected; 30 deselected (20 events, 4 mobile, 6 `@mobile` scenarios) |
| `--store mobile`, no Appium server | Mobile tests BLOCKED as on Day 11; 74 deselected |
| Lesson §B7.3 (pass that proved nothing) | Observed in the first version (Attempts 1, Duplicates 0); after `settle()`: Attempts 2, Duplicates 1, Charges 1 |
| CI workflow | New step: events tests against the fixed build. YAML validated; **not run on GitHub** |
| Real brokers (Kafka, RabbitMQ, SQS) | Not used; the sandbox's in-memory broker implements the documented semantics |
| Mobile on a device | Still not run here (see Day 11 and §A.5) |
