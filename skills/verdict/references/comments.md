# Pass C: comments

Adapted from `comment-sicko` in Cursor's pstack plugin (https://github.com/cursor/plugins,
`pstack/`), MIT license. Changes: report only (the reviewer never edits), scoped to a diff, severity
mapped to this skill's labels.

Comments rot: code changes and the comment beside it does not, and the reader trusts it. Hunt every
comment the change adds or edits, and every existing comment next to changed code, since a change
can leave an old comment lying.

## Keep-list

Only these stay. When you are not sure one applies, the comment goes.

1. Legal or license headers.
2. Behavior forced by something we cannot reshape: a dependency, platform, vendor or protocol.
3. Doc comments that define a public API contract.
4. Issue or RFC links explaining a constraint the code cannot express, including a known limit
   with its upgrade path.
5. Lint suppressions whose rule is faulty, pedantic or style-only.

A surprise in our own code is not on the list. The comment goes and the symbol it explains is the
target: `MUST KILL: <symbol>`, to be renamed, extracted, typed or restructured until the behavior
is obvious without prose.

## Read before judging

`IMPORTANT`, `do not remove`, `hack`, `fine for now` and long justifications are a scent, not
proof. Read the nearby code and trace the symbol the comment names. Keep it only if a keep-list
reason is true today on a live path. A long justification with no keep-list reason is a confession
of a design problem: report the symbol, do not suggest a shorter comment.

## Severity

Blocking:

- a comment that contradicts the code it describes (smell C2), added or left stale by the change;
- commented-out code the change adds (C5);
- a new suppression of a rule that catches real bugs or protects safety: report the rule and the
  symbol it hides.

Everything else is `suggestion (non-blocking)`, one finding per file: what to delete, and each
`MUST KILL: <symbol>` with the reshape that removes the need, e.g.
`suggestion (non-blocking): cache.py — 3 comments explain our own code. MUST KILL: Cache (rename to UnsyncedCache or add a lock)`.

Every finding names code in scope and is true. Findings count under the `maintainability` check.
