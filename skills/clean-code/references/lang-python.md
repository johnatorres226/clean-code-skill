# Clean Python

Python treats readability as a language value, not an add-on — PEP 20 says explicitly that
readability counts and that there should be one obvious way to do it. Clean Python means leaning
into that: idiomatic constructs, type hints on interfaces, small pure functions, and none of the
Java-flavored ceremony that Python doesn't need.

## Contents

- [PEP 8 and PEP 20 in practice](#pep-8-and-pep-20-in-practice)
- [Type hints](#type-hints)
- [Dataclasses over attribute soup](#dataclasses-over-attribute-soup)
- [Idiomatic constructs](#idiomatic-constructs)
- [Comprehensions and generators](#comprehensions-and-generators)
- [Context managers](#context-managers)
- [Errors: EAFP and exception hygiene](#errors-eafp-and-exception-hygiene)
- [Classic Python traps](#classic-python-traps)
- [Functions and modules](#functions-and-modules)
- [Testing](#testing)
- [Worked example](#worked-example)
- [Toolchain](#toolchain)

## PEP 8 and PEP 20 in practice

The non-negotiables: 4-space indentation, `snake_case` for functions and variables, `PascalCase`
for classes, `SCREAMING_SNAKE_CASE` for module constants, `_leading_underscore` for internals,
two blank lines between top-level definitions, imports grouped stdlib / third-party / first-party.

Line length: PEP 8 says 79; most modern projects use 88 (Black's default) or 100. Pick one, put
it in `pyproject.toml`, let the formatter enforce it, never discuss it again.

The PEP 20 lines that do real work in a code review:
- *Explicit is better than implicit* — no `import *`, no magic globals, no clever metaclasses
  where a function works.
- *Flat is better than nested* — guard clauses, early returns, extracted helpers.
- *Errors should never pass silently* — no bare `except`, no empty `except`.
- *If the implementation is hard to explain, it's a bad idea* — the honest test for cleverness.

## Type hints

Type hints are executable documentation. Annotate every public function; the checker then verifies
your docs stay true, and readers stop having to infer shapes from the implementation.

```python
from collections.abc import Iterable, Sequence
from decimal import Decimal

def total_with_tax(
    amounts: Iterable[Decimal],
    *,
    tax_rate: Decimal = Decimal("0.08"),
) -> Decimal:
    """Sum `amounts` and apply `tax_rate`."""
    return sum(amounts, start=Decimal(0)) * (Decimal(1) + tax_rate)
```

Guidance:
- **Accept the widest type, return the narrowest.** Take `Iterable[X]` or `Sequence[X]`, return
  `list[X]`. Callers can then pass whatever they have.
- **Modern syntax**: `list[str]`, `dict[str, int]`, `str | None` — not `List`, `Dict`, `Optional`.
- **`Protocol` for duck-typed interfaces** — structural typing, no inheritance required. This is
  the Pythonic way to define a seam for dependency injection.
- **`Final`, `Literal`, `NewType`** where they add safety:
  `OrderId = NewType("OrderId", str)` makes IDs unswappable.
- **Run `mypy --strict` or `pyright`** in CI. Unchecked hints drift and become lies.

```python
class Clock(Protocol):
    def now(self) -> datetime: ...


class RateProvider(Protocol):
    def current(self) -> dict[str, Decimal]: ...
```
No base class, no registration — anything with the right shape satisfies it, including a
three-line fake in a test.

## Dataclasses over attribute soup

```python
# bad — invisible schema, no validation, no equality, unreadable repr
class Order:
    def __init__(self, id, lines, customer, created):
        self.id = id
        self.lines = lines
        self.customer = customer
        self.created = created
```

```python
# good — schema visible, frozen (hashable, thread-safe), equality and repr for free
@dataclass(frozen=True, slots=True)
class Order:
    id: OrderId
    lines: tuple[LineItem, ...]
    customer: CustomerId
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.lines:
            raise ValueError(f"Order {self.id} must have at least one line item")

    @property
    def subtotal(self) -> Decimal:
        return sum((line.subtotal for line in self.lines), start=Decimal(0))
```

`frozen=True` for value objects (immutability, hashability), `slots=True` for memory and for
catching typo'd attribute assignment. Use a **tuple** rather than a list for a frozen collection
field — a frozen dataclass holding a mutable list isn't actually immutable.

Reach for `NamedTuple` for lightweight positional records, `TypedDict` for JSON-shaped dicts you
can't replace, and Pydantic when you need runtime validation at a system boundary.

## Idiomatic constructs

Non-idiomatic Python is a readability problem even when it works, because it makes readers stop
and check whether something unusual is intended.

```python
# indexing a range instead of iterating
for i in range(len(items)):  items[i].process()      # bad
for item in items:           item.process()          # good

# manual index tracking
i = 0
for item in items: print(i, item); i += 1            # bad
for index, item in enumerate(items): print(index, item)   # good

# parallel indexing of two sequences
for i in range(len(names)): print(names[i], ages[i]) # bad
for name, age in zip(names, ages, strict=True): print(name, age)   # good

# manual membership loop
found = False
for x in items:
    if x == target: found = True; break              # bad
found = target in items                              # good

# verbose truthiness
if len(items) > 0:                                   # bad
if items:                                            # good

# string building in a loop
out = ""
for line in lines: out += line + "\n"                # bad — O(n²)
out = "\n".join(lines)                               # good

# manual dict default
if key not in counts: counts[key] = 0
counts[key] += 1                                     # bad
counts = collections.Counter()                       # good
counts[key] += 1

# comparing to None / booleans
if x == None: ...          if flag == True: ...      # bad
if x is None: ...          if flag: ...              # good

# tuple unpacking and swapping
tmp = a; a = b; b = tmp                              # bad
a, b = b, a                                          # good
```

Also idiomatic and worth reaching for: `pathlib.Path` over `os.path` string surgery, f-strings
over `%` and `.format()`, `enumerate(items, start=1)` for 1-based reporting,
`itertools`/`functools` for pipelines, `match` statements for structural dispatch, and the walrus
operator where it genuinely shortens a read (`if (m := pattern.match(line)):`).

## Comprehensions and generators

A comprehension states a transformation; a loop with `.append()` makes the reader reconstruct it.

```python
active_names = [user.name for user in users if user.is_active]

by_id = {user.id: user for user in users}

# generator: constant memory over a huge file
total_bytes = sum(len(line) for line in file)
```

**Keep them to one level and one condition.** A nested comprehension with two `for`s and an `if`
is a loop wearing a disguise — write the loop, or extract a helper.

```python
# bad — nobody parses this on first read
result = [transform(y) for x in outer if x.ok for y in x.items if y.valid and y.size > 10]

# good
def valid_large_items(container: Container) -> Iterator[Item]:
    for item in container.items:
        if item.valid and item.size > MIN_SIZE:
            yield item

result = [transform(item) for container in outer if container.ok
          for item in valid_large_items(container)]
```

**Generators for streaming.** When the result doesn't need to exist all at once, `yield` keeps
memory flat and lets callers stop early.

```python
def parse_records(path: Path) -> Iterator[Record]:
    """Yield records lazily; the file is closed when iteration finishes or is abandoned."""
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if line.strip():
                yield _parse_line(line, line_number)
```

## Context managers

Any acquire/release pair belongs in a `with`. Write your own rather than pairing calls by hand.

```python
from contextlib import contextmanager

@contextmanager
def acquired(lock: Lock, *, timeout_s: float) -> Iterator[None]:
    """Acquire `lock` or raise TimeoutError; always releases on exit."""
    if not lock.acquire(timeout=timeout_s):
        raise TimeoutError(f"Could not acquire {lock} within {timeout_s}s")
    try:
        yield
    finally:
        lock.release()


with acquired(registry_lock, timeout_s=5.0):
    registry.update(entry)
```

`contextlib.suppress`, `ExitStack`, and `closing` cover most of the rest. Multiple resources go in
one `with`, comma-separated or via parentheses.

## Errors: EAFP and exception hygiene

Python prefers EAFP — try it and handle the failure — over checking first. It avoids the race
between the check and the use, and it reads better.

```python
# LBYL — has a TOCTOU race and reads as noise
if os.path.exists(path):
    with open(path) as f: ...

# EAFP — idiomatic
try:
    with open(path) as f: ...
except FileNotFoundError:
    ...
```

Rules:
- **Catch narrowly.** `except KeyError:` not `except Exception:`, never bare `except:` (which
  swallows `KeyboardInterrupt` and `SystemExit`).
- **Chain causes:** `raise ConfigError(...) from err` preserves the original traceback.
- **Define a module exception hierarchy** so callers can catch at the right granularity:
  ```python
  class BillingError(Exception): ...
  class InvoiceNotFound(BillingError): ...
  class PaymentDeclined(BillingError): ...
  ```
- **Never use `assert` for runtime validation** — `python -O` removes them. Raise a real exception.
- **`else` and `finally` on try** are underused: `else` runs only when no exception occurred,
  which keeps the `try` block down to just the line that can fail.

## Classic Python traps

```python
# 1. Mutable default argument — shared across ALL calls, forever
def add(item, items=[]): ...              # bad
def add(item, items: list | None = None):  # good
    items = [] if items is None else items

# 2. Late-binding closures in a loop — every lambda sees the final i
handlers = [lambda: print(i) for i in range(3)]        # prints 2, 2, 2
handlers = [lambda i=i: print(i) for i in range(3)]    # prints 0, 1, 2

# 3. Mutating a list while iterating it
for item in items:
    if item.stale: items.remove(item)      # silently skips elements
items = [item for item in items if not item.stale]     # good

# 4. Class attributes as instance state — shared by every instance
class Cart:
    items = []                             # bad: one list for the whole class
class Cart:
    def __init__(self) -> None: self.items: list[Item] = []   # good

# 5. `is` for value comparison — works for small ints by accident, then doesn't
if count is 256: ...                       # bad
if count == 256: ...                       # good ( `is` only for None / True / False / sentinels)

# 6. Broad except hiding real bugs
try: value = config[key]
except Exception: value = None             # bad — hides typos, KeyboardInterrupt, everything
except KeyError: value = None              # good
```

## Functions and modules

**Keyword-only arguments** for anything a reader couldn't guess at the call site. The `*` in the
signature makes booleans and options self-documenting, and defuses the flag-argument problem when
the flag is genuinely configuration:

```python
def export(report: Report, *, include_totals: bool = True, encoding: str = "utf-8") -> bytes: ...

export(report, include_totals=False)      # unambiguous; export(report, False) is now impossible
```

**Prefer functions to classes** when there's no state. A class with one method and a constructor
that only stores its arguments is a function with extra steps.

**Module layout:**
```python
"""One-line module summary.

Longer description if the module's purpose isn't obvious from the name.
"""
from __future__ import annotations       # if supporting older versions

import json                               # stdlib
from pathlib import Path

import httpx                              # third-party

from myapp.billing import Invoice         # first-party

MAX_RETRIES: Final = 3                    # constants

# public API, then private helpers below
```

Keep `if __name__ == "__main__":` blocks to a single call into a `main()` function so the module
stays importable and testable.

## Testing

pytest is the default. Plain functions, plain `assert`, fixtures for setup.

```python
import pytest

@pytest.fixture
def repository() -> InMemoryOrderRepository:
    return InMemoryOrderRepository()          # fresh per test — independence for free


def test_confirm_returns_total_including_tax(repository):
    repository.save(an_order(subtotal=Decimal("100.00")))
    service = OrderService(repository, FakeNotifier(), OrderPricing())

    total = service.confirm(OrderId("O-1"), ShippingOption.STANDARD)

    assert total == Decimal("108.00")


def test_confirm_raises_for_unknown_order(repository):
    service = OrderService(repository, FakeNotifier(), OrderPricing())
    with pytest.raises(OrderNotFound, match="O-99"):
        service.confirm(OrderId("O-99"), ShippingOption.STANDARD)


@pytest.mark.parametrize("attempt,expected", [(1, 0.5), (2, 1.0), (3, 2.0)])
def test_backoff_doubles(attempt, expected):
    assert RetryPolicy(max_attempts=5).delay_for(attempt) == expected
```

Prefer hand-written fakes to `unittest.mock` — mocks assert on *how* the code works and break on
every refactor. Use `monkeypatch` for environment and module-level globals, `tmp_path` for files,
`freezegun` or an injected clock for time. Add `hypothesis` for property-based testing where the
input space is large; it finds boundary cases you would never think of.

## Worked example

**Before**
```python
def proc(f, m=0):
    d = open(f).read().split("\n")
    r = []
    t = 0
    for i in range(len(d)):
        if d[i] != "":
            p = d[i].split(",")
            if p[2] == "1":
                v = float(p[0]) * float(p[1])
                if m == 1: v = v * 1.2
                t += v
                r.append(p[0] + " " + p[1] + " " + str(round(v, 2)))
    r.append("TOTAL " + str(round(t, 2)))
    return "\n".join(r)
```
Problems: the file is never closed, one-letter names, index-based iteration, magic column indices,
a magic `1.2`, a flag argument, float for money, four responsibilities, and nothing testable in
isolation.

**After**
```python
"""Billing report rendering."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Iterable, Iterator


class PricingTier(Enum):
    STANDARD = Decimal("1.00")
    PREMIUM = Decimal("1.20")

    def apply(self, amount: Decimal) -> Decimal:
        return amount * self.value


@dataclass(frozen=True, slots=True)
class LineItem:
    quantity: Decimal
    unit_price: Decimal
    is_billable: bool

    @property
    def subtotal(self) -> Decimal:
        return self.quantity * self.unit_price


def read_line_items(path: Path) -> Iterator[LineItem]:
    """Yield line items from a CSV of `quantity,unit_price,billable_flag`."""
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if line.strip():
                yield _parse_line_item(line, line_number)


def _parse_line_item(line: str, line_number: int) -> LineItem:
    try:
        quantity, unit_price, billable = line.strip().split(",")
        return LineItem(Decimal(quantity), Decimal(unit_price), billable == "1")
    except (ValueError, ArithmeticError) as err:
        raise ReportError(f"Malformed line {line_number}: {line.strip()!r}") from err


def render_billing_report(items: Iterable[LineItem], tier: PricingTier) -> str:
    """Render billable `items` priced at `tier`, with a trailing total line."""
    billable = [item for item in items if item.is_billable]
    lines = [_format_line(item, tier) for item in billable]
    total = sum((tier.apply(item.subtotal) for item in billable), start=Decimal(0))
    return "\n".join([*lines, f"TOTAL {total:.2f}"])


def _format_line(item: LineItem, tier: PricingTier) -> str:
    return f"{item.quantity} {item.unit_price} {tier.apply(item.subtotal):.2f}"
```

What improved: the file is closed by the context manager; parsing streams lazily and reports the
offending line number; `Decimal` replaces float for money; the flag argument became an enum that
owns its multiplier; each function does one thing and is testable without touching the filesystem
(`render_billing_report` takes any iterable, so a test passes a list).

## Toolchain

| Purpose | Tool |
|---|---|
| Format + lint | `ruff format` and `ruff check` (replaces black, isort, flake8, most of pylint) |
| Types | `mypy --strict` or `pyright` |
| Tests | `pytest`, `pytest-cov`, `hypothesis` |
| Security | `bandit`, `pip-audit` |
| Hooks | `pre-commit` running all of the above on staged files |
| Env / deps | `uv` or Poetry, with a committed lockfile |

`assets/pyproject.toml` has a working configuration; `bash scripts/setup_toolchain.sh python .`
installs it. Fail CI on lint and type errors — advisory checks get ignored.
