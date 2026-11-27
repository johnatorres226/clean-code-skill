# Roadmap

Where this plugin is going and in what order. Live status (what is open, blocked or done) lives on
the tracker, in the map (#15); this file changes only when the direction does. Decisions go in
`docs/adr/`, terms in `GLOSSARY.md`.

## Destination

A **harness-agnostic environment contract** for agentic development. Any agent, in any harness,
works under the same non-negotiables through one loop:

```
understand → plan → build atomically → verify → review (tiered) → merge → release → retro
   user        user          L0              L0          L1            L1       L1      user
```

`user`: the skills the user already has (`grill-with-docs`, `to-spec`, `to-tickets`, `retro`).

It does not compete with orchestration or review frameworks. It defines what acceptable work is
and leaves the other steps to the skills the user already has. Understanding is the spec and
ticket the user agreed to; the verdict grades the PR against that ticket.

## Layers, in build order

| # | Layer | What it gives the agent |
|---|---|---|
| L0 | Environment contract | `standards.toml`, hooks, CI `standards` check, `clean-code`, `verify`, `ship` |
| L3 | Tracker | An agent that keeps the tracker in order, so the orchestrator spends no context on it |
| L1 | Review, merge and release | Consequence tiers (ADR 0002), the reviewer agent and `verdict` rubric, release rules (ADR 0003) |
| L6 | Multi-harness | Packages for Claude Code, Codex, Gemini CLI and OpenCode; tracker adapters for GitLab and local Markdown |

The tracker came first because every later layer creates tickets.

**Cut (2026-11-26): L2 intake, L4 mode, L5 retro.** Each would load another skill into every
session for work that the agreed ticket, the reviewer or the user's own skills (`grill-with-docs`,
`to-spec`, `retro`) already do. New behavior goes into an existing role (tracker, reviewer) before
it becomes a skill.

## L3: tracker

- Does mechanics only: creates a ticket from a brief, sets labels and state, links parents and
  blockers, finds the next unblocked ticket, and keeps the map's index of decisions current.
- Never comments (comments belong to the implementer or reviewer working the ticket). Cleans up:
  deletes branches whose PR merged and closes released tickets (GitHub closes a ticket only when
  its PR reaches the default branch, and ticket PRs merge into `dev`); idle work is flagged, not
  touched.
- Follows the platform adapter doc (`docs/agents/issue-tracker.md`), never `gh` from memory.
- Runs on the cheapest model and returns at most three lines.
- The map holds one entry per layer. Tickets are created only for the layer being worked, a few at
  a time.

Agents sign every comment with their role in brackets on the first line (`[implementer]`,
`[reviewer]`); an untagged comment is a human's.

## L1: review, merge and release

Grounded in `docs/research/code-review.md`, ADR 0002 and ADR 0003.

- Reviewer agent, modeled on Cursor's Thermos plugin (MIT, credited): three hunting passes in
  fresh contexts (correctness and security, maintainability, comments), then a synthesis.
- `verdict` skill: seven checks (intent, consequence, correctness, security, tests,
  maintainability, docs), each `pass | concern | fail` with evidence, and one machine-readable
  verdict line. Runs its own hunt, or verifies other reviewers' findings one by one.
- `standards.py tier`: the floor the reviewer may only raise; `[review]` names the human triggers.
- Release rules: proof that every commit came through a checked ticket PR, the release-only check
  list, and the release approval setting.
- Validation (`tools/review_eval.py`, 18 synthetic cases) gates on one-way-door recall, clean PRs
  blocked and adversarial escapes. Sonnet is the production reviewer: it matches Opus on every
  metric at 73% of the cost. Haiku passes with no margin on clean PRs blocked, and on a real PR it
  lowered the tier floor. Reverts per tier need real PR history.

## Frameworks we compose with

| Framework | What we use | How |
|---|---|---|
| Thermos (cursor/plugins) | Review depth rules and the multi-pass structure | Copy and adapt, with credit |
| pstack (cursor/plugins) | Orchestration, `interrogate`, adversarial review | Run alongside |
| mattpocock/skills | `grill-with-docs`, `to-spec`, `to-tickets`, `wayfinder`, `triage`, `retro`, `codebase-design`, `improve-codebase-architecture` | Detect and hand off |

Most of Pocock's engineering skills can be started only by the user (`disable-model-invocation`);
the agent names the one to type.

## Parked

- A/A replicate of the v2.1 evaluation and multi-file tasks: waiting for a machine with more
  memory.
