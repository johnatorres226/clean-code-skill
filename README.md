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

Measured 2026-11-15 on Claude Opus 5.5, runs isolated from operator hooks and plugins. Raw data:
`results/` (git-ignored; reproduce with the commands above and `python tools/bench.py run`).

**1. Task benchmark — real agent, real repo, skill environment vs none** (`tools/bench.py`;
8 Exercism tasks incl. 3 refactoring exercises, 2 runs per arm, n = 16 per arm, all runs valid)

| Metric | No standards | Standards | Effect |
|---|---|---|---|
| Tests pass | 100% | 100% | no regression |
| Commits standards-compliant | 19% | **100%** | +81 pts |
| Wrote directly to `main`/`dev` | 100% | **0%** | eliminated |
| Lint weighted severity (mean) | 10.4 | **7.1** | −32%; 7/8 tasks better, sign-flip p = 0.039 |
| Lint-clean solutions | 6% | 25% | ×4 |
| Turns (mean) | 10.0 | 8.6 | −14% |
| Cost per task (mean) | $0.15 | $0.15 | ±0 |

**2. Code-quality eval — same prompts, skill read vs not** (`tools/skill_eval.py`; 6 cases × 3
runs per arm)

| Metric | No skill | `clean-code` | Effect |
|---|---|---|---|
| Weighted lint severity | 37.0 ± 1.4 | **19.0 ± 4.3** | −49% |
| Lint-clean cases | 5/18 | 7/18 | +2 |
| Cost per 6 cases | $0.32 | $0.95 | ×3 (reading the skill costs 2–3 extra turns) |

**3. Static skill quality** (NVIDIA SkillEvaluator 0.9.0 `quality-check`, gated in CI)

| Skill | Score |
|---|---|
| `clean-code` v1.1 (before this redesign) | 77.0 C |
| `clean-code` v2 | 89.2 B |
| `verify` / `ship` / `setup-standards` | 93.8 A / 91.2 A / 93.8 A |

**Verdict.** The environment works where it is enforced: compliance went from 19% to 100% and
protected-branch writes from 100% to 0% at **no extra cost per task**, with no loss in test pass
rate, and solutions were measurably cleaner. Reading the `clean-code` skill halves lint severity
but triples cost, so it pays for itself on code that will be maintained, not on throwaway work.

**Limits.** Agents never auto-invoked a skill in headless runs (0/32); the benchmark effect comes
from the always-loaded `CLAUDE.md` block plus the hooks, not from skill bodies. n is small (2 runs
per task); tasks are single-file Python; the lint scorer is heuristic. SWE-bench-scale and
multi-language runs need Docker and other toolchains and were not run.

## Bibliography

Robert C. Martin, *Clean Code* (2008) — source of the smell catalog's ID scheme; Fowler,
*Refactoring* (2018); Beck, *Test-Driven Development* (2002); Feathers, *Working Effectively with
Legacy Code* (2004); Hunt & Thomas, *The Pragmatic Programmer* (1999); the Conventional Commits
specification. All prose is original to this project.

## License

MIT — see [LICENSE](LICENSE).
