# Smells and Heuristics Catalog

A reference for reviewing and cleaning code. Each entry: the smell, why it costs you, and the fix.

The ID scheme (**C**omments, **E**nvironment, **F**unctions, **G**eneral, **J**ava/language,
**N**ames, **T**ests) follows the catalog in Robert C. Martin's *Clean Code* (2008), Chapter 17,
so IDs can be cited in review and cross-referenced with the book. The explanations here are
written for this skill and stated language-neutrally.

## Two ways to use this file — pick one deliberately

This is the largest reference in the skill (~4,800 tokens). Read it whole only when you mean to.

**1. Targeted lookup — you already have an ID.** This is the normal path after running
a linter or review that reports findings tagged with these IDs. Do **not** load the
file; grep the single entry:

```bash
grep -A4 '^\*\*G25' references/smells-catalog.md      # one entry, ~60 tokens
grep -A4 -E '^\*\*(F3|G25|G30)' references/smells-catalog.md   # several at once
```

Each entry names its related IDs, so follow those links rather than reading neighbours by hand.

**2. Browse — you are reviewing code and looking for what is wrong.** Grep cannot help you find
a smell you have not named yet. Read [the index](#index) first; it is the whole catalog in one
line per entry. Open the full section only for the entries the index makes you suspicious of, and
finish with the [quick review checklist](#quick-review-checklist), which is written to be walked
top to bottom.

Reading the entire file is the right call only when doing a deep audit of unfamiliar code.

## Index

One line per entry — enough to recognize a smell, not enough to fix it. Grep the ID for the fix.

**Comments**

- `C1` — Inappropriate information
- `C2` — Obsolete comment
- `C3` — Redundant comment
- `C4` — Poorly written comment
- `C5` — Commented-out code

**Environment**

- `E1` — Build requires more than one step
- `E2` — Tests require more than one step

**Functions**

- `F1` — Too many arguments
- `F2` — Output arguments
- `F3` — Flag arguments
- `F4` — Dead function

**General**

- `G1` — Multiple languages in one source file
- `G2` — Obvious behavior is unimplemented
- `G3` — Incorrect behavior at the boundaries
- `G4` — Overridden safeties
- `G5` — Duplication
- `G6` — Code at wrong level of abstraction
- `G7` — Base classes depending on their derivatives
- `G8` — Too much information
- `G9` — Dead code
- `G10` — Vertical separation
- `G11` — Inconsistency
- `G12` — Clutter
- `G13` — Artificial coupling
- `G14` — Feature envy
- `G15` — Selector arguments
- `G16` — Obscured intent
- `G17` — Misplaced responsibility
- `G18` — Inappropriate static
- `G19` — Use explanatory variables
- `G20` — Function names should say what they do
- `G21` — Understand the algorithm
- `G22` — Make logical dependencies physical
- `G23` — Prefer polymorphism to if/else or switch/case
- `G24` — Follow standard conventions
- `G25` — Replace magic numbers with named constants
- `G26` — Be precise
- `G27` — Structure over convention
- `G28` — Encapsulate conditionals
- `G29` — Avoid negative conditionals
- `G30` — Functions should do one thing
- `G31` — Hidden temporal couplings
- `G32` — Don't be arbitrary
- `G33` — Encapsulate boundary conditions
- `G34` — Functions should descend only one level of abstraction
- `G35` — Keep configurable data at high levels
- `G36` — Avoid transitive navigation

**Language-specific**

- `J1` — Keep imports explicit
- `J2` — Don't inherit constants
- `J3` — Constants versus enums

**Names**

- `N1` — Choose descriptive names
- `N2` — Choose names at the appropriate level of abstraction
- `N3` — Use standard nomenclature where possible
- `N4` — Unambiguous names
- `N5` — Use long names for long scopes
- `N6` — Avoid encodings
- `N7` — Names should describe side effects

**Tests**

- `T1` — Insufficient tests
- `T2` — Use a coverage tool!
- `T3` — Don't skip trivial tests
- `T4` — An ignored test is a question about an ambiguity
- `T5` — Test boundary conditions
- `T6` — Exhaustively test near bugs
- `T7` — Patterns of failure are revealing
- `T8` — Test coverage patterns can be revealing
- `T9` — Tests should be fast

---

## Full entries

Jump: [Comments](#comments) · [Environment](#environment) · [Functions](#functions) ·
[General](#general) · [Language-specific](#language-specific) · [Names](#names) ·
[Tests](#tests) · [Quick review checklist](#quick-review-checklist)

## Comments

**C1 — Inappropriate information.** A comment holding data that belongs in version control, an
issue tracker, or a design doc: changelogs, author lists, ticket histories. *Fix:* delete; the
right system already holds it.

**C2 — Obsolete comment.** A comment that no longer describes the code. It is worse than none,
because readers trust it. *Fix:* update in the same edit as the code, or delete it. When you see a
stale comment, fix it immediately — it will only get staler.

**C3 — Redundant comment.** Says exactly what the code says (`i += 1  # increment i`, a doc comment on
a one-line getter). Pure noise that must be maintained. *Fix:* delete.

**C4 — Poorly written comment.** Rambling, cryptic, misspelled, or stating the obvious at length.
If it's worth writing, it's worth writing well — be brief, be correct, be grammatical. *Fix:*
rewrite or delete.

**C5 — Commented-out code.** An abomination. Nobody who follows you will dare delete it, so it
accumulates and rots, and readers waste time wondering if it matters. *Fix:* delete it. Git
remembers.

## Environment

**E1 — Build requires more than one step.** You should be able to check out and build with a
single command. Multi-step incantations get half-remembered, drift between machines, and make
onboarding a two-day ordeal. *Fix:* one command — `make`, `./gradlew build`, `cmake --build`,
`uv sync`. Put it in the README's first section.

**E2 — Tests require more than one step.** You should be able to run all tests with one command
too, from a fresh clone. If running tests needs a database, a VPN, and three env vars, they will
not be run. *Fix:* one command; containerize or fake the dependencies; keep a fast suite that
needs nothing external.

## Functions

**F1 — Too many arguments.** Zero is best, three is a lot, more than three needs strong
justification. Each argument multiplies the combinations to test and the ways to call it wrong.
*Fix:* parameter object, or move state onto the receiver.

**F2 — Output arguments.** Callers expect arguments to be inputs. `appendFooter(s)` — is `s`
being appended to, or appended? *Fix:* return the result. In C, where out-params are idiomatic,
name them `out_*` and document ownership and the failure guarantee.

**F3 — Flag arguments.** A boolean parameter announces the function does two things, and makes
every call site (`render(true)`) unreadable. *Fix:* two functions. If they share logic, extract
the shared part. If the value comes from config, use an enum or strategy, not a bool.

**F4 — Dead function.** A method nobody calls. It still gets read, maintained, refactored, and
compiled. *Fix:* delete it. Version control remembers.

## General

**G1 — Multiple languages in one source file.** A template mixing a host language, HTML, JavaScript, CSS, and SQL is
unreadable and untestable. *Fix:* minimize the number of languages per file; extract templates,
queries, and scripts to their own files. (Some mixing is unavoidable — keep it small and
contained.)

**G2 — Obvious behavior is unimplemented.** The Principle of Least Surprise: a function named
`day_of_week(name)` should handle `"monday"`, `"Monday"`, `"Mon"`. Missing obvious behavior makes
readers stop trusting the code and start reading every implementation. *Fix:* implement it or
document the restriction in the name and contract.

**G3 — Incorrect behavior at the boundaries.** Off-by-one, empty input, zero, overflow, the last
element. Don't rely on intuition — prove each boundary with a test. *Fix:* enumerate and test the
edges (see `tdd-and-tests.md`).

**G4 — Overridden safeties.** Ignoring compiler warnings, `# type: ignore`, `@SuppressWarnings`
scattered widely, disabling failing tests, `-Wno-everything`, `catch (...) {}`. Turning off the
alarm doesn't extinguish the fire. *Fix:* fix the cause; suppress narrowly and only with a comment
explaining why, at the smallest possible scope.

**G5 — Duplication.** The most important smell. Every copy is a place a fix can fail to land.
Forms: identical code (extract a function), similar `switch`/`if` chains on the same type
(polymorphism), similar algorithms differing in a step (template method / strategy). *Fix:*
find the abstraction. But see `functions.md` — code that merely looks alike, and changes for
different reasons, is not duplication.

**G6 — Code at wrong level of abstraction.** A base class or interface exposing a detail that only
one implementation cares about; a high-level policy class doing byte manipulation. Concepts must
be fully separated, not partially. *Fix:* move the detail down, or the policy up.

**G7 — Base classes depending on their derivatives.** A base class mentioning a subclass name
means you cannot deploy them separately or add a subclass without editing the base. *Fix:* invert
the dependency — the base defines the abstraction; derivatives depend on it, never the reverse.

**G8 — Too much information.** A class or module with a huge public surface. Every exposed symbol
is a coupling point. Well-designed modules have small interfaces that let you do a lot with
little. *Fix:* hide it. Fewer public methods, fewer public fields, fewer protected members,
minimal headers.

**G9 — Dead code.** Unreachable branches, a condition that can never be true, a `catch` for an
exception never thrown, an unused utility. It doesn't get updated with the conventions around it
and slowly becomes misleading. *Fix:* delete.

**G10 — Vertical separation.** Variables and functions declared far from where they're used.
Locals just above first use; private functions just below their first caller. *Fix:* move them
closer.

**G11 — Inconsistency.** Doing similar things in different ways: `response` here, `resp` there;
`fetch` in one module, `get` in the next; one class using constructor injection and its sibling
using setters. Consistency lets readers predict; inconsistency forces them to check. *Fix:* pick a
convention, apply it, write it down.

**G12 — Clutter.** Default constructors with no purpose, unused variables and imports, meaningless
comments, empty `else` blocks. *Fix:* delete. Keep the file dense with meaning.

**G13 — Artificial coupling.** Things with no mutual purpose bound together: a general enum nested
in a specific class, a static utility declared inside an unrelated one. Usually the result of
putting something in a "temporarily convenient" spot. *Fix:* put it where it belongs, even if it
costs you a new file.

**G14 — Feature envy.** A method more interested in another class's data than its own — reaching
through getters to compute something the other class could compute itself. *Fix:* move the method
to the class that owns the data. (Exception: intentionally keeping a data structure dumb, e.g. a
DTO plus a separate formatter.)

**G15 — Selector arguments.** A generalization of F3: any argument (boolean, enum, int, string)
whose only job is to choose which branch of the function runs. It buries the intent at the call
site. *Fix:* separate functions, or dispatch polymorphically.

**G16 — Obscured intent.** Dense one-liners, Hungarian notation, magic numbers, over-clever
expressions. Being terse is not the goal; being clear is. *Fix:* explanatory variables, named
constants, extracted functions.

**G17 — Misplaced responsibility.** Code placed where it was convenient rather than where a reader
would naturally look for it. Ask: where would someone *expect* to find this? *Fix:* move it there.

**G18 — Inappropriate static.** A static function that should be polymorphic — you'll eventually
want to vary its behavior by type and won't be able to. Statics also resist test substitution.
*Fix:* make it an instance method unless there is genuinely no chance of variation
(`Math.max`-like pure functions are fine).

**G19 — Use explanatory variables.** Break complex computations into intermediate values with
meaningful names. One of the cheapest, highest-return moves in all of programming. *Fix:* name the
sub-expressions.

**G20 — Function names should say what they do.** If you must read the implementation to know what
a call does, the name failed. `date.add(5)` — days? weeks? mutating or returning? *Fix:*
`date.plusDays(5)` / `date.increaseByDays(5)`.

**G21 — Understand the algorithm.** Fiddling with conditions until the tests pass is not
understanding. Code that "works" for reasons you can't articulate will break for reasons you
can't diagnose. *Fix:* understand it, then restructure it so the understanding is obvious.

**G22 — Make logical dependencies physical.** If module A assumes something about module B (a
buffer size, a page length, an ordering), A must *ask* B rather than duplicating the assumption.
*Fix:* query the source of truth; make the dependency explicit in the code.

**G23 — Prefer polymorphism to if/else or switch/case.** A switch on a type code will be copied
into every module that cares about the type. *Fix:* one switch in a factory, polymorphism
everywhere else. (Counter-note: an exhaustive, compiler-checked switch over a closed type set is
fine when the operations vary more than the types — see `classes-and-design.md`.)

**G24 — Follow standard conventions.** Team conventions on layout, naming, brace placement, import
order. Everyone must follow them; the codebase should look like one author wrote it. *Fix:* encode
in tool config (`.clang-format`, `checkstyle.xml`, `pyproject.toml`) so it's automatic, not
argued.

**G25 — Replace magic numbers with named constants.** Any literal whose meaning must be inferred:
`86400`, `7`, `0.08`, `"OK"`, `-1`. Applies to strings and sentinel values too. *Fix:* named
constant including the unit — `SECONDS_PER_DAY`, `MAX_RETRIES`, `VAT_RATE`. (Genuine exceptions:
`0` and `1` in obvious arithmetic, and formulas where the literal is part of the standard notation
and better left visible.)

**G26 — Be precise.** Ambiguity in code is a bug in waiting: floating point for money, unchecked
nulls, no locking on shared state, unchecked query results, unhandled error returns. *Fix:* decide
deliberately and encode the decision — `BigDecimal`, `Optional`, a lock, a checked return.

**G27 — Structure over convention.** A convention ("always add a case to this switch") relies on
memory; structure (an abstract method the compiler demands) relies on the compiler. *Fix:* prefer
designs where doing it wrong doesn't compile.

**G28 — Encapsulate conditionals.** Extract complex boolean expressions into named predicates.
`if (shouldBeDeleted(timer))` beats `if (timer.hasExpired() && !timer.isRecurrent())`.

**G29 — Avoid negative conditionals.** `if (buffer.shouldCompact())` is easier to parse than
`if (!buffer.shouldNotCompact())`. Double negatives cost real reading time. *Fix:* express the
predicate positively.

**G30 — Functions should do one thing.** See `functions.md` for the three tests.

**G31 — Hidden temporal couplings.** When calls must happen in a specific order but nothing
enforces it, someone will eventually reorder them. *Fix:* make each step consume the previous
step's output, so the type system enforces the sequence:
```
# before — order matters, nothing says so
saturate_gradient(); reticulate_splines(); dive_for_more_gold()

# after — order is structurally enforced
gradient = saturate_gradient()
splines  = reticulate_splines(gradient)
dive_for_more_gold(splines)
```

**G32 — Don't be arbitrary.** Structure should have a reason a reader can infer. A class placed in
an odd package, a method in an odd class, a one-off ordering — if others can't see the rationale,
they'll "fix" it inconsistently. *Fix:* follow the surrounding structure, or explain the deviation.

**G33 — Encapsulate boundary conditions.** `level + 1` computed in three places is three chances
to get it wrong. *Fix:* compute once into a named variable and use that.

**G34 — Functions should descend only one level of abstraction.** Every statement in a function
should sit one level below the function's name. Mixing levels forces the reader to change
altitude mid-sentence. See `functions.md`.

**G35 — Keep configurable data at high levels.** Constants and defaults belong at the top level
of the system (config, `main`, a constants module), passed down — not buried in a low-level
function where nobody can find them to change. *Fix:* hoist them; inject them.

**G36 — Avoid transitive navigation.** `a.getB().getC().doSomething()` couples you to the entire
chain; any link changing breaks you. *Fix:* ask the immediate collaborator for what you need
(Law of Demeter). Note this targets *objects*, not data structures or fluent builders.

## Language-specific

The original catalog's J-entries are Java; they are stated here in language-neutral form. Anything
narrower than this belongs in the repo's linter config, not in prose.

**J1 — Keep imports explicit.** Wildcard imports hide where names come from, break static
analysis, and invite collisions. Import what you use; let the formatter order and fold them.

**J2 — Don't inherit constants.** Hiding constants in a base type so subtypes get them for free
misuses inheritance — the reader can't find where they come from. *Fix:* an enum or a named
constants holder, imported explicitly.

**J3 — Constants versus enums.** Bare integer or macro constants have no type safety, no
namespace, and no meaningful string form. Enums do, and can carry behavior. *Fix:* use the
language's typed enum.

## Names

**N1 — Choose descriptive names.** Names are 90% of readability. Choose carefully, and keep them
current: when the code's meaning drifts, rename. See `naming.md`.

**N2 — Choose names at the appropriate level of abstraction.** Don't name for implementation.
`Modem.dial(phoneNumber)` leaks that modems dial; `Modem.connect(connectionLocator)` survives
the move to a wired connection.

**N3 — Use standard nomenclature where possible.** `...Factory`, `...Visitor`, `...Decorator`,
`toString`, `__repr__`, `operator<<`. Pattern names and platform conventions are free
documentation for anyone who already knows them — which is everyone.

**N4 — Unambiguous names.** `doRename()` that actually renames a file *and* moves it is
ambiguous; `renameAndMoveFile()` at least tells the truth (and then fails the one-thing test,
prompting the real fix).

**N5 — Use long names for long scopes.** `i` is fine in a three-line loop and a crime as a
module-level variable. Length should track the distance between declaration and use.

**N6 — Avoid encodings.** No Hungarian notation, no type prefixes, no `m_`, no `I` on interfaces.
The type system knows; the editor knows.

**N7 — Names should describe side effects.** `getOos()` that creates the stream if absent should
be `createOrReturnOos()`. Hidden side effects in innocuously-named functions are among the most
expensive bugs in a codebase.

## Tests

**T1 — Insufficient tests.** A suite should test everything that could plausibly break. If it
does not, it does not tell you the system works — only that it hasn't broken in the places you
looked.

**T2 — Use a coverage tool!** Coverage tools show which branches you never exercised, which is
information you cannot get any other way. Read the report for shape, not for a number.

**T3 — Don't skip trivial tests.** They're cheap to write and their documentary value exceeds
their cost. The "trivial" boundary case is exactly where the off-by-one lives.

**T4 — An ignored test is a question about an ambiguity.** A `@Disabled`/`@skip` test says
"something here is unresolved". Either resolve it or delete the test and file the question. A
permanently-skipped test is dishonest.

**T5 — Test boundary conditions.** The middle of an algorithm is usually right; the ends are
usually where the bug is. Enumerate: empty, one, many, max, max±1, negative, null, duplicate.

**T6 — Exhaustively test near bugs.** Bugs cluster. When you find one, test the whole
neighborhood — the function probably isn't as well understood as you thought.

**T7 — Patterns of failure are revealing.** The *shape* of what fails often names the cause faster
than debugging: "all inputs over 255 chars", "only on the last day of the month". Read the failure
matrix as data.

**T8 — Test coverage patterns can be revealing.** *What is covered* when a test passes tells you
about the code's structure. A branch that no test reaches is either dead or dangerous.

**T9 — Tests should be fast.** A slow test is a test that stops being run, and then the whole
suite stops being trusted. Guard the fast suite's runtime like a budget.

## Quick review checklist

Print this. Walk it top to bottom on any diff.

**Names**
- [ ] Does every name state intent without needing a comment?
- [ ] Do booleans read as predicates and functions as verb phrases?
- [ ] Do numeric quantities carry their units?
- [ ] One word per concept, consistent with the rest of the codebase?

**Functions**
- [ ] ≤ 20 lines, ≤ 2 arguments, ≤ 2 levels of indentation?
- [ ] One thing, one level of abstraction?
- [ ] No flag arguments, no output arguments, no hidden side effects?
- [ ] Command or query — not both?

**Comments**
- [ ] Could this comment be a name or an extracted function instead?
- [ ] Does it explain *why*, not *what*?
- [ ] Is it still true after this change?
- [ ] Any commented-out code to delete?

**Structure**
- [ ] One responsibility per class/module; can you name it without "and"/"Manager"?
- [ ] High cohesion — do the methods use the fields?
- [ ] Dependencies injected, not constructed inline?
- [ ] Duplication removed (and no false duplication merged)?

**Errors**
- [ ] Every error path handled or deliberately propagated; nothing swallowed?
- [ ] Exceptions carry enough context to debug from a log line alone?
- [ ] No null returned or passed where a better option exists?
- [ ] Resources released on every path (RAII / try-with-resources / `with` / `goto cleanup`)?

**Tests**
- [ ] A test that fails without this change?
- [ ] Boundaries covered?
- [ ] Fast, independent, repeatable, self-validating?
- [ ] Test names read as behavior specifications?

**Overall**
- [ ] Cleaner than you found it?
- [ ] Would a newcomer read this once and understand it?
