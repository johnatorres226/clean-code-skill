---
name: setup-standards
description: Install the clean-code-standards environment into a repository — standards.toml (branches, commit and PR size limits, quality gates), git hooks, CI workflow, PR template, branch protection, and the always-loaded CLAUDE.md block. Use for /setup-standards, "set up standards", "adopt clean-code-standards", "add commit rules / branch protection / quality gates", or when a repo has no standards.toml and the user wants production-grade rules enforced.
version: 2.0.0
metadata:
  author: johnatorres226
  tags: [standards, git-hooks, ci, branch-protection, setup]
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

**A new project with no manifests yet:** ask which stack it will use and fill the gates with that
stack's commands. Most pass on an empty tree (`ruff check .`), and a gate left blank now is
rarely filled later.

Propose a secret scanner for the `secrets` gate the same way: `gitleaks git --pre-commit --staged
--redact` (gitleaks 8.19+). It runs at every commit, because a committed secret needs a history
rewrite; every machine needs the binary. On GitHub, push protection (step 4) is the backstop.

## 2. Copy the templates

```
standards.toml                          → repo root (gates filled from step 1)
.githooks/{pre-commit,commit-msg,pre-push,standards.py}
.github/workflows/standards.yml         → add the toolchain install step the gates need
.github/pull_request_template.md
.editorconfig  .gitattributes
CLAUDE.standards.md                     → appended to CLAUDE.md in step 5
.claude/settings.json                   → last, in step 6: agents may not edit the enforcement files
```

Fill `[roles]` in `standards.toml` (senior team, `guarded` paths, who reviews each `area`, the
`auto_merge` allow-list of docs-only paths), `[tests].holdout` (acceptance tests agents may not
rewrite) and `[review]` (the human-review paths and content patterns for this codebase, and the
reviewer agent's App id once it exists).

**Project type.** Ask once: who depends on this? The answer sets release approval and how
freely docs merge. Docs that describe code can drift from it, so the reviewer checks their
claims against the code at every tier.

| Answer | `[release].approval` | `[roles].auto_merge` | `auto_merge_max_lines` | `[size].exclude` adds |
|---|---|---|---|---|
| Only me | `auto` | `docs/`, `*.md` | 1000 | `docs/*`, `*.md` |
| My team | `tiered` | `docs/`, `*.md` | 1000 | `docs/*`, `*.md` |
| Others (a product or service) | `human` | notes only: `docs/research/`, `CHANGELOG.md` | 50 | nothing |

If the product itself is Markdown (skills, prompts, agent definitions), list docs paths
instead of `*.md`.

Check the floor with `python .githooks/standards.py tier <base>` on a few past PRs: a
consequential one it rates below human review means a missing trigger. Then generate
`.github/CODEOWNERS` with `python .githooks/standards.py codeowners > .github/CODEOWNERS`.

Then activate the hooks: `git config core.hooksPath .githooks`. This is per-clone, so it also
goes in the README's setup steps for humans.

## 3. Branches

Create the integration branch if missing: `git branch dev <release>` and push it. If the team
uses a different name, change `[branches]` rather than the scripts.

## 4. Rulesets and release environment — confirm first, they change shared settings

One ruleset per protected branch, generated from `standards.toml` (needs admin on the repo):

```bash
for b in dev main; do
  python .githooks/standards.py ruleset $b | gh api -X POST repos/{owner}/{repo}/rulesets --input -
done
```

Each requires a PR, the strict `standards` check from GitHub Actions, code-owner review,
dismissal of stale approvals, approval of the last push by someone else, resolved conversations,
and no force pushes or deletions; the integration branch also requires linear history. The bypass
list is empty. Only on a solo repo set `[roles].admin_bypass = true`: the admin may then merge
their own PRs, never push directly, and each bypass is logged. After the first apply, check that
the ruleset page lists "Repository admin" as the bypass actor. If you already ran classic
protection, delete it (`gh api -X DELETE repos/{owner}/{repo}/branches/<b>/protection`) so one
source of rules remains.

Releases: create a `release` environment with the senior team as required reviewers,
"Prevent self-review" on, admin bypass off, and deployments limited to `main`. Keep deploy
secrets in that environment, never in repository secrets.

Security settings, same confirmation (push protection is free on public repos):

```bash
gh api -X PATCH repos/{owner}/{repo} -f 'security_and_analysis[secret_scanning][status]=enabled' \
  -f 'security_and_analysis[secret_scanning_push_protection][status]=enabled'
```

If `gh` lacks admin rights, print the commands for the owner instead. Agents run with a GitHub
App or fine-grained token without Administration or Workflows permission, so they can never
change these settings.

## 5. The always-loaded block

Append `templates/CLAUDE.standards.md` to `CLAUDE.md` (or `AGENTS.md` if that is what the repo
uses; never create both). If a `## Standards` section exists, replace it in place. Keep the text
as shipped: it is the measured variant (tools/bench.py), and its one code line is what moved
agent code quality, since headless agents rarely load skills on their own.

## 6. Prove it and commit

Run `python3 .githooks/standards.py check` — every non-empty gate must pass on the current tree.
A gate that fails on existing code is a finding to report, not a reason to blank the gate. Then
commit on a branch as `chore: adopt clean-code-standards` and open a PR (skill: `ship`). The
hooks run on that very commit, which is the end-to-end test. Copy `.claude/settings.json` last:
from then on agents cannot edit `standards.toml`, `.githooks/`, `.github/` or `.claude/`.

Report: the gates chosen and why, files added or skipped, protection applied or the command
handed to the owner, and the first `check` result.
