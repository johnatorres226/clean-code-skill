# clean-code-skill

A Claude skill for clean code standards across **C, C++, Java, and Python** — packaged as a
plugin, with tooling to curate and evaluate the skill itself.

Covers naming, function design, comments, formatting, error handling, class and module design,
test-driven development, refactoring, and a 66-entry smell catalog. Ships a working linter, a TDD
scaffolder, and formatter/linter configs for all four languages.

## Install

**As a plugin** (gives you the skill plus the `/clean-code-*` commands):

```bash
git clone https://github.com/johnatorres226/clean-code-skill
# then point your plugin config at the cloned directory
```

**As a bare skill** — copy `skills/clean-code/` into your skills directory, or install the
packaged `clean-code.skill` file from the releases.

## What's in it

```
skills/clean-code/
├── SKILL.md              always loaded (~3,300 tokens) — triage protocol + core procedures
├── references/           10 language-agnostic files, ~22,000 tokens, loaded on demand
└── .skill-audit.json     declared exceptions to the audit defaults, each with a justification

tools/
├── skill_audit.py        context-budget and structural audit
├── skill_eval.py         does the skill actually change the generated code?
└── evals/                fixed eval cases + lint.py, the heuristic scorer
```

## Design: progressive disclosure, enforced

The failure mode for a large skill is loading all of it every time. This one is built in three
tiers and the boundaries are checked mechanically.

| Tier | Cost | When |
|---|---|---|
| Frontmatter | ~110 tokens | always in context |
| `SKILL.md` | ~3,600 tokens | when the skill triggers |
| References | ~37,000 tokens | only what the task needs |
| Scripts & assets | 0 | executed or copied, never read into context |

`SKILL.md` opens with a four-step triage protocol: run a script before reading anything, load one
reference by default (more when the task genuinely spans areas), and **never read the smell
catalog whole** — it is a lookup table with an index and grep-by-ID access, so a targeted lookup
costs ~60 tokens instead of 5,145.

Measured per-task cost:

| Task | Loaded | vs. everything |
|---|---|---|
| Name a variable | 3,636 | 40,814 |
| Write a Python function | 9,862 | 40,814 |
| Refactor legacy C, get it under test | 11,587 | 40,814 |

Two design decisions worth calling out because they cut against the obvious move:

- **The naming, TDD, and refactoring summaries in `SKILL.md` were kept, not stubbed.** Stubbing
  them would have saved ~630 tokens but forced every small question either into a 2,000-token
  reference load or into an answer with no guidance at all. Each summary instead ends with an
  **"Open the reference when:"** line naming exactly what it does not cover. The defect was never
  the duplication — it was the absent handoff signal.
- **References are language-agnostic.** Examples are neutral pseudocode, one per rule. Language
  idioms are enforced by each repo's linter and formatter config rather than described in prose,
  which removed four per-language references (~10k tokens).

## Curating the skill

```bash
python3 tools/skill_audit.py skills/clean-code
```

Reports the context budget per tier, the largest references, and structural problems: broken
links, orphaned reference files, files missing from the routing table, budget violations, and
`SKILL.md` sections that shadow a reference without an escalation trigger.

Deliberate exceptions go in `skills/clean-code/.skill-audit.json` **with a written justification**
rather than by loosening a threshold. A clean audit means "no undeclared problems", not "no
tradeoffs" — and the justifications are reviewable in the diff.

```bash
python3 tools/skill_audit.py skills/clean-code --fail-on-violation   # CI gate
```

## Evaluating the skill

Prose quality is not evidence. Because `tools/evals/lint.py` scores smells by catalog ID, generated code can be scored
objectively against the skill's own standard:

```bash
python3 tools/skill_eval.py run   --out results/baseline --no-skill
python3 tools/skill_eval.py run   --skill skills/clean-code --out results/with-skill
python3 tools/skill_eval.py score results/baseline
python3 tools/skill_eval.py score results/with-skill
python3 tools/skill_eval.py compare results/baseline results/with-skill
```

The six eval prompts deliberately never say "write clean code" — a skill that only works when
asked is not working. Each targets specific catalog IDs (flag arguments, magic numbers, raw
`new`/`delete`, unbounded string functions, mutable defaults).

Three measurement guarantees, because each of these would otherwise produce a flattering lie:

- A case that generated **no output** is marked `MISSING` and excluded from all aggregates —
  never scored as clean.
- **Only cases present in both runs** are compared.
- **Per-case regressions** are reported separately and set exit code 1, since an aggregate
  improvement can hide a case that got worse.

## Honest limitations

- **The eval linter's C-family parser is regex-and-brace based.** Heavily templated C++ or unusual
  macro layouts can be missed. Python analysis uses the `ast` module and is exact.
- **Token counts are estimates** (words × 4/3). Directionally reliable, not exact.
- **The eval measures lint-cleanliness, not correctness or design quality.** Code can lint clean
  and still be badly designed. It catches regressions on the mechanical dimension; it does not
  replace reading the output.
- **`skill_audit.py`'s duplication check compares exact paragraphs**, so it will not catch
  reworded near-duplicates.
- **No baseline eval has been run yet** — the harness is verified against known-dirty and
  known-clean fixtures, but the with-skill-versus-without comparison has not been executed.

## Bibliography

Follows the tradition of Robert C. Martin's *Clean Code* (2008) — the source of the catalog's
ID scheme — along with Fowler's *Refactoring* (2018), Beck's *Test-Driven Development* (2002),
Feathers' *Working Effectively with Legacy Code* (2004), Hunt & Thomas' *The Pragmatic
Programmer* (1999), Meyers' *Effective Modern C++* (2014), Bloch's *Effective Java* (2018),
PEP 8/20, and the ISO C++ Core Guidelines. All prose is original to this skill.

## License

MIT — see [LICENSE](LICENSE).
