# Classes, Modules, and Design

Functions make code readable; class and module structure makes it *survivable*. The test of a
design is not how it looks today but how it absorbs the change that arrives next quarter.

"Class" below means any unit that bundles state with behavior — a class, a module with private
state, a struct plus its functions. The rules hold for all of them.

## Contents

- [Classes should be small](#classes-should-be-small)
- [Single Responsibility Principle](#single-responsibility-principle)
- [Cohesion](#cohesion)
- [Encapsulation](#encapsulation)
- [Organizing for change](#organizing-for-change)
- [Dependency inversion and injection](#dependency-inversion-and-injection)
- [Objects vs. data structures](#objects-vs-data-structures)
- [The Law of Demeter](#the-law-of-demeter)
- [Prefer polymorphism to switch](#prefer-polymorphism-to-switch)
- [Rules of simple design](#rules-of-simple-design)
- [Concurrency](#concurrency)

## Classes should be small

For functions we count lines; for classes we count **responsibilities**.

The name is the measuring stick. If you cannot name a class in about 25 characters without
`Manager`, `Processor`, `Handler`, `Data`, `Info`, `Util`, or "and", it is doing too much. Those
words are what we reach for when there is more than one responsibility to name.

`SuperDashboard` with focus-tracking methods *and* `major_version()`, `minor_version()`,
`build_number()` is two classes: version reporting has nothing to do with focus. Extract `Version`
and it becomes reusable and independently testable.

"Many small classes are harder to navigate" — the opposite is true in practice. With small classes
you read one small file to understand one idea; with big ones you read the whole file every time.

## Single Responsibility Principle

**A class should have one, and only one, reason to change.**

"Reason to change" means *a stakeholder or force that could demand a modification*. A class that
renders HTML and computes tax has two: the design team and the tax authority.

Identifying responsibilities:
- List the reasons this file might need editing next year. More than one? Split.
- Do some methods use only fields A and B, and others only C and D? Two classes hiding in one.
- Do the imports span layers (database *and* UI)? Two layers.

Getting a program *working* and getting it *clean* are different activities, and most people stop
after the first. Treat "organize into single-responsibility pieces" as a required second pass.

## Cohesion

A class is cohesive when its methods use its fields — ideally most methods touching most fields.

**Maintaining cohesion produces many small classes, and that is the point.** When you split a big
function and find yourself threading four locals into every helper, those locals want to be fields
of a new class:

```
# before: shared state threaded through helpers
function render(rows, width, palette, locale): ...
function header(width, palette, locale): ...
function body(rows, width, locale): ...
function footer(width, palette): ...

# after: the shared state became a class; each method takes almost nothing
class ReportRenderer(width, palette, locale):
    function render(rows): ...
    private function header(): ...
    private function body(rows): ...
    private function footer(): ...
```

Losing cohesion in a big function, then splitting it into classes, is one of the most productive
moves in the discipline. Watch for it.

## Encapsulation

Default everything to the most restrictive visibility that works; loosen only with a reason.

- Private state, public behavior. Expose the interface first in the type's body.
- **Immutability by default:** no setters, read-only fields, value types for data. Mark every
  operation that doesn't mutate as such where the language can express it.
- Computed values that read like attributes may be properties; don't write getter/setter pairs
  for plain data.
- Where the language has no access control, make the type **opaque**: expose only a handle and
  functions in the interface, keep the layout in the implementation. Callers then physically
  cannot reach in.

Relaxing encapsulation for tests is sometimes the right trade, but treat it as a last resort.
Needing to reach inside usually means a hidden collaborator wants to be extracted and tested alone.

## Organizing for change

Most systems change constantly. Clean design means most changes touch one place.

**Open/Closed: open for extension, closed for modification.** Adding a new kind of thing should
mean adding a class, not editing a switch in six files.

```
# before — every new report type edits this function
function generate(type, data):
    if type == "pdf":  ...50 lines...
    if type == "csv":  ...40 lines...
    if type == "html": ...60 lines...
    raise InvalidArgument(type)

# after — adding XLSX means adding one class and one registration
interface ReportFormat:
    id
    function render(data) -> bytes

class ReportGenerator(available_formats):
    formats_by_id = {f.id: f for f in available_formats}
    function generate(format_id, data):
        if format_id not in formats_by_id: raise UnknownFormat(format_id)
        return formats_by_id[format_id].render(data)
```

**Isolate from change.** Depend on abstractions at every seam you expect to move: the database,
the clock, the network, the filesystem, the payment provider. Testability and changeability are the
same property viewed from two angles.

```
# before — untestable: hits the real exchange
class Portfolio:
    function value(): return TokyoStockExchange().current_price(symbol) * shares

# after — the seam makes it testable *and* swappable
class Portfolio(exchange: StockExchange):
    function value(): return exchange.current_price(symbol) * shares
```

## Dependency inversion and injection

**High-level policy should not depend on low-level detail; both should depend on abstractions.**

Business logic should not construct its infrastructure. Keep object *wiring* at the edge (`main`,
a composition root, a DI container) and let everything else receive its collaborators.

```
# bad — the rule engine reaches out and grabs the world
class PricingEngine:
    constructor():
        db = connect(env["DSN"])       # untestable, unswappable
        clock = system_clock

# good — collaborators arrive from outside; the signature lists the needs
class PricingEngine(rates: RateRepository, clock: Clock)
```

Constructor injection is the default: dependencies are explicit and impossible to forget. Setter
injection and service locators hide dependencies — avoid them unless a framework forces it.

## Objects vs. data structures

These are opposites, and confusing them creates the worst of both.

- **Objects** hide data and expose behavior. Easy to add new *types*; hard to add new *operations*.
- **Data structures** expose data and have little behavior. Easy to add new *operations*; hard to
  add new *types*.

Choose by which axis will change. A DTO, config record, or wire-format struct is a plain data
structure — public fields, no fake getters. A domain concept with rules is an object.

The failure mode is the **hybrid**: getters and setters for every field *and* significant
behavior — hard to extend in either direction. Push the behavior back in.

**Feature envy** — a method more interested in another class's data than its own — means behavior
lives in the wrong place. `PayCalculator.weekly_pay(employee)` that reads five employee fields
wants to be `employee.weekly_pay()`.

## The Law of Demeter

A method talks only to: itself, its fields, its parameters, and objects it creates — not to objects
returned by other objects.

```
# train wreck: couples this code to Options, ScratchDir, and File at once
out_dir = ctxt.options().scratch_dir().absolute_path()

# ask for the job, not the path to it
out = ctxt.create_scratch_file_stream(file_name)
```

Demeter applies to *objects*, not to data structures or fluent builders:
`builder.name("x").age(3).build()` and `config.server.port` are fine.

## Prefer polymorphism to switch

A switch on a type code is fine **once**, in a factory, where it turns data into objects. Elsewhere
the same switch reappears in every module that cares about the type, and adding a case means
editing all of them.

```
# bad — this switch gets copy-pasted into calculate_hours(), deliver_pay(), ...
function calculate_pay(employee):
    switch employee.type:
        COMMISSIONED: return commissioned_pay(employee)
        HOURLY:       return hourly_pay(employee)
        SALARIED:     return salaried_pay(employee)

# good — one switch, buried in a factory; everything else is polymorphic
interface Employee:
    function calculate_pay()
    function calculate_hours()
    function deliver_pay(pay)

function make_employee(record):          # the one legitimate switch
    switch record.type:
        COMMISSIONED: return CommissionedEmployee(record)
        HOURLY:       return HourlyEmployee(record)
        SALARIED:     return SalariedEmployee(record)
```

Without built-in polymorphism, the same move is a dispatch table indexed by type.

**Counter-note:** an exhaustive switch over a *closed* sum type, with the compiler checking
exhaustiveness, is legitimate and often *better* when the set of types is fixed and the set of
operations keeps growing. Choose by which axis varies. Make illegal states unrepresentable.

## Rules of simple design

In priority order, a design is "simple enough" when it:

1. **Runs all the tests.** Making a system testable *forces* small, decoupled classes.
2. **Contains no duplication.** Every piece of knowledge has one authoritative expression.
3. **Expresses the programmer's intent.** Good names, small functions, standard patterns.
4. **Minimizes classes and methods.** Real but *lowest-priority*: don't let dogmatic decomposition
   produce hundreds of trivial indirections.

If removing duplication or expressing intent conflicts with minimizing class count, add the class.

## Concurrency

Concurrency separates *what* from *when*. Its bugs do not reproduce, do not show in tests, and
usually appear first in production.

**Design:**
- **Keep concurrency code separate** from business logic. A class manages one or the other.
- **Limit shared data.** Every shared mutable variable is a liability; keep critical sections tiny.
- **Prefer copies and immutable values.** Copying is almost always cheaper than the bugs.
- **Make workers independent** — own input, own output, no synchronization needed.
- **Use the platform's concurrency library** (concurrent maps, atomics, executors, channels).
  Hand-rolled locking loses.
- **Name your execution model** — producer/consumer, readers/writers — to reach the known-correct
  solution.
- **Two correct synchronized calls in sequence are not atomic together.** Deadlock lives here.
- **Design shutdown early.** Retrofitting it produces deadlocks in the cleanup path.

**Testing threaded code:**
- Treat spurious failures as real threading bugs, never as "flaky". One failure in 500 runs is the
  truth.
- Get the non-threaded logic working first, so failures aren't ambiguous.
- Make thread counts, pool sizes, and delays configurable to shake out timing bugs.
- Run with more threads than cores, repeatedly, with jitter injected; use race detectors and
  sanitizers where the platform has them.

## Related heuristics

`smells-catalog.md`: **G6** wrong level of abstraction, **G7** base classes depending on
derivatives, **G13** artificial coupling, **G14** feature envy, **G17** misplaced responsibility,
**G18** inappropriate static, **G22** make logical dependencies physical, **G23** prefer
polymorphism, **G36** avoid transitive navigation.
