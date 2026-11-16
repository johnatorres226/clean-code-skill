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

Three independent measurements, each A/B against a no-standards control, plus a regression gate.

```bash
pip install -r tools/evals/requirements.txt                     # eval-only deps (radon, ruff, ...)
python tools/bench.py all --variant NAME [--claude-md FILE]       # agent benchmark, resumable
python tools/skill_eval.py run --skill skills/clean-code --out results/lint/x   # code-quality eval
python tools/regress.py static          # every PR (CI): token cost, SkillEvaluator score, self-checks
python tools/regress.py bench NAME      # before release: agent tier vs tools/evals/baseline.json
```

**Methods.** Agent benchmark: 8 Exercism tasks (3 refactoring), 2 runs each, n = 16 per arm,
Claude Opus 5.5 headless, isolated from operator hooks and plugins. Code metrics are established
ones: McCabe cyclomatic complexity (1976), Cognitive Complexity (Campbell 2018; validated against
human understandability, Muñoz Barón et al., ESEM 2020), Halstead volume (1977), Maintainability
Index (Oman & Hagemeister 1992) reported **structurally**, because its comment term rewards
comment density (Heitlager et al. 2007). Phase 2 measures change cost: a neutral agent, identical
in both arms, extends each arm's code against hidden tests. The blind judge (Claude Sonnet 5.5)
sees each pair in both orders and counts only order-consistent verdicts (Zheng et al. 2023).
p-values: sign-flip permutation test over per-task differences.

### Results (shipped version, v2.1)

| Agent benchmark | No standards | Standards | p |
|---|---|---|---|
| Tests pass | 100% | 100% | — |
| Commits standards-compliant | 19% | **100%** | 0.009 |
| Wrote directly to `main`/`dev` | 100% | **0%** | 0.009 |
| Lint severity | 10.4 | **2.6 (−75%)** | 0.017 |
| Cognitive complexity (total) | 15.8 | **10.1 (−36%)** | 0.023 |
| Max cyclomatic complexity | 9.8 | **4.9 (−50%)** | 0.023 |
| Maintainability Index, structural | 48.5 | 48.3 | 0.80 |
| Cost per task | $0.15 | **$0.09 (−40%)** | 0.048 |
| **Change cost:** tokens to apply a follow-up | 10.2k | **9.6k (−5%)** | 0.023 |
| **Change cost:** cognitive complexity after it | 19.8 | **12.8 (−36%)** | 0.039 |
| **Blind judge:** preferred | 1 | **12** (3 ties) | ≈ 0.003 (sign test) |

| Code-quality eval (`clean-code` read; 6 cases × 3 runs) | No skill | v2.0 | **v2.1** |
|---|---|---|---|
| Weighted lint severity | 37.0 | 19.0 | **16.0** |
| Lint-clean cases | 5/18 | 7/18 | **9/18** |
| Cost per 6 cases | $0.32 | $0.95 | **$0.31** |

NVIDIA SkillEvaluator 0.9.0 static quality: `clean-code` 87.5 (v1.1 was 77.0), `verify` 93.8,
`ship` 91.2, `setup-standards` 93.8.

**Verdict.** The standards make agent output compliant, measurably simpler, preferred by a blind
reviewer, and cheaper to change — at **lower** cost per task than no standards. The effect comes
from the always-loaded `CLAUDE.md` block and the hooks: headless agents invoked a skill in 1 of 16
runs, so the block carries the highest-value rules and the skills hold the depth.

**Rejected candidate (v2.2).** Adding "docstrings on public APIs" to the block barely moved the
comment ratio (0.01 → 0.02), lowered the judge's preference (12–1 → 9–4), raised change cost, and
failed the regression gate on ruff violations. v2.1 stays; the variant file is kept in
`tools/evals/variants/` so the result is reproducible.

**Limits.** n = 2 runs per task; single-file Python tasks; follow-ups too easy to separate pass
rates (both 100%); the v2.1 change also trimmed `SKILL.md`, so the two are not separated;
v2.1 code carries almost no comments (comment ratio 0.12 → 0.01). Multi-file and SWE-bench-scale
runs need Docker and were not run.

## Bibliography

Robert C. Martin, *Clean Code* (2008) — source of the smell catalog's ID scheme; Fowler,
*Refactoring* (2018); Beck, *Test-Driven Development* (2002); Feathers, *Working Effectively with
Legacy Code* (2004); Hunt & Thomas, *The Pragmatic Programmer* (1999); the Conventional Commits
specification. All prose is original to this project.

## License

MIT — see [LICENSE](LICENSE).
