# Functions

The function is the unit of clean code. If your functions are right, most other problems become
tractable; if they are wrong, no amount of class design will save you.

## Contents

- [Budgets](#budgets)
- [Small](#small)
- [Do one thing](#do-one-thing)
- [One level of abstraction](#one-level-of-abstraction)
- [The stepdown rule](#the-stepdown-rule)
- [Arguments](#arguments)
- [Side effects](#side-effects)
- [Command–query separation](#commandquery-separation)
- [Early return](#early-return)
- [Don't repeat yourself](#dont-repeat-yourself)
- [Efficiency without ugliness](#efficiency-without-ugliness)
- [Worked example](#worked-example)

## Budgets

These are defaults, not laws — but every violation should be a decision you can defend out loud,
not an accident.

| Property | Target | Hard look required above |
|---|---|---|
| Lines of body | ≤ 20 | 40 |
| Arguments | ≤ 2 | 3 |
| Indent depth inside body | ≤ 2 | 3 |
| Return points | as many as clarity wants | — |
| Cyclomatic complexity | ≤ 5 | 10 |
| Local variables | ≤ 5 | 8 |

The repo's linter enforces these mechanically. Use it; don't count by hand.

## Small

Functions should be small. Then they should be smaller than that.

The reason is not aesthetic. A short function fits in working memory, so the reader can verify it
without holding a stack of context. A short function has one obvious name. A short function can
be tested exhaustively. A short function can be moved, reused, and deleted without archaeology.

"But then I'll have hundreds of tiny functions" — correct, and fine. A hundred well-named
functions in a stepdown hierarchy are navigable; five 200-line functions are not.

```
# bad — 3 levels of nesting, 4 responsibilities, needs comments to survive
function process_orders(orders):
    for order in orders:
        if order.status == PENDING:
            # validate
            if order.items is empty or order.total < 0:
                log.warn("bad order " + order.id)
                continue
            # charge
            try:
                gateway.charge(order.customer_id, order.total)
                order.status = PAID
            catch GatewayError as e:
                order.status = FAILED
                log.error("charge failed", e)
            # notify
            mailer.send(order.customer_email, "Order " + order.id + " processed")

# good — each function is one thing, and the top level reads like a summary
function process_orders(orders):
    for order in orders where order.is_pending():
        process_order(order)

function process_order(order):
    if not is_valid(order):
        log.warn("Rejecting malformed order", order.id)
        return
    charge(order)
    notify_customer(order)
```

The comments disappeared. Each one became a function name. **That transformation — comment to
name — is the single most reliable cleanup move there is.**

## Do one thing

"One thing" is slippery, so use three concrete tests:

1. **The extraction test.** Can you extract another function with a name that is not just a
   restatement of the implementation? If yes, it was doing more than one thing.
2. **The `and`/`or` test.** Does the honest description contain "and", "or", or "then"?
   `validate_and_save` is two functions wearing a trench coat.
3. **The abstraction-level test.** Do all statements sit at the same conceptual level?

A function that does one thing may still call five others — that is one thing at *its* level.
`make_breakfast()` calling `brew_coffee()` and `fry_egg()` does one thing.

## One level of abstraction

Mixing levels forces the reader to change altitude mid-paragraph and is the main reason long
functions feel exhausting.

```
# bad — business intent and byte-level fiddling in the same breath
function publish_report(report, conn):
    payload = utf8(to_json(report.to_map()))
    header = pack_uint32_big_endian(length(payload))
    conn.send(header + payload)
    report.mark_published()
    audit_log.record(user=report.owner, action="publish", target=report.id)

# good — one altitude per function
function publish_report(report, conn):
    send_framed_json(conn, report.to_map())
    report.mark_published()
    audit_log.record(user=report.owner, action="publish", target=report.id)

# Sends payload as UTF-8 JSON prefixed with a 4-byte big-endian length.
function send_framed_json(conn, payload):
    body = utf8(to_json(payload))
    conn.send(pack_uint32_big_endian(length(body)) + body)
```

The comment on the helper is legitimate: it documents a wire format, which is a *contract*, not a
restatement of the code.

## The stepdown rule

Order functions so the file reads top-down like prose, each function followed by those it calls,
descending one level of abstraction at a time. The reader can stop at any depth and still have a
coherent picture — headline, lede, then details.

```
public entry point
  ├─ high-level step A
  │    ├─ detail A1
  │    └─ detail A2
  └─ high-level step B
       └─ detail B1
```

If the language forces declaration-before-use, use forward declarations rather than letting the
compiler dictate a bottom-up reading order.

## Arguments

Fewer arguments means fewer things to name, fewer combinations to test, fewer ways to call it
wrong.

- **Zero** — ideal. Often means the data is state on the object where it belongs.
- **One** — three legitimate shapes: ask a question (`file_exists(path)`), transform and return
  (`parse(text) -> Report`), or handle an event (`on_password_failed(attempt_count)`). Anything
  else has the wrong shape.
- **Two** — fine when the order is natural and memorized: `Point(x, y)`,
  `assert_equals(expected, actual)`. Suspicious when arbitrary: `write_field(stream, name)`
  invites a swap bug.
- **Three** — pause. Order errors multiply. Name them well or introduce a parameter object.
- **More than three** — you have discovered an unnamed concept. Name it.

```
# bad
make_circle(x, y, radius, filled, stroke_width)

# good — the parameter object is a real concept, and it can grow without breaking callers
make_circle(center: Point, radius, style: CircleStyle = default)
```

**Never pass a boolean flag.** It confesses that the function does two things and makes every
call site unreadable: `render(true)` — true what?

```
# bad
function render(report, as_pdf): ...

# good
function render_pdf(report): ...
function render_html(report): ...
```

If the branches share logic, extract it and let both call it. If the choice comes from
configuration, pass an enum or strategy — `render(Format.PDF)` still reads at the call site.

**Avoid output arguments.** A function should return its result; mutating an argument is
invisible at the call site. `append_footer(s)` — modifies `s`, or appends `s` somewhere? Prefer
`report = report.with_footer()`. Where the language makes out-parameters idiomatic, name them
`out_*` and document ownership and the failure guarantee ("on failure `out_config` is untouched").

## Side effects

A side effect the name does not promise is a lie, and it is the class of bug that survives code
review, because the reviewer trusted the name.

```
# bad — a session is initialized as a side effect of checking a password.
# check_password can now only be called at one specific moment, and nothing says so.
function check_password(user_name, password):
    user = repository.find(user_name)
    if user exists and hash(password) == user.password_hash:
        Session.initialize()          # <-- ambush
        return true
    return false
```

Separate them and let the caller sequence them. Temporal coupling should be made physical: if
`b()` must run after `a()`, have `a()` return a value that `b()` requires. Then the type system
enforces the order instead of a comment asking nicely.

## Command–query separation

A function either **does** something or **answers** something. Not both.

```
# bad — does this ask whether the attribute exists, or set it? Both.
if set("username", "unclebob"): ...

# good
if attribute_exists("username"):
    set_attribute("username", "unclebob")
```

Universal idioms where the combination is the point — `queue.pop()`, `iterator.next()`,
`put_if_absent()` — are acceptable exceptions, named unmistakably.

## Early return

One-entry-one-exit was written for long functions with `goto`. In small functions, **guard
clauses and early returns are clearer** than a single exit with deep nesting.

```
# bad — the happy path is buried three levels deep
function process(request):
    if request.is_valid():
        if auth.allows(request.user):
            if not rate_limiter.exceeded(request.user):
                handle(request)
                return true
    return false

# good — preconditions first, happy path unindented at the bottom
function process(request):
    if not request.is_valid():               return false
    if not auth.allows(request.user):        return false
    if rate_limiter.exceeded(request.user):  return false
    handle(request)
    return true
```

Exception: where the language has no scoped cleanup (no destructors, `defer`, `finally`, or
`with`), a single exit to one cleanup block is the accepted idiom — it beats duplicating release
logic at every return.

## Don't repeat yourself

Duplication is the root of most maintenance cost: every copy is a place a fix can fail to land.
Extract a function for textual duplication; use polymorphism, generics, or a table for structural
duplication.

Beware the over-correction. Code that looks alike today but changes for *different reasons* is not
duplication; merging it creates coupling that hurts later. Ask: "when requirement X changes, must
both change together?" If yes, deduplicate. If no, leave them alone.

## Efficiency without ugliness

Clean and fast are usually the same code, because clean code is the code you can optimize.

- **Measure first.** The hot spot is almost never where you guessed.
- **Fix the algorithm before the constant factor.** Replacing O(n²) with a hash lookup beats every
  micro-optimization and usually *shortens* the function.
- **Prefer the standard library.** Its sort is faster, clearer, and already correct.
- **Avoid work rather than doing it quickly.** Cache, batch, stream, short-circuit.
- **Quarantine necessary ugliness.** One small function, a name that says what it is, and a
  comment stating the measurement that justified it — plus the benchmark that will tell you when
  it stops being worth it.

## Worked example

```
# before — magic indexes, magic number, anonymous predicate, three jobs in one loop
function report(rows):
    out = []
    for r in rows:
        if r[3] == "A" and r[5] > 0:
            t = r[5] * 1.08
            out.append(r[0] + " | " + r[1] + " | " + format(t, 2))
    return join(out, "\n")

# after
TAX_RATE = 0.08

function format_billing_report(rows):
    return join([format_line(row) for row in rows if is_billable(row)], "\n")

function is_billable(row):
    return row.status == ACTIVE and row.amount > 0

function format_line(row):
    total_with_tax = row.amount * (1 + TAX_RATE)
    return row.id + " | " + row.name + " | " + format(total_with_tax, 2)
```

Wins: index positions became a named type, `1.08` became a constant that documents itself, the
predicate got a name that reads at the call site, and each function is independently testable.
For money, use a decimal type, not floating point — correctness outranks brevity.

## Related heuristics

`smells-catalog.md`: **F1–F4** (too many arguments, output arguments, flag arguments, dead
function), **G5** (duplication), **G30** (do one thing), **G34** (descend only one level of
abstraction), **G20** (names say what they do), **G31** (hidden temporal coupling).
