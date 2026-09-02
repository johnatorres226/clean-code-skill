---
description: Review code against clean-code standards — runs the linter, then reads for the judgment calls a tool cannot catch.
argument-hint: "[path to file or directory]"
---

Review the code at `$1` against the clean-code standards.

Follow this order — it is designed so mechanical findings cost nothing and human
attention goes where a tool cannot reach:

1. **Run the linter first.** Never spend reading effort on what a script can find:
   ```bash
   python3 skills/clean-code/scripts/clean_code_lint.py $1
   ```

2. **Look up only the IDs it reported.** Do not load the whole catalog:
   ```bash
   grep -A4 -E '^\*\*(G25|F3)' skills/clean-code/references/smells-catalog.md
   ```

3. **Read `skills/clean-code/references/review-rubric.md`** for the output format and
   severity levels.

4. **Read for what the linter cannot see:** does each name match the actual behavior,
   is the abstraction level consistent within each function, do the tests pin the real
   contract, would a newcomer be misled?

5. **Report** using the rubric's structure — Summary, Blocking, Should fix, Consider,
   Tests, Praise. Label every finding with a severity and cite the catalog ID. Include
   praise where it is earned; it tells the author which instincts to repeat.

Keep the depth proportional to the diff. A ten-line change gets a paragraph, not the
full template.
