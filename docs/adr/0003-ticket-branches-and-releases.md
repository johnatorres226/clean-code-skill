# 3. Ticket branches, inactive specs, and releases as promotions

Date: 2026-11-21. Status: accepted.

## Context

ADR 0002 decides how a change is reviewed. This ADR decides how reviewed changes travel from a
ticket to the release branch.

We keep an integration branch (`dev`) between ticket branches and the release branch (`main`).
DORA links better delivery to few, short-lived branches and does not endorse a long-lived
integration branch (`docs/research/process-control.md` §C). We keep it anyway, for one reason: a
release gets a second, heavier validation before `main`. That only pays off if the known costs of
an integration branch are designed out: big unreviewable release PRs, drift between `dev` and
`main`, and specs that reach `main` half-built.

A release PR contains every ticket since the last release, so it is almost always over the PR size
limit. The current `standards` check applies the ticket-PR rules (size, ticket link, holdout) to
release PRs too, so every real release fails CI.

## Decision

### 1. One branch per ticket

Each ticket gets one branch, `<type>/<ticket#>-<slug>`, created when work starts and deleted on
merge. It merges into `dev` by its tier (ADR 0002) with a rebase, which keeps its atomic commits. A
ticket that needs another ticket's unmerged code stacks on that branch and retargets to `dev` when
it merges; otherwise dependencies are blocking links between tickets.

### 2. A spec stays inactive until its enabling ticket

A spec's tickets merge into `dev` one at a time, each small and reviewed. Their code is merged
but inactive: behind a flag, not wired to an entry point, or not listed in the plugin. The spec's
last ticket, the enabling ticket, turns it on. A spec never reaches `main` half-on.

A spec branch, where a spec's tickets collect before reaching `dev`, is allowed only when partial
work cannot stay inactive (for example a migration sequence), and the spec says why. It is rebased
onto `dev` at least daily, and its final PR is reviewed for how the pieces fit together.

### 3. A release is a promotion, not a review

A `dev` → `main` PR is exempt from the ticket-PR rules (size, ticket link, holdout); per-commit
rules still apply. Instead it must show:

- **Proof of review.** Every commit belongs to a merged ticket PR with a passing `verdict`, plus a
  human approval where its tier required one (GitHub `commits/{sha}/pulls`; GitLab
  `commits/:sha/merge_requests`). An unreviewed commit blocks the release.
- **Whole specs.** Every spec in the release is enabled or still inactive.
- **Release checks.** A second check list, run only on release PRs, for checks that are slow,
  cost money or need special hardware. Ticket PRs run the cheap list. Each project fills in its
  own release list or leaves it empty.

The reviewer agent writes the release notes and reviews only where tickets interact (shared files,
shared config, specs being enabled). Re-reading the whole diff is not required: every line was
reviewed in its ticket, and review quality falls sharply on large diffs.

### 4. When to release

- A spec releases when its enabling ticket merges, all at once.
- A standalone ticket releases right after it merges. Before opening the release, the tracker
  lists other standalone tickets that are merged or close, so they can be bundled.
- An urgent fix releases `dev` early. A hotfix branch from `main` is only for when `dev` itself
  cannot be released; it is merged back into `dev` the same day.

### 5. Release approval is a project setting

| Setting | A human approves | Fits |
|---|---|---|
| `human` (default) | every release | products external users depend on |
| `tiered` | releases that enable a spec or contain a Human-review ticket | team tools |
| `auto` | none; release checks only | local and personal tools |

Setup proposes a value by asking who is affected if a release goes wrong. Human-review tickets were
already approved by a human at merge, so even `auto` never lets one reach `main` unjudged. This
repo uses `tiered`.

## Consequences

- `standards.py` must recognise a release PR (source branch protected) and swap the ticket-PR rules
  for the release rules above. Until then, release PRs fail CI.
- Unverified: GitHub is believed to associate rebase-merged commits with their PR. The proof-of-review
  check confirms that first; if it is wrong, the check is redesigned before the release rules ship.
- `dev` stays within about one ticket of `main`, because releases follow merges.
- With `human` approval and one-ticket releases, a human approves every fix that reaches `main`.
  Projects loosen this explicitly, through a Human-review change to `standards.toml`.
- Hotfixes become rare, so the second path to `main` is seldom exercised; the same-day merge back
  into `dev` is its main risk.
