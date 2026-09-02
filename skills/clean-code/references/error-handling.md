# Error Handling, Resources, and Boundaries

Error handling is important, but if it obscures the logic it is wrong. The goal is code where the
happy path reads cleanly top to bottom and the error paths are visible, honest, and out of the way.

## Contents

- [Principles](#principles)
- [Prefer exceptions to error codes](#prefer-exceptions-to-error-codes)
- [Provide context](#provide-context)
- [Define exceptions by the caller's needs](#define-exceptions-by-the-callers-needs)
- [Define the normal flow](#define-the-normal-flow)
- [Don't return null, don't pass null](#dont-return-null-dont-pass-null)
- [Resource management](#resource-management)
- [Error handling in C](#error-handling-in-c)
- [Boundaries: third-party code](#boundaries-third-party-code)

## Principles

1. **Errors are part of the contract.** A function's failure modes are as much its interface as
   its return type. Document them and test them.
2. **Handle errors where you have the context to decide.** Not everywhere — most functions should
   let errors pass through untouched.
3. **Never swallow an error silently.** An empty `catch` is a promise that something impossible
   will never happen. It will.
4. **Fail fast and loudly at the boundary; degrade gracefully in the interior** — or the other way
   around, but decide deliberately and be consistent.
5. **Error handling is one thing.** If a function has a try/catch, that is usually the *only*
   thing it should do — extract the body.

```java
// error handling is the whole job of this function
public void delete(Page page) {
    try {
        deletePageAndAllReferences(page);
    } catch (Exception e) {
        logError(e);
    }
}

private void deletePageAndAllReferences(Page page) throws Exception {
    deletePage(page);
    registry.deleteReference(page.name);
    configKeys.deleteKey(page.name.makeKey());
}
```

## Prefer exceptions to error codes

Return codes force every caller to check immediately, which buries the logic and — worse — is
easy to skip. Exceptions separate the happy path from the failure path.

```cpp
// bad — the algorithm is drowning
if (handle_ = open_device(); handle_ != OK) {
    if (handle_ == E_BUSY) { log(...); return E_BUSY; }
    else if (handle_ == E_PERM) { log(...); return E_PERM; }
    return E_UNKNOWN;
}
if (int rc = configure(handle_); rc != OK) { close_device(handle_); return rc; }
```

```cpp
// good — the happy path is the only path you read
Device device = open_device();   // throws DeviceUnavailable / PermissionDenied
device.configure();              // RAII closes on any exit
```

Where exceptions are unavailable or inappropriate (embedded C++, hot loops, kernel code, or plain
C), use a **result type** consistently rather than mixing conventions:

```cpp
std::expected<Config, ConfigError> parse_config(std::string_view text);   // C++23
// or absl::StatusOr<Config>, tl::expected<Config, E>, etc.
```

The cardinal sin is *mixing*: some functions throwing, some returning codes, some setting a global
errno-alike. Pick one per module and state it in the module's header comment.

**Java specifics.** Prefer unchecked exceptions for most application code. Checked exceptions
violate the Open/Closed Principle: adding a `throws` clause deep in the stack forces edits in
every function above it, and the intervening code is coupled to a detail it does not care about.
Reserve checked exceptions for genuinely recoverable conditions the immediate caller can act on.

**Python specifics.** Exceptions are the idiom — EAFP ("easier to ask forgiveness than
permission") is normal, readable Python. Catch narrowly (`except KeyError:`, never bare
`except:`), and use `raise ... from err` to preserve the chain.

## Provide context

An exception with no context turns a five-minute fix into an hour of log archaeology.

```python
# bad
raise ValueError("invalid input")

# good — what failed, what the input was, what was expected, what the caller can do
raise ConfigError(
    f"Invalid retry_budget in {path}:{line_no}: got {value!r}, "
    f"expected an integer between 1 and {MAX_RETRY_BUDGET}"
) from err
```

```java
throw new PaymentFailedException(
        "Charge rejected for order %s (gateway code %s)".formatted(orderId, code), cause);
```

Include: the operation attempted, the identifying data (ID, path, line), the expected shape, and
the cause. Do **not** include secrets, tokens, full PII, or raw payloads with credentials.

## Define exceptions by the caller's needs

Classify exceptions by *how the caller will handle them*, not by where they came from. If every
caller does the same thing with three different vendor exceptions, they should see one.

```java
// bad — the caller must know three vendor-specific types to do one thing
try {
    port.open();
} catch (DeviceResponseException e)    { reportPortError(e); }
catch (ATM1212UnlockedException e)     { reportPortError(e); }
catch (GMXError e)                     { reportPortError(e); }
```

```java
// good — wrap the third-party API; the caller sees one meaningful failure
public class LocalPort {
    private final ACMEPort inner;

    public void open() {
        try {
            inner.open();
        } catch (DeviceResponseException | ATM1212UnlockedException | GMXError e) {
            throw new PortDeviceFailure("Could not open port " + inner.id(), e);
        }
    }
}
```

This wrapper does double duty: it defines your error vocabulary *and* it is the boundary that
lets you swap the vendor later (see [Boundaries](#boundaries-third-party-code)).

## Define the normal flow

Sometimes the cleanest handling is to make the exceptional case not exceptional. The Special Case
pattern (a null object with sensible behavior) removes the branch entirely.

```java
// before — the exception is doing control flow
MealExpenses expenses;
try {
    expenses = expenseReportDAO.getMeals(employee.getID());
    total += expenses.getTotal();
} catch (MealExpensesNotFound e) {
    total += getMealPerDiem();
}

// after — the DAO returns a PerDiemMealExpenses when there are no meals
MealExpenses expenses = expenseReportDAO.getMeals(employee.getID());
total += expenses.getTotal();
```

## Don't return null, don't pass null

Returning null pushes a check onto every caller, and one missed check is a crash. Prefer:

- an **empty collection** over a null collection — `List.of()`, `[]`, `{}`
- an **`Optional` / `std::optional` / `T | None`** where absence is genuinely meaningful and the
  caller must decide
- a **Special Case object** where a default behavior exists
- an **exception** where absence is a real error

```java
// bad
List<Employee> employees = getEmployees();
if (employees != null) { for (Employee e : employees) { ... } }

// good
for (Employee e : getEmployees()) { ... }     // getEmployees() returns List.of() when empty
```

Passing null is worse, because there is rarely a good way to handle it. Ban it at your own APIs
and enforce with assertions or annotations:

```java
public double xProjection(Point p1, Point p2) {
    Objects.requireNonNull(p1, "p1");
    Objects.requireNonNull(p2, "p2");
    return (p2.x - p1.x) * 1.5;
}
```

```python
def x_projection(p1: Point, p2: Point) -> float:   # types say "not None"; mypy enforces it
    return (p2.x - p1.x) * 1.5
```

```cpp
double x_projection(const Point& p1, const Point& p2);   // references cannot be null — free safety
```

Note the C++ line: choosing a reference over a pointer moves the guarantee from documentation into
the type system. Prefer that move wherever a language offers it.

## Resource management

Leaks are error handling that wasn't. The rule: **the language should close it, not you.**

**C++ — RAII.** Every resource lives in an object whose destructor releases it. Prefer the Rule of
Zero: compose from `std::unique_ptr`, `std::vector`, `std::fstream`, `std::lock_guard`, and write
no destructor at all.

```cpp
void export_report(const Report& report, const std::filesystem::path& out) {
    std::ofstream file(out);                   // closed on every exit path, including throw
    if (!file) throw std::system_error(errno, std::generic_category(), out.string());
    std::lock_guard lock(registry_mutex_);     // released on every exit path
    file << render(report);
}
```

**Java — try-with-resources.**
```java
try (var in = Files.newInputStream(path);
     var out = Files.newOutputStream(target)) {
    in.transferTo(out);
}   // both closed, suppressed exceptions preserved
```

**Python — context managers.**
```python
with open(path, encoding="utf-8") as src, sqlite3.connect(db) as conn:
    conn.executemany("INSERT INTO rows VALUES (?, ?)", parse(src))
```
Write your own with `contextlib.contextmanager` rather than pairing manual acquire/release calls.

**C — paired allocate/free with single-exit cleanup.** See below.

## Error handling in C

C has no exceptions and no destructors, so cleanliness comes entirely from convention. Choose one
and apply it uniformly across the module.

**Convention: return an int status, deliver results through out-parameters.**

```c
/* Returns 0 on success, negative errno on failure.
 * On success, *out_doc is initialized and owned by the caller (free with document_free).
 * On failure, *out_doc is untouched. */
int document_load(const char *path, struct document *out_doc);
```

**Single cleanup label — the one place `goto` is idiomatic and clean.** It removes the duplicated
free-chain that otherwise appears at every early return.

```c
int document_load(const char *path, struct document *out_doc) {
    int    rc   = -EIO;
    FILE  *file = NULL;
    char  *text = NULL;
    struct document doc = {0};

    if (!path || !out_doc) return -EINVAL;      /* precondition: fail fast, nothing to clean */

    file = fopen(path, "rb");
    if (!file) { rc = -errno; goto cleanup; }

    text = read_all(file);
    if (!text) { rc = -ENOMEM; goto cleanup; }

    rc = document_parse(text, &doc);
    if (rc != 0) goto cleanup;

    *out_doc = doc;                              /* transfer ownership only on success */
    doc = (struct document){0};                  /* prevent cleanup from freeing it */
    rc = 0;

cleanup:
    document_free(&doc);                         /* must be safe on a zeroed struct */
    free(text);
    if (file) fclose(file);
    return rc;
}
```

Rules that make this work:
- **Initialize every resource variable to a null/zero sentinel** at declaration, so `cleanup` can
  run unconditionally.
- **Make every free/destroy function null-safe and idempotent.** `free(NULL)` is legal; make yours
  match.
- **Transfer ownership last**, after the last thing that can fail.
- **Never `goto` backwards or into a scope.** Forward-to-cleanup only.
- **Check every return value.** Use `__attribute__((warn_unused_result))` / `[[nodiscard]]` on
  functions whose result must not be ignored.

Document ownership at every boundary — "caller owns", "borrowed, valid until X", "callee takes
ownership". That sentence in the header is the whole memory-safety story in C.

## Boundaries: third-party code

Third-party APIs are written for many callers; yours is written for one. Wrapping them at the
boundary is what keeps their design decisions from leaking into your whole codebase.

**Wrap, don't spread.** If `Map<String, Sensor>` appears in forty places, forty places must change
when you switch to a typed collection — and all forty expose `clear()` to callers who shouldn't
have it.

```java
// bad — the raw type and its whole API leak everywhere
Map<String, Sensor> sensors = new HashMap<>();
Sensor s = (Sensor) sensors.get(sensorId);

// good — one narrow interface, shaped for your needs
public class Sensors {
    private final Map<String, Sensor> sensors = new HashMap<>();

    public Sensor byId(String id) { return sensors.get(id); }
    // no put(), no clear(), no keySet() — because callers don't need them
}
```

**Learning tests.** When adopting an unfamiliar library, write small tests that exercise it the
way you intend to use it. You learn the API faster than by reading docs, you get an executable
record of the behavior you're relying on, and when you upgrade the library, those tests tell you
immediately whether your assumptions still hold. They pay for themselves at the first upgrade.

**Code against interfaces you own.** When a dependency doesn't exist yet (another team's service,
unfinished hardware), define the interface *you wish you had*, write your code against it, and
implement an adapter later. This keeps the design driven by your needs rather than by someone
else's incomplete API — and gives you a natural seam for a fake in tests.

```python
class TransmitterPort(Protocol):                 # the interface we wish we had
    def transmit(self, frequency_hz: float, payload: bytes) -> None: ...


class RealTransmitter:                           # adapter, written when the SDK ships
    def __init__(self, sdk: VendorSdk) -> None: self._sdk = sdk
    def transmit(self, frequency_hz: float, payload: bytes) -> None:
        self._sdk.setFreq(int(frequency_hz)); self._sdk.send(payload)


class FakeTransmitter:                           # test double, available today
    def __init__(self) -> None: self.sent: list[tuple[float, bytes]] = []
    def transmit(self, frequency_hz: float, payload: bytes) -> None:
        self.sent.append((frequency_hz, payload))
```

## Related heuristics

`smells-catalog.md`: **G4** overridden safeties, **G3** incorrect behavior at boundaries,
**G33** encapsulate boundary conditions, **G2** obvious behavior unimplemented, **T5** test
boundary conditions.
