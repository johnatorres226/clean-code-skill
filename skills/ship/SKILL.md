---
name: ship
description: Production git workflow for repos with standards.toml — branch naming, atomic Conventional Commits within size limits, opening a PR, the post-PR review pass, addressing findings, and merging to dev and releasing to main. Use when committing, splitting a change into commits, opening or updating a PR, reviewing a PR, merging, releasing, or when asked to "commit", "ship", "open a PR", "review this PR", "merge", or "release".
version: 2.0.0
metadata:
  author: johnatorres226
  tags: [git, conventional-commits, pull-requests, code-review, release]
---

# Ship

Limits and branch names come from `standards.toml`; hooks and CI enforce them. This skill is the
order of operations and the judgment the hooks cannot make.

## 1. Branch

From the integration branch, as `<type>/<slug>`: `git switch dev && git pull && git switch -c
feat/csv-export`. One branch, one goal. A second goal is a second branch.

## 2. Commit — atomic, one concern each

- **One concern per commit:** a refactor, a behavior change, a test, a dependency bump, a
  formatting pass — each its own commit. Never mix a refactor with a behavior change.
- **Each commit builds and passes the fast gates.** History must be bisectable.
- **Order tells the story:** preparatory refactor → tests → behavior → cleanup.
- **Subject:** `<type>(<scope>): <imperative summary>`, ≤ 72 chars. Body says *why*, not what.
- **Over the size limit?** Split by concern (`git add <paths>`; `git add -p` is interactive, so agents stage
  hunks with `git apply --cached <patch>`), not by file count. Generated files and
  lockfiles are excluded from the count; vendored code goes in its own commit.
- **Mid-work fixes to an unpushed commit** use `git commit --fixup <sha>` then
  `GIT_SEQUENCE_EDITOR=: git rebase -i --autosquash dev` (non-interactive). Never rewrite pushed shared history.

## 3. Push early, as a draft PR

After the first commit, push and open a **draft** PR to `dev`, then push each commit after it. CI
runs on every push against the branch merged with `dev`, so integration problems show up early:

```bash
git push -u origin HEAD
gh pr create --draft --base dev --fill-first   # first line of the description: Closes #<ticket>
```

When the work is done, run the `verify` skill, complete the template and mark the PR ready:
`gh pr ready`. Review (step 4) starts there, never on a draft.

CI rejects a PR whose description does not link its ticket, and a PR that changes acceptance
tests (`[tests].holdout`) together with code: tests that define "done" change in their own PR.

Over the PR size limit → split into stacked PRs, each independently reviewable and green. The
only exception is work that cannot be split meaningfully (bootstrap, vendored code, a mechanical
bulk rename): say why in the description and ask a reviewer to label the PR `size-exempt` (CI ignores the
label when the author applied it). Messages are still
checked; deletions never count toward limits.

## 4. Review pass — once the PR is ready, before merge

Review the PR as a reviewer who did not write it: the `reviewer` agent, or the `verdict` skill
in a fresh context, so the author is not grading their own work. It returns a verdict line with the
merge tier and posts its findings. Other review tools (`/code-review`, pstack `interrogate`,
bugbot) feed it findings to verify; they do not replace it.

Then fix every **blocking** finding in new atomic commits, answer every non-blocking one (fix, or
decline with a reason), and re-run `verify`. Unaddressed blocking findings mean not mergeable.

## 5. Merge

Mergeable = CI `standards` green + required reviews + no open blocking findings + branch up to
date with `dev`. Who may merge follows the verdict's tier (`docs/adr/0002` in this plugin's repo):
**auto-merge** and **agent merge** merge once checks are green and no blocking finding is open;
**human review** also needs a senior's approval. Enable auto-merge (`gh pr merge --auto --rebase`) and
move on; never approve your own PR or ask an agent to approve it. pstack: use Autopilot-stack
for human review, Autopilot-full otherwise. Merge with the method in `[branches].merge` (default rebase, which keeps the
atomic commits): `gh pr merge --rebase --delete-branch`. Never force-push or push directly to a
protected branch — the guard hook blocks it.

Once merged, clean up locally: `git switch dev && git pull`, then `git branch -D <branch>` for the
branch you just merged (a rebase merge rewrites its commits, so `-d` refuses), and `git worktree
remove <path>` if it had one. The remote branch is deleted on merge (setup-standards step 4).

## 6. Release

A release promotes reviewed work (`docs/adr/0003` in this plugin's repo). Only `dev` merges to
`main`, through a PR titled `release: <version or date>` with a merge commit (`gh pr merge
--merge`); tag the merge commit.

- **When:** a spec releases when its enabling ticket merges; a standalone ticket right after it
  merges (ask the `tracker` agent which other merged tickets can join it).
- **The PR:** exempt from the size, ticket-link and holdout rules. CI checks that every commit came
  through a reviewed ticket PR and runs `[release.gates]`. Run the `verdict` skill in release mode
  for the release notes and where tickets interact.
- **Approval:** `[release].approval` decides whether a senior approves (`human`, `tiered`, `auto`).

Hotfix, only when `dev` cannot be released: branch `fix/` from `main`, PR to `main`, then merge
`main` back into `dev` the same day.
