# Formatting

Formatting is communication. It is also the cheapest kind of quality to obtain, because a tool can
do it — so there is no excuse for a codebase without one, and no excuse for humans arguing about it
in review.

**The rule that matters most: agree once, automate it, and never discuss it again.** A consistent
"wrong" style beats an inconsistent "right" one. The formatter runs in a pre-commit hook and in CI.

## Contents

- [Automate first](#automate-first)
- [Vertical formatting](#vertical-formatting)
- [Horizontal formatting](#horizontal-formatting)
- [Team rules over personal rules](#team-rules-over-personal-rules)
- [File and project organization](#file-and-project-organization)

## Automate first

Every repo declares one formatter and one linter per language, with config checked in, wired into
pre-commit and CI. The repo's standards config names them; the tools — not this document — are the
authority on casing, spacing, brace style, and import order. Everything below is what a formatter
*cannot* decide for you, plus the defaults to configure it with.

## Vertical formatting

**The newspaper metaphor.** A source file reads like a news article: the name tells you whether
you're in the right place, the top gives the high-level story, and detail increases as you descend.
You can stop at any point and have a coherent picture at that level.

**File length.** Most files should be a few hundred lines; 500 is a reasonable ceiling and 1000 is
a smell. A large file is almost always several concepts not yet separated.

**Vertical openness between concepts.** Blank lines separate thoughts. Each group of lines that
forms one idea gets one blank line after it.

```
function parse(text):
    header = parse_header(text)
    validate_version(header.version)

    entries = [parse_entry(line) for line in body_lines(text)]
    reject_duplicates(entries)

    return Manifest(header, entries)
```

**Vertical density implies association.** Lines that belong together stay together — no stray
blank lines or comments splitting a tightly coupled group. *Closeness means relatedness.*

**Vertical distance: declare close to use.**

- **Local variables** at their first use, as close as the language allows.
- **Fields / instance state** in one well-known place at the top of the type.
- **Loop control variables** inside the loop statement.
- **Dependent functions**: caller *above* callee, so the reader flows downward (the stepdown rule
  from `functions.md`, expressed as layout).
- **Conceptually affine functions** (`assert_true`/`assert_false`, overloads of `write`) stay
  adjacent even without a call relationship.

If a reader has to scroll or jump files to understand one function, its dependencies are too far
away.

**Vertical ordering within a file** — a defensible default; readers care about the interface
first:

```
1. License / file-level doc comment
2. Imports (grouped, ordered)
3. Constants and type declarations
4. Public entry points, in order of importance
5. Private helpers, in stepdown order beneath their callers
```

## Horizontal formatting

**Line length.** Pick a limit and enforce it: 80 (forces smaller functions), 100 (pragmatic
middle), or 120 (upper bound; beyond it side-by-side diffs and review get painful). Never rely on
wrapping. A line that will not fit is usually doing too much — extract a named intermediate rather
than adding an awkward continuation.

**Horizontal openness.** Use spaces to show which operators bind tighter: `b*b - 4*a*c` style
grouping, or uniform spacing — whichever the formatter enforces — but never spacing that lies about
precedence.

**Do not align columns artificially.** Aligning declarations looks tidy until one name grows and
the formatter reflows twenty lines, wrecking diff and blame. Let the formatter decide.

**Indentation reveals scope.** Never collapse a scope onto one line to save space
(`if level > MAX: level = MAX` on one line hides a scope). Spaces vs. tabs matters far less than
consistency; follow the ecosystem and never mix.

**Braces (where the language has them):** use them even for one-line bodies. The cost is one line;
the benefit is that a second statement added later cannot silently escape the conditional — this
has caused shipped security bugs.

**Empty bodies** should be loud: an explicit `pass` / `;` with a comment saying the emptiness is
intentional.

## Team rules over personal rules

A codebase should look as if one careful person wrote it, even with twenty authors. The *team's*
choices override yours: brace placement, import order, comment style, casing, test layout.

Encode those decisions in machine-readable config checked into the repo (formatter config,
`.editorconfig`, linter config) so the rules travel with the code and new contributors inherit them
automatically. Then review is about design instead of whitespace.

When editing a file whose local style differs from the project standard, match the file, unless
you are reformatting the whole file in a dedicated commit. A half-converted file is worse than
either style.

## File and project organization

**One primary concept per file.** A file named `utils` that has grown to 900 lines is several
missing modules.

**The public interface is the contract and must read on its own** — whether that is a header, an
interface file, or the top of a module. Expose nothing it doesn't have to; depend on declarations,
not implementations, where the language allows.

**Import ordering.** Group, separate with blank lines, fixed order — and let the tool sort it:

```
1. this file's own interface (where the language has one — proves it is self-contained)
2. standard library
3. third-party
4. this project
```

**Test file placement.** Mirror the source tree so the test for `billing/invoice` lives at
`tests/billing/invoice_test` (or the ecosystem's equivalent). Predictable location means tests get
found and updated.

## Related heuristics

`smells-catalog.md`: **G24** follow standard conventions, **G1** multiple languages in one source
file, **G11** inconsistency, **G10** vertical separation.
