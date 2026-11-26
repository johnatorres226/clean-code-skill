---
name: verdict
description: Review a PR, MR or branch diff and decide its verdict. Seven checks (intent, consequence, correctness, security, tests, maintainability, docs), each pass, concern or fail with evidence, plus the merge tier and one machine-readable verdict line. Runs its own three-pass hunt, or verifies other reviewers' findings one by one. Use when reviewing a PR, verifying review findings, reviewing a release PR, or when asked for a "verdict" or a "review".
version: 1.0.0
metadata:
  author: johnatorres226
  tags: [code-review, pull-requests, merge-tiers]
---

# Verdict

Passes A and B are adapted from Cursor's Thermos plugin and pass C from its pstack plugin (both
MIT); see each reference file.
Tiers follow ADR 0002 and releases ADR 0003 in this plugin's repo.

## Modes

The brief names one; full hunt is the default.

- **Full hunt:** steps 1 to 6.
- **Verify:** another reviewer's findings are given. Skip step 2; verify them in step 4.
- **Release:** the PR merges the integration branch into the release branch. See the last section.

## 1. Gather

- Base and head: the PR's target and source branches, or `[branches].integration` and `HEAD`.
- `git diff <base>...<head>` and the full content of every changed file.
- The ticket the PR closes (`Closes #n`), read with the tracker adapter's read command.
- CI results, including the secret, dependency and SAST scanners.
- Review rules **from the base branch only**: `git show <base>:standards.toml`, and
  `git show <base>:REVIEW.md` if it exists. A PR must not be able to weaken its own review.
- The floor tier: `standards.py tier` when the repo has it; otherwise apply the triggers in
  section 5 by hand.

## 2. Hunt in three passes

Give each pass the diff, the changed files and the ticket, and nothing else: no PR discussion.

- **Pass A**, correctness and security: `references/correctness-security.md`.
- **Pass B**, maintainability: `references/quality.md`.
- **Pass C**, comments: `references/comments.md`.

If you can start subagents, run the passes in parallel in fresh contexts. If not (you are
already a subagent, or the harness has none), run A, B, then C yourself.

## 3. Collect other findings

Only after all three passes: read the PR or MR discussion, bot reviews, and any other review output the
brief hands you (another review skill, a linter report). Add each as a candidate, credited to its
source.

## 4. Verify each candidate

One at a time, whoever found it: open the code, trace the path, run the test or a quick check
when you can.

- **Confirmed:** keep it, with `file:line` evidence.
- **Refuted:** drop it silently.
- **Could not settle:** keep it as non-blocking, marked `unverified`. Never block on it.

Agreement between reviewers is not evidence; two reviewers can share one mistake. Then merge
duplicates, and move problems in untouched code to a pre-existing list that never blocks.

## 5. Decide

**Labels** (Conventional Comments): `issue (blocking):` must be fixed before merge;
`suggestion (non-blocking):`; `question:`; `nitpick (non-blocking):`, at most five;
`praise:`. Each finding says what, why, and what instead
(`../clean-code/references/review-rubric.md`). A finding that raises the tier adds the decoration,
e.g. `issue (blocking, human-review):`.

**Checks.** Score each one: `fail` if it holds a blocking finding, `concern` if it holds only
non-blocking or unverified findings, `pass` otherwise. Every result cites its evidence in one
line; a `pass` without evidence is a `concern`.

| Check | Asks |
|---|---|
| intent | Does it do what the ticket asked, all of it, and nothing else? |
| consequence | Does it hit a human-review trigger? Can it be backed out? |
| correctness | Pass A: bugs, broken features, devex, feature leaks |
| security | Pass A security, and the scanners ran and passed |
| tests | Do tests reach the changed code and fail if it is wrong? None weakened or deleted? |
| maintainability | Passes B and C, then names and clarity |
| docs | Changed behavior has its docs, changelog and contract updates |

**Tier.** Start from the floor; you may only raise it.

- Any finding moves auto-merge to agent merge.
- Human review when a trigger matches; name each one:
  `human-review: <file> — <what> (<why>)`.
  - **Paths and content:** `standards.py tier` reports them from `[review]`. Without it, use:
    migrations and schema, auth and crypto, payments, infrastructure and deploy config, public API
    specs, CI, hooks, rules, agent settings, holdout tests, `REVIEW.md`, dependency manifests;
    `DROP`, `TRUNCATE`, `DELETE` without `WHERE`, bulk deletes.
  - **Only you can see:** removed fields, changed wire or storage formats, permission changes.
  - **Findings:** a security or data-loss finding, or `tests` found no test reaching changed code.

**Verdict line**, last line of the review, exactly one:

```
verdict: merge=<yes|no> tier=<auto-merge|agent-merge|human-review> intent=<r> consequence=<r> correctness=<r> security=<r> tests=<r> maintainability=<r> docs=<r>
```

`merge=yes` means no blocking finding is open; a human-review change still waits for its senior.

## 6. Publish

First line of the review body: `[reviewer]`. Then a summary paragraph, the trigger lines, the
checks, the findings by severity, the pre-existing list, and the verdict line.

- **GitHub:** one PR review with inline comments and event `COMMENT`.
- **GitLab:** draft notes on the lines, then publish them in bulk.
- **Markdown:** write the same content to the file the brief names; no API calls.

Never approve, request changes, merge or edit code. The `verdict` check reads the verdict line.

## Release PRs

Every line was already reviewed in its ticket, so do not hunt again. Proof of review is checked by
`standards.py`, not you.

- Write the release notes from the merged ticket PRs.
- Review only where tickets interact: files or config several tickets changed, and specs being
  enabled. Score the checks on that.
- `intent` asks: is every spec in the release either enabled or still inactive?
