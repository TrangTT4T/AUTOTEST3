# Unit 1 · Day 4 — BDD Framework Review: Maintainability, Traceability, Duplication, Improvement Actions

| | |
|---|---|
| **Course** | Advanced Automation Test Engineering (ATEST03) — Fast Track |
| **Learning outcomes** | **LO1** — Evaluate risk and testability to define the strategy (Bloom **B5: Evaluate**) · **LO2** — Implement maintainable, traceable BDD specifications (Bloom **B3: Apply**) |
| **Format** | Guides/Review · Hybrid · 60 minutes |
| **System under review** | The Day 3 framework (`day3-code/shop-bdd.zip`) |
| **Improved framework** | `day4-code/shop-bdd.zip` — the same framework after this review's improvement actions |
| **Output of the day** | A **review report**: rubric scores with evidence, findings, a prioritised improvement backlog, before/after measurements, and an updated risk register |

> **What was verified.** Every number, finding, and output in this guide comes from running the tools on the real Day 3 framework, then on the improved version (see the Verification log at the end). The improved framework passed **20 of 20 automated scenarios and 21 of 21 page-object tests on the live store** (plus the expected `xfail` for a known shop defect).

---

## How to use this guide

Days 1–3 built a framework. Day 4 asks: **is it good, and how do we know?** You will learn to review a test framework the way a senior engineer does — with measurements, a rubric, evidence for every claim, and actions that are re-measured.

| Badge | Level | After this level you can… |
|---|---|---|
| 🟢 | **Foundation** | Explain what a framework review is and write a finding that someone can act on |
| 🟡 | **Practitioner** | Run the measurement tools and score a framework with the rubric |
| 🔴 | **Senior** | Separate real problems from tool noise, prove a finding, prioritise and implement improvements, re-measure, and re-evaluate the test strategy |

### Session plan (60 min)

| Time | Activity | Part |
|---|---|---|
| 0–10 | What a review is; how to write a finding | 1 |
| 10–25 | Measure: run the tools, read the numbers | 2 |
| 25–40 | Assess: rubric scores and findings (worked review) | 3 |
| 40–50 | Improve: prioritise, act, re-measure | 4 |
| 50–60 | Re-evaluate the Day 1 strategy with Day 3 evidence (LO1) | 5 |

In the hybrid session, pairs review each other's frameworks with Part 6's protocol; this guide's worked review (Part 3) is the model answer.

---

## Glossary

| Term | Meaning | Vietnamese |
|---|---|---|
| Code review | Reading code to find problems and improvements before they cost more | Review mã |
| Rubric | A table of criteria and quality levels used to score consistently | Bảng tiêu chí chấm |
| Finding | One observed problem (or strength), with evidence and a recommendation | Phát hiện |
| Evidence | Something anyone can check: a command output, a file and line, a failing test | Bằng chứng |
| Severity | How much harm a finding can cause | Mức nghiêm trọng |
| Maintainability | How cheaply the framework can be changed and extended | Khả năng bảo trì |
| Traceability | Linking requirement ↔ scenario ↔ result | Khả năng truy vết |
| Duplication | The same knowledge written in more than one place | Trùng lặp |
| Ambiguous step | A Gherkin step that more than one step definition matches | Step mơ hồ |
| False positive | A tool warning that is not a real problem | Cảnh báo sai |
| Fitness function | An automated test that checks an architecture rule | Hàm kiểm tra kiến trúc |
| Technical debt | Known shortcuts that make future changes more expensive | Nợ kỹ thuật |
| Backlog | The prioritised list of improvement actions | Danh sách việc cần làm |
| Re-measure | Running the same measurement after a change to prove it helped | Đo lại |

---

## Part 1 — What a framework review is 🟢

### 1.1 Why review test code at all?

A test framework is code that a whole team depends on. When it is hard to change, people stop adding tests. When it lies (green when the product is broken, red when it is fine), people stop trusting it. Both failures are silent — nobody files a bug against the test suite. A review is how you find them early.

A review is **not** a second round of testing the product. It asks four questions about the framework itself:

| Question | Today's lens |
|---|---|
| Can we change it safely and cheaply? | **Maintainability** |
| Can we prove which requirement each result belongs to? | **Traceability** |
| Is each piece of knowledge written once? | **Duplication** |
| Does it tell the truth, reliably? | **Reliability and diagnosability** |

### 1.2 Three rules of a good review

1. **Evidence, not opinion.** "The steps feel messy" is an opinion. "`python -m framework.review` reports 1 ambiguous step at `features/cart.feature:35`" is evidence.
2. **About the code, not the person.** Write "this step pattern matches two definitions", never "you wrote it wrong".
3. **Prioritised.** Ten equal comments are noise. Say which one matters most, and why.

### 1.3 How to write a finding

Every finding has the same seven parts:

| Part | Question it answers |
|---|---|
| **ID** | How do we refer to it? (`F-01`) |
| **Observation** | What exactly is wrong (or right)? |
| **Evidence** | How can anyone check it? |
| **Impact** | What harm can it cause? |
| **Recommendation** | What should change? |
| **Severity** | High / Medium / Low / Info |
| **Effort** | S (< 1 h) / M (< 1 day) / L (more) |

**Weak finding:**

> Steps are confusing, please clean up.

**Strong finding:**

> **F-01 — Ambiguous step via a greedy placeholder.** `the cart contains 1 "Noir jacket" in variant "L / Red"` matches two definitions because `"{name}"` also matches text that contains quotes. *Evidence:* review tool, `features/cart.feature:35`; renaming one placeholder made a different scenario fail. *Impact:* an innocent refactor silently changes which code runs. *Recommendation:* a shared `Quoted` type for every quoted placeholder, plus a rule in the review tool. *Severity:* High. *Effort:* S.

The strong finding can be checked, understood, and acted on by someone who was not in the room.

### 1.4 Severity scale

| Severity | Meaning | Example |
|---|---|---|
| **High** | Tests can lie, or a change can silently break them | Ambiguous step, validator that never fires |
| **Medium** | Costs time on every change, or hides information | Technical detail in Gherkin, a rule only written in a document |
| **Low** | Small cost, easy to live with for a while | A function a bit too complex |
| **Info** | Worth knowing; also used for **strengths** to keep | "No duplicated code blocks found" |

A senior review always lists strengths too: they tell the team what *not* to change.

> **Checkpoint 1.** Rewrite this as a strong finding: *"The 404 test looks a bit technical."* (Answer in Part 3, F-02.)

---

## Part 2 — Measure before you judge 🟡

### 2.1 Six lenses and their tools

| Lens | Question | Tool | Command |
|---|---|---|---|
| Maintainability | Clean, typed, simple, layered? | ruff, mypy, McCabe complexity, architecture tests | `ruff check .` · `mypy` · `ruff check --select C901 .` · `pytest tests/unit/test_architecture.py` |
| Traceability | Every requirement covered and tagged correctly? | Registry, tag rules, matrix, coverage gate | `pytest --store fake --fail-on-uncovered` |
| Duplication (steps) | Is each step written once, and does each Gherkin line have exactly one definition? | **BDD review tool** (new today) | `python -m framework.review` |
| Duplication (code) | Copy-pasted Python? | pylint duplicate-code | `pylint --disable=all --enable=duplicate-code --min-similarity-lines=4 framework tests` |
| Gherkin quality | Declarative, short, one behaviour each? | BDD review tool | `python -m framework.review` |
| Reliability and diagnosability | Stable live? Failures explain themselves? | Live runs, traceability statuses, evidence folder | `pytest tests/test_*.py -m "not manual"` · `pytest tests/pages` |

### 2.2 The BDD review tool

`framework/review.py` reads the step definitions (with Python's `ast`, without importing them) and the feature files (with the official Gherkin parser), then matches every Gherkin step against every definition — the same matching pytest-bdd performs at runtime, but done **statically and completely**.

| It reports | Why it matters |
|---|---|
| Usage count per step definition, reuse ratio | Shows which steps carry the suite and which are one-offs |
| **Unused** definitions | Dead code that still has to be maintained |
| **Undefined** steps (outside `@manual`) | A scenario that would fail at runtime |
| **Ambiguous** steps | More than one definition matches: which code runs is decided by accident |
| **Near-duplicate** definitions | *Candidates* for merging — a person decides |
| Gherkin **smells** | Imperative wording, hard-coded money, too many steps, several `When`s, no `Then`, greedy placeholders |
| Requirements without scenarios | Coverage gaps against `requirements.toml` |

```bash
python -m framework.review
```

```bash
python -m framework.review --strict
```

It prints a Markdown report and writes `reports/bdd-review.md`. With `--strict` it exits 1 on any problem, so CI can enforce it. Near-duplicates never fail the build: they are judgement calls.

### 2.3 The measurements of the Day 3 framework

Real output of the first run (before any change):

| Metric | Value |
|---|---|
| Scenarios (as written / executed) | 18 / 22 |
| Steps per scenario (avg / max) | 3.5 / 6 |
| Step definitions | 36 |
| Step uses (in scenarios as written) | 58 |
| Reuse ratio (uses / definitions) | 1.61 |
| Unused definitions | 0 |
| Undefined steps | 6 |
| Ambiguous steps | **1** |
| Near-duplicate definition pairs | 4 |
| Gherkin smells | 1 |
| Requirements without scenarios | 0 |

The other tools:

| Tool | Result |
|---|---|
| `ruff check`, `ruff format --check`, `mypy --strict` | Clean |
| pylint duplicate-code (≥ 4 similar lines) | **Nothing found** |
| McCabe complexity > 7 | `tag_problems` = 9, `review` = 8 (ruff's default limit is 10) |
| Unit tests | 48 passed |
| Traceability | 9/9 requirements covered; REQ-08 manual |
| Live runs (Day 3) | 20/20 scenarios, 19 page tests + 1 expected xfail; two runs interrupted by bot protection / HTTP 429, both classified `BLOCKED` |
| Page-object methods exercised by tests | 82 of 91 |

### 2.4 Reading the numbers: tools find candidates, people decide

The tool raised 12 items. Before writing findings, each must be judged:

| Tool output | Judgement | Why |
|---|---|---|
| 6 undefined steps | **False positive** | All in `@manual` scenarios (REQ-08), which are skipped by design. The tool was improved to report them separately |
| 1 ambiguous step | **Real — High** | Proven in §3.3 |
| 4 near-duplicate pairs | 3 false positives, 1 judgement call | §3.4 |
| 1 imperative smell ("HTTP status 404") | **Real — Medium** | A protocol detail in a business specification |

A reviewer who copies all 12 items into the report wastes everyone's time; one who ignores the tool misses the High finding. The skill is in the judgement.

> **Checkpoint 2.** The reuse ratio is 1.58–1.61. Is that bad? (Hint: in BDD, many `Then` steps are legitimately specific. See answer guide, question 3.)

---

## Part 3 — Assess: the rubric and the worked review 🔴

### 3.1 The rubric

Seven criteria, four levels. Score each with evidence; a score without evidence does not count.

| Criterion | 1 — Initial | 2 — Developing | 3 — Proficient | 4 — Senior |
|---|---|---|---|---|
| **A. Specification quality** (Gherkin) | Imperative, UI words, long scenarios | Mostly declarative; some UI or data details | Declarative, one behaviour each, rules grouped | Plus: smells measured automatically; manual gaps written as Gherkin with reasons |
| **B. Step design and duplication** | Copy-pasted steps; selectors in steps | Parameterised; some near-duplicates | Thin, typed steps; no undefined/unused steps | Plus: no ambiguity possible (typed placeholders); usage measured and enforced in CI |
| **C. Architecture and maintainability** | One layer; selectors everywhere | Page objects exist but leak | Layers (spec / steps / port / adapters / pages) respected | Plus: layer rules enforced by fitness tests; lint and strict types clean |
| **D. Traceability** | No link from test to requirement | Tags by convention | Registry + tag rules + matrix | Plus: `NOT COVERED` visible, coverage gate in CI, risk tags checked against the registry |
| **E. Reliability** | `sleep`, shared state, flaky | Some explicit waits | Waits for proof; fresh state per test | Plus: environment failures classified (`BLOCKED`); known defects as strict `xfail`; low-load design |
| **F. Diagnosability** | "Test failed" only | Screenshots | Business-step logs, screenshots, traces | Plus: per-step evidence with browser diagnostics; failure messages show the whole state |
| **G. Framework quality gates** | None | Lint only | Lint, types, unit tests | Plus: framework logic in pure functions, unit- and architecture-tested; all gates in CI |

### 3.2 Scores for the Day 3 framework

| Criterion | Score | Evidence |
|---|---|---|
| A. Specification quality | **3** | 0 too-long scenarios (max 6 steps), 1 imperative smell (F-02); manual gaps written as Gherkin with reasons |
| B. Step design and duplication | **2** | 0 unused, 0 real undefined — but **1 ambiguous step** whose outcome depends on alphabetical order (F-01) |
| C. Architecture and maintainability | **3** | Layers respected, ruff/mypy clean, no duplicated code; but layer rules exist only in the README (F-04) |
| D. Traceability | **4** | Registry, automatic tag rules (risk checked against the registry), matrix with `NOT COVERED`, coverage gate in CI |
| E. Reliability | **4** | No sleeps; `expect_response` after every change; `BLOCKED` classification proven live (Cloudflare, HTTP 429); strict `xfail` for the mini-cart defect |
| F. Diagnosability | **4** | Step logs, per-step PNG + JSON with console errors and failed shop requests, Playwright traces |
| G. Framework quality gates | **3** | Lint, strict types, 48 unit tests, CI — but the BDD layer itself is not checked by any gate (F-01 slipped through) |
| **Total** | **23 / 28** | |

A score of 4 in Reliability, but 2 in Step design, is a useful shape: the framework is **trustworthy today**, and **fragile to change**. That points the improvement work exactly at B and C.

### 3.3 F-01 (High): the ambiguous step — proving a finding

A tool warning is a hypothesis. A senior reviewer **proves** it before rating it High.

**Observation.** Two step definitions:

```python
@then(parsers.parse('the cart contains {quantity:d} "{name}"'))
@then(parsers.parse('the cart contains {quantity:d} "{name}" in variant "{variant}"'))
```

The Gherkin line `the cart contains 1 "Noir jacket" in variant "L / Red"` matches **both**: in the first pattern, `"{name}"` happily matches `Noir jacket" in variant "L / Red` — quotes included.

**Experiment 1 — swap the two definitions in the file.** Still green. So the order in the file does not decide.

**Experiment 2 — read the source.** In pytest-bdd 9, `find_fixturedefs_for_step` collects *every* matching definition and registers them all under one fixture name; pytest then uses the last one. "Last" follows the alphabetical order of the generated fixture names, which contain the pattern text. The longer pattern sorts after its own prefix, so it happened to win.

**Experiment 3 — an innocent refactor.** Rename the placeholder `{name}` to `{product}` in the generic step only (a pure readability change):

```
E       AssertionError: expected 1 x Noir jacket" in variant "L / Red, cart: 1 x Noir jacket (L / Red); total £60.00
E        +  where 0 = quantity_of('Noir jacket" in variant "L / Red')
```

A **different** scenario breaks, with a baffling message, because `{p…}` now sorts after `{n…}` and the generic step wins.

**Impact.** Which code runs for a Gherkin line is decided by an accident of spelling. Any rename can silently change it.

**Recommendation (implemented in Part 4).** A shared `Quoted` type that cannot cross a quote, used by every quoted placeholder; a review-tool rule that flags untyped quoted placeholders; the review in CI with `--strict`.

### 3.4 The other findings

| ID | Severity | Observation | Evidence | Recommendation | Effort |
|---|---|---|---|---|---|
| **F-01** | High | Ambiguous step through a greedy `"{name}"` placeholder | §3.3 | `Quoted` type, review rule, review in CI | S |
| **F-02** | Medium | `Then the not-found page is shown with HTTP status 404` puts a protocol detail in a business spec | Review tool: imperative smell, `features/navigation.feature:27` | Write behaviour ("the visitor sees the not-found page"); check the status inside the step | S |
| **F-03** | Low | 4 near-duplicate step candidates | Review tool, similarity 0.85–0.94 | Judged one by one: "try to add" is a different behaviour (returns a result); "add these products:" takes a table; "add the product … N times" vs "add the product" — merging would need a regex with an optional part and make the Gherkin less readable. **Decision: keep all four**, recorded here so the next reviewer does not reopen it | — |
| **F-04** | Medium | Layer rules (no Playwright in steps, selectors only in page objects, no sleeps) are only written in the README | README §Layer rules; no test enforces them | Architecture fitness tests in `tests/unit/test_architecture.py` | S |
| **F-05** | Low | 5 safe page-object methods never executed by any test: `Breadcrumb.current`, `MiniCart.is_open`, `MiniCart.remove`, `Shop.article`, `ArticlePage.open_article` | Static usage count: 82 of 91 public methods exercised | Page-object tests for them | S |
| **F-06** | Low | Two functions above complexity 7 (`tag_problems` 9, `review` 8) | `ruff check --select C901` | Accept for now (below the default 10, fully unit-tested); split if they grow | — |
| **F-07** | Medium | Live reliability limited by the environment: Cloudflare verification and HTTP 429 interrupted runs | `BLOCKED` results, Day 3 and Part 10 runs | A test environment the team controls (staging, or an allow-list for the CI runner's address) | L |
| **F-08** | Medium | REQ-08 (accounts) cannot be automated on the public shop: CAPTCHA, and a wrong password showed no message | Reconnaissance, Day 3 Part 10 | Same test environment, with CAPTCHA disabled for test accounts | L |
| **F-09** | Low | The CI workflow has never run on GitHub | Validated locally only | Push to a repository and run it once | S |
| **F-10** | Info — **strength** | No duplicated Python code ≥ 4 lines; 0 unused steps; all 9 requirements covered | pylint, review tool, matrix | Keep: these are the result of the layering — protect them with the gates | — |
| **F-11** | Info — **strength** | Environment failures and product defects are reported separately, and proved live | `BLOCKED` on HTTP 429; strict `xfail` for the mini-cart | Keep | — |

**Product defects found along the way** belong in a separate report for the shop's developers, not in the framework backlog: the mini-cart is not refreshed after an AJAX add; hidden duplicate cart rows with duplicate ids; unlabeled quantity, registration, and recovery fields; duplicated ids in the registration form.

---

## Part 4 — Improve: prioritise, act, re-measure 🔴

### 4.1 Prioritise by impact and effort

```
                 Effort S                         Effort L
Impact high  │  DO NOW: F-01, F-04, F-02       │  PLAN: F-07, F-08
Impact low   │  QUICK WINS: F-05, F-09         │  ACCEPT: F-06 (and F-03, decided)
```

### 4.2 The improvement backlog

| ID | Action | Status |
|---|---|---|
| F-01 | `framework/step_types.py`: `Quoted` type and `parsed()` helper; every step pattern converted; review rule `greedy-placeholder`; regression unit test | **Done** |
| F-02 | Gherkin reworded; HTTP status asserted in the step | **Done** |
| F-04 | 9 architecture fitness tests | **Done** |
| F-05 | 2 new page-object tests and 1 extended test covering the 5 methods | **Done** (87 of 91 exercised; the other 4 must not run on a public shop) |
| — | Review tool: `@manual` steps reported separately, near-duplicates never fail `--strict`; tool unit-tested (9 tests) | **Done** |
| — | CI: `python -m framework.review --strict` in the `quality` job | **Done** |
| F-09 | Run the CI workflow on GitHub once | Planned — needs a repository |
| F-07, F-08 | Owned test environment without bot protection or CAPTCHA | Planned — needs the shop owner |
| F-06 | Split complex functions if they grow | Accepted |

### 4.3 The fix for F-01

`framework/step_types.py`:

```python
class _Quoted:
    """parse type: any text without a double quote (what ``@parse.with_pattern`` would build)."""

    pattern = r'[^"]*'

    def __call__(self, text: str) -> str:
        return text


STEP_TYPES = {"Quoted": _Quoted()}


def parsed(pattern: str) -> parsers.parse:
    """A pytest-bdd parse pattern that knows the shared types."""
    return parsers.parse(pattern, extra_types=STEP_TYPES)
```

Steps now read:

```python
@then(parsed('the cart contains {quantity:d} "{name:Quoted}"'))
def cart_contains(store: Store, quantity: int, name: str) -> None:
```

The regression test that keeps it fixed (`tests/unit/test_review.py`):

```python
def test_quoted_placeholders_no_longer_clash() -> None:
    """Regression test for the Day 4 finding: "{name}" swallowed '... in variant "L / Red'."""
    defs = step_definitions(STEPS_SOURCE, "steps.py")[:3]
    result = review(defs, [_scenario(_use("then", 'the cart contains 1 "Noir jacket" in variant "L / Red"'))])
    assert result.ambiguous == []
    assert result.usage[defs[2]] == 1
```

Why a class instead of `@parse.with_pattern`? The `parse` library has no type information, so the decorator would make the function untyped under `mypy --strict`. The class does exactly what the decorator does (it carries a `pattern` attribute) and stays fully typed.

### 4.4 The fix for F-04: rules that fail the build

`tests/unit/test_architecture.py` turns the README's layer rules into tests:

| Test | Rule |
|---|---|
| `test_steps_use_only_the_port_and_the_domain` (one per step module) | Steps import neither Playwright nor any adapter |
| `test_core_does_not_depend_on_tools` (domain, ports, errors) | The core imports neither Playwright nor pytest |
| `test_selectors_live_only_in_pages_and_components` | `locator(...)`, `get_by_*(...)` only in page objects and components — with a written allow-list (`guard.py` reads the whole page body to detect bot checks) |
| `test_no_sleep_anywhere` | No `sleep` or `wait_for_timeout` anywhere |

Proof that they bite — two violations injected on purpose:

```
E       AssertionError: tests/steps/cart_steps.py imports {'playwright.sync_api'}: steps must talk to the Store port only
E       AssertionError: selectors outside page objects:
E         framework/adapters/web/store.py:57 .locator(...)
```

### 4.5 Re-measure

The same tools, after the changes:

| Metric | Before | After |
|---|---|---|
| Ambiguous steps | **1** | **0** |
| Undefined steps (outside `@manual`) | 6 reported (false positives) | 0 (6 `@manual` steps reported separately) |
| Gherkin smells | 1 | 0 |
| Near-duplicate candidates | 4 | 4 (judged: keep) |
| `python -m framework.review --strict` | exit 1 | **exit 0** |
| Unit tests | 48 | **66** (incl. 9 for the review tool, 9 architecture) |
| Page-object methods exercised | 82 / 91 | **87 / 91** |
| Page-object tests (live) | 19 + 1 xfail | **21 + 1 xfail** |
| BDD scenarios (live) | 20 / 20 | **20 / 20** (rerun after every step pattern changed) |
| CI `quality` gate | lint, types, tests | + BDD review `--strict` |

Updated rubric: **B: 2 → 4** (typed placeholders, review enforced in CI), **C: 3 → 4** (fitness tests), **G: 3 → 4** (the BDD layer now has its own gate), **A: 3 → 4** (smells measured and enforced). **Total: 23 → 28 / 28.**

The score is not the goal; the re-measurement is. Without it, "we fixed it" is another opinion.

---

## Part 5 — Re-evaluate the strategy with evidence (LO1) 🔴

Day 1 scored risks and testability **before** any test existed. Day 3 produced evidence. An Evaluate-level tester updates the strategy when the evidence disagrees with the assumptions.

### 5.1 What the evidence changed

| Day 1 assumption | Day 3 evidence | Strategy change |
|---|---|---|
| REQ-08 testability "poor (CAPTCHA likely)" | Confirmed: CAPTCHA scripts; a wrong password returned silently | Stays `@manual`; automation **planned** for an owned test environment (F-08) |
| Automation access "poor for login and checkout" | Checkout was reachable and its summary readable without entering data | REQ-07 scope **raised**: checkout summary vs cart now automated |
| Cart (REQ-04) likelihood 4 | A real cart defect found (mini-cart stale after AJAX add); hidden duplicate rows | Keep likelihood 4; add the mini-cart to the cart's scope (page test + strict xfail) |
| Determinism "medium" | Prices and stock were stable during the project; catalogue snapshot recorded | Keep runtime data; add the **snapshot facts** unit tests as an early warning of change |
| Environment risk not listed | Cloudflare and HTTP 429 interrupted live runs | **New risk:** "automation blocked by the environment" — likelihood 3, impact 4 (score 12, Medium) |

### 5.2 The updated risk register (changes only)

| Item | L | I | Score | Level | Change |
|---|---|---|---|---|---|
| REQ-04 cart correctness, **including mini-cart** | 4 | 5 | 20 | High | Scope widened |
| REQ-07 reach checkout **and summary matches cart** | 2 | 5 | 10 | Medium | Scope widened, automated |
| REQ-08 sign up / log in | 2 | 4 | 8 | Medium | Testability confirmed poor; manual until owned environment |
| **ENV-01** automation blocked by bot protection / rate limits | 3 | 4 | 12 | Medium | **New** — mitigations: serial live runs, low-load design, `BLOCKED` classification, owned environment |

### 5.3 Updated exit criteria

| Day 1 exit criterion | Day 4 version |
|---|---|
| All `@risk-high` scenarios automated and passing | Unchanged |
| Every requirement has a scenario or a `@manual` tag with a reason | Now **enforced** by `--fail-on-uncovered` and the tag rules |
| Zero flaky failures in 3 consecutive runs | A `BLOCKED` run does not count; it is rerun later |
| — | **New:** `python -m framework.review --strict` passes (no ambiguous, undefined, or unused steps; no smells) |
| — | **New:** architecture fitness tests pass |

---

## Part 6 — Running a peer review (hybrid session) 🟡

### 6.1 Roles

| Role | Does |
|---|---|
| **Author** | Shows the framework, answers questions, does not defend |
| **Reviewer** | Runs the tools, scores with the rubric, writes findings |
| **Scribe** | Records findings in the template (Appendix A); can be the reviewer in pairs |

### 6.2 Protocol (40 minutes for one framework)

1. **5 min — Author's tour.** Folder layout, how to run, anything unfinished.
2. **10 min — Measure.** Reviewer runs every command from §2.1 and saves the outputs.
3. **15 min — Assess.** Score the rubric; turn tool output into findings (judge every item; prove the High ones).
4. **10 min — Agree actions.** Prioritise together (§4.1); the author owns the backlog.

### 6.3 Etiquette

- Comment on code, not on people: "this step…", never "you…".
- Every claim has evidence; if you cannot show it, ask a question instead.
- Name at least two strengths.
- The author decides how to fix; the reviewer decides whether the evidence is convincing.

---

## Appendix A — Review report template

```markdown
# Framework review — <project> — <date>

Reviewer: <name> · Author: <name> · Version reviewed: <commit or zip name>

## 1. Measurements
| Tool | Command | Result |
|---|---|---|
| ruff / mypy | `ruff check . && mypy` | |
| BDD review | `python -m framework.review` | |
| Code duplication | `pylint --disable=all --enable=duplicate-code --min-similarity-lines=4 framework tests` | |
| Complexity | `ruff check --select C901 .` | |
| Offline suite | `pytest --store fake -n auto --fail-on-uncovered` | |
| Live suite | `pytest tests/test_*.py -m "not manual"` and `pytest tests/pages` | |

## 2. Rubric
| Criterion | Score (1-4) | Evidence |
|---|---|---|
| A. Specification quality | | |
| B. Step design and duplication | | |
| C. Architecture and maintainability | | |
| D. Traceability | | |
| E. Reliability | | |
| F. Diagnosability | | |
| G. Framework quality gates | | |

## 3. Findings
| ID | Severity | Observation | Evidence | Recommendation | Effort |
|---|---|---|---|---|---|

## 4. Strengths to keep

## 5. Improvement backlog
| ID | Action | Owner | Status |
|---|---|---|---|

## 6. Re-measurement after the changes
| Metric | Before | After |
|---|---|---|

## 7. Strategy / risk register changes
```

## Appendix B — Command cheat-sheet

| Goal | Command |
|---|---|
| BDD review report | `python -m framework.review` |
| BDD review as a gate | `python -m framework.review --strict` |
| Architecture fitness tests | `pytest tests/unit/test_architecture.py` |
| All framework unit tests | `pytest tests/unit` |
| Code duplication | `pylint --disable=all --enable=duplicate-code --min-similarity-lines=4 framework tests` |
| Complexity above 7 | `ruff check --select C901 --config 'lint.mccabe.max-complexity = 7' .` |
| Full offline gate (as CI) | `ruff check . && ruff format --check . && mypy && python -m framework.review --strict && pytest --store fake -n auto --fail-on-uncovered` |

`pylint` is a review-time tool, not a project dependency: install it when you need it (`pip install pylint`).

---

## Self-check (answers below — try first)

1. What are the seven parts of a finding, and which part turns an opinion into a finding?
2. The review tool reported 6 undefined steps. Why were they not findings, and what did the tool change?
3. The reuse ratio is about 1.6. Is that a problem?
4. How was F-01 proven, and why was "swap the definitions in the file" not enough?
5. Why do near-duplicates never fail `--strict`, while ambiguous steps do?
6. Why turn README rules into architecture tests, and how do you know those tests work?
7. The rubric total went from 23 to 28. Why does the guide say the score is not the goal?
8. Which Day 1 assumption did the evidence overturn, and what changed in the strategy?

<details>
<summary><b>Answer guide</b></summary>

1. ID, observation, evidence, impact, recommendation, severity, effort. **Evidence** — something anyone can check — turns an opinion into a finding.
2. All six were in `@manual` scenarios, skipped by design. Reporting them as problems would teach the team to ignore the tool. The tool now lists them separately as "not automated, by design" and does not count them as problems.
3. Not by itself. `Given`/`When` steps should be reused heavily (the empty-cart step is used 7 times); many `Then` steps legitimately check one specific outcome. Watch the trend and the near-duplicates, not the ratio alone.
4. By experiments: the swap stayed green (so file order is not the rule); reading pytest-bdd's source showed that the definition is chosen by the alphabetical order of generated names; renaming one placeholder then broke a different scenario. The swap alone would have suggested "no problem" — a negative experiment proves little.
5. Ambiguity is objectively wrong (a Gherkin line must have exactly one meaning). Near-duplicates are judgement calls: three of the four were different behaviours or inputs. Failing the build on judgement calls produces noise and workarounds.
6. Rules that only live in documents erode silently. Tests fail the build the moment a rule is broken. They were proven by injecting two violations (a Playwright import in a step file, a locator in `store.py`) and watching them fail.
7. Because a score can be gamed; the re-measurement with the same tools shows what actually changed (ambiguous 1 → 0, strict review exit 1 → 0, 48 → 66 unit tests, 82 → 87 methods exercised), and that live results stayed 20/20.
8. "Checkout is poor for automation" — the checkout summary turned out to be reachable and readable without entering data, so REQ-07's automated scope grew. Also new: an environment risk (bot protection / rate limits) entered the register with mitigations.
</details>

---

## Verification log

| Check | Result |
|---|---|
| Review tool, first run on the Day 3 framework | Output in §2.3 (1 ambiguous, 6 undefined, 4 near-duplicate pairs, 1 smell) |
| F-01 experiment 1: swap definition order | Still passed |
| F-01 experiment 2: pytest-bdd 9.0.1 source | `find_fixturedefs_for_step` collects all matches; the last registered wins |
| F-01 experiment 3: rename `{name}` → `{product}` | `test_adding_a_chosen_variant…` failed with the message shown in §3.3 |
| pylint duplicate-code (≥ 4 lines) | Nothing found |
| Complexity > 7 | `tag_problems` 9, `review` 8 |
| Architecture tests with two injected violations | Both failed with the messages in §4.4; 9 passed on the real code |
| After the changes: `ruff`, `ruff format --check`, `mypy --strict` | Clean (68 source files) |
| After: `python -m framework.review --strict` | Exit 0; metrics in §4.5 |
| After: unit tests | 66 passed |
| After: `pytest --store fake -n auto --fail-on-uncovered` | 86 passed, 24 skipped (2 manual + 22 live-only page tests), exit 0 |
| After: live BDD (`pytest tests/test_*.py -m "not manual"`) | **20 passed** in 79 s |
| After: live page-object tests (`pytest tests/pages`) | **21 passed, 1 xfailed** in 56 s |
| CI workflow | YAML validated with the new review step; **not run on GitHub** (F-09) |
| Versions | Python 3.13; pytest 9.2.0, pytest-bdd 9.0.1, Playwright 1.63.0, ruff 0.17.5, mypy 2.4.1, pylint 4.1.4 (review-time only) |
