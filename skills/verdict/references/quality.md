# Pass B: maintainability

Adapted from `thermo-nuclear-code-quality-review` in Cursor's Thermos plugin
(https://github.com/cursor/plugins, `thermos/`), MIT license. Changes: shortened, severity mapped
to this skill's labels, mechanical limits left to the linter.

Audit the quality of the branch's changes. Rethink how they could be structured to make the code
meaningfully better without changing behavior: better abstractions, more modular, less spaghetti,
shorter and easier to read. Be ambitious: if restructuring part of the codebase gives a clearly
simpler result, propose it. Measure twice, cut once.

Do not report what the repo's linter (`[gates].lint`) already catches: function length,
parameters, nesting, magic numbers. Cite a `clean-code` smell ID when one applies.

## Standards

1. **Look for the code-judo move.** A reorganization that uses the existing architecture better and
   makes whole branches, helpers, modes or layers disappear. Prefer deleting complexity over
   rearranging it.
2. **No file crosses 1000 lines** because of this change without a strong reason. Ask whether it
   should be decomposed first.
3. **No spaghetti growth.** New ad-hoc conditionals, scattered special cases and one-off branches
   in unrelated flows are design problems, not style. Push the logic into its own abstraction.
4. **Clean the design, not only accept working code.** If behavior can stay the same while the
   structure gets clearly cleaner, ask for the cleaner version.
5. **Direct, boring code over magic.** Flag generic mechanisms that hide simple data shapes, and
   wrappers or pass-through helpers that add indirection without clarity.
6. **Clean types and boundaries.** Question needless optionality, `any`, casts and silent
   fallbacks that paper over an unclear invariant.
7. **Canonical layer, canonical helpers.** Flag feature logic leaking into shared paths, and
   bespoke helpers where the codebase already has one.
8. **Parallel and atomic where it is obviously simpler.** Flag independent work serialized for no
   reason, and updates that can leave state half-applied.

## Severity

Blocking unless the author justified it in the PR description:

- a plausible code-judo move would delete much of the incidental complexity;
- a file is pushed from under to over 1000 lines;
- ad-hoc branching tangles an existing flow;
- feature checks are scattered across shared code;
- an unnecessary wrapper, abstraction or cast-heavy contract makes the design more indirect;
- an existing helper is duplicated, or logic sits in the wrong layer with a clear canonical home.

Everything else is a suggestion. Prefer a few high-conviction findings to many cosmetic ones, and
never settle for "maybe rename this" when the problem is structural.

## Tone

Direct and serious, never rude. If the change makes the codebase messier, say so plainly:
`this adds another special-case branch to a busy flow. can we move it behind its own abstraction?`
