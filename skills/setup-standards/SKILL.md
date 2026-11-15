---
name: setup-standards
description: Install the clean-code-standards environment into a repository — standards.toml (branches, commit and PR size limits, quality gates), git hooks, CI workflow, PR template, branch protection, and the always-loaded CLAUDE.md block. Use for /setup-standards, "set up standards", "adopt clean-code-standards", "add commit rules / branch protection / quality gates", or when a repo has no standards.toml and the user wants production-grade rules enforced.
---

# Setup standards

Install the environment so the rules are enforced by tools, not remembered by agents. Templates
live in `templates/` next to this file. Never overwrite an existing file — merge or skip, and say
which.

## 1. Detect the stack and its existing commands

Read the manifests and configs that exist: `package.json` scripts, `pyproject.toml`, `Makefile`,
`go.mod`, `Cargo.toml`, `pom.xml`/`build.gradle`, `CMakeLists.txt`, and any formatter/linter
config. Prefer commands the repo already runs (`npm test`, `make lint`) over inventing new ones.

Fill `[gates]` in `standards.toml` with **check-only** commands: format (`--check`, never
rewriting), lint, typecheck, test. A gate the stack has no tool for stays `""`. If the repo has no
linter or formatter at all, propose the ecosystem default once (ruff, eslint+prettier, gofmt+vet,
clippy+rustfmt, clang-format+clang-tidy, checkstyle) and add it only on a yes.

## 2. Copy the templates

```
standards.toml                          → repo root (gates filled from step 1)
.githooks/{pre-commit,commit-msg,pre-push,standards.py}
.github/workflows/standards.yml         → add the toolchain install step the gates need
.github/pull_request_template.md
.editorconfig  .gitattributes
```

Then activate the hooks: `git config core.hooksPath .githooks`. This is per-clone, so it also
goes in the README's setup steps for humans.

## 3. Branches

Create the integration branch if missing: `git branch dev <release>` and push it. If the team
uses a different name, change `[branches]` rather than the scripts.

## 4. Branch protection — confirm first, it changes shared settings

For each protected branch, with `gh` (needs admin on the repo):

```bash
gh api -X PUT repos/{owner}/{repo}/branches/<branch>/protection --input - <<'JSON'
{"required_status_checks": {"strict": true, "contexts": ["standards"]},
 "enforce_admins": true,
 "required_pull_request_reviews": {"required_approving_review_count": 1},
 "restrictions": null, "allow_force_pushes": false, "allow_deletions": false}
JSON
```

Set the review count from `[pr].reviews_required`. On a solo repo, offer `0` reviews with the
status check still required. If `gh` lacks admin rights, print the command for the owner instead.

## 5. The always-loaded block

Add this to `CLAUDE.md` (or `AGENTS.md` if that is what the repo uses; never create both). If a
`## Standards` section exists, update it in place.

```markdown
## Standards

Rules: `standards.toml`. Hooks and CI enforce them — fix failures, never bypass (`--no-verify`).
- Branch from `dev` as `<type>/<slug>`; never commit or push to `main`/`dev`.
- One concern per commit, Conventional Commit subject, within the size limits.
- Done = `python3 .githooks/standards.py check` green + evidence. Skill: `verify`.
- PR to `dev`, review pass, merge per `[branches].merge`. Only `dev` merges to `main`. Skill: `ship`.
- Writing or reviewing code: skill `clean-code`.
```

## 6. Prove it and commit

Run `python3 .githooks/standards.py check` — every non-empty gate must pass on the current tree.
A gate that fails on existing code is a finding to report, not a reason to blank the gate. Then
commit on a branch as `chore: adopt clean-code-standards` and open a PR (skill: `ship`). The
hooks run on that very commit, which is the end-to-end test.

Report: the gates chosen and why, files added or skipped, protection applied or the command
handed to the owner, and the first `check` result.
