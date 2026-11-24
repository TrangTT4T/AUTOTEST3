# Unit 5 · Day 21 — Mock Project (3/4): Asynchronous Behaviour, Performance, Containers and CI

| | |
|---|---|
| **Course** | Advanced Automation Test Engineering (ATEST03) — Fast Track |
| **Unit** | Unit 5 — Mock Project Design and Implementation |
| **Session** | Assignment/Lab, part 3 of 4 · **120 min** |
| **Learning outcomes** | **LO6** asynchronous behaviour: retries, duplicates, ordering, eventual consistency (B4) · **LO8** performance evidence → bottlenecks (B4) · **LO4** containerised, reproducible, isolated, recoverable execution (B3) · **LO7** distributed execution with retained artifacts — on GitHub Actions instead of ECS/Fargate + Device Farm (B3) |
| **Code** | `features/dynamic_catalogue.feature`, `swaglabs/waiting.py`, `swaglabs/perf.py`, `swaglabs/network.py`, `docker/`, `.github/workflows/mock-project.yml` |
| **Output today** | Async scenarios that never flake · budgets with a bottleneck verdict · a pinned, read-only test image · an 8-job CI matrix with a merged quality matrix |

---

## Plan for today (120 min)

| Time | Block | Level |
|---|---|---|
| 0–35 | 1. Asynchronous content: spinner, lazy loading, slider, two tabs, double clicks | 🟢→🔴 |
| 35–65 | 2. Performance: budgets, the network/client split, and an instrument that lied | 🟡→🔴 |
| 65–90 | 3. The test-runner container | 🟡 |
| 90–115 | 4. The CI pipeline, evidence and the quality matrix | 🟡→🔴 |
| 115–120 | Self-check | |

---

## 1. Asynchronous content

### 1.1 🟢 The one rule: wait for a **state**, never for a time

`time.sleep(2)` is wrong twice: too long when the system is fast (slow suite), too short when it
is slow (flaky suite). Wait for the state you need:

| What you need | Tool | Retries until |
|---|---|---|
| an element's state | `expect(locator).to_be_visible()` / `to_have_text(...)` | the assertion holds or the UI timeout ends |
| anything else (storage, cookies, values computed from several elements) | `eventually(probe, predicate)` | the predicate holds; the failure shows the **last** value |

```python
def eventually(probe, predicate, *, timeout_s, description, interval_s=0.1, backoff=1.5,
               max_interval_s=1.0, clock=time.monotonic, sleep=time.sleep):
    deadline = clock() + timeout_s
    wait = interval_s
    attempts = 0
    while True:
        value = probe()
        attempts += 1
        if predicate(value):
            return value
        remaining = deadline - clock()
        if remaining <= 0:
            raise AssertionError(
                f"{description}: not reached within {timeout_s:g} s ({attempts} tries); last value: {value!r}"
            )
        sleep(min(wait, remaining))
        wait = min(wait * backoff, max_interval_s)
```

Three design points a senior reviewer looks for:

1. **Retry reads, never actions.** A retried click can add a product twice.
2. **Back-off** (0.1 s, 0.15 s, … up to 1 s): fast when the system is fast, gentle when it is slow.
3. **Inject the clock and the sleep.** Unit tests use a fake clock and run in microseconds; the
   browser version sleeps *inside* Playwright (`page.wait_for_timeout`) because the sync API
   only delivers browser events while a Playwright call is running — a `time.sleep` would
   freeze the event stream (this matters in section 2).

### 1.2 🟡 Spinner — a state, not a delay

```gherkin
  Scenario: Products appear once the spinner has gone
    When I open the spinner catalogue
    Then the products appear once the spinner has gone
    And every tile shows a reference product at its reference price
```

```python
def wait_for_products(self) -> None:
    expect(self.find(self._spinner), "the spinner should go away").to_be_hidden()
    expect(self.find(self._grid)).to_be_visible()
# --- Locators ---
_spinner = "role=status[name='Loading']"
```

Note what we do **not** assert: "a spinner is shown first". It is visible for about a second;
checking it is a race against the page. Assert the end state, plus the content against the oracle.

### 1.3 🟡→🔴 Lazy loading — a test that passed on desktop and failed on a phone

The page appends batches of tiles when a sentinel at the bottom scrolls into view; each tile
then loads its content **when it is on screen** (until then it is a *Loading…* placeholder).

The first version jumped straight to the sentinel (`scroll_into_view_if_needed`) and expected
every tile to load. It passed on a desktop (three columns, everything visible) and **failed on
Pixel 7**: in one column, jumping to the end skipped the tiles in between — they never came on
screen, so they stayed placeholders forever. The page was right; the test was wrong.

The fixed scenario behaves like a reader and asserts properties that hold on every screen size:

```gherkin
  Scenario: Scrolling loads more products without duplicates or gaps
    When I open the lazy-loading catalogue
    And I scroll down until at least 30 products have loaded
    Then every tile on screen finishes loading
    And every loaded tile shows a reference product at its reference price
    And the tiles are numbered without duplicates or gaps
```

```python
def scroll_one_screen(self) -> None:
    """Scroll down by one screen, like a reader. Tiles load only once they are ON SCREEN..."""
    self.find(self._container).evaluate("() => window.scrollBy(0, window.innerHeight)")

@then("the tiles are numbered without duplicates or gaps")
def tiles_numbered(shop):
    numbers = [int(t.id.rsplit("-", 1)[-1]) for t in shop.lazy_catalogue().read_tiles()]
    assert numbers == list(range(len(numbers))), f"tile numbers {numbers}"
```

The numbering check is the classic **duplicates + ordering** oracle for paged data: a batch
loaded twice gives duplicates, a lost batch gives a gap, a race gives the wrong order.
(Scrolling inside the retry loop is the one "action" we retry — it is idempotent: one screen too
many does no harm. Say so in a comment when you break a rule on purpose.)

### 1.4 🔴 The slider — assert an invariant and a history

The slider rotates by itself every ~2.5 s. "Click dot 5, then the name is Fleece Jacket" is a
race: the rotation may move on between the click and the read.

**Invariant over time:** whatever is shown, the active dot names it. Read both in **one**
`evaluate` (two separate reads could straddle a rotation and disagree for no real reason):

```python
def snapshot(self) -> tuple[str, str]:
    values = self.page.evaluate(
        "(s) => [document.querySelector(s.name).innerText,"
        " document.querySelector(s.active).getAttribute('aria-label')]",
        {"name": self._shown_name, "active": self._active_dot},
    )
    return str(values[0]), re.sub(r"^Show ", "", str(values[1]))
```

**History instead of snapshot:** install a `MutationObserver` *before* clicking; it records
every product shown. The assertion "Fleece Jacket was shown after my choice" holds even if the
slider moved on a millisecond later:

```python
slider.start_recording()  # BEFORE the click: a change right after it cannot be missed
slider.choose(name)
...
shop.eventually(shop.slider().history, lambda history: name in history, f"{name!r} should be shown")
```

### 1.5 🟡 Duplicates and eventual consistency in the cart

**Double click (idempotency).** On Swag Labs the button toggles: a double click adds, then
removes. Whatever it does, the cart must never hold the same product twice, and the badge must
agree with the stored cart:

```python
@then("the cart badge agrees with the stored cart")
def badge_agrees(shop):
    # Two sources of truth that update separately: wait until they agree (eventual consistency).
    shop.eventually(
        lambda: (shop.header.cart_count(), len(set(shop.stored_cart_ids()))),
        lambda pair: pair[0] == pair[1],
        "badge count and number of stored products should agree",
    )
```

**Two tabs.** Remove a product in tab 2; the stored cart (shared `localStorage`) changes at once,
but tab 1 still shows the old badge until it reloads — Swag Labs has no live sync. We assert
what the product promises (*eventually consistent after a reload*), not what it does not:

```gherkin
  Scenario: A change made in a second tab reaches the first tab
    Given my cart holds "Sauce Labs Backpack" and "Sauce Labs Onesie"
    And a second tab shows the cart
    When I remove "Sauce Labs Onesie" in the second tab
    Then the stored cart eventually holds only "Sauce Labs Backpack"
    And after a reload the first tab's badge shows 1
```

---

## 2. Performance evidence (LO8, without CloudWatch and without load)

### 2.1 🟢 Budgets, not load

We may not load-test someone else's site. What we *can* measure honestly is what one user
waits for, on every run. `perf-budgets.toml`:

```toml
[budgets]
login = 2500           # click Login -> products list visible
sort = 2000            # choose a sort order -> first card re-ordered
add-to-cart = 1000     # click Add -> badge updated
...
```

A measurement covers the action **and** its visible result — the step puts both inside the timer:

```python
with shop.perf.measure("sort"):
    inventory.sort_by(order)
    inventory.expect_first_name(expected_first)
```

`reports/perf.md` gives p50, p95 (nearest rank) and max per action, and the budget verdict.
The `@area-response-time` scenarios turn the budget into a pass/fail check (REQ-SL-14).

### 2.2 🟡 Where does the time go? The network/client split

A slow interaction is either **waiting for the network** (server, CDN, big files) or **busy in
the client** (JavaScript, rendering, a deliberate delay). The fix lives in different places, so
this is the first question of any investigation.

The browser monitor records the start and end of every request; inside the measured window, the
**union** of those intervals is the network-busy time:

```python
def busy_time(intervals, start, end):
    """Length of the union of ``intervals`` clipped to [start, end].
    Overlapping requests count once: four parallel 100 ms downloads keep the network busy for
    100 ms, not 400 ms."""
```

`client = duration − network-busy`. Less than 25 % network → **client**-bound; more than 75 % →
**network**-bound; otherwise **mixed**.

### 2.3 🔴 The instrument lied — twice

The first runs as `performance_glitch_user` said: *login 5.2 s, network-bound; sort 5.1 s,
network-bound, 0 requests*. "Network-bound with zero requests" is a contradiction — so before
writing a word of analysis we checked the instrument against a **second, independent
measurement**: a raw request timeline recorded around one login.

```
login took 5.07 s
(5.05, 'req', '.../sauce-backpack-1200x1500-....jpg', 'image')
(5.05, 'req', '.../bike-light-1200x1500-....jpg', 'image')
... (no request at all in the first 5.05 s)
```

The network was idle for five seconds. Two bugs in our monitor:

1. **Unfinished requests from before the window** (cancelled by a navigation, never reporting an
   end) were counted as "in flight until now" → busy for the whole window. Fix: an unfinished
   request counts only if it **started inside** the window (`window_activity`, unit-tested).
2. **Late timestamps.** We time-stamped a request when *Python received* the event. While the
   page's JavaScript spins, Playwright delivers events late — a request that ended *before* the
   click looked as if it lasted into it. Fix: use the **browser's own** record,
   `request.timing` (`startTime`, `responseEnd`), and a wall-clock window to compare with it.

```python
timing = request.timing
start_ms, end_offset_ms = timing.get("startTime", -1), timing.get("responseEnd", -1)
if start_ms > 0 and end_offset_ms >= 0:  # the browser's own record of the request
    self._intervals.append((start_ms / 1000, (start_ms + end_offset_ms) / 1000))
```

After the fix (Chromium, 4 workers):

| Action | p50 ms | p95 ms | Budget | Network busy | Requests | Verdict |
|---|---:|---:|---:|---:|---:|---|
| login | 5199 | 5270 | 2500 | 120–170 ms | 6 (images, after the page appears) | **client** |
| sort | 5070 | 5089 | 2000 | 10–370 ms | 0 | **client** |
| add-to-cart | 64 | 91 | 1000 | | | OK |

**Bottleneck statement (the format for your report):** *For performance_glitch_user, login and
sorting take ~5.1 s (p95 5.3 s / 5.1 s, budgets 2.5 s / 2 s) while the network is idle for more
than 90 % of the time and sorting sends no request: the delay is client-side JavaScript in those
two actions. All other interactions match standard_user. Fix in the client code of login and
sort; re-measure with the same scenarios.*

> **Lesson.** Every instrument has blind spots. Before you explain a number, check it against a
> second, independent measurement. The unit tests now pin both fixes so they cannot return.

---

## 3. The test-runner container (LO4)

```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.63.0-noble@sha256:72bd171a9ffc2b4b59532aaa6210e21014d07093120dc25528870c0b840da1f0

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOME=/tmp
WORKDIR /work
COPY requirements.txt .
RUN --mount=type=secret,id=proxy_ca,required=false \
    if [ -f /run/secrets/proxy_ca ]; then export PIP_CERT=/run/secrets/proxy_ca; fi; \
    pip install -r requirements.txt \
    && python -m playwright --version
COPY . .
RUN mkdir -p /work/reports && chown pwuser:pwuser /work/reports
USER pwuser
ENTRYPOINT ["python", "-m", "pytest", "-p", "no:cacheprovider"]
CMD ["-n", "4"]
```

(Abridged — the file has a comment on every decision.)

| Line | Property | Why |
|---|---|---|
| `FROM …@sha256:` | reproducible | the browsers and their system libraries match `playwright==1.63.0`; a digest cannot move |
| requirements before code | fast builds | the dependency layer is rebuilt only when `requirements.txt` changes |
| secret mount | no secret in layers | a corporate proxy CA is used at build time and never stored |
| `HOME=/tmp` | read-only friendly | browsers write profiles under `$HOME`; `/tmp` is a tmpfs at run time |
| `USER pwuser` | least privilege | uid 1001 = the GitHub runner's uid, so mounted reports belong to the runner |
| `ENTRYPOINT pytest` | one purpose | arguments after the image name are pytest arguments |

Run it like CI does:

```bash
docker build -f docker/Dockerfile -t swaglabs-tests:local .
```

```bash
docker run --rm --init --ipc=host --read-only --tmpfs /tmp:exec \
  -v "$PWD/reports:/work/reports" -e SWAGLABS_PERSONA=visual_user \
  swaglabs-tests:local tests/test_scenarios.py -n 4 --browser webkit
```

| Flag | Property |
|---|---|
| `--read-only` + `--tmpfs /tmp` | isolation: the code cannot be changed by a test; nothing survives the run except `reports/` |
| `--init` | recoverability: a real PID 1 forwards signals to pytest and reaps zombie browser processes |
| `--ipc=host` | Chromium needs more shared memory than Docker's 64 MB default |
| `-v reports` | evidence outlives the container |

**Fail fast on lost evidence.** If `reports/` is not writable, the run refuses to start:

```
ERROR: cannot write evidence to /work/reports (Read-only file system); in a read-only
container mount a volume or tmpfs there, e.g. -v "$PWD/reports:/work/reports"
```

`docker/compose.yaml` wraps the flags (`docker compose -f docker/compose.yaml run --rm tests`)
and has an `unit` service with `network_mode: none` — proof that the unit suite needs no network.

---

## 4. The CI pipeline (LO7 without AWS)

`.github/workflows/mock-project.yml`:

```
quality ──► e2e matrix (8 containers in parallel) ──► quality-matrix
```

### 4.1 Job `quality` (no browser, ~1 min)

`ruff check` + `ruff format --check` → `mypy` (strict) → unit and plugin tests with the 90 %
coverage ratchet → `pytest --collect-only --fail-on-uncovered` (every requirement and every
finding has a scenario) → `actionlint` on the workflow. If the framework is broken, no browser
minute is spent.

### 4.2 Job `e2e` — the distributed execution

```yaml
    strategy:
      fail-fast: false  # one persona's result must not hide another's
      matrix:
        include:
          - { label: standard_user-chromium, persona: standard_user, browser: chromium }
          - { label: problem_user-chromium, persona: problem_user, browser: chromium }
          ...
          - { label: standard_user-Pixel-7, persona: standard_user, browser: chromium, device: Pixel 7 }
    env:
      # Matrix values reach the shell through the environment, never by ${{ }} inside a script.
      PERSONA: ${{ matrix.persona }}
      BROWSER: ${{ matrix.browser }}
      DEVICE: ${{ matrix.device }}
```

Each of the 8 jobs: build the image → run the scenarios in it → verify the evidence manifest →
append `traceability.md` and `perf.md` to the job summary → upload `reports/` as
`reports-<label>` with **14-day retention** (`if: always()`, so failed runs keep their evidence).

| AWS reference | Here |
|---|---|
| ECS/Fargate task per shard | one container per matrix job on a fresh runner VM |
| Device Farm | Chromium, Firefox, WebKit + Pixel 7 emulation |
| S3 + lifecycle | artifacts with `retention-days` + SHA-256 manifest |
| CloudWatch | JSON-lines logs, `perf.json`, job summaries |

### 4.3 Job `quality-matrix` — the release view

Downloads every `reports-*` artifact and merges the traceability files:

```bash
python3 -m swaglabs.matrix all-reports/*/traceability.json | tee quality-matrix.md >> "$GITHUB_STEP_SUMMARY"
```

Real output, merged from six local runs on 2026-11-24 (CI adds the Firefox and WebKit columns):

| Requirement | error | glitch | problem | std Pixel 7 | std chromium | visual |
|---|---|---|---|---|---|---|
| REQ-SL-01 log in, land on products | PASS | PASS | PASS | PASS | PASS | PASS |
| REQ-SL-02 bad credentials refused | - | - | - | PASS | PASS | - |
| REQ-SL-04 true name, price, image | PASS | PASS | DEFECT | PASS | PASS | DEFECT |
| REQ-SL-05 sorting | DEFECT | PASS | DEFECT | PASS | PASS | PASS |
| REQ-SL-07 any product added/removed | DEFECT | PASS | DEFECT | PASS | PASS | PASS |
| REQ-SL-12 Reset App State | DEFECT | DEFECT | DEFECT | DEFECT | DEFECT | DEFECT |
| REQ-SL-13 dynamic content | PASS | PASS | PASS | PASS | PASS | PASS |
| REQ-SL-14 time budgets | DEFECT | DEFECT | DEFECT | PASS | PASS | PASS |
| REQ-SL-16 looks right | manual | manual | manual | manual | manual | manual |

*(9 of 16 rows; `-` = NOT RUN in that job: persona-independent scenarios run only for standard_user.)*

```
Known defects observed: SL-01, SL-02, SL-03, SL-04, SL-05, SL-06, SL-07, SL-08, SL-09, SL-10, SL-11, SL-12, SL-14.
Runs with unexpected failures: none.
```

Read it like a release manager: `standard_user` passes everything except the low-risk
REQ-SL-12 on every browser target; the fault personas fail exactly where the register says,
nowhere else. Note REQ-SL-14 for error_user and problem_user: the *sorting budget* scenario
depends on sorting (`@area-sorting`), which they break — the matrix shows the dependency, the
evidence says which finding caused it.

The tool exits **1** if any run has a FAIL — so the release view is itself a gate.

### 4.4 🔴 Pipeline hygiene

| Practice | Line |
|---|---|
| least privilege | `permissions: contents: read` |
| no wasted minutes | `concurrency: cancel-in-progress`; `paths:` filter on `mock-project/**` |
| drift detection | nightly `schedule` — the site can change without a commit of ours |
| no injection | matrix values via `env:`; actionlint + shellcheck check every script |
| polite load | 8 jobs × 4 workers ≤ 32 browsers for ~2 minutes; no load tests |
| evidence integrity | `python3 -m swaglabs.evidence reports` → `evidence intact` or a list of changed/missing files |

---

## Lab tasks — Day 21

| # | Task | Done when |
|---|---|---|
| L21.1 | Spinner, lazy-load and slider scenarios; run them on desktop **and** with `--device "Pixel 7"`. | Both pass 3 times in a row |
| L21.2 | Double-click and two-tab cart scenarios using `eventually`. | Unit tests for `eventually` with a fake clock |
| L21.3 | Budgets + `perf.measure` around login, sort, add, cart, overview, finish. Run as performance_glitch_user. | `perf.md` shows two actions OVER BUDGET, both **client** |
| L21.4 | Cross-check one slow interaction with an independent request timeline. | Your verdict agrees with the timeline (or you found your instrument's bug) |
| L21.5 | Build the image; run unit tests with `--network none`; run one persona with `--read-only`. | Reports on the host; manifest verifies |
| L21.6 | The workflow: quality → matrix → quality-matrix; `actionlint` clean. | A green run, or (without GitHub) `act`-free review: every step explained in your report |

---

## Self-check

1. Why does `eventually` sleep through `page.wait_for_timeout` in browser tests rather than `time.sleep`?
2. Why is "a spinner is shown first" a bad assertion?
3. Which property of the lazy-load test catches a batch that was loaded twice? One that was lost?
4. Why does the slider scenario read the name and the active dot in one `evaluate` call?
5. "Sorting: 5.1 s, network-bound, 0 requests." What do you conclude before anything else?
6. Name four `docker run` flags from today and the property each gives.
7. Why are matrix values passed through `env:` instead of `${{ matrix.persona }}` inside `run:`?
8. The quality-matrix job is red but every e2e job is green. Is that possible? What would it mean?

<details>
<summary>Answers</summary>

1. Playwright's sync API delivers browser events (requests, dialogs) only while a Playwright call runs. `time.sleep` blocks that delivery: listeners fire late and timing data goes wrong; dialogs could stay open.
2. The spinner is visible for about a second; whether the check sees it depends on timing (a race). Assert the end state (spinner hidden, grid visible) and the content.
3. Tile numbering must be exactly 0..n-1: a duplicate batch repeats numbers, a lost batch leaves a gap.
4. Two separate reads can straddle a rotation and disagree although the page is consistent. One `evaluate` reads both at the same instant.
5. That the instrument is wrong: network-bound with no request is a contradiction. Check it against an independent measurement before analysing the product.
6. `--read-only` (isolation), `--tmpfs /tmp` (writable scratch that disappears), `--init` (signals and zombie reaping → recoverable), `--ipc=host` (Chromium stability), `-v reports` (evidence survives), `--network none` (proves offline tests are offline), `--user`/image `USER` (least privilege).
7. To prevent expression injection: `${{ }}` is substituted into the script text before the shell runs. Static matrix values are harmless today, but the habit protects the day a value comes from a branch name or a pull request.
8. Yes, in two cases: a job's evidence was missing or unreadable, or a run reported FAIL in its traceability while pytest still exited 0 (e.g. a misconfigured run). Either way the release view refuses to call it green — that is the point of a gate on the merged evidence.
</details>

---

## Verification log

| Check | Result |
|---|---|
| Dynamic scenarios | pass on Chromium desktop and Pixel 7 emulation (after the scroll fix); WebKit in the container |
| Lazy-load failure on Pixel 7 (before the fix) | reproduced: *no tile should still be a placeholder: not reached within 10 s* |
| performance_glitch_user timings | p50 login 5199 ms, sort 5070 ms; both **client** after the monitor fix; independent timeline: first request 5.05 s after the click |
| Monitor fixes | `window_activity` and browser-timestamp intervals covered by `tests/unit/test_reports.py` |
| Image | built from the pinned digest; `tests/unit` pass inside it with `--read-only --network none` (and refuse to start without a writable `reports/`) |
| Container live runs | Chromium and WebKit suites pass inside the image (this sandbox needed its proxy CA added at run time — a local workaround kept outside the project). Firefox runs only in CI here |
| Workflow | `actionlint` clean; passes the repository's own policy audit (`python -m framework.cloud.audit … --fail-on high`) |
| `python -m swaglabs.matrix` | unit-tested (merge, NOT RUN cells, exit code 1 on any FAIL) |
