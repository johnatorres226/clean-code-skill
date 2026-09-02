# Naming

Naming is the cheapest documentation you will ever write and the most expensive to get wrong.
A wrong name costs every future reader a wrong mental model, silently, forever.

## Contents

- [The test](#the-test)
- [Core rules](#core-rules)
- [Scope determines length](#scope-determines-length)
- [Grammar by kind](#grammar-by-kind)
- [Anti-patterns](#anti-patterns)
- [Casing conventions by language](#casing-conventions-by-language)
- [Naming worked examples](#naming-worked-examples)
- [Vocabulary: pick one word per concept](#vocabulary-pick-one-word-per-concept)

## The test

A name passes if a competent stranger, reading only the name and its type, can predict:

1. **What it holds or does**
2. **When it is valid or applicable**
3. **What it will not do** (no surprise side effects)

If you need a comment to answer any of those, rename instead of commenting.

## Core rules

**1. Reveal intent, not mechanics.**

```python
# bad — mechanics, requires a comment
d = 0          # elapsed time in days

# good — the name is the comment
elapsed_days = 0
```

**2. Avoid disinformation.** Do not call something a `List` unless it is one. `accountList` for a
`Map` is a lie. `hp`, `aix`, `sco` look like variables but are platform names. Do not use names
that differ only in a character or two — `XYZControllerForEfficientHandlingOfStrings` vs.
`XYZControllerForEfficientStorageOfStrings` is a bug waiting to be committed.

**3. Make meaningful distinctions.** If two things need different names, they need different
*meanings*. `a1`, `a2` are number-series naming. `ProductInfo`, `ProductData`, `ProductObject`
are noise-word naming — the reader cannot tell which to call. If you cannot articulate the
difference, there probably shouldn't be two of them.

**4. Use pronounceable names.** `genymdhms` cannot be discussed in a meeting.
`generation_timestamp` can. Code is a social artifact.

**5. Use searchable names.** A bare `7` in a codebase is unfindable; `MAX_RETRY_ATTEMPTS = 7` is
one grep away. Single letters are acceptable only as short-scope loop indices.

**6. Avoid encodings.** No Hungarian notation (`strName`, `iCount`, `pNode`), no `m_` member
prefixes, no `I` prefix on interfaces. These date from weakly-typed languages and dumb editors;
today they are noise that goes stale when the type changes.

```java
// bad
public interface IShapeFactory { Shape m_createShape(String strKind); }

// good — if you must distinguish, encode the *implementation*, not the interface
public interface ShapeFactory { Shape createShape(String kind); }
final class ShapeFactoryImpl implements ShapeFactory { ... }
```

**7. Avoid mental mapping.** The reader should not have to hold a translation table. `r` meaning
"the lowercased URL with the host stripped" is a mapping; `stripped_url` is a name.

**8. Names must describe side effects.** `getOrCreateInstance()` is honest;
`getInstance()` that quietly constructs is not. `save()` that also mutates the argument should be
named for both — or, better, should stop doing both.

**9. Add context, but not gratuitous context.** `state` alone is ambiguous; `address_state` or a
member of an `Address` class is clear. But in a project called Gas Station Deluxe, prefixing
every class with `GSD` is a search-destroying tax.

**10. Prefer domain language.** If the traders say "notional", the class is `Notional`, not
`AmountHolder`. Where the concept genuinely *is* a CS pattern, the CS name is free documentation:
`AccountVisitor`, `JobQueue`, `ConnectionPool`.

## Scope determines length

The longer a name lives and the further it travels, the more it must carry.

| Scope | Guidance | Example |
|---|---|---|
| 1–5 line loop / lambda | 1 char fine | `for (int i = 0; i < n; ++i)` |
| Small function local | 1 word | `total`, `row`, `parsed` |
| Long function local | phrase | `unmatched_invoice_lines` |
| Member / field | phrase, no prefix | `retry_budget` |
| Public API / constant | fully explicit | `DEFAULT_CONNECT_TIMEOUT_MS` |
| Package / module | short, ubiquitous | `billing`, `net`, `parser` |

The inverse holds for classes: a class used everywhere should have a *short* name, because you
type it constantly. `File`, `Instant`, `Path`. Long class names often signal a class doing too much.

## Grammar by kind

| Kind | Grammar | Examples |
|---|---|---|
| Class / struct / type | noun phrase | `InvoiceLine`, `RetryPolicy`, `PayrollCalculator` |
| Function / method | verb phrase | `parse_header`, `computeTax`, `flush()` |
| Predicate (bool) | `is/has/can/should/needs` | `is_expired`, `hasPendingWrites`, `can_retry` |
| Getter / accessor | noun or `get`-noun (per language) | `name()`, `getName()`, `@property name` |
| Mutator | `set`/verb | `set_timeout`, `withdraw` |
| Factory | `create`/`make`/`from` | `create_session`, `Instant.from(...)` |
| Converter | `to`/`as` | `to_json`, `asList` |
| Constant | noun, SCREAMING_SNAKE (most langs) | `MAX_PAYLOAD_BYTES` |
| Enum type / values | singular noun / noun-ish | `Color.RED`, `State.PENDING` |
| Unit-bearing value | append the unit | `timeout_ms`, `distance_km`, `size_bytes` |

**Always append units to numeric quantities.** A staggering share of production incidents are
seconds-vs-milliseconds. `timeout` is a bug; `timeout_ms` is not. Better still, use a type:
`Duration`, `std::chrono::milliseconds`, `datetime.timedelta`.

## Anti-patterns

| Anti-pattern | Why it hurts | Fix |
|---|---|---|
| `data`, `info`, `manager`, `processor`, `helper`, `util` | Says nothing; often hides a missing abstraction | Name the actual responsibility (`InvoiceRenderer`, not `InvoiceHelper`) |
| `temp`, `tmp`, `foo`, `result2` | Zero intent | Name what it holds at that moment |
| Abbreviations (`cust`, `acct`, `mgr`) | Ambiguous, unsearchable | Spell it out; modern editors complete |
| Cute names / jokes (`whack()` for `kill()`) | Culture- and mood-dependent | Say what it means |
| Puns (`add` for both "sum" and "append") | Same word, different concept | Different concepts get different words |
| Negative booleans (`is_not_ready`) | `if (!is_not_ready)` is a headache | `is_ready` |
| Type names in variables (`account_list`) | Rots when the type changes | `accounts` |
| Numbered series (`a1`, `a2`) | Reader must diff | Name the roles (`source`, `destination`) |

## Casing conventions by language

Follow the ecosystem, not a personal preference. Consistency with the platform is itself clarity.

**C**
```c
typedef struct ring_buffer ring_buffer;      /* snake_case types */
int  ring_buffer_push(ring_buffer *rb, uint8_t byte);   /* module_noun_verb */
#define RING_BUFFER_CAPACITY 4096            /* SCREAMING_SNAKE macros */
static size_t head_index;                    /* snake_case */
```
C has no namespaces, so **prefix every exported symbol with the module name**. That prefix is your
namespace and it is not optional in a shared codebase.

**C++**
```cpp
class ConnectionPool {                       // PascalCase types
public:
    void acquire_connection();               // snake_case (STL-style) or camelCase — pick one
private:
    std::size_t active_count_ = 0;           // trailing underscore for members is acceptable
};
constexpr int kMaxRetries = 3;               // or MAX_RETRIES; be consistent
namespace billing::detail { }                // lowercase namespaces
```
Both STL-style `snake_case` and Google/Qt-style `camelCase` members are defensible. What is not
defensible is mixing them inside one codebase.

**Java**
```java
public final class RetryPolicy {             // PascalCase
    private static final int MAX_ATTEMPTS = 3;   // SCREAMING_SNAKE constants
    private final Duration backoff;          // camelCase fields, no m_ prefix
    public boolean shouldRetry(int attempt) { ... }   // camelCase methods
}
package com.example.billing;                 // lowercase, reverse-domain packages
```

**Python**
```python
MAX_ATTEMPTS = 3                             # module constant
class RetryPolicy:                           # PascalCase
    def should_retry(self, attempt: int) -> bool:   # snake_case
        ...
    def _compute_backoff(self) -> float:     # single underscore = internal
        ...
```
A single leading underscore means "not part of the public API"; respect it as a contract. Double
leading underscore triggers name mangling and is for avoiding subclass collisions only — do not
use it as "private".

## Naming worked examples

**Before (C++)**
```cpp
// returns the list of things that are ok
std::vector<Rec> proc(const std::vector<Rec>& v, int t) {
    std::vector<Rec> r;
    for (const auto& x : v) if (x.f > t && !x.d) r.push_back(x);
    return r;
}
```
Every name forces a lookup and the comment is doing the work the names should do.

**After**
```cpp
std::vector<Record> select_active_above_threshold(
        const std::vector<Record>& records, int score_threshold) {
    std::vector<Record> selected;
    for (const Record& record : records) {
        if (record.score > score_threshold && !record.is_deleted) {
            selected.push_back(record);
        }
    }
    return selected;
}
```
The comment is gone because it is redundant. That is the goal.

**Before (Python)**
```python
def chk(u, d):
    if u.t + d < time.time():
        return False
    return True
```

**After**
```python
def is_session_still_valid(session: Session, lifetime_seconds: float) -> bool:
    expires_at = session.created_at + lifetime_seconds
    return time.time() < expires_at
```
Note three separate wins: the predicate name reads as the condition at the call site
(`if is_session_still_valid(...)`), the unit is in the parameter name, and the extracted
`expires_at` variable explains the arithmetic without a comment.

## Vocabulary: pick one word per concept

Maintain a project glossary — even three lines in the README — and hold the line on it.

| Concept | Pick exactly one | Do not also use |
|---|---|---|
| Retrieve from store | `fetch` | `get`, `retrieve`, `load`, `read`, `pull` |
| Persist | `save` | `store`, `persist`, `write`, `commit` |
| Remove | `delete` | `remove`, `destroy`, `erase`, `purge` |
| Build a new instance | `create` | `make`, `new`, `build`, `construct` |
| Convert | `to_x` | `as_x`, `x_of`, `convert_to_x` |

The exception: when two words genuinely mean different things, keep both and *document the
distinction* — e.g. `delete` (soft, sets a flag) vs. `purge` (hard, removes the row). Consistent
vocabulary is what lets a reader navigate an unfamiliar module by guessing method names correctly.

## Related heuristics

See `smells-catalog.md`, entries **N1–N7** (descriptive names, appropriate abstraction level,
standard nomenclature, unambiguity, long names for long scopes, no encodings, describe side
effects) and **G20** (function names should say what they do).
