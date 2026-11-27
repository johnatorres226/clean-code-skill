# 4. One contract, native files per harness

Date: 2026-11-27. Status: proposed. Each decision below is a recommendation awaiting the owner's
yes; research and its open claims are in `docs/research/multi-harness.md`.

## Context

L6 makes the contract work in Codex CLI, Gemini CLI and OpenCode, and on GitLab. Two rules from
earlier layers bound the design:

- **No new systems.** The plugin uses git, what the platform and each harness provide out of the
  box, and the project's own language tooling. No npm package, no generator service.
- **No new skills.** Skills cost context in every session; new behavior goes into an existing role.

The research found that most of the contract already ports: git hooks, CI and server-side rules are
harness-agnostic, and all three harnesses read `AGENTS.md` and `.agents/skills/`. What differs is
agents (four formats), the pre-tool guard (three protocols) and packaging (no harness can install
everything in one step).

## Decision

### 1. `AGENTS.md` is the always-on block

`setup-standards` writes the contract block to `AGENTS.md`, which Codex and OpenCode read by
default. `CLAUDE.md` imports it with one `@AGENTS.md` line, and so does `GEMINI.md`, so there is
one copy of the text.

### 2. Skills stay where they are; projects get `.agents/skills/`

The plugin's `skills/` is the only source. Claude Code reads it as a plugin; Codex installs it from
the repo's plugin manifest; Gemini from an extension manifest. For OpenCode, which cannot carry
skills in a plugin, `setup-standards` copies the skills into the project's `.agents/skills/`, and
`standards.py check` fails if that copy drifts from the installed plugin.

### 3. Agents run inline outside Claude Code

The reviewer and tracker stay as `agents/*.md`. In a harness without a matching agent format, the
orchestrator reads the file and follows it in its own session, as `agents/tracker.md` already
allows. No per-harness agent files are generated until inline runs prove too costly in context.

### 4. One guard, three adapters, native config only

`standards.py guard` accepts the Claude, Codex (`PreToolUse`) and Gemini (`BeforeTool`) stdin
shapes and exits 2 to block. `setup-standards` writes `.codex/hooks.json` and the hook stanza in
`.gemini/settings.json`. OpenCode gets declarative `permissions` deny rules (push to protected
branches, `--no-verify`, `core.hooksPath`), not a TypeScript plugin. The guard stays a guardrail:
git hooks, CI and branch rules remain the enforcement.

### 5. Per-harness manifests at the repo root

`.claude-plugin/` (exists), a Codex `plugin.json` with `.agents/plugins/marketplace.json`, and a
`gemini-extension.json`. Each points at the same `skills/` and the same `AGENTS.md` text.

### 6. Order: Codex and OpenCode first; Gemini and GitLab wait

Gemini CLI was replaced by Antigravity CLI for unpaid and Google One users in June 2026, so it
waits until Antigravity's surface is checked. The GitLab adapter (tracker doc, MR-based proof of
review, protected-branch rules) waits until there is a GitLab project to test against: its key
behaviors (Free-tier `blocks` links, MR lookup for rebased commits) are unverified. A local
Markdown tracker adapter is dropped until someone needs it.

### 7. Verify before building

Each harness step starts by installing that CLI on a test project and confirming the unverified
claims it depends on (hook input field names, skill discovery, `@AGENTS.md` imports). A claim that
fails reopens the matching decision here.

## Consequences

- Installing a CLI to test against is a maintainer step, not something projects need.
- `setup-standards` writes more files per project (`AGENTS.md`, `.codex/hooks.json`, OpenCode
  rules), and `standards.py` gains input adapters and a drift check, all covered by its tests.
- Inline agents spend the orchestrator's context in Codex and OpenCode; that is the price of not
  maintaining four agent formats.
- OpenCode's guard is glob rules, so it is weaker than the hook: a command that hides a push inside
  a script is caught only by the pre-push hook and branch rules.
- Gemini users and GitLab projects get only the harness-agnostic part (git hooks, CI) until their
  steps ship.
