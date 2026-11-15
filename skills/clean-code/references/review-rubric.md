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

Label every finding. Unlabeled reviews force authors to guess what actually blocks them, and they
either over-react to nitpicks or under-react to real problems.

| Label | Meaning | Examples |
|---|---|---|
| **Blocking** | Must fix before merge | Correctness bug, resource leak, security issue, data loss, missing test for new behavior, swallowed error |
| **Should fix** | Fix now unless there's a reason not to | Function doing three things, misleading name, duplicated logic, missing boundary test |
| **Consider** | Author's call | Alternative structure, a cleaner idiom, naming preference |
| **Nit** | Trivial; never blocks | Wording, ordering, a spare blank line. If the formatter could fix it, don't raise it at all |
| **Praise** | Genuinely good work | A clean extraction, a well-chosen test case, a good name |

Include praise. It is not padding — it tells the author which instincts to repeat, which is the
main way review improves a team over time.

## Writing a review comment

A good comment has three parts: **what**, **why**, **what instead**.

```
Should fix — `process(order, true)` is unreadable at the call site, and the boolean
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

## Blocking
- **`file.py:42` — Resource leak.** The connection isn't closed if `parse()` raises.
  Wrap in `with` / try-with-resources / RAII.
- **`file.py:88` — Off-by-one at the upper boundary.** `range(1, n)` excludes `n`;
  the docstring says inclusive. Add a test at `n`.

## Should fix
- **`file.py:15` — `process()` does four things** (G30): validates, prices, formats,
  sends. Suggest extracting `validate`, `price`, `format_receipt`.
- **`file.py:60` — `1.08` is a magic number** (G25). Name it `TAX_RATE` and move it
  to module level (G35).

## Consider
- `LineItem` would be a good `@dataclass(frozen=True)` — you'd get equality and repr
  for free and the schema would be visible.

## Tests
What's covered, what isn't, which boundary cases are missing.

## Praise
- The `RetryPolicy` extraction is clean and the parameterized boundary test is exactly
  right.
```

Adjust depth to the size of the change. A ten-line diff gets a paragraph, not this template.

## Scoring rubric

When a numeric or graded assessment is requested, score each dimension 1–5 and justify with
specific line references. Never give a score without the justification — the reasoning is the
useful part.

| Dimension | 1 | 3 | 5 |
|---|---|---|---|
| **Correctness** | Known bugs; boundaries wrong | Happy path right, edges untested | Correct including boundaries, proven by tests |
| **Naming** | Cryptic, misleading | Mostly reasonable, some noise words | Every name states intent; consistent vocabulary |
| **Functions** | Long, many args, deep nesting | Mixed; a few too long | Small, one thing, one abstraction level, ≤2 args |
| **Comments** | Absent where needed, or redundant/stale | Some useful, some noise | Rare, all explain *why*; API contracts documented |
| **Structure** | God class; tangled dependencies | Reasonable split, some coupling | One responsibility per unit; dependencies injected |
| **Error handling** | Swallowed or ignored | Handled but thin on context | Every path handled; rich context; resources released |
| **Tests** | None, or assert nothing | Happy path covered | Behavior-named, boundaries covered, fast, independent |
| **Consistency** | Fights the codebase | Mostly matches | Indistinguishable from the best code in the repo |

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
