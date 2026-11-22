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
| `verdict` | reviewing a PR: seven checks, findings, merge tier | ~1.2k; passes on demand |

Agents: `reviewer` (runs `verdict`; never edits, approves or merges) and `tracker` (ticket
mechanics; never comments or closes).

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
| ≤ 400 added lines / 25 files per PR | CI range check (`size-exempt` label overrides only when applied by someone other than the author) |
| Branch names `<type>/<slug>`, no pushes to protected | `pre-push` hook, CI range check, branch protection |
| Gates (format, lint, typecheck, test) pass | `pre-commit` (fast), `pre-push` + CI (all) |
| Agents never bypass hooks or push to protected | Claude Code `PreToolUse` guard hook (incl. `sh -c`, `core.hooksPath`) |
| A PR cannot loosen its own checks | CI runs `standards.py` + `standards.toml` from the base branch |
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
| `/code-review`, pstack `interrogate`, bugbot | findings the `verdict` skill verifies one by one |

Review passes adapted from Cursor's Thermos plugin (MIT); credited in `skills/verdict/references/`.

## Evaluation

Three independent measurements, each A/B against a no-standards control, plus a regression gate.

```bash
pip install -r tools/evals/requirements.txt                     # eval-only deps (radon, ruff, ...)
python tools/bench.py all --variant NAME [--claude-md FILE]       # agent benchmark, resumable
python tools/skill_eval.py run --skill skills/clean-code --out results/lint/x   # code-quality eval
python tools/regress.py static          # every PR (CI): token cost, SkillEvaluator score, self-checks
python tools/regress.py bench NAME      # before release: agent tier vs tools/evals/baseline.json
```

**Methods.** Agent benchmark: 32 Exercism tasks (24 never used for tuning), 1 run per task per
arm, every agent pinned to one model (`--model`; an unpinned default silently drifted between
Opus, Sonnet and Haiku and invalidated an earlier cost result). Agents run headless, isolated from
operator hooks and plugins. Code metrics are established ones: McCabe cyclomatic complexity (1976),
Cognitive Complexity (Campbell 2018; validated against human understandability, Muñoz Barón et al.,
ESEM 2020), Halstead volume (1977), Maintainability Index (Oman & Hagemeister 1992) reported
**structurally**, because its comment term rewards comment density (Heitlager et al. 2007).
Change cost: on 8 tasks a neutral agent, identical in both arms, applies a 3-step chain of hidden
follow-up requirements to each arm's code. The blind judge (Claude Sonnet 5.5) sees each pair in
both orders and counts only order-consistent verdicts (Zheng et al. 2023). Statistics: per-task
paired differences, sign-flip permutation p-values and bootstrap 95% CIs (tasks are the unit).

### Results (shipped version, v2.1)

| Agent benchmark, Claude Sonnet 5.5, n = 32 tasks | No standards | Standards | Δ per task [95% CI] |
|---|---|---|---|
| Tests pass | 100% | 100% | — |
| Commits standards-compliant | 22% | **100%** | +78 pp [+62, +91] |
| Wrote directly to `main`/`dev` | 100% | **0%** | −100 pp |
| Lint severity | 6.25 | **2.16 (−65%)** | −4.1 [−6.6, −2.2] |
| Cognitive complexity (total) | 14.5 | **8.1 (−44%)** | −6.3 [−10.3, −3.3] |
| Max cyclomatic complexity | 7.9 | **4.4 (−44%)** | −3.5 [−5.1, −2.0] |
| Halstead volume | 236 | **170 (−28%)** | −66 [−115, −25] |
| Maintainability Index, structural | 51.5 | 51.3 | −0.3 [−1.7, +1.0] |
| New tokens per task | 12.2k | 14.2k (**+16%**) | +1.95k [+1.4k, +2.6k] |
| Cost per task | $0.07 | $0.08 | +$0.01 |
| **Blind judge:** preferred | 5 | **20** (7 ties) | p ≈ 0.004 (sign test) |
| **Change chain:** all suites pass after 3 steps | 75% | 75% | 0 |
| **Change chain:** cognitive complexity after | 25.3 | **18.1** | −7.1 [−14.3, −0.4] |

Claude Haiku 5.5 on the 24 held-out tasks agrees: lint −77%, cognitive complexity −41%, max
cyclomatic −33%, Halstead −13% (all CIs exclude 0), at +45% new tokens.

NVIDIA SkillEvaluator 0.9.0 static quality: `clean-code` 87.5 (v1.1 was 77.0), `verify` 93.8,
`ship` 91.2, `setup-standards` 93.8.

**Verdict.** The standards make agent output compliant, measurably simpler, and preferred by a
blind reviewer, for about +16% tokens per task on Sonnet. Code stays simpler through later changes,
but the chains did not separate on correctness. The effect comes from the always-loaded `CLAUDE.md`
block and the hooks: headless agents rarely invoke a skill, so the block carries the
highest-value rules and the skills hold the depth.

**Retracted.** An earlier "−40% cost per task" came from runs whose model had drifted between arms;
the clean, pinned measurement above shows a cost *increase*.

**Rejected candidate (v2.3).** Trimming the process lines ("branch in one step", "run the check
once, right before you commit") to cut cost passed the regression gate but missed its goal: new
tokens −2.3% [−5.4%, +1.0%] versus v2.1 (n = 32, Sonnet), while cognitive complexity rose +0.7
[+0.03, +1.3]. No gain, so no version bump.

**Rejected candidate (v2.2).** Adding "docstrings on public APIs" to the block barely moved the
comment ratio, lowered the judge's preference, and failed the regression gate on ruff violations.
It was measured before model pinning, so the rejection is provisional; the variant file is kept in
`tools/evals/variants/`.

**Robustness.** On the 24 held-out tasks alone, with a Holm correction across 8 metrics, lint
(p = 0.002), cognitive complexity (p < 0.001), max cyclomatic complexity (p = 0.002) and the token
increase (p < 0.001) stay significant; Halstead becomes borderline (p = 0.058). Every solution in
both arms passes its tests.

**Limits** (from an independent audit of methods). Compliance is enforced by the hooks, so it
measures enforcement, not learning. Max CC and lint partly mirror the block's own rules; Halstead,
the judge and the change chains are the less circular signals. The judge shares the agent's model
family. 1 run per task and no A/A replicate, so small variant deltas (v2.2, v2.3) are within
unmeasured run-to-run noise. Single-file Python tasks; change chains too easy to separate pass
rates; v2.1 code carries almost no comments. Multi-file and SWE-bench-scale runs need Docker and
were not run.

## Bibliography

Robert C. Martin, *Clean Code* (2008) — source of the smell catalog's ID scheme; Fowler,
*Refactoring* (2018); Beck, *Test-Driven Development* (2002); Feathers, *Working Effectively with
Legacy Code* (2004); Hunt & Thomas, *The Pragmatic Programmer* (1999); the Conventional Commits
specification. All prose is original to this project.

## License

MIT — see [LICENSE](LICENSE).
