Closes #<!-- ticket number: CI fails a PR that does not link its ticket -->

## Why

<!-- The user/maintainer goal this serves. One or two sentences. -->

## What changed

<!-- One line per commit is usually enough. -->

## Scope

<!-- What this PR deliberately does not do. Anything beyond the ticket is a reason to reject. -->

## Blast radius

<!-- What breaks if this is wrong, and the door: two-way (easy to revert) or one-way (data,
     migrations, public API, auth) — one-way doors always need a human approval. -->

## Verification

<!-- Gate output (`python3 .githooks/standards.py check`) and proof the behavior works:
     failing-then-passing test, command output, screenshot. "It compiles" is not evidence. -->

## Review

- [ ] One concern per commit, Conventional Commit messages
- [ ] Within size limits (`standards.toml`), or split
- [ ] Acceptance tests (`[tests].holdout`) untouched, or changed in their own PR
- [ ] Review pass done; blocking findings fixed or answered on the thread
