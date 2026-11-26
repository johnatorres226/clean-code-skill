## Standards

Rules: `standards.toml`. Hooks enforce them — fix failures, never bypass (`--no-verify`).
- Branch from `dev` in one step: `git switch -c <type>/<slug>`; never commit or push to `main`/`dev`.
- One concern per commit, Conventional Commit subject, within the size limits.
- Done = one `python .githooks/standards.py check` run, green, right before you commit. Skill: `verify`.
- Writing or reviewing code: skill `clean-code`. Committing: skill `ship`.
- Code: one job per function (≤ 20 lines, ≤ 3 params, no boolean-flag params, nesting ≤ 2),
  named constants instead of magic numbers, comments only for *why*. Full procedure: skill `clean-code`.
