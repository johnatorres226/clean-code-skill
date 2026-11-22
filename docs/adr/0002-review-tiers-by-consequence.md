# 2. Review tiers decided by consequence

Date: 2026-11-20. Status: accepted. Supersedes 0001.

## Context

ADR 0001 tiered merge authority **by path**: humans approve everything except paths a
`standards.toml` change has declared verifiable. That default makes humans review routine changes,
and a path list cannot see what a change does: a one-line `DROP COLUMN` in an unguarded file
passes as easily as a typo fix.

The research (`docs/research/code-review.md`) points the other way. What makes a change dangerous
is its consequence: data loss, critical infrastructure, or no way back (AWS rollback safety,
GitLab database review, one-way doors). It also shows that reading a diff is a poor way to find
security defects, whoever reads it. Review missed 81.1% of leaked credentials in agent PRs, and an
author agent can revise until an agent reviewer approves vulnerable code (AFCRA).

## Decision

### 1. Three tiers, named by consequence

| Tier | When | What happens |
|---|---|---|
| **Auto-merge** | Docs, comments, or config with no runtime effect, on an allow-list of paths, under a size cap | The reviewer agent passes it with no findings and it merges. Any finding moves it to agent merge. |
| **Agent merge** | The default: a normal, reversible change | The reviewer agent posts its review. It merges when every blocking finding is fixed, every thread is resolved and all checks are green. |
| **Human review** | Critical infrastructure, possible data loss, or no way back | A senior approves. The review names the trigger, e.g. `human-review: db/migrate/0042.sql — DROP COLUMN (irreversible)`. |

### 2. A script sets the floor; the reviewer can only raise it

`standards.py tier` reads the diff and assigns the lowest tier the change may take. The reviewer
agent may raise the tier, never lower it. Triggers for **human review** (first match wins):

- **Paths:** migrations and schema, auth and crypto, payments, infrastructure-as-code and deploy
  config, public API specs, and everything 0001 guarded (rules, CI, hooks, agent settings, holdout
  acceptance tests, `REVIEW.md`).
- **Content:** destructive SQL (`DROP`, `TRUNCATE`, `DELETE` without `WHERE`), bulk deletes,
  removed fields, changed wire or storage formats, new dependencies, permission changes.
- **Reviewer findings:** a security or data-loss finding, or "could not verify" (no test reaches
  the changed code).

The lists live in `standards.toml` `[review]`, which is itself a human-review path.

### 3. Tools detect; humans judge

Secret scanning with push protection, dependency review and SAST are **required checks** that block
on their own. The agent reviewer is a second net: its findings escalate, but a clean agent review is
not evidence of safety. On human-tier changes the senior does not hunt for defects. They judge
consequence: is the design right, what breaks if it is wrong, can it be backed out, do we accept
the risk. They also sit outside the author agent's revise-and-resubmit loop, so the author cannot
optimize against them.

### 4. The likelihood score is advisory

A risk score from size, files, directories, churn and change type deepens the review but never
changes the tier. It is logged per PR. Once revert data exists, a separate ADR may let it escalate.

### 5. Enforcement on GitHub and GitLab

| Need | GitHub | GitLab |
|---|---|---|
| Human gate | `tier` check passes only after a senior approves the head commit; CODEOWNERS on human paths as a second lock | Same `tier` job reading MR approvals; code-owner approval rules on Premium+ |
| Reviewer verdict | Required `verdict` check from the reviewer's own App, never an approval | Required pipeline job; external status check on Ultimate |
| Comments | Pull request review API | Draft notes, published in bulk |
| Merge | Auto-merge after checks | Auto-merge after pipeline and resolved threads |

The reviewer can instead write its review to a Markdown file with the same sections and verdict
line, for repos that do not want it posting.

## Consequences

- Agents merge routine work without waiting for a human. Humans see fewer PRs, and each one says
  why it needs them.
- CODEOWNERS shrinks from "seniors own everything" to the human-review paths. `[roles].auto_merge`
  becomes the auto-merge allow-list. `[roles.areas]` names who reviews an area when it escalates,
  and no longer gates by itself.
- Content triggers cannot be expressed in CODEOWNERS, so the `tier` check carries them. On GitLab
  an approval does not start a pipeline, so the `tier` job must be re-run after approval.
- On GitLab Free, approvals are optional, but the `tier` job can still read them and block.
  Required approval rules need Premium.
- Favor over-escalating: a missed escalation lets an irreversible change through unjudged. But
  escalations are not free; too many train seniors to rubber-stamp. Track the escalation rate and
  the share of escalated PRs approved with no change; a high share means a trigger is too broad.
- The reviewer is measured on
  seeded defects, false findings on clean PRs, recall on one-way-door PRs (target 100%), an
  adversarial run, and reverts per tier (`docs/research/code-review.md`, synthesis d). If
  human-tier recall drops, the trigger lists widen before anything else changes.
- An agent reviewer is still not SLSA's "two trusted persons". Regulated code stays human-only.
