# Unit 3 · Day 10 — Testing Asynchronous Systems: WebSocket, Queues, Event Correlation, Polling, Retries, Eventual Consistency

| | |
|---|---|
| **Course** | Advanced Automation Test Engineering (ATEST03) — Fast Track |
| **Unit** | Unit 3 — Mobile and Asynchronous-System Testing |
| **Learning outcome** | **LO6** — Analyze and test asynchronous or event-driven workflows for retries, duplicates, ordering, and eventual consistency (Bloom **B4: Analyze**) |
| **Format** | Concept/Lecture · Virtual · 120 minutes · no code to produce (short illustrations only) |
| **Output of the day** | Your analysis of the **event-correlation dataset** (Part 7) and your **async test design notes** |

> **How the facts here were checked.** The WebSocket techniques were run with Playwright 1.63 against a local WebSocket server (`websockets` 17.4): observing frames, replacing the server with a mock, and sitting between page and server to drop, reorder, and duplicate real messages. The polling helper was run against a simulated eventually-consistent store. No message broker (Kafka, RabbitMQ, SQS) was available, so broker behaviour is described from the delivery guarantees those systems document, not from a run. While preparing this lecture we also found an error in Day 5 (soft assertions); it is corrected there.

---

## How to use this lecture

LO6 is the first **Analyze** outcome of the course. "Apply" asked *can you write the test?*; "Analyze" asks *can you look at what a distributed system did and explain it* — which messages arrived, twice, late, out of order, or never, and whether the system still reached the right state.

| Badge | Level | After this level you can… |
|---|---|---|
| 🟢 | **Foundation** | Explain why asynchronous systems break synchronous test habits; define the key terms |
| 🟡 | **Practitioner** | Wait correctly for asynchronous outcomes; correlate events to one test; design tests for retries, duplicates, and ordering |
| 🔴 | **Senior** | Analyse event logs to find the failure mode, choose test oracles for eventual consistency, and inject faults deliberately |

### Lecture plan (120 min)

| Time | Part |
|---|---|
| 0–10 | Part 0 — Why asynchronous systems are hard to test |
| 10–30 | Part 1 — Building blocks: WebSocket, queues, delivery guarantees |
| 30–50 | Part 2 — Event correlation |
| 50–70 | Part 3 — Waiting for asynchronous outcomes: polling |
| 70–90 | Part 4 — Retries and duplicates |
| 90–105 | Part 5 — Ordering and eventual consistency |
| 105–115 | Part 6 — Tools: controlling WebSocket traffic with Playwright |
| 115–120 | Part 7 — Analysis exercise and evidence |

---

## Glossary

| Term | Meaning | Vietnamese |
|---|---|---|
| Synchronous | The caller waits for the answer before continuing | Đồng bộ |
| Asynchronous | Work continues after the call returns; the result arrives later | Bất đồng bộ |
| Event | A record that something happened ("OrderPaid") | Sự kiện |
| Producer / consumer | Who publishes a message / who processes it | Bên gửi / bên nhận |
| Queue / topic | A buffer of messages for one consumer group / for many subscribers | Hàng đợi / chủ đề |
| Acknowledgement (ack) | The consumer's "done" that lets the broker delete the message | Xác nhận |
| At-least-once delivery | Every message arrives, possibly more than once | Giao ít nhất một lần |
| Idempotent | Doing it twice has the same effect as once | Lũy đẳng |
| Dead-letter queue (DLQ) | Where messages go after failing too many times | Hàng đợi thư lỗi |
| Correlation id | An id shared by every event of one business flow | Mã liên kết |
| Eventual consistency | Different parts of the system agree **after** some time, not immediately | Nhất quán sau cùng |
| Read model | A copy of data optimised for reading, updated from events | Mô hình đọc |
| Polling | Asking repeatedly until a condition holds or time runs out | Thăm dò lặp |
| Backoff | Waiting longer between successive attempts | Giãn cách tăng dần |
| Fault injection | Causing failures on purpose to test the system's reaction | Tiêm lỗi |

---

## Part 0 — Why asynchronous systems are hard to test 🟢

### 0.1 The synchronous habit

```
test ── request ──▶ system ── answer ──▶ test checks the answer        (Units 1–2, mostly)
```

### 0.2 The asynchronous reality

```
test ── command ──▶ API ── "accepted" ──▶ test        ← the answer says nothing about the outcome
                     │
                     └─▶ queue ─▶ worker ─▶ database ─▶ event ─▶ read model / WebSocket ─▶ UI
                              (later; maybe twice; maybe out of order; maybe never)
```

A synchronous test checks the answer immediately. In an asynchronous system, the immediate answer is "accepted", and the real outcome happens later, somewhere else.

### 0.3 You have already met it in this course

| Observation | Asynchronous pattern |
|---|---|
| Right after the server confirmed Add to Cart, the header still said "My Cart (0)" (Unit 2, Day 8 case 7) | The UI is updated **after** the server — eventual consistency at the UI level |
| The mini-cart drawer stayed empty until the next page load (Unit 1, Day 3) | A **stale read model** that is never refreshed — a defect |
| Aborting the shop's telemetry made the scripts send more requests (Unit 2, Day 6) | **Client retries**: a failure produced extra attempts |

> **Checkpoint 0.** Why is an HTTP `202 Accepted` a weaker test oracle than a `200 OK` with the result in the body?

---

## Part 1 — Building blocks 🟢 → 🟡

### 1.1 🟢 WebSocket

A WebSocket is a **long-lived, two-way connection**: after one handshake, both sides send **frames** whenever they want. Used for live order status, chat, prices, notifications.

| Property | Testing consequence |
|---|---|
| The server pushes without being asked | The test must **listen**, not request |
| Frames have no built-in ids or order guarantees across reconnects | The application's messages need their own ids and sequence numbers |
| Connections drop and reconnect | Test what happens to messages sent during the gap |

### 1.2 🟢 Message queues and topics

| Concept | Meaning |
|---|---|
| Queue | Each message is processed by **one** consumer of a group |
| Topic / pub-sub | Each subscriber receives its **own copy** |
| Partition / ordering key | Messages with the same key keep their order; different keys do not |
| Ack | The consumer confirms; until then the broker may redeliver |
| Visibility timeout / redelivery | An unacknowledged message becomes visible again and is delivered again |
| Dead-letter queue | After N failed attempts, the message is parked for humans |

### 1.3 🟡 Delivery guarantees and what they mean for tests

| Guarantee | Can lose messages? | Can duplicate? | What you must test |
|---|---|---|---|
| At-most-once | Yes | No | Loss is detected or acceptable |
| **At-least-once** (the common default) | No | **Yes** | Consumers are **idempotent** |
| "Exactly-once" | Only within one system's boundaries, under its conditions | — | Read the conditions; the moment a side effect leaves the boundary (an e-mail, a payment call), duplicates are possible again |

The practical rule: **assume duplicates and reordering, and test that the business outcome is still correct.**

---

## Part 2 — Event correlation 🟡 → 🔴

### 2.1 🟡 The problem

A shared test environment receives events from every test, every developer, and every background job. Your test must find **its own** events, and you must be able to follow **one** business flow across services.

### 2.2 🟡 An event envelope

| Field | Example | Purpose |
|---|---|---|
| `event_id` | `e-7f3a…` | Unique per event — detects duplicates |
| `type` | `OrderPaid` | What happened |
| `correlation_id` | `order-A-1042` / test run id | Groups every event of one flow |
| `causation_id` | the `event_id` that caused this one | Rebuilds the chain |
| `sequence` / `version` | `3` | Order within one entity |
| `occurred_at` | `2026-11-18T08:15:49.120Z` | When it happened (producer clock) |
| `attempt` | `2` | Which delivery/processing attempt |
| `idempotency_key` | `pay-A-1042` | Lets the consumer ignore repeats |

### 2.3 🔴 Trace context

Across HTTP calls, the W3C Trace Context standard carries a `traceparent` header:

```
traceparent: 00-<32-hex trace id>-<16-hex parent span id>-<2-hex flags>
```

When services propagate it into the events they publish, a test can follow one request through logs and traces of every service. (The shop's pages in Unit 2 sent telemetry to an OpenTelemetry endpoint — the same family of tools.)

### 2.4 🔴 How tests use correlation

| Practice | Why |
|---|---|
| Generate a **unique** correlation id per test (`testrun_uid` + test name + worker id) | Parallel tests and other users never see each other's events (Unit 2, Day 6 isolation) |
| Put it into the command that starts the flow | Every downstream event inherits it |
| Filter streams, logs, and read models **by it** | The assertion only looks at your events |
| Attach it to the evidence | A failed test points to every log line of its flow |

---

## Part 3 — Waiting for asynchronous outcomes 🟡 → 🔴

### 3.1 🟢 Three ways to wait — two are wrong

| Way | Problem |
|---|---|
| Check immediately | The outcome has not happened yet → false failure |
| `sleep(5)` then check | Too long when fast, too short when slow → slow **and** flaky |
| **Poll until a condition holds, with a deadline** | Fast when the system is fast; fails with information when it is not |

### 3.2 🟡 A polling helper

Python Playwright has `expect(...)` retries for **page** facts, but no `expect.poll` for arbitrary values (checked in 1.63). For backend state, a small helper does the job:

```python
def wait_until(read, done, *, timeout=10.0, interval=0.1, backoff=2.0, max_interval=2.0):
    """Poll `read()` until `done(value)` holds; return the value, or raise with the last value seen."""
    deadline = time.monotonic() + timeout
    value = read()
    while not done(value):
        if time.monotonic() >= deadline:
            raise TimeoutError(f"condition not met within {timeout}s; last value: {value!r}")
        time.sleep(min(interval, max(0.0, deadline - time.monotonic())))
        interval = min(interval * backoff, max_interval)
        value = read()
    return value
```

Run against a store that applied a write 1.2 s late: the first read returned `pending`; the helper returned `shipped` after 1.5 s and 5 reads (intervals 0.1, 0.2, 0.4, 0.8 s). With a 0.5 s deadline it raised `condition not met within 0.5s; last value: 'pending'` — the last value is half of the diagnosis.

This is the **one** place where sleeping is legitimate: a short, bounded interval **between checks of a condition**. The Unit 1 architecture test forbids `sleep` elsewhere; a polling helper belongs on its written allow-list.

### 3.3 🔴 Designing the condition

| Ask | Good condition | Weak condition |
|---|---|---|
| What is the **final** state? | `status == "shipped"` | `status != "pending"` (also true for `"failed"`) |
| Can it pass for the wrong reason? | Also check the correlation id | Any order is shipped |
| What if it overshoots? | `count == 1` (exactly once) | `count >= 1` hides duplicates |
| How long is acceptable? | Timeout from the system's consistency target (Part 5.4) | "30 s to be safe" |

### 3.4 🟡 Push instead of pull

When the system **publishes** the outcome (a WebSocket frame, an event on a topic), subscribe **before** triggering the action and wait for the message — no polling interval at all. In Playwright, `page.expect_websocket()` and the WebSocket's frame events do this for browser traffic (Part 6).

---

## Part 4 — Retries and duplicates 🟡 → 🔴

### 4.1 🟢 Why retries create duplicates

```
consumer receives "ChargeCard" ─▶ charges the card ─▶ crashes before ack
broker: no ack → redeliver ─▶ consumer charges the card AGAIN
```

The first attempt **succeeded**, but nobody heard about it. Retrying is correct — and without idempotency it double-charges.

### 4.2 🟡 What a retry policy contains

| Element | Example | Test question |
|---|---|---|
| Which errors are retried | Timeouts, 503 — not 400 | Is a validation error retried by mistake? |
| How many attempts | 3 | What happens after the last one (DLQ, alert, compensation)? |
| Backoff | 1 s, 2 s, 4 s | Does the total fit the user-facing timeout? |
| Jitter | ±20 % | Do many clients avoid retrying in lockstep? |
| Idempotency | Keyed on `idempotency_key` | Does a repeat produce exactly one effect? |

### 4.3 🔴 Test patterns

| Pattern | How | Oracle |
|---|---|---|
| **Duplicate delivery** | Deliver the same message twice (or replay it) | Exactly **one** business effect; the second is recorded as ignored |
| **Transient failure** | Fail the first N attempts (fault injection), then succeed | One effect; attempt count = N + 1; total time within budget |
| **Permanent failure** | Fail every attempt | Message in the DLQ after the configured attempts; no partial effect; alert raised |
| **Poison message** | Malformed payload | Goes to DLQ without blocking the messages behind it |
| **Timeout** | The dependency answers after the caller gave up | No duplicate effect when the late answer arrives |

### 4.4 🔴 The course's evidence for "retry is not free"

In Unit 2, Day 6, failing the shop's telemetry requests made the client **retry** (74 requests instead of 65). Answering with an empty `204` stopped it. The same lesson holds for any producer: a failure you inject in a test can multiply traffic, and the test should measure that, not just the final state.

---

## Part 5 — Ordering and eventual consistency 🟡 → 🔴

### 5.1 🟡 Ordering is usually per key, never global

Brokers typically keep order **within one partition or ordering key** (all events of order A-1042), not across keys. Retries, reconnects, and parallel consumers can still reorder delivery to the application.

| Strategy in the system | What to test |
|---|---|
| Sequence numbers / versions per entity | Event 3 before event 2 → buffered or applied correctly; never "packed" overwritten by an older "paid" |
| Last-write-wins on timestamps | Clock skew between producers → wrong winner |
| Commutative updates (order does not matter) | Any order → same result |

### 5.2 🟡 Eventual consistency in plain words

After a write, different parts of the system (database, read model, search index, cache, UI) **agree later**. Until then, a read can return the **old** value.

| Guarantee | Meaning | Test |
|---|---|---|
| Read-your-writes | The user who wrote sees their own write at once | Write, then read through the same user's path immediately |
| Monotonic reads | Once you saw a newer value, you never see an older one | Read repeatedly; versions never go backwards |
| Convergence | All copies end up equal | Poll every copy until equal, within the consistency target |

### 5.3 🔴 Oracles for systems that are "temporarily wrong"

| Oracle | Example |
|---|---|
| **Final state** after convergence | Order status `shipped` in every read model |
| **Invariants** that must hold at **every** moment | Stock never negative; one payment per order; total = sum of lines |
| **Convergence time** | All copies agree within the agreed target |
| **No stale overwrite** | A late "paid" never replaces "shipped" |

Invariants are the senior tool: they catch bugs that are visible only **during** the inconsistent window, which a final-state check misses.

### 5.4 🔴 The consistency target is a requirement

"It will be consistent eventually" is not testable. "The order list shows a new order within 2 seconds in 99 % of cases" is. Ask for the number; use it as the polling timeout; report the measured times (Part 7's evidence template has a column for it).

The mini-cart in Unit 1 is the counter-example: it never converged without a page load. Under a "within 2 seconds" requirement that is a clear defect; without a requirement it is an argument.

---

## Part 6 — Tools: controlling WebSocket traffic with Playwright 🟡 → 🔴

All three techniques were run with Playwright 1.63 against a local server that sends `paid` (1), `packed` (2), `shipped` (3).

### 6.1 🟡 Observe

```python
page.on("websocket", lambda ws: ws.on("framereceived", lambda payload: frames.append(payload)))
```

A server that deliberately sent seq 2, 1, 2 was observed exactly so: the test **sees** duplicates and reordering in the raw frames — evidence for analysis.

### 6.2 🟡 Replace the server (mock)

```python
page.route_web_socket("**/feed", lambda ws: ws.on_message(lambda message: ws.send(MOCK_EVENT)))
```

The page received the mock's message without any real server.

### 6.3 🔴 Sit in the middle (fault injection)

```python
def drop_packed(ws):
    server = ws.connect_to_server()
    server.on_message(lambda message: None if '"packed"' in message else ws.send(message))
```

| Proxy behaviour | Server sent | Page received |
|---|---|---|
| None | 1, 2, 3 | 1, 2, 3 |
| Drop "packed" | 1, 2, 3 | **1, 3** |
| Hold seq 2, then send it twice after 3 | 1, 2, 3 | **1, 3, 2, 2** |

This is how Day 12's lab creates loss, reordering, and duplicates **on purpose** against a real server.

### 6.4 🔴 A trap found while preparing

`route_web_socket` had **no effect** on a page created with `page.set_content(...)` (an `about:blank` page); the same code worked on a page loaded over HTTP, with a glob, an exact URL, or a regular expression. Test WebSocket routing on pages served from a real origin.

### 6.5 🟡 For queues and back-end events

| Technique | Use |
|---|---|
| A **local broker** (in containers) in the test environment | Real broker semantics: redelivery, DLQ, ordering per key |
| A **test double** of the broker in the consumer's own tests | Fast, deterministic retries and duplicates |
| **Contract tests** on event schemas | Producer and consumer agree on fields and versions |
| **Correlation-filtered** reads of logs and read models | Assertions only on your test's flow |

---

## Part 7 — Analysis exercise and evidence 🔴

### 7.1 Event-correlation dataset (required material)

An **example** log from an order-fulfilment flow (synthetic data for analysis). Times are seconds after the test started. `read_model` shows what the order screen displayed at that moment.

| # | t (s) | correlation_id | event_id | type | seq | attempt | consumer result | read_model |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.0 | T-A | e1 | OrderPlaced | 1 | 1 | applied | placed |
| 2 | 0.3 | T-B | e2 | OrderPlaced | 1 | 1 | applied | placed |
| 3 | 0.9 | T-A | e3 | OrderPaid | 2 | 1 | timeout (no ack) | placed |
| 4 | 1.0 | T-B | e4 | OrderPaid | 2 | 1 | applied | paid |
| 5 | 2.9 | T-A | e3 | OrderPaid | 2 | 2 | applied | paid |
| 6 | 3.1 | T-B | e6 | OrderShipped | 4 | 1 | applied | shipped |
| 7 | 3.4 | T-B | e5 | OrderPacked | 3 | 1 | applied | **packed** |
| 8 | 4.0 | T-A | e7 | OrderPacked | 3 | 1 | applied | packed |
| 9 | 4.2 | T-A | e7 | OrderPacked | 3 | 2 | applied | packed |
| 10 | 5.0 | T-C | e8 | OrderPlaced | 1 | 1 | rejected: schema error | — |
| 11 | 7.0 | T-C | e8 | OrderPlaced | 1 | 2 | rejected: schema error | — |
| 12 | 11.0 | T-C | e8 | OrderPlaced | 1 | 3 | moved to DLQ | — |
| 13 | 12.0 | T-A | e9 | OrderShipped | 4 | 1 | applied | shipped |

Business requirements for this flow: each order is paid exactly once; the screen never shows an older status than one already shown; failed messages reach the DLQ after 3 attempts; the screen reflects a new status within 2 seconds.

### 7.2 Questions (Analyze)

1. Group the rows by `correlation_id`. Which flows completed?
2. Find every **retry**. Which retries were caused by a lost acknowledgement, and which by a real failure?
3. Find every **duplicate delivery**. Did any cause a duplicate business effect? What would you need to check to be sure?
4. Find the **ordering** problem. What did the customer see, and which requirement does it break?
5. Was the DLQ behaviour correct for T-C?
6. Is the 2-second consistency requirement met for T-A's payment? Measure from the first delivery.
7. Write the three test cases (name, injected fault, oracle) that would have caught the defects you found.

<details>
<summary><b>Analysis guide</b></summary>

1. T-A completed (placed → paid → packed → shipped). T-B reached `shipped` but ended **displaying `packed`** (row 7). T-C never entered the system (DLQ).
2. Row 5 (e3, attempt 2) follows a timeout without ack on row 3: the first attempt may have been processed — a **lost-ack** retry. Rows 11–12 (e8) are retries of a **real** failure (schema error). Row 9 (e7, attempt 2) is a redelivery of an event that had been applied (row 8).
3. e3 (rows 3 and 5) and e7 (rows 8 and 9) were delivered twice. The log shows `applied` for e7 twice — the consumer did **not** report ignoring the repeat, so it may have applied it twice. To be sure, check the business effect (one payment record for T-A; packing tasks created once) and whether the consumer records duplicates as ignored. For e3, row 3 is "timeout", so whether the first attempt charged the card is **unknown** — exactly the case idempotency keys exist for.
4. T-B: `OrderShipped` (seq 4) was applied at 3.1 s, then the older `OrderPacked` (seq 3) at 3.4 s overwrote the screen to `packed`. The customer saw shipped → packed: it breaks "never show an older status". The consumer ignores sequence numbers.
5. Yes: three attempts (rows 10–12), then DLQ, with no read-model change. Also check: an alert was raised, and the schema error was not retried as if it were transient (retrying a schema error 3 times is wasteful — a design finding).
6. First delivery of the payment at 0.9 s; the screen showed `paid` at 2.9 s → **2.0 s**, exactly at the limit. With a lost ack, the requirement is met only by luck; a real retry interval of 2 s plus processing time would break it.
7. (a) *Out-of-order delivery* — inject seq 4 before seq 3 for one order; oracle: displayed status never goes backwards, final status `shipped`. (b) *Duplicate delivery* — deliver `OrderPaid` twice with the same `event_id`; oracle: exactly one payment record, second delivery logged as ignored. (c) *Lost ack* — drop the ack of `OrderPaid` once; oracle: one payment, status `paid` within 2 s, attempt count 2.
</details>

### 7.3 Asynchronous execution-evidence template

Extends Day 9's template; fill it on Day 12:

```markdown
# Async execution evidence — <run id>

| Field | Value |
|---|---|
| Correlation id(s) used | |
| Injected faults | e.g. drop "packed"; duplicate "OrderPaid"; ack lost once |
| Broker / WebSocket endpoint and version | |
| Consistency target | e.g. status visible within 2 s |

## Per test
| Test | Correlation id | Fault | Oracle (final state + invariants) | Result | Measured convergence time | Attempts seen | Duplicates seen |
|---|---|---|---|---|---|---|---|

## Event log excerpt (filtered by correlation id)
Attach the ordered list of events and frames, with event_id, sequence, attempt, and timestamps.
```

---

## Your output: async test design notes (one page)

| Topic | Your decision and the reason |
|---|---|
| How each test gets a unique correlation id, and where it is attached | |
| Polling: helper, intervals, timeout source (consistency target) | |
| Oracles: final state, invariants, convergence time | |
| Duplicate, retry, and DLQ tests you will write | |
| Ordering tests and how you inject reordering | |
| Evidence collected per test | |

---

## Self-check (answers below — try first)

1. Why does a `202 Accepted` not prove that an order was processed?
2. Under at-least-once delivery, what must every consumer be, and how do you test it?
3. What is the difference between a correlation id and an event id?
4. Why is `sleep(5)` worse than polling, and when is a short sleep legitimate?
5. Your polling condition is `status != "pending"`. What can go wrong?
6. Why are invariants stronger oracles than a final-state check in an eventually consistent system?
7. A broker guarantees order per partition. How can your application still see events out of order?
8. You routed a WebSocket on a page made with `set_content`, and nothing happened. Why?
9. In the dataset, why is "the payment requirement met in 2.0 s" a weak result?

<details>
<summary><b>Answer guide</b></summary>

1. It only says the request was accepted for later processing; the outcome happens elsewhere, later, and can fail.
2. Idempotent. Deliver the same message twice (same event id / idempotency key) and assert exactly one business effect.
3. A correlation id groups all events of one flow (or test); an event id identifies one event, so repeats of it are duplicates.
4. A fixed sleep is too long when the system is fast and too short when it is slow. A short, bounded sleep between condition checks inside a polling helper is legitimate.
5. It also passes for `"failed"` or any other wrong state. Poll for the expected final state, and check failure states explicitly.
6. They must hold at every moment, so they catch problems inside the inconsistent window (a status going backwards, a double charge) that disappear by the time the final state is checked.
7. Retries and redeliveries, reconnects, several consumers processing in parallel, or producers using different keys for related events.
8. In the check made for this lecture, `route_web_socket` had no effect on an `about:blank` page created with `set_content`, while it worked on a page loaded over HTTP.
9. It sits exactly on the limit, and only because of a lost-ack retry that happened to take 2 s; any slower retry or processing breaks it. Report it as a risk, not a pass.
</details>

## Next: Day 11 — mobile lab

Implement prioritised Android/iOS workflows on My Demo App with Appium, and collect execution evidence (Day 9's template).

---

## Verification notes

| Check | Result |
|---|---|
| Observe WebSocket frames (`page.on("websocket")`, `framereceived`) | Duplicate and out-of-order frames (seq 2, 1, 2) observed as sent |
| Mock server (`route_web_socket` + `on_message` / `send`) | Works on a page loaded over HTTP (glob, exact URL, and regex); **no effect** on a `set_content` page |
| Proxy (`connect_to_server`) | Dropped "packed" → page got 1, 3; held and duplicated seq 2 → page got 1, 3, 2, 2 |
| `expect.poll` in Python Playwright 1.63 | Not available (`expect` offers `soft` and `set_options`) |
| `expect.soft` | Available; with pytest-playwright 0.10 the test continued and failed at the end with both errors — Day 5 corrected |
| Polling helper | Returned `shipped` after 1.5 s / 5 reads; timeout message included the last value |
| Message brokers | **Not run** (none available); described from their documented delivery guarantees |
| Event-correlation dataset | Synthetic example created for the analysis exercise |
