# Classes, Modules, and Design

Functions make code readable; class and module structure makes it *survivable*. The test of a
design is not how it looks today but how it absorbs the change that arrives next quarter.

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
- [Design rules of simple design](#design-rules-of-simple-design)
- [Concurrency](#concurrency)

## Classes should be small

For functions we count lines; for classes we count **responsibilities**.

The name is the measuring stick. If you cannot name a class in about 25 characters without using
`Manager`, `Processor`, `Handler`, `Data`, `Info`, `Util`, or the word "and", the class is doing
too much. Those words are what we reach for when we cannot name the actual responsibility —
because there is more than one.

```java
// smells: "SuperDashboard" — vague name, unrelated members
public class SuperDashboard extends JFrame implements MetaDataUser {
    public Component getLastFocusedComponent();
    public void setLastFocused(Component c);
    public int getMajorVersionNumber();
    public int getMinorVersionNumber();
    public int getBuildNumber();
    // ...70 more methods
}
```
Version reporting has nothing to do with focus tracking. `Version` wants to be its own tiny class
— and once extracted, it is reusable and independently testable.

The usual objection is that many small classes are harder to navigate than a few big ones. The
opposite is true in practice: with small classes you read one small file to understand one idea.
With big classes you read the whole file every time, because you cannot tell what's relevant.

## Single Responsibility Principle

**A class should have one, and only one, reason to change.**

"Reason to change" means *a stakeholder or force that could demand a modification*. A class that
renders HTML and computes tax has two: the design team and the tax authority. When either shows
up, you touch the same file, risk the other behavior, and fight for the merge.

Identifying responsibilities:
- List the reasons this file might need editing next year. More than one? Split.
- Look at the fields: do some methods use only fields A and B, and others only C and D? That's
  two classes hiding in one.
- Look at the imports: does the class pull in both `java.sql` and `javax.swing`? Two layers.

SRP is the most-cited and least-applied principle in software. The reason is that getting a
program *working* and getting it *clean* are different activities, and most people stop after the
first. Treat "organize into single-responsibility pieces" as a required second pass, not optional.

## Cohesion

A class is cohesive when its methods use its fields — ideally most methods touching most fields.
High cohesion means the pieces genuinely belong together.

```python
class Stack:                     # maximally cohesive: every method uses both fields
    def __init__(self) -> None:
        self._elements: list[int] = []

    def size(self) -> int:            return len(self._elements)
    def push(self, value: int) -> None: self._elements.append(value)
    def pop(self) -> int:
        if not self._elements:
            raise IndexError("pop from empty stack")
        return self._elements.pop()
```

**Maintaining cohesion produces many small classes, and that is the point.** When you break a big
function into small ones and find yourself passing four locals into each helper, those locals want
to be fields of a new class. Promote them, and the parameter lists collapse:

```python
# before: helpers threaded through a big function
def render(rows, width, palette, locale): ...
def _header(width, palette, locale): ...
def _body(rows, width, locale): ...
def _footer(width, palette): ...

# after: the shared state became a class; each method now takes almost nothing
class ReportRenderer:
    def __init__(self, width: int, palette: Palette, locale: Locale) -> None: ...
    def render(self, rows: Sequence[Row]) -> str: ...
    def _header(self) -> str: ...
    def _body(self, rows: Sequence[Row]) -> str: ...
    def _footer(self) -> str: ...
```

That refactoring — losing cohesion in a big function, then splitting it into classes — is one of
the most productive moves in the whole discipline. Watch for it.

## Encapsulation

Default everything to the most restrictive visibility that works, and loosen only with a reason.

- **Java**: private fields, package-private for test seams if needed, public only for the API.
  Prefer immutability: `final` fields, no setters, `record` for value types.
- **C++**: `private` members with a trailing underscore, `public` interface first in the class
  body, `const` on every method that doesn't mutate, and pass by `const&` unless you need a copy.
- **Python**: single `_leading_underscore` for internals — a convention that mature codebases
  actually respect. Use `@property` when a computed value should read like an attribute; don't
  write Java-style `get_x()`/`set_x()` for plain data.
- **C**: put the struct definition in the `.c` file and expose only an opaque `typedef struct foo
  foo;` in the header. Callers then physically cannot reach in.

```c
/* widget.h — opaque handle: the layout is nobody's business */
typedef struct widget widget;

widget *widget_create(const char *label);
void    widget_destroy(widget *w);
int     widget_set_label(widget *w, const char *label);
const char *widget_label(const widget *w);
```

Relaxing encapsulation for tests is sometimes the right trade — package-private in Java, a
`_`-prefixed hook in Python — but treat it as a last resort. Needing to reach inside usually means
the class has a hidden collaborator that wants to be extracted and tested on its own.

## Organizing for change

Most systems change constantly. Clean design means most changes touch one place.

**Open/Closed: open for extension, closed for modification.** Adding a new kind of thing should
mean adding a class, not editing a switch statement in six files.

```java
// before — every new report type edits this class
public class ReportGenerator {
    public String generate(String type, Data d) {
        if (type.equals("pdf"))  { ...50 lines... }
        if (type.equals("csv"))  { ...40 lines... }
        if (type.equals("html")) { ...60 lines... }
        throw new IllegalArgumentException(type);
    }
}

// after — adding XLSX means adding one class and one registration
public interface ReportFormat {
    String id();
    byte[] render(Data data);
}

public class ReportGenerator {
    private final Map<String, ReportFormat> formats;
    public ReportGenerator(Set<ReportFormat> available) {
        this.formats = available.stream().collect(toMap(ReportFormat::id, identity()));
    }
    public byte[] generate(String formatId, Data data) {
        ReportFormat format = formats.get(formatId);
        if (format == null) throw new UnknownFormatException(formatId);
        return format.render(data);
    }
}
```

**Isolate from change.** Depend on abstractions, not concretions, at every seam you expect to
move: the database, the clock, the network, the filesystem, the payment provider. That isolation
is what makes the code testable, and testability and changeability turn out to be the same
property viewed from two angles.

```java
// before — untestable: hits the real exchange, real clock
public class Portfolio {
    public Money value() {
        return new TokyoStockExchange().currentPrice(symbol).times(shares);
    }
}

// after — the seam makes it testable *and* swappable
public class Portfolio {
    private final StockExchange exchange;
    public Portfolio(StockExchange exchange) { this.exchange = exchange; }
    public Money value() { return exchange.currentPrice(symbol).times(shares); }
}
```

## Dependency inversion and injection

**High-level policy should not depend on low-level detail; both should depend on abstractions.**

Practically: business logic should not `new` up its infrastructure. Construction is a separate
concern from use — keep object *wiring* at the edge of the system (`main`, a composition root, a
DI container) and let everything else receive its collaborators.

```python
# bad — the rule engine reaches out and grabs the world
class PricingEngine:
    def __init__(self) -> None:
        self._db = psycopg.connect(os.environ["DSN"])       # untestable, unswappable
        self._clock = datetime.now


# good — collaborators arrive from outside; the class states its needs in its signature
class PricingEngine:
    def __init__(self, rates: RateRepository, clock: Clock) -> None:
        self._rates = rates
        self._clock = clock
```

Constructor injection is the default. It makes dependencies explicit and impossible to forget,
and the constructor signature becomes an honest list of what the class needs. Setter injection
and service locators hide dependencies — avoid them unless a framework forces your hand.

Beware **transitive navigation**: `a.getB().getC().doSomething()` couples you to the whole chain.
Ask for what you need, don't navigate to it.

## Objects vs. data structures

These are opposites, and confusing them creates the worst of both.

- **Objects** hide their data and expose behavior. Easy to add new *types* (implement the
  interface); hard to add new *operations* (touch every type).
- **Data structures** expose their data and have little behavior. Easy to add new *operations*
  (write one function); hard to add new *types* (touch every function).

Choose deliberately based on which axis will change. A DTO, a config record, a wire-format struct
should be a plain data structure — public fields, no fake getters. A domain concept with rules
should be an object with behavior and hidden state.

The failure mode is the **hybrid**: a class with public getters and setters for every field *and*
significant behavior. It's hard to extend in either direction. Usually it's an object that has
been strip-mined by an ORM or a framework — push the behavior back in.

**Feature envy** — a method more interested in another class's data than its own — is the signal
that behavior lives in the wrong place:

```java
// bad — HourlyPayCalculator is envious of HourlyEmployee
public Money calculateWeeklyPay(HourlyEmployee e) {
    int tenthRate = e.getTenthRate().getPennies();
    int tenthsWorked = e.getTenthsWorked();
    // ...
}

// good — the employee knows how to compute its own pay
public class HourlyEmployee {
    public Money weeklyPay() { ... }
}
```

## The Law of Demeter

A method should only talk to: itself, its own fields, its parameters, and objects it creates. Not
to objects returned by other objects.

```java
// train wreck: couples this code to Options, ScratchDir, and File all at once
String outDir = ctxt.getOptions().getScratchDir().getAbsolutePath();
```

The fix depends on what you actually need. If you need the directory, don't ask for the path —
ask the context to do the job:

```java
BufferedOutputStream out = ctxt.createScratchFileStream(fileName);
```

Now `ctxt` can change its internals freely. Note the exception: Demeter applies to *objects*, not
to data structures or fluent builders — `builder.name("x").age(3).build()` is fine, and
`config.server.port` on a plain config struct is fine.

## Prefer polymorphism to switch

A `switch` on a type code is fine **once**, in a factory, where it turns data into objects. It is
a smell everywhere else, because the same switch tends to reappear in every module that cares
about the type, and adding a case means editing all of them.

```java
// bad — this switch will be copy-pasted into calculateHours(), deliverPay(), ...
public Money calculatePay(Employee e) {
    switch (e.type) {
        case COMMISSIONED: return calculateCommissionedPay(e);
        case HOURLY:       return calculateHourlyPay(e);
        case SALARIED:     return calculateSalariedPay(e);
        default: throw new InvalidEmployeeType(e.type);
    }
}

// good — one switch, buried in a factory; everything else is polymorphic
public abstract class Employee {
    public abstract Money calculatePay();
    public abstract Money calculateHours();
    public abstract void  deliverPay(Money pay);
}

public class EmployeeFactoryImpl implements EmployeeFactory {
    public Employee makeEmployee(EmployeeRecord r) {
        return switch (r.type()) {                 // the one legitimate switch
            case COMMISSIONED -> new CommissionedEmployee(r);
            case HOURLY       -> new HourlyEmployee(r);
            case SALARIED     -> new SalariedEmployee(r);
        };
    }
}
```

C has no polymorphism built in, but the same move exists: a struct of function pointers (a vtable)
or a dispatch table indexed by type. C++ offers virtual functions, `std::variant` + `std::visit`,
or templates depending on whether you need runtime or compile-time dispatch. Python has duck
typing and `functools.singledispatch`.

**Counter-note:** an exhaustive `switch` over a closed enum, with the compiler checking
exhaustiveness (Java sealed interfaces + pattern matching, C++ `std::variant`, Python
`match` + `assert_never`), is a legitimate and often *better* design when the set of types is
fixed and the set of operations keeps growing. Choose by which axis varies.

## Design rules of simple design

In priority order, a design is "simple enough" when it:

1. **Runs all the tests.** A system that cannot be verified must not be shipped. This rule comes
   first because making a system testable *forces* small, single-purpose, decoupled classes.
2. **Contains no duplication.** Every piece of knowledge has one authoritative expression.
3. **Expresses the intent of the programmer.** Good names, small functions, standard vocabulary
   and patterns — write for the reader who maintains it.
4. **Minimizes the number of classes and methods.** A real but *lowest-priority* concern: don't
   let dogmatic decomposition produce hundreds of trivial indirections. Pragmatism outranks
   purity here.

Note the ordering: eliminating duplication and expressing intent beat minimizing class count. If
those conflict, add the class.

## Concurrency

Concurrency is a decoupling strategy — separating *what* from *when* — and it deserves its own
clean-design treatment because concurrency bugs do not reproduce, do not show up in tests, and
usually appear first in production.

**Design principles:**
- **Keep concurrency code separate from everything else.** Threading is a responsibility; a class
  should manage concurrency *or* business logic, not both.
- **Limit the scope of shared data.** Every shared mutable variable is a liability. Use `private`,
  keep critical sections tiny, and prefer one synchronized method over several.
- **Use copies of data.** Copying avoids sharing entirely, and the copy is almost always cheaper
  than the bugs. Immutable value objects are the strongest version of this.
- **Make threads as independent as possible.** Each thread working from its own unshared input,
  producing its own output, needs no synchronization at all.
- **Know your library.** `ConcurrentHashMap`, `java.util.concurrent`, `std::atomic` and
  `std::jthread`, `concurrent.futures`, channels. Hand-rolled locking loses to the library.
- **Know your execution models** — producer/consumer, readers/writers, dining philosophers — and
  name yours. Recognizing the shape leads you to the known-correct solution.
- **Beware dependencies between synchronized methods.** Two correct synchronized methods called in
  sequence are not atomic together. Deadlock lives here.
- **Shutdown is hard.** Design it early; retrofitting graceful shutdown reliably produces
  deadlocks in the cleanup path.

**Testing threaded code:**
- Treat spurious failures as real threading bugs, never as "flaky tests". A test that fails once
  in 500 runs is telling you the truth.
- Get the non-threaded logic working first, so failures aren't ambiguous.
- Make the threading pluggable and tunable — number of threads, pool sizes, delays as config — so
  you can shake out timing bugs.
- Run with more threads than processors, on multiple platforms, repeatedly, with jitter injected
  at plausible interleaving points.
- Use the tools: ThreadSanitizer / Helgrind (C/C++), Java Flight Recorder + jcstress,
  `pytest-xdist` plus deterministic scheduling harnesses.

## Related heuristics

`smells-catalog.md`: **G6** wrong level of abstraction, **G7** base classes depending on
derivatives, **G13** artificial coupling, **G14** feature envy, **G17** misplaced responsibility,
**G18** inappropriate static, **G22** make logical dependencies physical, **G23** prefer
polymorphism, **G36** avoid transitive navigation.
