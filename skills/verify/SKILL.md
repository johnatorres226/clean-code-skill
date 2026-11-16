---
name: verify
description: Definition of done for any code change in a repo with standards.toml — run the quality gates, prove the behavior with evidence, and report pass, fail, or inconclusive honestly. Use before claiming a task is done, before every commit that changes behavior, before opening or updating a PR, and whenever asked "does it work", "verify", "check it", or "is this ready".
version: 2.0.0
metadata:
  author: johnatorres226
  tags: [verification, quality-gates, testing, definition-of-done]
---

# Verify

"It compiles" is not evidence. Done means the gates pass **and** the changed behavior is shown
working on the real artifact.

## 1. Run the gates

```bash
python3 .githooks/standards.py check          # all gates from standards.toml, in order
python3 .githooks/standards.py check --fast   # format + lint only, while iterating
```

A failing gate is fixed at the cause. Never blank a gate, loosen a limit, skip a test, or use
`--no-verify` to get green — if a rule is wrong, say so and change `standards.toml` in its own
commit with the reason.

## 2. Prove the behavior — match the check to the change

| Change | Evidence |
|---|---|
| Bug fix | A test that fails before the fix and passes after. Show both runs. |
| New behavior | Tests for the contract, including the boundaries (empty, one, many, max, invalid). |
| Refactor | The existing suite, unchanged and green. A test edit means it was not a pure refactor. |
| CLI / API | Run the real command or request; paste the output. |
| UI | Drive the changed flow in the running app; screenshot or recording. |
| Performance | Before/after on the same machine and build, several runs, median and range. |
| Config / infra | Apply it somewhere disposable, read back the result. |

No tests exist for the area? Write characterization tests for what you touch first (skill:
`clean-code`, `references/tdd-and-tests.md`).

## 3. Report honestly

State each result as **pass**, **fail**, or **inconclusive** — with the command and its output.
A check you could not run is inconclusive, never pass. Mark claims as measured, inferred, or
guessed. That report goes in the PR's Evidence section verbatim.
