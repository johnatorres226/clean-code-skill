## Agent skills

### Issue tracker

Issues live in GitHub Issues for johnatorres226/clean-code-skill (via `gh`). See `docs/agents/issue-tracker.md`.

### Triage labels

Default five labels: needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one root `GLOSSARY.md` + `docs/adr/`, created lazily. See `docs/agents/domain.md`.

## Standards

This repo adopts its own plugin. Rules: `standards.toml`; hooks live in
`skills/setup-standards/templates/.githooks` (`git config core.hooksPath` points there).
- Branch from `dev` as `<type>/<slug>`; never commit or push to `main`/`dev`.
- One concern per commit, Conventional Commit subject, within the size limits.
- Done = `python skills/setup-standards/templates/.githooks/standards.py check` green.
- Maintainer tools: `tools/skill_audit.py`, `tools/skill_eval.py`, `tests/test_standards.py`.
