# Code Review Rubric

Use this when asked to review, critique, or assess code. The goal of a review is not to find
faults — it is to make the code better and the author stronger. Both of those fail if the review
is a wall of nitpicks or a vague "looks good".

## Procedure

1. **Run the linter first.** The repo's lint command (`standards.toml`) catches the mechanical
   findings for free — length, arity, nesting, magic numbers, commented-out code. Never spend
   human review attention on what a tool can find.
2. **Read for correctness.** Does it do the right thing, including at the boundaries? This
   outranks everything else in this document.
3. **Read for clarity.** Would a newcomer understand it on one pass? Do the names match the
   behavior?
4. **Read for structure.** One responsibility per unit? Dependencies injected? Duplication
   removed?
5. **Read the tests.** Do they fail if the code is wrong? Do they read as a specification?
6. **Check what's missing.** Error paths, boundary cases, resource cleanup, documentation of a
   changed contract.

## Severity levels

Label every finding with a Conventional Comments label, the same ones the `verdict` skill uses.
Unlabeled reviews force authors to guess what actually blocks them, and they either over-react to
nitpicks or under-react to real problems.

| Label | Meaning | Examples |
|---|---|---|
| **`issue (blocking)`** | Must fix before merge | Correctness bug, resource leak, security issue, data loss, missing test for new behavior, swallowed error |
| **`issue (non-blocking)`** | Fix now unless there's a reason not to | Function doing three things, misleading name, duplicated logic, missing boundary test |
| **`suggestion`** | Author's call | Alternative structure, a cleaner idiom, naming preference |
| **`nitpick`** | Trivial; never blocks; at most five | Wording, ordering, a spare blank line. If the formatter could fix it, don't raise it at all |
| **`praise`** | Genuinely good work | A clean extraction, a well-chosen test case, a good name |

Include praise. It is not padding — it tells the author which instincts to repeat, which is the
main way review improves a team over time.

## Writing a review comment

A good comment has three parts: **what**, **why**, **what instead**.

```
issue (non-blocking): `process(order, true)` is unreadable at the call site, and the boolean
means this function has two behaviors (F3, flag argument).

Suggest splitting into `process_express(order)` and `process_standard(order)`,
with the shared body extracted into `apply_pricing(order, tier)`.
```

Cite the heuristic ID from `smells-catalog.md` when one applies — it makes the standard shared and
impersonal rather than a matter of taste.

**Avoid:**
- "This is wrong." — say what's wrong and what would be right.
- "Why did you do it this way?" when you mean "I'd do it this other way." Ask real questions; make
  suggestions as suggestions.
- Rewriting the whole thing in the comment. Point at the smell; let the author solve it.
- Twenty nits and no mention of the concurrency bug on line 140. Lead with what matters.

## Output format

When asked for a code review, use this structure:

```markdown
## Summary
One paragraph: what the code does, whether it's fundamentally sound, and the
single most important thing to address.

## issue (blocking)
- **`file.py:42` — Resource leak.** The connection isn't closed if `parse()` raises.
  Wrap in `with` / try-with-resources / RAII.
- **`file.py:88` — Off-by-one at the upper boundary.** `range(1, n)` excludes `n`;
  the docstring says inclusive. Add a test at `n`.

## issue (non-blocking)
- **`file.py:15` — `process()` does four things** (G30): validates, prices, formats,
  sends. Suggest extracting `validate`, `price`, `format_receipt`.
- **`file.py:60` — `1.08` is a magic number** (G25). Name it `TAX_RATE` and move it
  to module level (G35).

## suggestion
- `LineItem` would be a good `@dataclass(frozen=True)` — you'd get equality and repr
  for free and the schema would be visible.

## Tests
What's covered, what isn't, which boundary cases are missing.

## praise
- The `RetryPolicy` extraction is clean and the parameterized boundary test is exactly
  right.
```

Adjust depth to the size of the change. A ten-line diff gets a paragraph, not this template.

## Scoring rubric

When a numeric or graded assessment is requested, and in a refactor scan, score each dimension
1–5 and justify with specific line references. Never give a score without the justification —
the reasoning is the useful part.

| Dimension | 1 | 3 | 5 |
|---|---|---|---|
| **Correctness** | Known bugs; boundaries wrong | Happy path right, edges untested | Correct including boundaries, proven by tests |
| **Naming** | Cryptic, misleading | Mostly reasonable, some noise words | Every name states intent; consistent vocabulary |
| **Functions** | Long, many args, deep nesting | Mixed; a few too long | Small, one thing, one abstraction level, ≤2 args |
| **Comments** | A comment contradicts the code (C2), or commented-out code (C5) | Some noise or `MUST KILL` flags (C3, C6) | Only keep-list comments (`comments.md`); no `MUST KILL` flags |
| **Structure** | God class; tangled dependencies | Reasonable split, some coupling | One responsibility per unit; dependencies injected |
| **Error handling** | Swallowed or ignored | Handled but thin on context | Every path handled; rich context; resources released |
| **Tests** | None, or assert nothing | Happy path covered | Behavior-named, boundaries covered, fast, independent |
| **Consistency** | Fights the codebase | Mostly matches | Indistinguishable from the best code in the repo |

## Scanning code for a refactor plan

Use this to assess existing code (a directory, a module or the whole repo) and plan its refactor,
rather than to review a change. Report only: change nothing. The plan becomes tickets only when the
user asks (the `tracker` agent creates them).

1. **Scope.** The path you were given. For the whole repo, give each top-level module to its own
   subagent running steps 2–4, then merge in step 5; without subagents, go one module at a time.
2. **Lint first.** Run the repo's lint gate (`standards.toml`). Count its findings in the scores;
   do not re-report them.
3. **Score each module** on the eight dimensions above, each with one `file:line` of evidence. Run
   the comments pass (`skills/verdict/references/comments.md`) over the whole module: its
   `MUST KILL` flags set the Comments score and become refactor targets.
4. **Measure churn:** `git log --since=90.days --format= --name-only -- <module> | sort | uniq -c`.
5. **Rank by gap × churn.** Gap is the sum of (5 − score) over the dimensions; churn is the
   module's changes in 90 days. Bad code nobody touches ranks low: it costs nothing until someone
   edits it. A Correctness score of 1 is a bug, not a refactor: list it first, as a bug.
6. **Plan in slices.** Each slice is one PR within the `[pr]` size limits, with one goal. It starts
   with tests that pin current behavior, then refactor commits that change no behavior. It names
   its files, the smell IDs and `MUST KILL` targets it removes, and the score it should raise.

```markdown
## Scores
| module | correctness | naming | functions | comments | structure | errors | tests | consistency | gap | changes (90d) |
|---|---|---|---|---|---|---|---|---|---|---|
| billing/ | 4 | 3 | 2 | 1 | 2 | 3 | 3 | 3 | 19 | 41 |

## Bugs found
- `billing/tax.py:88` — rounds before summing; totals drift by a cent on large orders.

## Slices, in order
1. **billing/: split `Invoice.process()`** — G30, F3; MUST KILL: `Invoice.process`. Tests first:
   pin totals for empty, one-line and mixed-tax invoices. Raises Functions 2 → 4. ~250 lines.

## Not now
Low-churn modules with low scores: improve them when a ticket touches them (Boy Scout Rule).
```

## Reviewing your own output

Before delivering code you wrote, run the same pass. Specifically:

- [ ] Did I run the linter on what I produced?
- [ ] Is every function under ~20 lines with ≤2 arguments?
- [ ] Does every name state intent without a comment?
- [ ] Did I leave a comment that a name or extraction should have replaced?
- [ ] Are there tests, and do they fail if the code is wrong?
- [ ] Is every error path handled, and every resource released on every path?
- [ ] Are there magic numbers, dead code, or commented-out blocks?
- [ ] Would the next programmer understand this on one read?

The last question is the one that matters. Everything else in this skill is scaffolding for it.
