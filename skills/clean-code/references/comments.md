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
- [Placement](#placement)
- [Worked examples](#worked-examples)

## The decision procedure

Before writing any comment, run this in order. Stop as soon as one works.

**1. Can a better name remove the need?**
```
# bad
# check if the employee is eligible for full benefits
if employee.flags & HOURLY_FLAG and employee.age > 65: ...

# good
if is_eligible_for_full_benefits(employee): ...
```

**2. Can an extracted function remove the need?** If you are about to write
`# now validate the header`, you are about to name a function. Extract `validate_header()` and
delete the comment.

**3. Can an explanatory variable remove the need?**
```
# bad
# ensure the discount doesn't exceed the order total
if amount > 0 and amount <= total * 0.5 and customer.tier >= 2: ...

# good
is_positive      = amount > 0
is_within_cap    = amount <= total * MAX_DISCOUNT_FRACTION
is_eligible_tier = customer.tier >= Tier.SILVER
if is_positive and is_within_cap and is_eligible_tier: ...
```

**4. Is the comment apologizing for a design flaw?** `# hack because the API is broken` — fix the
design, or wrap the broken API behind a clean adapter and comment *there*, once.

**5. Only now: write the comment — and explain *why*, not *what*.** The reader can see the loop.
What they cannot see is the reasoning, the constraint, the incident that made this necessary.

## Good comments

These earn their place.

- **Legal / provenance.** Copyright headers, license identifiers, attribution for adapted
  algorithms. Point to the LICENSE file rather than pasting a license.
- **Intent / rationale.** `# Poll instead of file-watch: the data dir is an NFS mount and watch
  events don't fire for other hosts' writes. See INFRA-4127.`
- **Warning of consequences.** `# Not thread-safe: mutates the shared cache without locking.
  Callers must hold registry_lock.` or `# Takes ~15 min against the prod snapshot; excluded from
  the fast suite.`
- **Clarifying something you cannot change.** A cryptic third-party return value you cannot
  rename.
- **Amplification.** Flagging something that looks removable but is load-bearing: `# strip() is
  essential: a leading space makes the downstream parser drop the record silently.`
- **TODO with an owner and an exit condition.** `# TODO(rlee, 2026-11): remove once the v1
  endpoint is decommissioned (PLAT-882).` A TODO without both is litter. Grep for them each sprint.
- **Non-obvious algorithmic justification**, with its preconditions: `# Round up to power of two
  (Hacker's Delight §3-2). Undefined for v == 0; excluded by the caller's precondition.`
- **Public API documentation.** See its own section below.

## Bad comments

- **Redundant.** `# increment i` above `i += 1`; a doc comment `@return the name` on a one-line
  getter. Takes longer to read than the code and can go stale.
- **Mumbling.** `catch IOError: # give up` — give up on what? Why is that safe? What does the
  caller see?
- **Misleading / obsolete.** The most dangerous kind. `# retries 3 times` above a loop that now
  retries 5. If you touch the code, touch the comment in the same edit.
- **Mandated.** A rule requiring a docblock on every function produces noise. Document contracts
  that need it; skip the getter.
- **Journal.** A changelog at the top of the file. Version control owns this.
- **Noise, banners, attributions.** `# Default constructor.`, `# ///// UTILITIES /////`,
  `# Added by Rachel`. If you need a banner, you need a new file; `blame` knows the author.
- **Closing-brace comments.** `} # end for` is a symptom: the function is too long. Shorten it.
- **Commented-out code.** Delete it. Always. Version control remembers, and nobody after you will
  feel entitled to remove it, so it accumulates forever.
- **Nonlocal information.** `# port defaults to 8080` next to a setter, while the truth lives in
  `config.yaml`. It will not be updated when that file changes.
- **Too much information.** Don't paste an RFC excerpt; cite it: `# Base64 alphabet per RFC 4648 §4.`
- **Inobvious connection or embedded markup.** If the reader has to decode the comment, it has
  failed twice.

## API documentation

Doc comments on *public* interfaces are a different animal: they are the contract, read by people
who will never see the implementation, and generated into reference docs. Write them well and keep
them to the contract.

Document, in this order: **what it does (one line), parameters and valid ranges, the return value,
what it raises and when, ownership and lifetime, thread-safety, and complexity if surprising.** Do
not document the algorithm — that is what the body is for. Don't repeat types the signature
already states.

```
# Resolve `hostname` to its IPv4 addresses.
#
# hostname:  A DNS name. Unicode names are IDNA-encoded before lookup.
# timeout_s: Total budget across all retries. Must be > 0.
# returns:   Addresses in resolver order; empty if the name has no A record.
# raises:    InvalidArgument if timeout_s <= 0.
#            ResolutionError if the name does not exist or the lookup times out.
function resolve(hostname, timeout_s = 5.0) -> list of IPv4Address
```

Where the language cannot express ownership or nullability in types, **those are the contract**:
state who frees what and which references may be absent. There is no other place to say it.

## Placement

Put comments **above** the code they describe, not trailing (except very short unit or annotation
notes). Indent them to match the code, keep them within the line limit, write complete sentences,
and prefer one well-written paragraph to five terse fragments. Use the language's doc-comment tool
for public APIs and plain line comments everywhere else.

## Worked examples

```
# 1. Turning a comment into a name
# before
# skip whitespace and comments to find the start of the next token
while p.char in WHITESPACE or (p.char == "#" and p.skip_to_line_end()):
    p.advance()
# after
p = skip_whitespace_and_comments(p)

# 2. Keeping the comment because it carries the why
# before — restates the code
# sleep for 100ms
sleep(0.1)
# after — code says what; comment says why and cites evidence
POLL_INTERVAL_S = 0.1
# The device firmware NAKs any command within 80ms of the previous one
# (datasheet rev C, §7.3). 100ms gives margin without hurting throughput.
sleep(POLL_INTERVAL_S)

# 3. Deleting an apology by fixing the design
# before — repeated at 4 call sites
# HACK: vendor SDK throws on empty results instead of returning []. Sorry.
try: return sdk.query(q)
catch VendorEmptyError: return []
# after — one adapter, one comment, four call sites cleaned
# Adapts the vendor SDK to normal collection semantics: the SDK signals
# "no results" by throwing VendorEmptyError; this returns [] instead.
class VendorClient:
    function query(q):
        try: return sdk.query(q)
        catch VendorEmptyError: return []
```

## Related heuristics

`smells-catalog.md`: **C1** inappropriate information, **C2** obsolete comment, **C3** redundant
comment, **C4** poorly written comment, **C5** commented-out code.
