## Standards

Rules: `standards.toml`. Hooks enforce them — fix failures, never bypass (`--no-verify`).
- Branch from `dev` as `<type>/<slug>`; never commit or push to `main`/`dev`.
- One concern per commit, Conventional Commit subject, within the size limits.
- Done = `python .githooks/standards.py check` green + evidence. Skill: `verify`.
- Writing or reviewing code: skill `clean-code`. Committing: skill `ship`.
- Code: one job per function (≤ 20 lines, ≤ 3 params, no boolean-flag params, nesting ≤ 2),
  named constants instead of magic numbers, comments only for *why*, docstrings on public APIs. Full procedure: skill `clean-code`.
