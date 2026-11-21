# Roadmap

Where this plugin is going, where it is now, and what comes next. Update the status column when a
layer moves; record decisions in `docs/adr/`, not here.

## Destination

A **harness-agnostic environment contract** for agentic development. Any agent, in any harness,
works under the same non-negotiables through one loop:

```
understand → plan → build atomically → verify → review (tiered) → merge → retro
   L2          L2         L0              L0          L1            L1      L5
```

It does not compete with orchestration or review frameworks. It defines what acceptable work is,
detects what the user already has installed, and hands each step to the best skill available,
falling back to its own.

## Layers

| # | Layer | What it gives the agent | Status |
|---|---|---|---|
| L0 | Environment contract | `standards.toml`, hooks, CI `standards` check, `clean-code`, `verify`, `ship` | Shipped (v2.1) |
| L1 | Code review | Consequence tiers (ADR 0002), a reviewer agent with two parallel passes, a `verdict` rubric | **In progress** |
| L2 | Intake | A rubric the agent uses to confirm it understands the request before building, sized from a 3-line fix to a multi-session feature | Planned |
| L3 | Tracker agent | A subagent that does issue and PR mechanics (labels, templates, state, checks) and returns two or three sentences, saving the orchestrator's context | Planned |
| L4 | Mode | One entry point that injects the non-negotiables, lists the skills and agents available, and checks the user's existing setup before changing it | Planned |
| L5 | Retro | After each iteration, improve the environment: a check first, a standard second, steering text last | Planned |
| L6 | Multi-harness | Packages for Claude Code, Codex, Gemini CLI and OpenCode (primary-agent support); drop-in files for any other harness | Planned |

Order: L1 → L2 → L3 → L4 → L5 → L6. L1 comes first because the verdict defines "done". Its
first check (does the PR do what the ticket asked) needs a ticket, which L2 provides; until then
a missing ticket is a `concern`.

## L1: code review (current)

Done: research (`docs/research/code-review.md`), ADR 0002 (proposed).

Next:
1. Reviewer agent, modeled on Cursor's Thermos plugin (MIT, credited): an orchestrator runs a
   correctness-and-security pass and a quality pass in parallel, then synthesizes.
2. `verdict` skill: seven checks (intent, consequence, correctness, security, tests,
   maintainability, docs), each `pass | concern | fail` with evidence, and one machine-readable
   verdict line. Runs its own full hunt, or synthesizes other reviewers' findings (Thermos,
   `code-review`, BugBot) by verifying each one, not by counting votes.
3. `standards.py tier` and the `[review]` config, test-first.
4. Validation: seeded defects, false findings on clean PRs, one-way-door recall, an adversarial
   run, reverts per tier.

Done when: the agent runs in at least two harnesses, and the evaluation in
`docs/research/code-review.md` (synthesis d) has a first baseline.

## L2: intake (sketch)

Before building, the agent checks its understanding against a rubric and the user confirms it.
Each item is `pass | concern | fail`, like the verdict:

- **Problem:** whose problem, in their words.
- **Outcome:** how we will know it is done (acceptance criteria).
- **Scope:** what is in and what is explicitly out.
- **Size:** fix, feature, or multi-session effort. This picks the artifact: a ticket, a spec plus
  tickets, or a map of decision tickets.
- **Consequence:** a tier preview. Does this touch anything human-tier?
- **Unknowns:** assumptions said out loud.

Where present, it hands off to Pocock's skills instead of reimplementing them: `grilling` or
`grill-with-docs` to build shared understanding, `to-spec` and `to-tickets` to write the
artifacts, `wayfinder` for multi-session work, `triage` for incoming issues.

## Frameworks we compose with

| Framework | What we use | How |
|---|---|---|
| Thermos (cursor/plugins) | Review depth rules and the two-pass structure | Copy and adapt, with credit |
| pstack (cursor/plugins) | Orchestration, `interrogate`, adversarial review | Run alongside |
| mattpocock/skills | `grill-with-docs`, `to-spec`, `to-tickets`, `wayfinder`, `triage`, `retro`, `codebase-design`, `improve-codebase-architecture` | Detect and hand off |

Most of Pocock's engineering skills can only be started by the user (`disable-model-invocation`).
The mode (L4) has to tell the user when to type them, or ship its own fallback.

## Parked

- A/A replicate of the v2.1 evaluation and multi-file tasks: waiting for a machine with more
  memory.
- Pushing to `dev`: waiting for `gh auth refresh -h github.com -s workflow`.
