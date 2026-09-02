# Test-Driven Development and Clean Tests

Tests are not a tax on clean code — they are what makes it possible. Without a suite you trust,
you will not refactor; without refactoring, code decays; decayed code is why teams stop shipping.
**Tests keep the code soft.**

That means test code is not second-class. It is production code, held to the same standard.

## Contents

- [The three laws of TDD](#the-three-laws-of-tdd)
- [The cycle in practice](#the-cycle-in-practice)
- [Worked TDD session](#worked-tdd-session)
- [F.I.R.S.T.](#first)
- [One assert concept per test](#one-assert-concept-per-test)
- [Arrange–Act–Assert and the domain-specific test language](#arrangeactassert-and-the-domain-specific-test-language)
- [Naming tests](#naming-tests)
- [What to test: boundaries](#what-to-test-boundaries)
- [Test doubles](#test-doubles)
- [Legacy code: characterization tests](#legacy-code-characterization-tests)
- [Coverage and metrics](#coverage-and-metrics)
- [Framework cheat sheet](#framework-cheat-sheet)

## The three laws of TDD

1. Do not write production code until you have a failing test that requires it.
2. Do not write more of a test than is sufficient to fail — a compile error counts as a failure.
3. Do not write more production code than is sufficient to pass the current failing test.

Followed strictly, these produce a cycle measured in **seconds**, tests that cover essentially
everything, and — the underrated benefit — a design pulled into shape by the constant pressure of
having to instantiate and drive each piece in isolation.

You will not always follow them strictly. That's fine. But when you skip them, know what you're
trading: you're betting you can design better without feedback than with it.

## The cycle in practice

**RED.** Write the smallest test that expresses the next behavior you want.
- Run it. **Watch it fail.** A test you have never seen fail is not a test; it may be asserting
  nothing at all.
- Check the failure *message*. If it doesn't tell you what went wrong, improve it now — you will
  read it fifty more times.

**GREEN.** Write the least code that makes it pass.
- Hardcoding a return value is legitimate here. The next test will force generalization. This
  feels wrong the first ten times and then becomes obviously correct.
- Do not design ahead. Do not add the parameter you "know" you'll need. YAGNI.

**REFACTOR.** With the suite green, clean up.
- Clean the production code: extract, rename, dedupe, reduce nesting.
- **Clean the tests too.** Duplication in tests is duplication; a 60-line setup block is a smell.
- Run the tests after each small move. Green between every step.

**This third step is where the design happens.** Teams that skip it write TDD-shaped code that is
just as tangled as untested code, then conclude the practice doesn't work. It's the refactoring
that pays.

## Worked TDD session

Requirement: a `RetryPolicy` that decides whether to retry, with exponential backoff and a cap.

**Cycle 1 — the simplest thing that could be true**

```python
# test_retry_policy.py
def test_first_attempt_is_always_retried():
    policy = RetryPolicy(max_attempts=3)
    assert policy.should_retry(attempt=1) is True
```
Fails: `RetryPolicy` doesn't exist. Now the minimum:
```python
class RetryPolicy:
    def __init__(self, max_attempts: int) -> None:
        self._max_attempts = max_attempts

    def should_retry(self, attempt: int) -> bool:
        return True                      # hardcoded on purpose — no test demands more
```
Green.

**Cycle 2 — force the generalization**

```python
def test_does_not_retry_past_max_attempts():
    policy = RetryPolicy(max_attempts=3)
    assert policy.should_retry(attempt=3) is False
```
Red. Minimum change:
```python
    def should_retry(self, attempt: int) -> bool:
        return attempt < self._max_attempts
```
Green. The hardcode is gone, driven out by a test rather than by speculation.

**Cycle 3 — the boundary, deliberately**

```python
@pytest.mark.parametrize("attempt,expected", [(1, True), (2, True), (3, False), (4, False)])
def test_retry_decision_at_and_around_the_limit(attempt, expected):
    assert RetryPolicy(max_attempts=3).should_retry(attempt) is expected
```
Green already — and that's fine. This test documents the boundary and will catch a future
off-by-one. Trivial tests are worth writing.

**Cycle 4 — new behavior: backoff**

```python
def test_backoff_doubles_each_attempt():
    policy = RetryPolicy(max_attempts=5, base_delay_s=0.5)
    assert policy.delay_for(attempt=1) == 0.5
    assert policy.delay_for(attempt=2) == 1.0
    assert policy.delay_for(attempt=3) == 2.0


def test_backoff_is_capped():
    policy = RetryPolicy(max_attempts=10, base_delay_s=0.5, max_delay_s=2.0)
    assert policy.delay_for(attempt=9) == 2.0
```
Red, then:
```python
    def delay_for(self, attempt: int) -> float:
        exponential = self._base_delay_s * (2 ** (attempt - 1))
        return min(exponential, self._max_delay_s)
```
Green.

**REFACTOR** — now clean. Extract the doubling into a named expression, add type hints and a
docstring that states the contract, make the class frozen since it holds no mutable state:

```python
@dataclass(frozen=True)
class RetryPolicy:
    """Decides whether and how long to wait before retrying an operation.

    Attempts are 1-based. Delay grows exponentially from `base_delay_s`,
    clamped to `max_delay_s`.
    """
    max_attempts: int
    base_delay_s: float = 0.5
    max_delay_s: float = 30.0

    def should_retry(self, attempt: int) -> bool:
        return attempt < self.max_attempts

    def delay_for(self, attempt: int) -> float:
        exponential_delay = self.base_delay_s * 2 ** (attempt - 1)
        return min(exponential_delay, self.max_delay_s)
```
Run the suite. Still green. **That confidence is the entire product of the practice.**

Note what did *not* happen: no jitter, no logging, no metrics, no `Clock` injection. None of those
were required by a test, so none were built. When they're needed, a test will demand them.

## F.I.R.S.T.

**Fast.** Slow tests don't get run; unrun tests don't catch anything, and rot sets in unnoticed.
Unit tests should be milliseconds. If a test needs a database or the network, it is an integration
test — valuable, but keep it in a separate, slower suite so the fast suite stays fast.

**Independent.** No test depends on another's side effects or on ordering. Shared mutable
fixtures cause the cascade where one failure produces forty red tests and no information. Build
fresh state per test.

**Repeatable.** Same result on a laptop, in CI, offline, on a Friday, in any timezone. That means
injecting the clock, seeding randomness, and never depending on wall time or network availability.

```java
// bad — fails at midnight, fails in another timezone, fails on Feb 29
assertEquals(LocalDate.now().plusDays(30), subscription.expiryDate());

// good — clock injected, result deterministic
Clock clock = Clock.fixed(Instant.parse("2026-03-01T00:00:00Z"), ZoneOffset.UTC);
Subscription subscription = new Subscription(clock, Period.ofDays(30));
assertEquals(LocalDate.parse("2026-03-31"), subscription.expiryDate());
```

**Self-validating.** A boolean outcome. No reading log output, no comparing files by eye. A test
that requires interpretation will eventually be interpreted wrong.

**Timely.** Written just before the production code. Written after, tests tend to confirm what the
code *does* rather than what it *should do* — and by then the code is often hard to test, which is
exactly the design feedback you missed.

## One assert concept per test

The goal is a test that **fails for exactly one reason**. Multiple asserts are acceptable when
they check facets of one concept; they are not acceptable when they check unrelated behaviors,
because the first failure hides the rest.

```java
// bad — two behaviors, one test. If parsing breaks you never learn whether formatting works.
@Test
void testInvoice() {
    Invoice inv = Invoice.parse(RAW);
    assertEquals(3, inv.lineCount());
    assertEquals("2026-01-05", inv.date().toString());
    inv.addLine(new Line("Shipping", money("5.00")));
    assertEquals("$105.00", inv.render());
    assertTrue(inv.isModified());
}

// good — separate concepts, each failing for one reason
@Test
void parses_all_line_items() { ... }

@Test
void parses_invoice_date() { ... }

@Test
void rendering_includes_added_lines() { ... }

@Test
void adding_a_line_marks_the_invoice_modified() { ... }
```

Facets of one concept in one test is fine:
```python
def test_parsed_address_has_all_components():
    address = parse_address("221B Baker St, London, NW1 6XE")
    assert address.street == "221B Baker St"
    assert address.city == "London"
    assert address.postcode == "NW1 6XE"
```

## Arrange–Act–Assert and the domain-specific test language

Make the three phases visible. A reader should see the setup, the single action under test, and
the verification at a glance.

```cpp
TEST(RingBufferTest, PopReturnsBytesInInsertionOrder) {
    // Arrange
    io::RingBuffer buffer(4);
    buffer.push(0xAA);
    buffer.push(0xBB);

    // Act
    const auto first  = buffer.pop();
    const auto second = buffer.pop();

    // Assert
    EXPECT_EQ(first,  std::optional<std::uint8_t>{0xAA});
    EXPECT_EQ(second, std::optional<std::uint8_t>{0xBB});
}
```

When setup gets repetitive, **build a small testing API** — helper functions and builders written
for the tests, which turn a wall of construction into a sentence. This is a domain-specific
language that grows with the suite, and it is one of the highest-value investments in a codebase.

```java
// before — 12 lines of construction noise per test, repeated 40 times
Customer c = new Customer();
c.setId("C-1"); c.setTier(Tier.GOLD); c.setCountry("GB");
Order o = new Order(); o.setCustomer(c); o.addLine(new Line("SKU-9", 2, money("10.00")));
// ...

// after — intent-revealing builders written for the tests
Order order = anOrder()
        .forCustomer(aCustomer().gold().in("GB"))
        .withLine("SKU-9", quantity(2), price("10.00"))
        .build();

assertThat(pricing.total(order)).isEqualTo(money("18.00"));   // gold = 10% off
```

Test helper code may be less efficient than production code — it runs in a test environment, not a
tight loop. Optimize it for readability without apology.

## Naming tests

The name is the specification. Someone reading the list of test names should learn what the unit
does without opening the bodies.

```
<unit>_<behavior>_<condition>
```

| Bad | Good |
|---|---|
| `test1` | `pop_raises_when_buffer_is_empty` |
| `testWithdraw` | `withdraw_fails_when_amount_exceeds_balance` |
| `TestParserWorks` | `Parse_ReturnsError_WhenHeaderVersionIsUnsupported` |
| `test_edge_case` | `delay_for_is_clamped_to_max_delay` |

Conventions differ by ecosystem — `snake_case` in Python and often C++, `camelCase` or
`should_...` in Java, `Method_Scenario_Expectation` in some C++ shops. Pick one, apply it
everywhere.

## What to test: boundaries

Bugs cluster at edges. Enumerate them deliberately rather than testing three random happy paths.

For any input, test: **zero / empty**, **one**, **many**, **maximum**, **max ± 1**, **negative**,
**null / None / nullptr**, **duplicate**, **out of order**, **unicode and empty string**,
**overflow**, and **concurrent access** where relevant.

```python
@pytest.mark.parametrize("value,expected", [
    (0, "0 bytes"),
    (1, "1 byte"),                       # singular boundary
    (1023, "1023 bytes"),
    (1024, "1.0 KiB"),                   # unit boundary
    (1025, "1.0 KiB"),
    (1024**5, "1024.0 TiB"),             # top of the unit table
])
def test_format_bytes_at_unit_boundaries(value, expected):
    assert format_bytes(value) == expected


def test_format_bytes_rejects_negative():
    with pytest.raises(ValueError, match="negative"):
        format_bytes(-1)
```

Additional rules worth keeping:
- **Exhaustively test near a bug.** Bugs cluster; when you find one, test its whole neighborhood.
- **Patterns of failure are revealing.** If the failures form a shape (all lengths > 255, all
  inputs with a hyphen), the shape names the bug.
- **A disabled test is an unanswered question.** Either fix it or delete it and file the ambiguity
  as an issue. `@Ignore`/`@pytest.mark.skip` with no comment is a lie of omission.

## Test doubles

| Kind | What it does | Use when |
|---|---|---|
| **Dummy** | Passed but never used | Filling a required parameter |
| **Stub** | Returns canned answers | The unit needs input from a collaborator |
| **Fake** | Working lightweight implementation (in-memory repo) | Best default — real behavior, no I/O |
| **Spy** | Records calls for later assertion | You must verify an interaction happened |
| **Mock** | Pre-programmed with expectations, fails on mismatch | Rare; use sparingly |

**Prefer fakes and stubs over mocks.** Heavy mocking couples tests to the *implementation* — the
exact call sequence — so every refactor breaks tests even when behavior is unchanged. That's the
opposite of what the suite is for. Assert on observable outcomes, not on internal calls, unless
the interaction genuinely *is* the behavior (e.g. "an audit record must be written").

```python
# brittle — asserts how, not what. Renaming or reordering internals breaks it.
def test_charges_customer(mocker):
    gateway = mocker.Mock()
    Checkout(gateway).submit(order)
    gateway.charge.assert_called_once_with("C-1", 100, currency="GBP", idempotency_key=ANY)

# robust — a fake with real behavior; asserts the outcome
def test_successful_checkout_marks_order_paid():
    gateway = FakeGateway(approve=True)
    order = an_order(total=money("100.00"))

    Checkout(gateway).submit(order)

    assert order.status is Status.PAID
    assert gateway.total_charged == money("100.00")
```

## Legacy code: characterization tests

When you inherit untested code you must change, do not start by cleaning. Start by pinning
behavior — including behavior that looks wrong.

1. Find a seam: a place you can inject a dependency or intercept a call without restructuring.
2. Write a test asserting whatever the code currently does. Run it; if it fails, correct the
   *test* to match reality. You are documenting, not judging.
3. Repeat until the behavior you're about to touch is covered.
4. Now refactor, with the net underneath.
5. Only then change behavior — in a separate commit, with a test that fails first.

If the code resists testing (statics, globals, constructors doing I/O, `new` in the middle of
business logic), the smallest safe first step is usually **extract-and-inject**: pull the
untestable dependency into a parameter or constructor argument, changing nothing else.

## Coverage and metrics

Coverage is a **diagnostic instrument, not a target**. Use it to find branches nobody thought
about; do not use it as a KPI, because the fastest way to hit a coverage number is to write tests
that assert nothing.

Read coverage reports for *shape*: an untested `else`, an uncovered error path, a whole module at
0%. Those are questions worth asking. Branch coverage tells you more than line coverage. Mutation
testing (PIT for Java, `mutmut`/`cosmic-ray` for Python) tells you more than either, because it
measures whether your assertions actually catch changes.

Test suite speed is worth tracking too — a suite that creeps past a couple of minutes stops being
run on every save, and the tight feedback loop that makes TDD work quietly dies.

## Framework cheat sheet

**Python — pytest**
```python
import pytest

@pytest.fixture
def repository() -> InMemoryRepository:
    return InMemoryRepository()          # fresh per test — independence for free

def test_saved_invoice_can_be_retrieved(repository):
    invoice = an_invoice(id="INV-1")
    repository.save(invoice)
    assert repository.find("INV-1") == invoice

def test_find_raises_for_unknown_id(repository):
    with pytest.raises(NotFound, match="INV-99"):
        repository.find("INV-99")
```
Run: `pytest -q`, `pytest --cov=myapp --cov-branch`, `pytest -x --ff` for fast feedback.

**Java — JUnit 5 + AssertJ**
```java
class RetryPolicyTest {
    @Test
    void doesNotRetryPastMaxAttempts() {
        RetryPolicy policy = new RetryPolicy(3);
        assertThat(policy.shouldRetry(3)).isFalse();
    }

    @ParameterizedTest
    @CsvSource({"1,0.5", "2,1.0", "3,2.0"})
    void backoffDoublesEachAttempt(int attempt, double expectedSeconds) {
        assertThat(new RetryPolicy(5, 0.5).delayFor(attempt))
                .isEqualTo(expectedSeconds);
    }

    @Test
    void rejectsNonPositiveMaxAttempts() {
        assertThatThrownBy(() -> new RetryPolicy(0))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("max_attempts");
    }
}
```

**C++ — GoogleTest**
```cpp
TEST(RetryPolicyTest, DoesNotRetryPastMaxAttempts) {
    const RetryPolicy policy{/*max_attempts=*/3};
    EXPECT_FALSE(policy.should_retry(3));
}

class BackoffTest : public testing::TestWithParam<std::pair<int, double>> {};

TEST_P(BackoffTest, DoublesEachAttempt) {
    const auto [attempt, expected] = GetParam();
    EXPECT_DOUBLE_EQ(RetryPolicy{5, 0.5}.delay_for(attempt), expected);
}

INSTANTIATE_TEST_SUITE_P(Exponential, BackoffTest,
                         testing::Values(std::pair{1, 0.5}, std::pair{2, 1.0},
                                         std::pair{3, 2.0}));
```
Build with sanitizers in CI: `-fsanitize=address,undefined` for unit tests, `-fsanitize=thread`
for the concurrency suite.

**C — Unity / CMocka / plain asserts**
```c
static void test_ring_buffer_pop_returns_insertion_order(void) {
    ring_buffer *rb = ring_buffer_create(4);
    TEST_ASSERT_NOT_NULL(rb);

    TEST_ASSERT_EQUAL_INT(0, ring_buffer_push(rb, 0xAA));
    TEST_ASSERT_EQUAL_INT(0, ring_buffer_push(rb, 0xBB));

    uint8_t byte = 0;
    TEST_ASSERT_EQUAL_INT(0, ring_buffer_pop(rb, &byte));
    TEST_ASSERT_EQUAL_HEX8(0xAA, byte);

    ring_buffer_destroy(rb);
}
```
Run the C suite under Valgrind or ASan — in C, a passing test that leaks or corrupts memory is not
a passing test.

## Related heuristics

`smells-catalog.md`: **T1–T9** (insufficient tests, use a coverage tool, don't skip trivial tests,
an ignored test is a question, test boundary conditions, exhaustively test near bugs, patterns of
failure are revealing, coverage patterns are revealing, tests should be fast), **E2** (tests
require more than one step).
