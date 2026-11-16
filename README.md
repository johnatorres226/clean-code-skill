# clean-code-standards

The **environment contract** for production-grade agentic development. Orchestration frameworks
like [pstack](https://github.com/cursor/plugins/tree/main/pstack) and
[mattpocock-skills](https://github.com/mattpocock/skills) define *how agents run the work*. This
plugin defines *what acceptable work is* — up front, as config, enforced by tools:

- **How to code** — language-agnostic clean-code standards (naming, functions, errors, design, tests).
- **Quality gates** — format, lint, typecheck, test commands every change must pass.
- **Git discipline** — atomic Conventional Commits with size limits, protected `main`/`dev`,
  feature branches by type, PR size limits, post-PR review, merge and release rules.
- **Definition of done** — gates green plus evidence the behavior works, reported honestly.

It is not a comprehensive guide. Rules a tool can check are enforced by a tool; prose covers only
judgment calls. That keeps the token cost low and the rules impossible to forget.

## Install and adopt

```bash
claude plugin install <path-or-url-to-this-repo>   # or point your plugin config at a clone
```

Then, in the repository you want governed: `/setup-standards`. It detects the stack, writes
`standards.toml` with the repo's own gate commands, installs git hooks, a CI workflow, a PR
template, branch protection, and a short always-loaded `CLAUDE.md` block.

## Skills

| Skill | Use when | Cost when triggered |
|---|---|---|
| `setup-standards` | adopting the standards in a repo | ~1.2k tokens |
| `clean-code` | writing, reviewing, refactoring code | `SKILL.md` ~3.3k; references on demand |
| `verify` | before claiming done, committing behavior, opening a PR | ~600 tokens |
| `ship` | branching, committing, PRs, review, merge, release | ~1.2k tokens |

The only always-loaded cost is the ~120-token `## Standards` block in the governed repo's
`CLAUDE.md`.

## Enforcement

`standards.toml` is the single source of truth. One stdlib Python file
(`.githooks/standards.py`) reads it everywhere:

| Rule | Enforced by |
|---|---|
| No commits to `main`/`dev` | `pre-commit` hook, branch protection |
| Conventional Commit subject ≤ 72 chars | `commit-msg` hook, CI range check |
| ≤ 300 added lines / 10 files per commit | `pre-commit` hook, CI range check |
| ≤ 400 added lines / 25 files per PR | CI range check (`size-exempt` label overrides, visibly) |
| Branch names `<type>/<slug>`, no pushes to protected | `pre-push` hook, branch protection |
| Gates (format, lint, typecheck, test) pass | `pre-commit` (fast), `pre-push` + CI (all) |
| Agents never bypass hooks or push to protected | Claude Code `PreToolUse` guard hook |
| Review before merge | branch protection (required checks and reviews), `ship` skill |

Deletions never count toward size limits, so cleanup is never blocked. The guard hook is a no-op
in repositories without `standards.toml`.

## Working with pstack and mattpocock-skills

This plugin does not orchestrate; it is the floor every orchestrator's output must clear.

| Their step | Gate it hits here |
|---|---|
| pstack `poteto-mode` Feature / Bug fix, mattpocock `implement` | `clean-code` while writing; `verify` before done |
| mattpocock `tdd`, pstack `principle-prove-it-works` | `verify` evidence table (red-then-green for fixes) |
| pstack Opening a PR (small ordered commits) | `ship` commit rules; hooks reject oversize or malformed commits |
| pstack Babysit, bugbot triage | CI `standards` check; `ship` §4 review findings |
| pstack Shipping (land the verified stack) | branch protection + `ship` §5 merge, §6 release |
| mattpocock `to-tickets`, `triage` | one ticket → one `<type>/<slug>` branch → one PR to `dev` |
| `/code-review`, pstack `interrogate` | satisfies the `ship` §4 review pass |

## Evaluation

```bash
python tools/skill_audit.py skills/clean-code          # context budget and structure
python tools/skill_eval.py run --no-skill --out results/base
python tools/skill_eval.py run --skill skills/clean-code --out results/skill
python tools/skill_eval.py compare results/base results/skill
python tests/test_standards.py                          # enforcement self-check
pip install skillevaluator && skillevaluator quality-check skills/verify   # NVIDIA static tier
```

### Results

_Filled in by the evaluation phase._

## Bibliography

Robert C. Martin, *Clean Code* (2008) — source of the smell catalog's ID scheme; Fowler,
*Refactoring* (2018); Beck, *Test-Driven Development* (2002); Feathers, *Working Effectively with
Legacy Code* (2004); Hunt & Thomas, *The Pragmatic Programmer* (1999); the Conventional Commits
specification. All prose is original to this project.

## License

MIT — see [LICENSE](LICENSE).
