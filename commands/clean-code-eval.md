---
description: Evaluate whether the skill actually improves generated code, scored by the skill's own linter.
argument-hint: "[baseline-dir] [comparison-dir]"
---

Evaluate the clean-code skill by generating code with and without it and scoring both
with `clean_code_lint.py`. Grading the output rather than the prose is the point: if
code written with the skill does not lint cleaner than code written without it, the
skill is not working no matter how well it reads.

```bash
# 1. Baseline — no skill in context
python3 tools/skill_eval.py run --out results/baseline --no-skill

# 2. With the skill
python3 tools/skill_eval.py run --skill skills/clean-code --out results/with-skill

# 3. Score each, then compare
python3 tools/skill_eval.py score results/baseline
python3 tools/skill_eval.py score results/with-skill
python3 tools/skill_eval.py compare results/baseline results/with-skill
```

Read the results carefully:

- **Cases marked MISSING produced no output** and are excluded from every aggregate. A
  failed generation must never read as a perfect score.
- **Only cases present in both runs are compared.** Aggregates over different case sets
  would flatter whichever run produced fewer files.
- **Per-case regressions are reported separately** and set exit code 1. An aggregate
  improvement can hide a case that got worse — read that section before concluding the
  change was good.

Without the `claude` CLI on PATH, `run` writes a manual runbook of prompts instead;
paste the generated code into the output directory and `score` still works.
