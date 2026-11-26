# 1. Tiered merge authority for agent pull requests

Date: 2026-11-17. Status: superseded by 0002.

## Context

Agents build most changes here, so who may merge decides how far we trust them. Research
(`docs/research/software-factories.md`, `pstack-orchestration.md`) found three models:

- **Human gate.** Copilot, GitHub Agentic Workflows, Stripe, Anthropic and Codex require a human
  approval on every PR.
- **Sampling.** poteto lets agents merge their own verified PRs and audits merged history afterward.
- **Dark factory.** StrongDM uses no human review.

Independent studies report lasting complexity growth in agent-written code (He et al., MSR 2026),
instability (DORA 2025) and gamed agent-written tests (StrongDM, Anthropic). Sampling only works
where the environment can verify the change.

## Decision

Merge authority is **tiered by path**, and the server enforces it (CODEOWNERS plus rulesets):

1. **Default: human.** Every path is owned by `[roles].senior`, so the ruleset's code-owner
   review requires a human approval.
2. **Verifiable paths: agent.** Paths in `[roles].auto_merge` have no code owner. A PR touching
   only those paths merges once the `standards` check and the reviewer agent's `verdict` check
   pass. The verdict comes from a separate GitHub App bound to the head commit. It is a status
   check and never an approval.
3. **Guarded paths: always human.** These are rules, CI, hooks, agent settings, holdout
   acceptance tests, and whatever else `[roles].guarded` lists. They are matched last, so they
   win over `auto_merge`.

## Consequences

- Agents keep throughput on well-tested code, and the cases where trust fails stay human.
- A path earns `auto_merge` only through a `standards.toml` change, which itself needs owner
  review.
- The reviewer agent's quality must be measured (seeded defects, addressed-comment rate,
  post-merge reverts). If it drops, auto-merge paths go back to human review.
- An agent reviewer is not SLSA's "two trusted persons". Regulated code stays human-only.
