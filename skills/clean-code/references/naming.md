# Naming

Naming is the cheapest documentation you will ever write and the most expensive to get wrong.
A wrong name costs every future reader a wrong mental model, silently, forever.

## Contents

- [The test](#the-test)
- [Core rules](#core-rules)
- [Scope determines length](#scope-determines-length)
- [Grammar by kind](#grammar-by-kind)
- [Anti-patterns](#anti-patterns)
- [Casing](#casing)
- [Worked example](#worked-example)
- [Vocabulary: pick one word per concept](#vocabulary-pick-one-word-per-concept)

## The test

A name passes if a competent stranger, reading only the name and its type, can predict:

1. **What it holds or does**
2. **When it is valid or applicable**
3. **What it will not do** (no surprise side effects)

If you need a comment to answer any of those, rename instead of commenting.

## Core rules

**1. Reveal intent, not mechanics.**

```
d = 0              # bad — mechanics, requires a comment: elapsed time in days
elapsed_days = 0   # good — the name is the comment
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
today they are noise that goes stale when the type changes. If you must distinguish an interface
from its implementation, encode the *implementation*: `ShapeFactory` and `ShapeFactoryImpl`, not
`IShapeFactory`.

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
| 1–5 line loop / lambda | 1 char fine | `for i in range(n)` |
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
a `Duration` type.

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

## Casing

Follow the ecosystem's casing, not a personal preference — consistency with the platform is
itself clarity. The repo's linter config is the authority; don't restate it here. Two rules hold
everywhere:

- **Never mix conventions inside one codebase.** Two defensible styles mixed is worse than either.
- **Where the language has no namespaces, prefix every exported symbol with its module name**
  (`ring_buffer_push`). That prefix *is* the namespace.

A leading-underscore or `internal` marker means "not public API"; respect it as a contract.

## Worked example

```
# before — every name forces a lookup, and the comment does the names' job
# returns the list of things that are ok
function proc(v, t):
    return [x for x in v if x.f > t and not x.d]

# after — the comment is gone because it is redundant
function select_active_above_threshold(records, score_threshold):
    return [r for r in records if r.score > score_threshold and not r.is_deleted]

# before
function chk(u, d):
    if u.t + d < now(): return false
    return true

# after
function is_session_still_valid(session, lifetime_seconds):
    expires_at = session.created_at + lifetime_seconds
    return now() < expires_at
```

Three wins in the second pair: the predicate reads as the condition at the call site
(`if is_session_still_valid(...)`), the unit is in the parameter name, and the extracted
`expires_at` explains the arithmetic without a comment.

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
