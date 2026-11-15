---
name: clean-code
description: Language-agnostic clean code standards — naming, function design, comments, formatting, error handling, class design, test-driven development, refactoring, and a full code-smell catalog. Use this skill whenever writing new code, reviewing or critiquing code, refactoring, cleaning up a legacy file, naming things, deciding whether to write a comment, designing a function or class, setting up linters/formatters, writing unit tests or doing TDD, or when the user mentions "clean code", "readable", "maintainable", "code quality", "code review", "refactor", "tech debt", "style guide", or asks how to make code better. Also use it proactively any time you are about to produce more than a trivial amount of code in any language, so that what you write is code the next programmer will thank you for.
---

# Clean Code

Code is read far more often than it is written. Every line you write is a message to the next
programmer — who is very often yourself, six months from now, at 2 a.m., under pressure. This
skill exists to make that message clear, honest, and short.

The standard this skill holds you to: **someone unfamiliar with the code should be able to read a
function top to bottom, once, and know what it does and why.** If they have to scroll, decode,
or guess, the code is not done.

## The four qualities

Every judgment call in this skill resolves against these, in this order when they conflict:

1. **Correct** — it does the right thing, including at the boundaries. Beauty never outranks truth.
2. **Clear** — intent is on the surface. The reader spends attention on the problem, not the code.
3. **Small** — small functions, small classes, small files, few arguments, shallow nesting.
   Smallness is what makes clarity survivable as the system grows.
4. **Fast enough** — measured, not guessed. Optimize only where a profiler points, and when you
   do, isolate the ugly part behind a clean name and comment *why*.

Efficiency and beauty are not opposed. A tight, well-named, non-duplicated function is usually
also the fast one, because it is the one that is easy to make fast.

## How to use this skill — triage before you load

The references total ~22,000 tokens. Loading them naively costs more than it returns. Work in
this order and stop as soon as you have what you need.

**Step 1 — run a script instead of reading.** Anything mechanical is cheaper to detect than to
look up. The linter reports findings tagged with catalog IDs, which is also what makes Step 3
cheap.

```bash
python3 scripts/clean_code_lint.py <paths...>          # smells (C, C++, Java, Python)
python3 scripts/clean_code_lint.py <paths> --json      # machine-readable, for CI
python3 scripts/tdd_scaffold.py --lang python --unit Parser --dir src/
bash scripts/setup_toolchain.sh <c|cpp|java|python> .  # formatter + linter configs from assets/
```

**Step 2 — load one reference. Two if the task genuinely spans two areas.**

This is a default, not a cap. Go to three when the task really is that wide — "refactor this
legacy module and get it under test" legitimately needs `refactoring.md` and `tdd-and-tests.md`.
Skipping a needed file to obey a budget produces worse work and hides the fact that it did. Load
what the task needs, and know what each file costs before you open it.

References are language-agnostic: examples are neutral pseudocode. Language idioms — casing,
formatter rules, framework syntax — are the job of the repo's linter and formatter config, not of
this skill. Follow the ecosystem's idioms; let the tools enforce them.

| Task | Read | ~Tokens |
|---|---|---|
| Writing or splitting a function | `references/functions.md` | 2,200 |
| Naming anything | `references/naming.md` | 1,700 |
| Deciding whether/how to comment | `references/comments.md` | 1,600 |
| Layout, line length, file organization | `references/formatting.md` | 1,200 |
| Errors, exceptions, null, resources | `references/error-handling.md` | 1,700 |
| Classes, modules, cohesion, dependencies | `references/classes-and-design.md` | 2,200 |
| Writing tests, doing TDD | `references/tdd-and-tests.md` | 2,800 |
| Cleaning existing code | `references/refactoring.md` | 2,700 |
| Running a formal review | `references/review-rubric.md` | 1,400 |
| Looking up a smell | `references/smells-catalog.md` | **grep it — see Step 3** |

**Step 3 — never read the smells catalog whole.** It is the largest file (~4,800 tokens) and it
is a lookup table. Grep the entry you want:

```bash
grep -A4 '^\*\*G25' references/smells-catalog.md               # one entry, ~60 tokens
grep -A4 -E '^\*\*(F3|G25|G30)' references/smells-catalog.md    # several at once
```

If you are browsing rather than looking up a known ID, read only its `## Index` section (~630
tokens) — one line per entry across all 66 — then grep the ones that look relevant. Read the file
in full only for a deep audit of unfamiliar code.

**Step 4 — the sections below are self-contained.** Naming, TDD, and refactoring each have a
working summary here. Act on it directly for ordinary cases. Each one ends with an **Open the
reference when** line naming the specific situations the summary does not cover — that line, not
a vague sense of needing more, is the signal to load the file.

## Writing a function — the procedure

This is the highest-leverage skill in the whole discipline. Follow it literally.

1. **Write it badly first.** Get something that works and is covered by a test. You cannot polish
   what does not run. Nobody writes a clean function on the first pass — clean functions are
   *refined*, not authored.
2. **Name it as a verb phrase describing the single thing it does.** `calculate_payroll`,
   `is_eligible`, `render_invoice_line`. If the honest name needs "and" or "then", the function
   is doing more than one thing. Split it.
3. **Reduce it to one level of abstraction.** Every statement in the body should sit at roughly
   the same conceptual altitude. A function that mixes `for (int i = 0; ...)` byte-shuffling with
   `submitOrder(order)` is asking the reader to change altitude mid-sentence.
4. **Extract until you cannot extract meaningfully.** If a block needs a comment to explain what
   it does, that comment is the name of a function you have not written yet. Extract it, and the
   comment becomes the name.
5. **Cut the arguments.** Zero is ideal, one is fine, two is acceptable, three needs a reason,
   more than three needs a parameter object. Never pass a boolean flag — it announces the
   function does two things; write the two functions.
6. **Remove output arguments.** A function should return its result. In C, where an out-pointer
   is idiomatic, document ownership and nullability precisely.
7. **Flatten the nesting.** Aim for a maximum indent depth of two inside the body. Guard clauses
   and early returns beat pyramids. Extract the inner block into a named helper.
8. **Make it total or make it explicit.** Either the function handles every input it accepts, or
   its precondition is enforced and visible (assert, exception, type). No silent partial behavior.
9. **Have no side effects the name does not promise.** `check_password` must not also initialize
   the session. Hidden side effects are the single most expensive lie in a codebase.
10. **Re-read it as the next programmer.** Would they need to look anywhere else to trust it? If
    yes, keep going.

Full treatment with before/after examples: `references/functions.md`.

## Writing a comment — the procedure

The default is **no comment**. A comment is a failure to express intent in code, and it is
tolerated only where code genuinely cannot carry the meaning. Comments also rot; code does not.

Before writing one, try in order:

1. **Rename** — can a better name make the comment unnecessary?
2. **Extract** — can a named function or explanatory variable say it?
3. **Restructure** — is the comment apologizing for a design problem you should just fix?

Write the comment only if all three fail. Then follow these rules:

- **Explain *why*, never *what*.** The code says what. Only the human knows why the timeout is
  300 ms, why the loop counts down, why this workaround exists and what ticket kills it.
- **Legal, licensing, and provenance headers** are legitimate and stay.
- **Warnings of consequence** are legitimate: "not thread-safe", "O(n²) — fine below 1000 rows,
  do not use on the full table".
- **`TODO:`** is legitimate when it carries an owner and a condition for removal. Audit them
  regularly; a TODO with no plan is litter.
- **Public API documentation** (Javadoc, docstrings, Doxygen) is legitimate and expected —
  document contracts: parameters, returns, raises/throws, ownership, thread-safety, complexity.
  Do not Javadoc a private one-line getter.
- **Never leave commented-out code.** Version control remembers. Commented-out code is a corpse
  that no one will dare bury.
- **A comment that lies is worse than no comment.** If you change the code, change the comment in
  the same edit or delete it.

Full rules, plus the good/bad comment taxonomy: `references/comments.md`.

## Naming — the short version

Names are the primary interface to your code. Spend real time here.

- **Reveal intent.** `elapsed_days` beats `d`. If a name needs a comment, the name is wrong.
- **Length tracks scope.** A three-line loop index may be `i`. A module-level constant may not.
- **Pronounceable and searchable.** You will discuss this code out loud and grep for it.
- **One word per concept.** Pick `fetch` or `get` or `retrieve` and use it consistently forever.
- **Classes are nouns; methods are verbs; booleans read as predicates** (`is_`, `has_`, `can_`).
- **No encodings.** No Hungarian notation, no `m_` prefixes, no `I` on interfaces. The type system
  and your editor already know.
- **No noise words.** `ProductInfo`, `ProductData`, and `Product` are indistinguishable. `the_`,
  `a_`, `_variable`, `_object` add nothing.
- **Say the side effect.** If `get_instance()` might create the instance, the name should hint it.
- **Use domain language.** Prefer the term the business actually uses; fall back to CS terms
  (`Visitor`, `Queue`, `Factory`) when the concept genuinely is one — that is free documentation.

**Open `references/naming.md` when:** you need casing conventions for a specific language; the
name is a numeric quantity and you are unsure how to encode the unit; you are choosing between two
plausible names and need the scope-vs-length rule; you are setting a project-wide vocabulary; or
you are renaming across an existing codebase and need the anti-pattern table.

## Test-driven development — the loop

Tests are not an accessory to clean code; they are what *permits* it. Without tests you cannot
refactor, and without refactoring code decays. Tests are the thing that keeps the code soft.

**Red → Green → Refactor:**

1. **Red** — write the smallest failing test that expresses the next piece of desired behavior.
   Watch it fail, for the right reason. A test you never saw fail is a test you cannot trust.
2. **Green** — write the least code that passes. Ugly is fine here. Do not design ahead.
3. **Refactor** — now clean both the production code *and the test*, with the safety net on.
   This third step is where the design actually happens. Skipping it is why teams conclude "TDD
   didn't work."

Keep the cycle to minutes, not hours.

**Test quality rules — tests are production code:**

- **One assert concept per test.** A test should fail for exactly one reason.
- **Follow Arrange–Act–Assert** (Given–When–Then). Make the three blocks visually obvious.
- **Name the test as a sentence about behavior**: `withdraw_fails_when_balance_below_amount`, not
  `test_withdraw_2`.
- **F.I.R.S.T.** — Fast, Independent (no order dependence, no shared mutable state), Repeatable
  (any machine, offline), Self-validating (pass/fail, no eyeballing logs), Timely (written with
  or before the code).
- **Test behavior at the boundary**, not the internals: empty, one, many, max, off-by-one,
  negative, null/None, overflow, duplicate, unicode, concurrent.
- **Do not skip trivial tests** — they document intent cheaply. A disabled test is an unanswered
  question; either fix it or delete it and record the ambiguity.
- Coverage is a *diagnostic*, not a goal. Use it to find untested branches, not to hit a number.

**Open `references/tdd-and-tests.md` when:** you are writing the tests rather than just deciding
to; you need framework syntax (pytest, JUnit 5, GoogleTest, Unity); you are choosing between a
stub, fake, spy, and mock; you are getting untested legacy code under test (characterization
tests, seams, extract-and-inject); or you need the worked red-green-refactor session.

## Refactoring — the discipline

**The Boy Scout Rule: leave every file cleaner than you found it.** Not rewritten — cleaner. One
better name, one extracted function, one deleted dead branch, per visit. Large codebases are
saved by accumulated small improvements, never by the grand rewrite.

Non-negotiable preconditions:

1. **Tests pass before you start.** If there are none, write characterization tests that pin down
   current behavior — including behavior you think is wrong — before touching anything.
2. **Separate the commits.** Behavior changes and refactors never share a commit. A reviewer must
   be able to trust that a "refactor" commit changed nothing observable.
3. **Small steps, green between each.** Rename, extract, inline, move, replace conditional with
   polymorphism — one at a time, tests green after each.

Sequence: make it work → make it right → make it fast (if measurement says so).

**Open `references/refactoring.md` when:** you need the mechanics of a specific move (extract,
inline, introduce parameter object, replace conditional with polymorphism, split loop); you are
working without tests and need the characterization-test procedure; or you want the multi-step
worked example showing green-between-every-step in practice.

## Reviewing code

Run the linter first so the mechanical findings are free, then read for the things a tool cannot
see: does the name match the behavior, is the abstraction level consistent, does the test suite
actually pin the contract, would a newcomer be misled.

Grep `references/smells-catalog.md` by ID for anything the linter flags; read
`references/review-rubric.md` for the output format and severity levels. Review comments should be specific, kind, and actionable — cite the principle,
propose the concrete edit, and distinguish blocking issues from suggestions.

## Language stance

The principles are universal; the idioms are not. Write each language the way its ecosystem
writes it — translating one language's idioms into another is clean by the letter and wrong by the
spirit. In every language: bind resources to a scope that releases them, use one error convention
per module, make data immutable by default, make absence explicit in the type, and inject
collaborators instead of constructing them. The repo's linter and formatter enforce the rest.

## What to do when the codebase disagrees with this skill

**Local consistency wins.** A file with a coherent existing style is easier to read than a file
half-converted to a better style. Match the surrounding conventions, apply the Boy Scout Rule
within them, and raise the broader style question separately rather than smuggling a migration
into an unrelated change.

## Bibliography

The principles here follow the tradition established by:

- Robert C. Martin, *Clean Code: A Handbook of Agile Software Craftsmanship* (Prentice Hall, 2008)
  — the source of the smell/heuristic ID scheme (N*, F*, C*, G*, T*, E*) referenced in
  `references/smells-catalog.md`.
- Martin Fowler, *Refactoring: Improving the Design of Existing Code*, 2nd ed. (2018).
- Kent Beck, *Test-Driven Development: By Example* (2002).
- Andrew Hunt & David Thomas, *The Pragmatic Programmer* (1999).
- Michael Feathers, *Working Effectively with Legacy Code* (2004).
- Scott Meyers, *Effective Modern C++* (2014); Joshua Bloch, *Effective Java*, 3rd ed. (2018).
- PEP 8 and PEP 20; the ISO C++ Core Guidelines; the Google style guides.
