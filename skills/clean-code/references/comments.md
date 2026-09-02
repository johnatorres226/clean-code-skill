# Comments

> The proper use of comments is to compensate for our failure to express ourselves in code.

Every comment is a small admission that the code did not carry its own meaning. Sometimes that
admission is honest and necessary. Usually it is not.

Comments also **rot**. Code gets refactored; the comment three lines above it does not. An
outdated comment actively misleads — it is worse than silence, because the reader trusts it. The
only comment guaranteed accurate is the one that doesn't exist.

## Contents

- [The decision procedure](#the-decision-procedure)
- [Good comments](#good-comments)
- [Bad comments](#bad-comments)
- [API documentation](#api-documentation)
- [Comment style by language](#comment-style-by-language)
- [Worked examples](#worked-examples)

## The decision procedure

Before writing any comment, run this in order. Stop as soon as one works.

**1. Can a better name remove the need?**
```c
// bad
// check if the employee is eligible for full benefits
if (employee.flags & HOURLY_FLAG && employee.age > 65) { ... }

// good
if (employee_is_eligible_for_full_benefits(employee)) { ... }
```

**2. Can an extracted function remove the need?**
If you are about to write `// now validate the header`, you are about to name a function.
Extract it, call it `validate_header()`, delete the comment.

**3. Can an explanatory variable remove the need?**
```python
# bad
# ensure the discount doesn't exceed the order total
if amount > 0 and amount <= total * 0.5 and customer.tier >= 2:

# good
is_positive        = amount > 0
is_within_cap      = amount <= total * MAX_DISCOUNT_FRACTION
is_eligible_tier   = customer.tier >= Tier.SILVER
if is_positive and is_within_cap and is_eligible_tier:
```

**4. Is the comment apologizing for a design flaw?**
`// this is a hack because the API is broken` — fix the design, or wrap the broken API behind a
clean adapter and comment *there*, once.

**5. Only now: write the comment — and explain *why*, not *what*.**

The code already states what happens. The reader can see the loop. What they cannot see is the
reasoning, the constraint, the incident that made this necessary. That is what you owe them.

## Good comments

These earn their place.

**Legal / provenance.** Copyright headers, license identifiers, attribution for adapted
algorithms. Keep them short; point to the LICENSE file rather than pasting a full license.

```java
// Copyright (c) 2026 Example Corp. Licensed under Apache-2.0; see LICENSE.
```

**Explanation of intent / rationale.** The decision behind the code.

```python
# We poll instead of using inotify because the data directory is an NFS mount
# and inotify does not fire for changes made by other hosts. See INFRA-4127.
```

**Warning of consequences.** Protects the next person from an expensive mistake.

```cpp
// Not thread-safe: mutates the shared cache without locking. Callers must hold
// `registry_mutex_`. Verified by TSan in test/registry_race_test.cpp.
```
```java
// Takes ~15 minutes against the production snapshot. Excluded from the fast suite.
@Tag("slow")
```

**Clarification of something you cannot change.** When a third-party or standard-library return
value is cryptic and you cannot rename it.

```java
// compareTo returns 0 only when the two intervals are exactly coincident,
// not merely overlapping — see java.time.Interval#compareTo.
assertThat(a.compareTo(b)).isEqualTo(0);
```

**Amplification.** Flagging something that looks removable but is load-bearing.

```python
# trim() is essential here: a leading space makes the downstream parser treat
# the whole line as a continuation, silently dropping the record.
list_item_content = match.group(1).strip()
```

**TODO with an owner and an exit condition.**

```python
# TODO(rlee, 2026-11): remove once the v1 endpoint is decommissioned (PLAT-882).
```
A TODO without a name and a condition is not a plan, it is litter. Grep for them each sprint.

**Non-obvious algorithmic or mathematical justification.**

```c
/* Bit-twiddling round-up-to-power-of-two (Hacker's Delight §3-2).
 * Undefined for v == 0 and for v > 2^31; both are excluded by the caller's
 * precondition check in ring_buffer_create(). */
static uint32_t round_up_pow2(uint32_t v) { ... }
```

**Public API documentation.** See its own section below.

## Bad comments

**Redundant.** Says exactly what the code says, but takes longer to read and can go stale.
```java
// increment i
i++;

/** @return the name */
public String getName() { return name; }
```

**Mumbling.** A comment written without care, that only the author could decode.
```java
catch (IOException e) {
    // give up            <-- give up on what? why is that safe? what does the caller see?
}
```

**Misleading / obsolete.** The most dangerous kind. If you touch the code, touch the comment in
the same edit.
```python
# retries 3 times                 <-- it retries 5 times now, and the reader will trust the 3
for attempt in range(5): ...
```

**Mandated comments.** A rule requiring a docblock on every function produces noise, not
documentation. Document contracts that need documenting; skip the one-line getter.

**Journal comments.** A changelog at the top of the file. Version control owns this.
```java
/* Changes:
 * 2019-03-04 rl  added retry
 * 2021-08-11 ka  fixed npe          <-- git log, git blame. Delete this. */
```

**Noise, banners, and attributions.**
```python
# Default constructor.
# ///////////////// UTILITIES /////////////////   <-- if you need a banner, you need a new file
# Added by Rachel                                 <-- git blame knows
```

**Position markers** every few lines. A rare, sparse banner in a genuinely long generated file is
tolerable. Otherwise, they are a sign the file should be split.

**Closing-brace comments.**
```java
    } // end for
  } // end try
} // end try
```
This is a symptom, not a solution: the function is too long. Shorten it.

**Commented-out code.** Delete it. Always. Version control remembers, and nobody who comes after
you will feel entitled to remove it, so it accumulates forever and slowly poisons the file.

**Nonlocal information.** A comment describing something declared in another file will not be
updated when that other file changes.
```java
/** The port defaults to 8080 */         <-- lives here, truth lives in config.yaml
public void setPort(int port) { ... }
```

**Too much information.** Do not paste an RFC excerpt into a source file. Cite it:
`// Base64 alphabet per RFC 4648 §4.`

**Inobvious connection.** If the reader has to decode the comment, it has failed twice.

**HTML in comments.** Markup belongs in the documentation toolchain, not smeared through source.

## API documentation

Doc comments on *public* interfaces are a different animal from inline comments: they are the
contract, they are read by people who will never see the implementation, and they are generated
into reference docs. Write them; write them well; keep them to the contract.

Document, in this order: **what it does (one line), parameters and their valid ranges, the return
value, what it raises/throws and when, ownership and lifetime, thread-safety, and complexity if
it is surprising.** Do not document the algorithm — that is what the body is for.

**Python (PEP 257 + type hints)**
```python
def resolve(hostname: str, *, timeout_s: float = 5.0) -> list[IPv4Address]:
    """Resolve `hostname` to its IPv4 addresses.

    Args:
        hostname: A DNS name. Punycode is accepted; unicode names are encoded
            with IDNA before lookup.
        timeout_s: Total budget across all retries. Must be > 0.

    Returns:
        Addresses in the order returned by the resolver, possibly empty if the
        name exists but has no A record.

    Raises:
        ValueError: If `timeout_s` <= 0.
        ResolutionError: If the name does not exist or the lookup times out.
    """
```
Types live in the signature, not the docstring — don't duplicate what the annotation says.

**Java (Javadoc)**
```java
/**
 * Withdraws {@code amount} from this account.
 *
 * @param amount strictly positive amount in the account's currency
 * @return the resulting balance, never {@code null}
 * @throws InsufficientFundsException if {@code amount} exceeds the available balance
 * @throws IllegalArgumentException   if {@code amount} is not positive
 * @implNote Not thread-safe; callers must serialize access per account.
 */
public Money withdraw(Money amount) { ... }
```

**C / C++ (Doxygen)**
```c
/**
 * @brief Reads an entire file into a newly allocated buffer.
 *
 * @param path      NUL-terminated path; must not be NULL.
 * @param out_size  Receives the byte count on success; may be NULL.
 * @return Heap buffer owned by the caller, to be released with free(),
 *         or NULL on failure with errno set.
 * @note  The buffer is NUL-terminated for convenience; @p out_size excludes
 *        that terminator.
 */
char *file_slurp(const char *path, size_t *out_size);
```
In C especially, **ownership and nullability are the contract**. State who frees what, and which
pointers may be NULL. There is no other mechanism to say it.

## Comment style by language

| | Line | Block | Doc tool |
|---|---|---|---|
| C | `//` (C99+) | `/* */` | Doxygen |
| C++ | `//` | `/* */` (avoid nesting) | Doxygen |
| Java | `//` | `/* */` | Javadoc `/** */` |
| Python | `#` | (none — triple-quoted strings are docstrings, not comments) | docstrings, PEP 257 |

Python note: a triple-quoted string floating in the middle of a function is not a comment; it is a
no-op string expression. Use `#`.

Formatting rules that hold everywhere: put comments **above** the code they describe, not trailing
at end of line (except very short units/annotations); indent them to match the code; keep them
within the project line limit; write complete sentences with normal capitalization; and prefer one
well-written paragraph to five terse fragments.

## Worked examples

**Turning a comment into a name (C)**

```c
/* before */
/* skip whitespace and comments to find the start of the next token */
while (*p == ' ' || *p == '\t' || *p == '\n' ||
       (*p == '#' && (p = strchr(p, '\n')) != NULL)) {
    p++;
}
```
```c
/* after */
p = skip_whitespace_and_comments(p);
```

**Keeping the comment because it carries the *why* (Python)**

```python
# before — comment restates the code
# sleep for 100ms
time.sleep(0.1)

# after — the code says what; the comment says why, and cites evidence
POLL_INTERVAL_S = 0.1
# The device firmware NAKs any command issued within 80ms of the previous one
# (datasheet rev C, §7.3). 100ms gives margin without hurting throughput.
time.sleep(POLL_INTERVAL_S)
```

**Deleting an apology and fixing the design (Java)**

```java
// before
// HACK: the vendor SDK throws on empty results instead of returning an empty
// list, so we swallow it here. Sorry. Same hack appears in 4 other places.
try {
    return sdk.query(q);
} catch (VendorEmptyException e) {
    return List.of();
}
```
```java
// after — one adapter, one comment, four call sites cleaned
/** Adapts the vendor SDK to normal Java collection semantics. */
final class VendorClient {
    /**
     * @return matching records, empty if none. The underlying SDK signals
     *         "no results" by throwing {@link VendorEmptyException}; this
     *         class normalizes that to an empty list.
     */
    List<Record> query(Query q) {
        try {
            return sdk.query(q);
        } catch (VendorEmptyException e) {
            return List.of();
        }
    }
}
```

## Related heuristics

`smells-catalog.md`: **C1** inappropriate information, **C2** obsolete comment, **C3** redundant
comment, **C4** poorly written comment, **C5** commented-out code.
