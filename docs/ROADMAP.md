# Roadmap

Where this plugin is going and in what order. Live status (what is open, blocked or done) lives on
the tracker, in the map; this file changes only when the direction does. Decisions go in
`docs/adr/`, terms in `GLOSSARY.md`.

## Destination

A **harness-agnostic environment contract** for agentic development. Any agent, in any harness,
works under the same non-negotiables through one loop:

```
understand → plan → build atomically → verify → review (tiered) → merge → release → retro
   L2          L2         L0              L0          L1            L1       L1       L5
```

It does not compete with orchestration or review frameworks. It defines what acceptable work is,
detects what the user already has installed, and hands each step to the best skill available,
falling back to its own.

## Layers, in build order

| # | Layer | What it gives the agent |
|---|---|---|
| L0 | Environment contract | `standards.toml`, hooks, CI `standards` check, `clean-code`, `verify`, `ship`. Shipped in v2.1. |
| L3 | Tracker | An agent that keeps the tracker in order, so the orchestrator spends no context on it |
| L1 | Review, merge and release | Consequence tiers (ADR 0002), the reviewer agent and `verdict` rubric, release rules (ADR 0003) |
| L2 | Intake | A rubric the agent uses to confirm it understands the request before building |
| L4 | Mode | One entry point that injects the non-negotiables, lists available skills and agents, and checks the user's setup before changing it |
| L5 | Retro | After each iteration, improve the environment: a check first, a standard second, steering text last |
| L6 | Multi-harness | Packages for Claude Code, Codex, Gemini CLI and OpenCode; tracker adapters for GitLab and local Markdown |

The tracker comes first because every later layer creates tickets. Review comes before intake
because the verdict defines "done"; until intake exists, a PR with no ticket fails the CI link
check.

## L3: tracker

- Does mechanics only: creates a ticket from a brief, sets labels and state, links parents and
  blockers, finds the next unblocked ticket, and keeps the map's index of decisions current.
- Never comments (comments belong to the implementer or reviewer working the ticket) and never
  closes a ticket (merged PRs close their own tickets; a stale ticket is flagged, not closed).
- Follows the platform adapter doc (`docs/agents/issue-tracker.md`), never `gh` from memory.
- Runs on the cheapest model and returns at most three lines.
- First job: create the map and one entry per layer. Tickets are created only for the layer being
  worked, a few at a time.

Agents sign every comment with their role in brackets on the first line (`[implementer]`,
`[reviewer]`); an untagged comment is a human's.

## L1: review, merge and release

Done: research (`docs/research/code-review.md`), ADR 0002, ADR 0003.

Next:
1. Reviewer agent, modeled on Cursor's Thermos plugin (MIT, credited): a correctness-and-security
   pass and a quality pass in parallel, then a synthesis.
2. `verdict` skill: seven checks (intent, consequence, correctness, security, tests,
   maintainability, docs), each `pass | concern | fail` with evidence, and one machine-readable
   verdict line. Runs its own full hunt, or verifies other reviewers' findings one by one.
3. `standards.py tier` and the `[review]` config, test-first.
4. Release rules in `standards.py`: recognise release PRs, check proof of review and whole specs,
   run the release-only check list, honour the release approval setting.
5. Validation: seeded defects, false findings on clean PRs, one-way-door recall, an adversarial
   run, reverts per tier. Harness built (`tools/review_eval.py`, 18 synthetic cases); first Opus
   and Haiku runs pending. Reverts per tier need real PR history.

## L2: intake (sketch)

Before building, the agent checks its understanding against a rubric and the user confirms it.
Each item is `pass | concern | fail`:

- **Problem:** whose problem, in their words.
- **Outcome:** how we will know it is done.
- **Scope:** what is in and what is explicitly out.
- **Size:** standalone ticket, spec, or multi-session effort, which picks the artifact.
- **Consequence:** a tier preview.
- **Unknowns:** assumptions said out loud.

Where present, it hands off to Pocock's skills: `grilling` or `grill-with-docs` for shared
understanding, `to-spec` and `to-tickets` for the artifacts, `wayfinder` for multi-session work,
`triage` for incoming tickets.

## Frameworks we compose with

| Framework | What we use | How |
|---|---|---|
| Thermos (cursor/plugins) | Review depth rules and the two-pass structure | Copy and adapt, with credit |
| pstack (cursor/plugins) | Orchestration, `interrogate`, adversarial review | Run alongside |
| mattpocock/skills | `grill-with-docs`, `to-spec`, `to-tickets`, `wayfinder`, `triage`, `retro`, `codebase-design`, `improve-codebase-architecture` | Detect and hand off |

Most of Pocock's engineering skills can be started only by the user (`disable-model-invocation`).
The mode (L4) has to tell the user when to type them, or ship its own fallback.

## Parked

- A/A replicate of the v2.1 evaluation and multi-file tasks: waiting for a machine with more
  memory.
- Pushing to `dev`: waiting for `gh auth refresh -h github.com -s workflow`.
