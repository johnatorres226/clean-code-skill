---
name: clean-code
description: Language-agnostic clean code standards for writing, reviewing, and refactoring code — naming, functions, comments, formatting, error handling, class design, TDD, and a smell catalog with IDs. Use when writing more than a few lines of code, reviewing or refactoring code, naming things, deciding on a comment, designing a function or class, or writing tests.
version: 2.0.0
metadata:
  author: johnatorres226
  tags: [clean-code, refactoring, naming, testing, code-review]
---

# Clean Code

Done means a stranger can read each function top to bottom, once, and know what it does and why.
When rules conflict, resolve in this order: **correct** (including boundaries) → **clear** →
**small** (functions, classes, arguments, nesting) → **fast enough** (measured, never guessed;
isolate any necessary ugliness behind a clean name).

## Load only what the task needs

Run the repo's linter first (`standards.toml` gates) and fix what it reports. Then act on the
procedures below; open a reference only when a section's **Open the reference when** line
matches your situation — usually one file, two or three when the task genuinely spans areas.
Examples in references are language-neutral pseudocode; the repo's linter owns language idioms.

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
| Running a formal review, or scanning code for a refactor plan | `references/review-rubric.md` | 2,100 |
| Looking up a smell | `references/smells-catalog.md` | **grep it — see Step 3** |

Never read the smell catalog whole: `grep -A4 -E '^\*\*(G25|F3)' references/smells-catalog.md`
returns just those entries (~60 tokens each); its `## Index` lists all 67 in one line each.

## Writing a function — the procedure

This is the highest-leverage skill in the whole discipline. Follow it literally.

1. **Write it badly first.** Get something that works and is covered by a test. You cannot polish
   what does not run. Nobody writes a clean function on the first pass — clean functions are
   *refined*, not authored.
2. **Name it as a verb phrase describing the single thing it does.** `calculate_payroll`,
   `is_eligible`, `render_invoice_line`. If the honest name needs "and" or "then", the function
   is doing more than one thing. Split it.
3. **Reduce it to one level of abstraction.** Every statement in the body should sit at roughly
   the same conceptual altitude. A function that mixes index-by-index byte shuffling with
   `submit_order(order)` is asking the reader to change altitude mid-sentence.
4. **Extract until you cannot extract meaningfully.** If a block needs a comment to explain what
   it does, that comment is the name of a function you have not written yet. Extract it, and the
   comment becomes the name.
5. **Cut the arguments.** Zero is ideal, one is fine, two is acceptable, three needs a reason,
   more than three needs a parameter object. Never pass a boolean flag — it announces the
   function does two things; write the two functions.
6. **Remove output arguments.** A function should return its result. Where out-parameters are
   idiomatic, document ownership and nullability precisely.
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

Even then, only these comments stay (the reviewer flags the rest), and each explains *why*, never
*what*:

- **Legal, licensing, and provenance headers.**
- **Behavior forced by something we cannot reshape** — a dependency, platform, vendor, protocol or
  device: why the timeout is 300 ms when the vendor drops idle sockets at 350.
- **Public API documentation** (Javadoc, docstrings, Doxygen) — document contracts: parameters,
  returns, raises/throws, ownership, thread-safety, complexity. Not a private one-line getter.
- **Links to an issue, RFC or source** for a constraint the code cannot express. A `TODO` or known
  limit needs an owner, an exit condition and an issue; without them it is litter.
- **Lint suppressions whose rule is faulty, pedantic or style-only**, with the reason.

A surprise in our own code ("not thread-safe", "do not remove") is a design problem: rename, type,
test or restructure until it needs no comment. **Never leave commented-out code** — version control
remembers. **A comment that lies is worse than none:** change or delete it in the same edit as
the code.

Full rules, the reshapes, and the bad-comment taxonomy: `references/comments.md`.

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

## Tests

Tests are what permit clean code: without them you cannot refactor. Work red → green →
refactor in minutes-long cycles, and watch each new test fail first. Tests are production code:

- One behavior per test, named as a sentence (`withdraw_fails_when_balance_below_amount`),
  arrange–act–assert visibly separated.
- Fast, independent, repeatable (inject the clock, seed randomness), self-validating.
- Cover the boundaries: empty, one, many, max, off-by-one, invalid, duplicate.
- Assert observable behavior, not internal calls; prefer fakes to mocks.

**Open `references/tdd-and-tests.md` when:** writing the tests rather than deciding to; choosing
between stub, fake, spy, and mock; or getting untested legacy code under test.

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
