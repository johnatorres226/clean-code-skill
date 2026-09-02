---
description: Audit the clean-code skill's own context budget and structural integrity.
argument-hint: "[skill directory, defaults to skills/clean-code]"
---

Audit the skill at `${1:-skills/clean-code}`.

```bash
python3 tools/skill_audit.py ${1:-skills/clean-code} \
  --task "write a python function" \
  --task "refactor legacy c" \
  --task "review a java pr"
```

Report:

- **Context budget** — what loads always, what loads on demand, and the realistic
  per-task cost versus loading everything.
- **Issues** — broken links, orphaned references, unrouted files, budget violations,
  and sections in SKILL.md that shadow a reference without an escalation trigger.

Anything the skill deliberately accepts is declared in
`${1:-skills/clean-code}/.skill-audit.json` with a written justification, so a clean
run means "no undeclared problems", not "no tradeoffs". If a check fires on something
that is actually a considered decision, add it there **with the reasoning** rather than
loosening a threshold — the justification is the artifact worth keeping.
