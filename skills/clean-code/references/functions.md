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
- [Structured programming and early return](#structured-programming-and-early-return)
- [Don't repeat yourself](#dont-repeat-yourself)
- [Efficiency without ugliness](#efficiency-without-ugliness)
- [Worked example: extraction in three languages](#worked-example-extraction-in-three-languages)

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

`scripts/clean_code_lint.py` enforces these mechanically. Use it; don't count by hand.

## Small

Functions should be small. Then they should be smaller than that.

The reason is not aesthetic. A short function fits in working memory, so the reader can verify it
without holding a stack of context. A short function has one obvious name. A short function can
be tested exhaustively. A short function can be moved, reused, and deleted without archaeology.

The most common objection — "but then I'll have hundreds of tiny functions" — is correct, and it
is fine. A hundred well-named functions organized in a stepdown hierarchy is navigable; five
200-line functions are not. Reading `dispatch_order()` and seeing four named calls tells you the
whole story in four seconds.

```java
// bad — 3 levels of nesting, 4 responsibilities, needs comments to survive
public void processOrders(List<Order> orders) {
    for (Order o : orders) {
        if (o.getStatus() == Status.PENDING) {
            // validate
            if (o.getItems().isEmpty() || o.getTotal() < 0) {
                log.warn("bad order " + o.getId());
                continue;
            }
            // charge
            try {
                gateway.charge(o.getCustomerId(), o.getTotal());
                o.setStatus(Status.PAID);
            } catch (GatewayException e) {
                o.setStatus(Status.FAILED);
                log.error("charge failed", e);
            }
            // notify
            mailer.send(o.getCustomerEmail(), "Order " + o.getId() + " processed");
        }
    }
}
```

```java
// good — each function is one thing, and the top level reads like a summary
public void processOrders(List<Order> orders) {
    orders.stream().filter(Order::isPending).forEach(this::processOrder);
}

private void processOrder(Order order) {
    if (!isValid(order)) {
        log.warn("Rejecting malformed order {}", order.getId());
        return;
    }
    charge(order);
    notifyCustomer(order);
}

private boolean isValid(Order order) {
    return !order.getItems().isEmpty() && order.getTotal().signum() >= 0;
}

private void charge(Order order) {
    try {
        gateway.charge(order.getCustomerId(), order.getTotal());
        order.setStatus(Status.PAID);
    } catch (GatewayException e) {
        order.setStatus(Status.FAILED);
        log.error("Charge failed for order {}", order.getId(), e);
    }
}

private void notifyCustomer(Order order) {
    mailer.send(order.getCustomerEmail(), receiptFor(order));
}
```

Notice the comments disappeared. Each one became a function name. **That transformation — comment
to name — is the single most reliable cleanup move there is.**

## Do one thing

"One thing" is slippery, so use these three concrete tests:

1. **The extraction test.** Can you extract another function from it with a name that is not just
   a restatement of the implementation? If yes, it was doing more than one thing.
2. **The `and`/`or` test.** Does the honest description of the function contain "and", "or", or
   "then"? `validate_and_save` is two functions wearing a trench coat.
3. **The abstraction-level test.** Do all statements sit at the same conceptual level? (Next
   section.)

A function that does one thing may still call five other functions — that is one thing at *its*
level of abstraction. `make_breakfast()` calling `brew_coffee()` and `fry_egg()` does one thing.

## One level of abstraction

Mixing levels forces the reader to change altitude mid-paragraph and is the main reason long
functions feel exhausting.

```python
# bad — business intent and byte-level fiddling in the same breath
def publish_report(report, conn):
    payload = json.dumps(report.to_dict()).encode("utf-8")
    header = struct.pack("!I", len(payload))
    conn.sendall(header + payload)
    report.mark_published()
    audit_log.record(user=report.owner, action="publish", target=report.id)
```

```python
# good — one altitude per function
def publish_report(report: Report, conn: socket.socket) -> None:
    _send_framed_json(conn, report.to_dict())
    report.mark_published()
    audit_log.record(user=report.owner, action="publish", target=report.id)


def _send_framed_json(conn: socket.socket, payload: dict) -> None:
    """Send `payload` as UTF-8 JSON prefixed with a 4-byte big-endian length."""
    body = json.dumps(payload).encode("utf-8")
    conn.sendall(struct.pack("!I", len(body)) + body)
```

The docstring on the helper is legitimate: it documents a wire format, which is a *contract*, not
a restatement of the code.

## The stepdown rule

Order functions so the file reads top-down like prose, each function followed by those it calls,
descending one level of abstraction at a time. The reader can stop at any depth and still have a
complete, coherent understanding. This is the "newspaper" layout: headline, lede, then details.

```
public entry point
  ├─ high-level step A
  │    ├─ detail A1
  │    └─ detail A2
  └─ high-level step B
       └─ detail B1
```

In C, the header declares the contract and the `.c` file can follow the stepdown order using
forward declarations at the top of the file (or `static` prototypes) rather than bottom-up
ordering forced by the compiler.

## Arguments

Fewer arguments means fewer things to name, fewer combinations to test, and fewer ways to call it
wrong.

**Zero (niladic)** — ideal. Often means the data is state on the object where it belongs.

**One (monadic)** — three legitimate shapes:
- Ask a question about it: `bool file_exists(path)`
- Transform it and return the result: `Report parse(std::string_view text)`
- Handle an event (no return): `void on_password_failed(int attempt_count)`

If a monadic function neither asks, transforms, nor handles an event, its shape is wrong.

**Two (dyadic)** — fine when the arguments have a natural, memorized order:
`Point(x, y)`, `assertEquals(expected, actual)`. Suspicious when the order is arbitrary:
`writeField(output_stream, name)` invites a swap bug. Consider making one of them the receiver.

**Three (triadic)** — pause. Order errors multiply. `assertEquals(message, expected, actual)` is
famously misread. If you keep three, name them well and consider a builder.

**More than three** — you have discovered an unnamed concept. Introduce a parameter object.

```cpp
// bad
Circle make_circle(double x, double y, double radius, bool filled, int stroke_width);

// good — the parameter object is a real concept, and it can grow without breaking callers
struct CircleStyle { bool filled = false; int stroke_width = 1; };
Circle make_circle(Point center, double radius, CircleStyle style = {});
```

**Never pass a boolean flag.** A flag argument is a public confession that the function does two
things. It also makes every call site unreadable: `render(true)` — true what?

```python
# bad
def render(report, as_pdf):
    if as_pdf: ...
    else: ...

# good
def render_pdf(report): ...
def render_html(report): ...
```

If the two branches share substantial logic, extract the shared part and let both call it. If the
flag comes from configuration rather than a literal, prefer an enum or a strategy object over a
boolean — `render(Format.PDF)` still reads at the call site.

**Avoid output arguments.** In an OO or expression-oriented language, a function should return
its result; mutating an argument is invisible at the call site.

```java
// bad — does appendFooter modify s, or append s somewhere?
appendFooter(s);

// good
report = report.withFooter();
```

In C, out-parameters are idiomatic and unavoidable. Then the obligation is to be explicit:

```c
/* Parses `text` into `*out_config`.
 * Returns 0 on success, or a negative errno-style code on failure.
 * On failure `*out_config` is untouched. On success the caller owns
 * `out_config->name` and must free it with config_free(). */
int config_parse(const char *text, struct config *out_config);
```

Naming the parameter `out_config`, stating ownership, and stating the failure guarantee turns a
dangerous idiom into a safe one.

## Side effects

A side effect the name does not promise is a lie, and it is the class of bug that survives code
review, because the reviewer trusted the name.

```java
// bad — a session gets initialized as a side effect of checking a password.
// Now checkPassword() can only be called at one specific time, and nothing says so.
public boolean checkPassword(String user, String password) {
    User u = repository.find(user);
    if (u != null && crypt(password).equals(u.getHash())) {
        Session.initialize();     // <-- ambush
        return true;
    }
    return false;
}
```

Either rename to `checkPasswordAndInitializeSession` (which then fails the "one thing" test and
forces the real fix), or — correctly — separate them and let the caller sequence them.

Temporal couplings created by side effects should be made physical: if `b()` must run after
`a()`, have `a()` return a token that `b()` requires as an argument. Then the compiler enforces
the order instead of a comment asking nicely.

## Command–query separation

A function either **does** something or **answers** something. Not both.

```java
// bad — does this ask whether the attribute exists, or set it? Both. Read the call site:
if (set("username", "unclebob")) { ... }
```

```java
// good
if (attributeExists("username")) {
    setAttribute("username", "unclebob");
}
```

The pragmatic exceptions are well-known idioms where the combination is the point:
`queue.pop()`, `iterator.next()`, `map.putIfAbsent()`. These are acceptable because the
convention is universal — but they are exceptions, and they should be named unmistakably.

## Structured programming and early return

The one-entry-one-exit rule was written for languages with `goto` and functions hundreds of lines
long. In small functions, **guard clauses and early returns are clearer** than a single exit with
deep nesting.

```cpp
// bad — the happy path is buried three levels deep
bool process(const Request& req) {
    if (req.is_valid()) {
        if (auth.allows(req.user())) {
            if (!rate_limiter.exceeded(req.user())) {
                handle(req);
                return true;
            }
        }
    }
    return false;
}

// good — preconditions first, happy path unindented at the bottom
bool process(const Request& req) {
    if (!req.is_valid())                  return false;
    if (!auth.allows(req.user()))         return false;
    if (rate_limiter.exceeded(req.user())) return false;

    handle(req);
    return true;
}
```

**The exception is C with manual cleanup.** There, a single exit via `goto cleanup` genuinely
reduces duplicated free/close logic and is the accepted idiom:

```c
int load_document(const char *path, struct document *out) {
    int   rc   = -EIO;
    FILE *file = NULL;
    char *buf  = NULL;

    file = fopen(path, "rb");
    if (!file) { rc = -errno; goto cleanup; }

    buf = malloc(MAX_DOCUMENT_BYTES);
    if (!buf) { rc = -ENOMEM; goto cleanup; }

    if (!read_all(file, buf, MAX_DOCUMENT_BYTES)) { rc = -EIO; goto cleanup; }

    rc = document_parse(buf, out);

cleanup:
    free(buf);
    if (file) fclose(file);
    return rc;
}
```

In C++, this whole pattern is replaced by RAII and the function needs no cleanup block at all.

## Don't repeat yourself

Duplication is the root of most maintenance cost: every copy is a place a fix can fail to land.
The classic response — extract a function — is right most of the time. When the duplication is
structural rather than textual, the answer is polymorphism, a template/generic, or a
table-driven design.

Beware the over-correction. Two pieces of code that look alike today but change for *different
reasons* are not duplication; merging them creates a coupling that will hurt later. Ask: "when
requirement X changes, do both of these have to change together?" If yes, deduplicate. If no,
leave them alone.

## Efficiency without ugliness

Clean and fast are usually the same code, because clean code is the code you can optimize.

- **Measure first.** Profile. The hot spot is almost never where you guessed.
- **Fix the algorithm before the constant factor.** Replacing O(n²) with a hash lookup beats every
  micro-optimization, and usually *shortens* the function.
- **Prefer the standard library.** `std::sort`, `Collections.sort`, `sorted()` are faster and
  clearer than a hand-rolled loop, and they are already correct.
- **Avoid work rather than doing work quickly.** Cache, batch, stream, short-circuit.
- **When you must write ugly fast code, quarantine it.** One small function, a name that says what
  it is, and a comment stating the measurement that justified it:

```cpp
// Hot path: called ~2M times/sec by the tick handler. The branchless form
// measured 3.1x faster than std::min on our target (gcc 13, -O2, Zen 4).
// Benchmark: bench/clamp_bench.cpp. Revisit if the compiler improves.
inline int32_t clamp_fast(int32_t value, int32_t lo, int32_t hi) { ... }
```

Now the rest of the codebase stays readable, and the one dirty spot is documented, isolated, and
covered by a benchmark that will tell you when it stops being worth it.

## Worked example: extraction in three languages

The same cleanup, showing that the discipline is language-independent.

**Python — before**
```python
def report(rows):
    out = []
    for r in rows:
        if r[3] == "A" and r[5] > 0:
            t = r[5] * 1.08
            out.append("%s | %s | %.2f" % (r[0], r[1], t))
    return "\n".join(out)
```

**Python — after**
```python
TAX_RATE = 0.08


def format_active_billing_report(rows: Iterable[Row]) -> str:
    lines = [_format_line(row) for row in rows if _is_billable(row)]
    return "\n".join(lines)


def _is_billable(row: Row) -> bool:
    return row.status == Status.ACTIVE and row.amount > 0


def _format_line(row: Row) -> str:
    total_with_tax = row.amount * (1 + TAX_RATE)
    return f"{row.id} | {row.name} | {total_with_tax:.2f}"
```
Wins: magic index positions replaced by a named type, the magic `1.08` became a named constant
that documents itself, the predicate got a name that reads at the call site, and each function
now fits on one screen and is independently testable.

**Java — after (same shape)**
```java
private static final BigDecimal TAX_RATE = new BigDecimal("0.08");

public String formatActiveBillingReport(List<Row> rows) {
    return rows.stream()
               .filter(this::isBillable)
               .map(this::formatLine)
               .collect(joining("\n"));
}

private boolean isBillable(Row row) {
    return row.status() == Status.ACTIVE && row.amount().signum() > 0;
}

private String formatLine(Row row) {
    BigDecimal total = row.amount().multiply(BigDecimal.ONE.add(TAX_RATE));
    return "%s | %s | %.2f".formatted(row.id(), row.name(), total);
}
```
Note `BigDecimal` rather than `double`: correctness outranks brevity for money.

**C++ — after (same shape)**
```cpp
namespace {
constexpr double kTaxRate = 0.08;

bool is_billable(const Row& row) {
    return row.status == Status::Active && row.amount_cents > 0;
}

std::string format_line(const Row& row) {
    const std::int64_t total_cents =
        static_cast<std::int64_t>(std::llround(row.amount_cents * (1.0 + kTaxRate)));
    return std::format("{} | {} | {}", row.id, row.name, format_cents(total_cents));
}
}  // namespace

std::string format_active_billing_report(std::span<const Row> rows) {
    std::string report;
    for (const Row& row : rows) {
        if (!is_billable(row)) continue;
        report += format_line(row);
        report += '\n';
    }
    if (!report.empty()) report.pop_back();
    return report;
}
```
Helpers live in an anonymous namespace because they are implementation details; `std::span`
accepts any contiguous range without forcing a copy.

## Related heuristics

`smells-catalog.md`: **F1–F4** (too many arguments, output arguments, flag arguments, dead
function), **G5** (duplication), **G30** (do one thing), **G34** (descend only one level of
abstraction), **G20** (names say what they do), **G31** (hidden temporal coupling).
