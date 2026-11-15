# Error Handling, Resources, and Boundaries

Error handling is important, but if it obscures the logic it is wrong. The goal is code where the
happy path reads cleanly top to bottom and the error paths are visible, honest, and out of the way.

## Contents

- [Principles](#principles)
- [One error convention per module](#one-error-convention-per-module)
- [Provide context](#provide-context)
- [Define errors by the caller's needs](#define-errors-by-the-callers-needs)
- [Define the normal flow](#define-the-normal-flow)
- [Don't return null, don't pass null](#dont-return-null-dont-pass-null)
- [Resource management](#resource-management)
- [Boundaries: third-party code](#boundaries-third-party-code)

## Principles

1. **Errors are part of the contract.** A function's failure modes are as much its interface as
   its return type. Document them and test them.
2. **Handle errors where you have the context to decide.** Most functions should let errors pass
   through untouched.
3. **Never swallow an error silently.** An empty `catch` is a promise that something impossible
   will never happen. It will.
4. **Fail fast and loudly at the boundary; degrade gracefully in the interior** — or the reverse,
   but decide deliberately and be consistent.
5. **Error handling is one thing.** If a function has a try/catch, that is usually the *only* thing
   it should do — extract the body.

```
# error handling is the whole job of this function
function delete(page):
    try:
        delete_page_and_all_references(page)
    catch error:
        log_error(error)

function delete_page_and_all_references(page):
    delete_page(page)
    registry.delete_reference(page.name)
    config_keys.delete_key(page.name.as_key())
```

## One error convention per module

Return codes force every caller to check immediately, which buries the logic and is easy to skip.
Exceptions or result types separate the happy path from the failure path.

```
# bad — the algorithm is drowning in status checks
status = open_device(out handle)
if status == BUSY: log(...); return BUSY
if status == PERM: log(...); return PERM
status = configure(handle)
if status != OK: close_device(handle); return status

# good — the happy path is the only path you read
device = open_device()      # raises DeviceUnavailable / PermissionDenied
device.configure()          # device released on every exit by scoped cleanup
```

Where exceptions are unavailable or inappropriate (hot loops, embedded, kernel code, languages
without them), return a **result type** — `Result<Config, ConfigError>` — or a status code, and
use it consistently.

The cardinal sin is *mixing*: some functions raising, some returning codes, some setting a global
error variable. Pick one per module and state it in the module's header comment.

Catch narrowly — the specific error you can handle, never a catch-all that also traps bugs. When
rethrowing, chain the cause. Reserve errors the caller is *forced* to declare or handle for
conditions the immediate caller can genuinely recover from; everything else propagates freely.

## Provide context

An error with no context turns a five-minute fix into an hour of log archaeology.

```
# bad
raise InvalidInput("invalid input")

# good — what failed, the input, what was expected, the cause
raise ConfigError(
    "Invalid retry_budget in " + path + ":" + line_no + ": got " + repr(value) +
    ", expected an integer between 1 and " + MAX_RETRY_BUDGET,
    cause=error)
```

Include: the operation attempted, the identifying data (ID, path, line), the expected shape, and
the cause. Do **not** include secrets, tokens, full PII, or raw payloads with credentials.

## Define errors by the caller's needs

Classify errors by *how the caller will handle them*, not by where they came from. If every caller
does the same thing with three vendor errors, they should see one.

```
# bad — the caller must know three vendor-specific types to do one thing
try: port.open()
catch DeviceResponseError as e:  report_port_error(e)
catch ATM1212UnlockedError as e: report_port_error(e)
catch GMXError as e:             report_port_error(e)

# good — wrap the third-party API; the caller sees one meaningful failure
class LocalPort:
    function open():
        try: inner.open()
        catch DeviceResponseError, ATM1212UnlockedError, GMXError as e:
            raise PortDeviceFailure("Could not open port " + inner.id, cause=e)
```

This wrapper does double duty: it defines your error vocabulary *and* it is the boundary that lets
you swap the vendor later.

## Define the normal flow

Sometimes the cleanest handling is to make the exceptional case not exceptional. The Special Case
pattern (an object with sensible default behavior) removes the branch entirely.

```
# before — the error is doing control flow
try:
    total += expense_reports.meals_for(employee.id).total
catch MealExpensesNotFound:
    total += meal_per_diem()

# after — meals_for returns a PerDiemMealExpenses when there are no meals
total += expense_reports.meals_for(employee.id).total
```

## Don't return null, don't pass null

Returning null pushes a check onto every caller, and one missed check is a crash. Prefer:

- an **empty collection** over a null collection
- an **optional / maybe type** where absence is meaningful and the caller must decide
- a **Special Case object** where a default behavior exists
- an **error** where absence is a real failure

```
# bad
employees = get_employees()
if employees != null:
    for e in employees: ...

# good — get_employees() returns [] when empty
for e in get_employees(): ...
```

Passing null is worse, because there is rarely a good way to handle it. Ban it at your own APIs:
use non-nullable types or references where the language offers them (moving the guarantee from
documentation into the type system), and assert at the boundary where it doesn't.

## Resource management

Leaks are error handling that wasn't. The rule: **the language should release it, not you.**

Bind every resource — file, socket, lock, transaction — to a scope that releases it on *every*
exit path, including errors: destructors, `with`, `using`, try-with-resources, `defer`. Compose
from owning types and write no manual release code at all.

```
with open(path) as source, db.connect() as conn:   # both released on any exit
    conn.insert_all(parse(source))
```

Where the language has no scoped cleanup, use one convention uniformly:

- **One owner per resource**, stated at every boundary: "caller owns", "borrowed, valid until X",
  "callee takes ownership". That sentence is the whole memory-safety story.
- **Single forward exit to one cleanup block**, so release logic is written once.
- **Initialize every resource variable to an empty sentinel**, so cleanup can run unconditionally.
- **Make every release function safe on empty and idempotent.**
- **Transfer ownership last**, after the last thing that can fail.
- **Never ignore a returned status** — mark must-use results so the compiler enforces it.

## Boundaries: third-party code

Third-party APIs are written for many callers; yours is written for one. Wrapping them at the
boundary keeps their design decisions from leaking into your whole codebase.

**Wrap, don't spread.** If a raw `Map<String, Sensor>` appears in forty places, forty places change
when you switch types — and all forty expose `clear()` to callers who shouldn't have it.

```
# good — one narrow interface, shaped for your needs
class Sensors:
    private sensors_by_id = {}
    function by_id(id): return sensors_by_id[id]
    # no put(), no clear(), no keys() — callers don't need them
```

**Learning tests.** When adopting an unfamiliar library, write small tests that exercise it the way
you intend to use it. You learn the API faster, you get an executable record of the behavior you
rely on, and at the next upgrade those tests tell you immediately whether your assumptions hold.

**Code against interfaces you own.** When a dependency doesn't exist yet, define the interface
*you wish you had*, code against it, and write the adapter later. The design stays driven by your
needs, and you get a natural seam for a fake in tests.

```
interface TransmitterPort:                  # the interface we wish we had
    function transmit(frequency_hz, payload)

class RealTransmitter implements TransmitterPort:   # adapter, written when the SDK ships
    function transmit(frequency_hz, payload):
        sdk.set_freq(round(frequency_hz)); sdk.send(payload)

class FakeTransmitter implements TransmitterPort:   # test double, available today
    sent = []
    function transmit(frequency_hz, payload): sent.append((frequency_hz, payload))
```

## Related heuristics

`smells-catalog.md`: **G4** overridden safeties, **G3** incorrect behavior at boundaries,
**G33** encapsulate boundary conditions, **G2** obvious behavior unimplemented, **T5** test
boundary conditions.
