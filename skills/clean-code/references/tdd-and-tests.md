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
- [Running the suite](#running-the-suite)

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

```
test first_attempt_is_always_retried:
    assert RetryPolicy(max_attempts=3).should_retry(attempt=1) == true
```
Fails: `RetryPolicy` doesn't exist. Now the minimum:
```
class RetryPolicy(max_attempts):
    function should_retry(attempt):
        return true                      # hardcoded on purpose — no test demands more
```
Green.

**Cycle 2 — force the generalization**

```
test does_not_retry_past_max_attempts:
    assert RetryPolicy(max_attempts=3).should_retry(attempt=3) == false
```
Red. Minimum change: `return attempt < max_attempts`. Green. The hardcode is gone, driven out by
a test rather than by speculation.

**Cycle 3 — the boundary, deliberately**

```
test retry_decision_at_and_around_the_limit, for (attempt, expected) in
        [(1, true), (2, true), (3, false), (4, false)]:
    assert RetryPolicy(max_attempts=3).should_retry(attempt) == expected
```
Green already — and that's fine. This test documents the boundary and will catch a future
off-by-one. Trivial tests are worth writing.

**Cycle 4 — new behavior: backoff**

```
test backoff_doubles_each_attempt:
    policy = RetryPolicy(max_attempts=5, base_delay_s=0.5)
    assert [policy.delay_for(a) for a in 1..3] == [0.5, 1.0, 2.0]

test backoff_is_capped:
    policy = RetryPolicy(max_attempts=10, base_delay_s=0.5, max_delay_s=2.0)
    assert policy.delay_for(attempt=9) == 2.0
```
Red, then the least code that passes. Green.

**REFACTOR** — now clean. Name the doubling, document the contract, make the type immutable
since it holds no mutable state:

```
# Decides whether and how long to wait before retrying an operation.
# Attempts are 1-based. Delay grows exponentially from base_delay_s, clamped to max_delay_s.
immutable type RetryPolicy(max_attempts, base_delay_s = 0.5, max_delay_s = 30.0):
    function should_retry(attempt):
        return attempt < max_attempts

    function delay_for(attempt):
        exponential_delay = base_delay_s * 2 ** (attempt - 1)
        return min(exponential_delay, max_delay_s)
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

```
# bad — fails at midnight, in another timezone, on Feb 29
assert subscription.expiry_date() == today() + days(30)

# good — clock injected, result deterministic
clock = FixedClock("2026-03-01T00:00:00Z")
subscription = Subscription(clock, period=days(30))
assert subscription.expiry_date() == date("2026-03-31")
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

```
# bad — two behaviors, one test. If parsing breaks you never learn whether rendering works.
test invoice:
    invoice = Invoice.parse(RAW)
    assert invoice.line_count() == 3
    assert invoice.date() == "2026-01-05"
    invoice.add_line(Line("Shipping", money("5.00")))
    assert invoice.render() == "$105.00"
    assert invoice.is_modified()

# good — separate concepts, each failing for one reason
test parses_all_line_items: ...
test parses_invoice_date: ...
test rendering_includes_added_lines: ...
test adding_a_line_marks_the_invoice_modified: ...

# fine — facets of ONE concept in one test
test parsed_address_has_all_components:
    address = parse_address("221B Baker St, London, NW1 6XE")
    assert (address.street, address.city, address.postcode) ==
           ("221B Baker St", "London", "NW1 6XE")
```

## Arrange–Act–Assert and the domain-specific test language

Make the three phases visible. A reader should see the setup, the single action under test, and
the verification at a glance.

```
test pop_returns_bytes_in_insertion_order:
    buffer = RingBuffer(capacity=4)          # arrange
    buffer.push(0xAA)
    buffer.push(0xBB)

    first, second = buffer.pop(), buffer.pop()   # act

    assert (first, second) == (0xAA, 0xBB)   # assert
```

When setup gets repetitive, **build a small testing API** — helper functions and builders written
for the tests, which turn a wall of construction into a sentence. This is a domain-specific
language that grows with the suite, and it is one of the highest-value investments in a codebase.

```
# before — 12 lines of construction noise per test, repeated 40 times
c = Customer(); c.id = "C-1"; c.tier = GOLD; c.country = "GB"
o = Order(); o.customer = c; o.add_line(Line("SKU-9", 2, money("10.00")))
# ...

# after — intent-revealing builders written for the tests
order = an_order()
    .for_customer(a_customer().gold().in("GB"))
    .with_line("SKU-9", quantity(2), price("10.00"))
    .build()

assert pricing.total(order) == money("18.00")   # gold = 10% off
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

Casing follows the ecosystem. Pick one pattern and apply it everywhere.

## What to test: boundaries

Bugs cluster at edges. Enumerate them deliberately rather than testing three random happy paths.

For any input, test: **zero / empty**, **one**, **many**, **maximum**, **max ± 1**, **negative**,
**null / absent**, **duplicate**, **out of order**, **unicode and empty string**,
**overflow**, and **concurrent access** where relevant.

```
test format_bytes_at_unit_boundaries, for (value, expected) in [
        (0, "0 bytes"),
        (1, "1 byte"),                   # singular boundary
        (1023, "1023 bytes"),
        (1024, "1.0 KiB"),               # unit boundary
        (1025, "1.0 KiB"),
        (1024**5, "1024.0 TiB")]:        # top of the unit table
    assert format_bytes(value) == expected

test format_bytes_rejects_negative:
    assert raises(InvalidArgument, matching="negative"): format_bytes(-1)
```

Additional rules worth keeping:
- **Exhaustively test near a bug.** Bugs cluster; when you find one, test its whole neighborhood.
- **Patterns of failure are revealing.** If the failures form a shape (all lengths > 255, all
  inputs with a hyphen), the shape names the bug.
- **A disabled test is an unanswered question.** Either fix it or delete it and file the ambiguity
  as an issue. A skip marker with no comment is a lie of omission.

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

```
# brittle — asserts how, not what. Renaming or reordering internals breaks it.
test charges_customer:
    gateway = Mock()
    Checkout(gateway).submit(order)
    assert gateway.charge called once with ("C-1", 100, currency="GBP", idempotency_key=ANY)

# robust — a fake with real behavior; asserts the outcome
test successful_checkout_marks_order_paid:
    gateway = FakeGateway(approve=true)
    order = an_order(total=money("100.00"))

    Checkout(gateway).submit(order)

    assert order.status == PAID
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
testing tells you more than either, because it
measures whether your assertions actually catch changes.

Test suite speed is worth tracking too — a suite that creeps past a couple of minutes stops being
run on every save, and the tight feedback loop that makes TDD work quietly dies.

## Running the suite

The repo's standards config names the test command, the fast-suite filter, and the coverage
command; use those rather than guessing framework flags. Run memory-unsafe code under the
platform's sanitizers or memory checker — a passing test that leaks or corrupts memory is not a
passing test.

## Related heuristics

`smells-catalog.md`: **T1–T9** (insufficient tests, use a coverage tool, don't skip trivial tests,
an ignored test is a question, test boundary conditions, exhaustively test near bugs, patterns of
failure are revealing, coverage patterns are revealing, tests should be fast), **E2** (tests
require more than one step).
