# Refactoring

Refactoring is changing the structure of code **without changing its observable behavior**. That
definition is strict and load-bearing: the moment behavior changes, it is not a refactor, and it
must not be reviewed, committed, or reasoned about as one.

## Contents

- [The Boy Scout Rule](#the-boy-scout-rule)
- [Preconditions](#preconditions)
- [The workflow](#the-workflow)
- [When to refactor and when not to](#when-to-refactor-and-when-not-to)
- [Catalog of moves](#catalog-of-moves)
- [Extended worked example](#extended-worked-example)
- [Refactoring legacy code without tests](#refactoring-legacy-code-without-tests)
- [Commit hygiene](#commit-hygiene)

## The Boy Scout Rule

**Leave the code cleaner than you found it.** Not rewritten — *cleaner*. One improvement per visit:

- rename one badly-named variable
- extract one well-named function from a long one
- delete one dead branch or one commented-out block
- replace one magic number with a named constant
- add one missing test for the thing you just touched

Codebases are not saved by heroic rewrites; they are saved by thousands of these. The rewrite
almost always loses, because the old system keeps accreting features while the new one struggles
to reach parity, and the team ends up maintaining two.

## Preconditions

Do not start without these.

1. **A green test suite.** Refactoring without tests is just editing and hoping. If there are no
   tests, write characterization tests first (see below).
2. **A clean working tree.** Commit or stash. You need to be able to abandon a bad refactor
   instantly.
3. **A defined scope.** Know which smell you are removing before you start. "Cleaning up" without
   a target expands until the diff is unreviewable.
4. **Separate commits.** Behavior changes never ride along with refactors. A reviewer must be able
   to trust a "refactor" commit changed nothing observable, and skim it accordingly.

## The workflow

```
1. Run tests.                → green
2. Identify one smell.       → e.g. "processOrders() does four things"
3. Make one small move.      → extract one function
4. Run tests.                → green
5. Commit (or continue).
6. Repeat from 2.
```

The discipline is in step 4. Running the suite after every move sounds slow; it is what lets you
move fast, because when something breaks you know it was the last thirty seconds of work, not the
last two hours. If your suite is too slow to run every couple of minutes, fixing that is the
higher-priority refactor.

**Use the IDE's automated refactorings** where they exist — rename, extract method, inline, move,
change signature. They are mechanically correct in ways manual editing is not, especially for
renames across a large codebase.

## When to refactor and when not to

**Refactor when:**
- You are about to add a feature and the current structure makes it awkward. *Make the change
  easy, then make the easy change.*
- You are fixing a bug and the code's shape hid it.
- You just got a test to pass (the third step of the TDD cycle — the default and most important
  case).
- You are reading code to understand it, and understanding takes effort you could bank for the
  next reader.
- The smell is on your path anyway (Boy Scout Rule).

**Don't refactor when:**
- The code is genuinely done and untouched — "we might need to change it someday" is not a reason.
- You are mid-incident. Fix the outage; refactor after.
- A rewrite is genuinely warranted and scheduled (rare, and needs its own decision).
- You cannot test it and cannot get it under test. Then reduce the blast radius instead: wrap it,
  don't reorganize it.
- The deadline is tonight and the change is not required for correctness. Note it, file it, move
  on. *But be honest about how often "later" arrives.*

## Catalog of moves

Each entry: the smell, the move, and the mechanics.

### Extract Function
**Smell:** long function, or a block preceded by an explanatory comment.
**Mechanics:** name the new function after *what* it does, not how. Move the block. Pass what it
reads; return what it writes. If it writes more than one thing, you extracted the wrong boundary.

### Inline Function
**Smell:** a function whose body is as clear as its name, adding only indirection.
**Mechanics:** replace calls with the body, delete the function. The opposite of Extract, and just
as often correct — over-extraction is real.

### Extract Variable (Explanatory Variable)
**Smell:** a complex expression, especially a compound conditional.
**Mechanics:** name each sub-expression for its *meaning*, not its computation.
```java
// before
if (platform.toUpperCase().indexOf("MAC") > -1 && browser.contains("IE") && wasInitialized()) {

// after
boolean isMacOs         = platform.toUpperCase().contains("MAC");
boolean isInternetExplorer = browser.contains("IE");
boolean wasResized      = resize > 0;
if (isMacOs && isInternetExplorer && wasInitialized() && wasResized) {
```

### Rename
**Smell:** the name doesn't match what the thing is or does.
**Mechanics:** use the IDE. Rename in its own commit so the diff is trivially reviewable.

### Introduce Parameter Object
**Smell:** three or more parameters that travel together, repeatedly.
**Mechanics:** create a small type, move the fields in, update signatures. Often reveals a domain
concept nobody had named (`DateRange`, `Money`, `PagingSpec`).

### Replace Magic Number with Named Constant
**Smell:** a literal whose meaning must be inferred.
**Mechanics:** `const`/`final`/module-level constant with a name that states the meaning *and the
unit*. Applies to strings and to `""`, `0`, `-1` sentinels too.

### Replace Conditional with Polymorphism
**Smell:** the same `switch`/`if`-chain on a type code appearing in more than one place.
**Mechanics:** create a type per case, move each branch into an override, keep one switch in a
factory. See `classes-and-design.md`.

### Replace Nested Conditional with Guard Clauses
**Smell:** the happy path is buried three levels deep.
**Mechanics:** invert each precondition into an early return at the top; the main logic
un-indents. See `functions.md`.

### Decompose Conditional
**Smell:** a hairy `if`/`else` where you cannot tell what the condition means.
**Mechanics:** extract the condition into a named predicate and each branch into a named function.
```python
# before
if date < SUMMER_START or date > SUMMER_END:
    charge = quantity * winter_rate + winter_service_charge
else:
    charge = quantity * summer_rate

# after
charge = winter_charge(quantity) if is_winter(date) else summer_charge(quantity)
```

### Encapsulate Conditional / Boundary Condition
**Smell:** `if (timer.hasExpired() && !timer.isRecurrent())`, or `level + 1` computed in five
places.
**Mechanics:** `if (shouldBeDeleted(timer))`. For boundaries, compute once into a named variable:
`int nextLevel = level + 1;`.

### Encapsulate Field / Hide Delegate
**Smell:** callers reaching through your object into its collaborators (`a.getB().getC()`).
**Mechanics:** add a method that does what the caller actually wanted; make the field private.

### Move Function/Field
**Smell:** feature envy — a method uses another class's data more than its own.
**Mechanics:** move it to the class it envies. Often shrinks both classes.

### Extract Class
**Smell:** a class with two responsibilities; a subset of fields used by only a subset of methods.
**Mechanics:** create the new class, move that field/method cluster, hold a reference. Watch the
parameter lists of the remaining methods shrink — that shrinkage is the confirmation you split
correctly.

### Replace Loop with Pipeline / Algorithm
**Smell:** a hand-rolled loop doing filter/map/reduce.
**Mechanics:** `std::ranges` / streams / comprehensions. Usually shorter, often faster, and the
intent becomes visible.
```cpp
// before
std::vector<std::string> names;
for (const auto& u : users) { if (u.active) names.push_back(u.name); }

// after
auto names = users | std::views::filter(&User::active)
                   | std::views::transform(&User::name);
```

### Remove Dead Code
**Smell:** unreachable branches, unused functions, commented-out blocks, flags always one value.
**Mechanics:** delete. Version control remembers. Dead code confuses every future reader and
survives forever if you don't kill it now.

### Split Loop / Split Variable
**Smell:** one loop doing two accumulations; one variable reused for two meanings.
**Mechanics:** two loops (then extract each), two variables with two names. Clarity beats the
micro-optimization of a single pass — and if profiling later says otherwise, merge them back with
a comment saying why.

### Separate Query from Modifier
**Smell:** a function that both answers and changes something.
**Mechanics:** split into a pure query and a command. See `functions.md`.

## Extended worked example

A real-shaped legacy function, cleaned in steps. **Tests are green after every step.**

**Step 0 — the starting point (Java)**

```java
public String report(List<int[]> data, int mode) {
    String s = "";
    double t = 0;
    for (int i = 0; i < data.size(); i++) {
        int[] r = data.get(i);
        if (r[2] != 0) {
            double v = r[0] * r[1];
            if (mode == 1) { v = v * 1.2; }
            else if (mode == 2) { v = v * 0.8; }
            t += v;
            s = s + r[0] + "\t" + r[1] + "\t" + String.format("%.2f", v) + "\n";
        }
    }
    s = s + "TOTAL\t\t" + String.format("%.2f", t) + "\n";
    return s;
}
```
Smells: magic indices, magic multipliers, a mode flag, mixed abstraction levels, string
concatenation in a loop, meaningless names, one function doing filtering + pricing + formatting +
totalling.

**Step 1 — name things (Rename, Extract Variable).**
```java
public String report(List<int[]> lines, int mode) {
    StringBuilder report = new StringBuilder();
    double total = 0;
    for (int[] line : lines) {
        int quantity  = line[0];
        int unitPrice = line[1];
        int status    = line[2];
        if (status != 0) {
            double amount = quantity * unitPrice;
            ...
        }
    }
}
```

**Step 2 — replace the array with a type (Introduce Parameter Object).**
```java
record LineItem(int quantity, int unitPrice, Status status) {
    int subtotal() { return quantity * unitPrice; }
}
```
The `[0]/[1]/[2]` decoding disappears from every call site, and `subtotal()` lands where the data
lives instead of where the loop happens.

**Step 3 — kill the mode flag (Replace Conditional with Polymorphism).**
```java
enum PricingTier {
    STANDARD(1.00), PREMIUM(1.20), DISCOUNT(0.80);
    private final double multiplier;
    PricingTier(double multiplier) { this.multiplier = multiplier; }
    BigDecimal apply(BigDecimal amount) { return amount.multiply(BigDecimal.valueOf(multiplier)); }
}
```
The magic numbers now have names and one home. `report(lines, 1)` becomes
`report(lines, PricingTier.PREMIUM)` — readable at the call site.

**Step 4 — extract the responsibilities (Extract Function, Split Loop).**
```java
public String report(List<LineItem> lines, PricingTier tier) {
    List<LineItem> billable = lines.stream().filter(LineItem::isBillable).toList();
    return formatLines(billable, tier) + formatTotal(totalFor(billable, tier));
}

private BigDecimal totalFor(List<LineItem> lines, PricingTier tier) {
    return lines.stream().map(line -> tier.apply(line.subtotal()))
                .reduce(BigDecimal.ZERO, BigDecimal::add);
}

private String formatLines(List<LineItem> lines, PricingTier tier) {
    return lines.stream().map(line -> formatLine(line, tier)).collect(joining("\n", "", "\n"));
}

private String formatLine(LineItem line, PricingTier tier) {
    return "%d\t%d\t%.2f".formatted(line.quantity(), line.unitPrice(), tier.apply(line.subtotal()));
}

private String formatTotal(BigDecimal total) {
    return "TOTAL\t\t%.2f%n".formatted(total);
}
```

**Step 5 — fix the correctness bug the cleanup exposed.** `double` for money is wrong; the
refactor made it visible, so switch to `BigDecimal` — **in its own commit, with its own test**,
because *that* is a behavior change.

Result: four small named functions, no magic numbers, no flag argument, no array indexing, a
domain type, and a latent money bug found and fixed. Each step was mechanical and verified.

## Refactoring legacy code without tests

The chicken-and-egg problem: you need tests to refactor safely, but the code is untestable.

**Break it with the smallest possible safe change.**

1. **Find a seam** — a place where behavior can be altered without editing in place: a virtual
   method, a parameter, an import, a link-time substitution.
2. **Apply extract-and-inject**, the lowest-risk move there is: take the untestable dependency
   (a `new`, a static call, a global, a clock) and lift it into a constructor parameter or
   argument. Nothing else changes.
   ```java
   // before — cannot test without a real database
   public class Report {
       public String render() {
           Data d = new DatabaseGateway().load();   // <-- the obstacle
           ...
   ```
   ```java
   // after — one parameter added; behavior identical; now fakeable
   public class Report {
       private final Gateway gateway;
       public Report(Gateway gateway) { this.gateway = gateway; }
       public String render() {
           Data d = gateway.load();
   ```
3. **Write characterization tests** that assert what the code *currently* does. If a test fails,
   fix the test to match reality — you're documenting, not judging.
4. **Now refactor**, with the net.
5. **Then** change behavior, separately.

Where a seam genuinely cannot be made (a 400-line static method calling four singletons), fall
back to a **golden-master test**: capture the output for a large set of realistic inputs, store
it, and assert future runs match byte-for-byte. Crude, but it pins behavior well enough to start
carving.

## Commit hygiene

- **One refactoring type per commit.** "Rename `x` to `elapsed_days`" and "extract
  `validate_header`" are two commits.
- **Message says what and why**: `refactor: extract validate_header from parse (no behavior
  change)`.
- **Never mix** `refactor:` and `fix:`/`feat:` in one commit. If you notice a bug while
  refactoring, finish the refactor, commit it, then fix the bug in the next commit with a test
  that fails first.
- **Keep refactor commits reviewable**: if the diff exceeds a few hundred lines, split it. The
  point of a mechanical refactor commit is that a reviewer can verify it *is* mechanical.

## Related heuristics

`smells-catalog.md`: **G5** duplication, **G9** dead code, **G12** clutter, **G19** use
explanatory variables, **G23** prefer polymorphism, **G25** replace magic numbers with named
constants, **G28** encapsulate conditionals, **G29** avoid negative conditionals, **G33**
encapsulate boundary conditions.
