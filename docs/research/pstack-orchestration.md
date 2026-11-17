# Research: how pstack intends agent orchestration to work

Scope: the end-to-end agent workflow poteto (Lauren Tan) designed into pstack. It covers lifecycle,
roles, review, merge, traceability, and the human line, and what our environment contract has to
supply around it. Ground truth is the installed source,
`~/.claude/marketplaces-src/cursor-plugins/pstack`, pstack 0.15.42 at commit `bf0c7cd`
(2026-11-14). The Claude Code cache copy (`plugins/cache/cursor-plugins/pstack/0.15.42`) differs
only in harness details. The second source is the Matt Pocock livestream with poteto. Its
transcript came from YouTube's own transcript panel, which is auto-generated captions (see §6).
Claims I could not trace to a primary source are marked UNVERIFIED. Paths below are relative to
the pstack root unless stated.

## 1. The intended lifecycle, step by step

pstack has no fixed pipeline. `/poteto-mode` (`skills/poteto-mode/SKILL.md`) matches the task to
one of 23 playbooks. It copies that playbook's steps verbatim into a todo list, and a step it
skips stays on the list with `skip: <reason>`. The README states that there is no planning
stage: "i don't believe in planning. the best spec is code". A plan exists only when the
Multi-phase plan playbook is invoked. For a code change, the stages compose like this:

| # | Stage | Implemented by | What it demands |
|---|---|---|---|
| 0 | Restate intent | `poteto-mode` Non-negotiables | First message restates goal, problem, smallest change. The same goal opens every subagent brief, every PR `## Why`, and every final report. |
| 1 | Understand | `playbooks/investigation.md`, `how`, `why`, `recall` | Read-only. `why` answers "from the record" (commits, PR discussions). |
| 2 | Settle forks empirically | `playbooks/prototype.md` | A question answerable by running something is not the human's to answer. |
| 3 | Design | `architect` → `arena` (multi-model sketch, cross-judge from another vendor); `interrogate` if contested | At least two structurally distinct designs. The human checkpoint is opt-in only (`architect` Phase C). |
| 4 | Throughput checkpoint | `playbooks/feature.md` step 3 | Blocking steps, independent workstreams, shared mutable state, smallest safe decomposition. |
| 5 | Build | `poteto-agent` delegates, `tdd`, principle skills | The parent never writes the code. Delegation is "Mandatory: no skip-with-reason escape" (`feature.md` step 4). |
| 6 | Verify on the real surface | `principle-prove-it-works`, project `verify-<app>` skill (`create-verification-skill`), `control-ui`/`control-cli` (cursor-team-kit) | "Inconclusive or wrong-surface is not a pass." |
| 7 | Clean | `/deslop` (cursor-team-kit), `/no-comments` → `comment-sicko`, `/unslop`, `/technical-writing` | Comments are reviewed by an agent that did not write them. |
| 8 | Commit and open PR | `playbooks/opening-a-pr.md` | Worktree off main. Small ordered commits, each "a future PR". Conventional Commit title. Opened ready, never draft. Stacks are base-branch chains. |
| 9 | Babysit to merge-ready | `playbooks/babysit.md`, `scripts/watch-pr/` | Only on request. Order is conflicts, then threads, then CI. Stops at merge-ready and "never authorizes merging". |
| 10 | Ship | `playbooks/shipping.md` | Independent verdict per PR. Lands only the contiguous verified run, bottom-up. |
| 11 | Learn | `correct`, `reflect`, `bugbot-triage.md` candidates | Repeated mistakes become architecture, types, lint, CI, or tests, with docs last. |

Long or unattended work wraps this sequence. `autonomous-run.md` drives one task to a checkable
predicate under `/loop`. `figure-it-out` designs a bespoke phased run. `autopilot-full.md`
handles a queue of independent PRs taken to merged, and `autopilot-stack.md` handles the same
queue built and verified for a human to land. `orchestrate.md` runs a standing multi-day program.
`multi-phase-plan.md` is the one place a plan is the deliverable. Its template is a checkbox
how-to whose verification rule is "Tests alone are not sufficient verification". It also has a
linter, `scripts/check-plan.mjs`.

**Confidence.** High. This is read directly from the playbooks.

## 2. Roles and handoffs

| Role | Who | Context it gets | May not |
|---|---|---|---|
| Runner | The chat that received `/poteto-mode` | Playbook, todo list, every spawn | Pass a subagent's summary through. "You own every subagent's work. Review the diff". |
| Delegate | `poteto-agent` (`agents/poteto-agent.md`) | Reads `poteto-mode/SKILL.md` in full first. Gets file pointers, not inlined context. | Run the playbook itself |
| Owner (autopilot/orchestrate) | One agent per PR | Full kickoff, with upstream reports pasted in full | Merge on its own verdict. Only the owner pushes, rebases, or retargets its branch. |
| Coordinator | `orchestrate.md` root | Program state in `notes.md` | "You never author or edit code." Never relays messages between agents. |
| Sub-coordinator | Optional | One area's workers | More than three levels. About ten workers in flight. |
| Verifier | Fresh agent, different model family (`orchestrate.md`) | Exact head SHA and a boot recipe | Count as a verifier if it wrote the code |
| Adversaries | `interrogate`, `arena` panels (Fable/Opus/Gemini defaults) | Scope, intent, and a "break this" brief | Keep a finding no run proves |
| Comment reviewer | `comment-sicko` | Diff | Write application code |
| Trail reviewer | `show-me-your-work` cross-model reviewer | Decision TSV and transcript | Be the same model family as the worker |

Handoff rules (`poteto-mode` §Subagents). Each new unit of work goes to a **fresh** subagent with
consolidated scope: the original brief, every later directive, and the prior report and branch.
An agent is resumed only when the work needs state that lives in it, such as a checkout or a
running process. The stated reason: "Interrupt-chained resumes silently drop directives". Each
kickoff names the evidence that proves the work is done, the paths the worker may and may not
write, and the actions it must not take. "If you can't name the evidence, the unit isn't scoped
yet" (`orchestrate.md`). Fan-out starts with one unit carried end to end, "so a flaw in the
kickoff costs one agent instead of fifty". Models are assigned per role through `/setup-pstack`.
In Claude Code the rule is written to `~/.claude/rules/pstack-models.md`
(`docs/harness/claude-code.md`).

## 3. Review and verification

pstack's quality model has three layers.

**Author-side discipline.** There are 24 principle skills, cited by name in replies along with
the decision each changed. Commit and PR text get `/deslop` and `/unslop`. Comments get the
`/no-comments` pass. Bug fixes land the failing repro before the fix in history (`bug-fix.md`
step 5).

**Separation of judge from author.** This appears everywhere. Comments go to Comment Sicko
because "An author defends its comments" (`docs/guide/05-build-and-clean.md`). Shipping counts
"Only a verdict from an agent that did not write the code". `arena` takes its cross-judge from
another vendor. `interrogate` keeps only findings "a run proves". `autopilot-full` swarm-verifies
each PR at the code-ready head. The swarm has a gates lane, live lanes that drive the real
surface, and audit lanes that "distrust the PR body". `multi-phase-plan.md` sets ten live lanes,
one of them a regression lane against trunk, plus a dual-sided perf gate.

**Verdicts are pinned to code.** A verdict covers one head SHA. After a rebase, `git patch-id`
decides whether the verdict survives (`shipping.md` step 3). A new head gets a fresh verifier,
and only new behavior or a large diff gets a full swarm again. "Green CI and an approving bot
review are not verdicts" (`shipping.md` step 1). CI is "an input to a verdict" (`orchestrate.md`).

Review comments are untrusted data. Bugbot and security-review threads are triaged
fix/dismiss/ask per `references/bugbot-triage.md`. Security, auth, billing, data, and migration
findings always go to the human. Noise is dismissed with a posted disproof, and team-useful
dismissal patterns are proposed as rubric entries in their own PR. CI failures are classified
before any retry: one fresh build for flake, and "An identical second failure means it was never
flake" (`babysit.md` step 7).

**Confidence.** High that this is the design. It is untested here whether the verifier swarm
catches what it claims. pstack ships no eval of its own verdict accuracy.

## 4. Merge, CI and automation boundaries

| Action | Automated? | Source |
|---|---|---|
| Reversible work: commits, PRs, team chat, ticket updates, kicking off evals | Yes, "Just do it" | `poteto-mode` §Autonomy |
| Opening PRs (ready, not draft) | Yes | `opening-a-pr.md` |
| Babysitting | Only when asked, and it stops at merge-ready | `babysit.md` steps 1, 9 |
| Merging | Only on an explicit request to merge, land, ship, or "merge when ready", or under an Autopilot-full grant | `babysit.md` step 9, `autopilot-full.md` |
| Arming auto-merge | Only when the verdict covers the current head | `shipping.md` step 4 |
| Loosening a gate (raised budget, allowlist entry) | Needs a verifier's proof plus the root's countersign. "A disabled or soft-failed check always comes out" | `autopilot-full.md` step 6 |
| Forge-enforced approvals | **Never given or bypassed by an agent**. "no countersign covers it" | `autopilot-full.md` step 6 |
| Force-push to shared branches, deploys, data deletion, customer messages | **Always pause** | `poteto-mode` §Autonomy |
| Product or preference calls no experiment can settle | Human | Non-negotiables, `orchestrate.md` |
| Review-gated PRs (changed interactions) | Human reviews screenshots and video before merge | `multi-phase-plan.md` |
| Operator's own queue items, PRs outside the grant | Stop at merge-ready | `autopilot-full.md` step 1 |
| Stop or hold | Zero-writes order to every owner immediately | `autopilot-full.md` step 7 |

Shipping always lands bottom-up, one PR at a time, with `gh pr merge --squash` or `origin pr
merge`. It reads the PR back to confirm, because "a requested auto-merge is not a merge". While
a run lands, nobody touches stack topology. The benny automation (`automations/benny/`) is
stricter still. It opens only draft PRs, and "Never merge or deploy from this workflow".

**Finding.** pstack treats the merge decision as the operator's grant, and treats the forge's
enforced rules as a hard ceiling that agents do not cross. It does not define those rules. The
human line is whatever branch protection says, plus the Always-pause list.

## 5. Traceability: how a change links back to intent

- **Restated goal.** It appears in the first message, every subagent brief, every PR `## Why`,
  and every final report (`poteto-mode` Non-negotiables).
- **PR body as briefing.** `## Why`, `## What changed`, `## Scope`, `## Tradeoffs`,
  `## Blast Radius`, `## Verification`, kept under about 40 lines because "The body becomes the
  squash commit body". Evidence that does not fit goes in linked artifacts (`opening-a-pr.md`).
- **Decision trail.** `show-me-your-work` keeps an append-only TSV
  (`ts, phase, decision, why, evidence, result`), with evidence as a SHA, PR, `file:line`, or
  artifact. It is audited against the transcript and reviewed by another model family. It is
  **local by default** and committed only when "a reviewer needs the trail to trust the result".
- **Verdicts on the PR.** `PASS` / `PASS+NOTES` / `FAIL` is posted per PR at a named SHA.
- **History as the record.** `why` reconstructs rationale from commits and PR threads. Commits
  are ordered "to tell the story". The repro commit lands before the fix.
- **Not present.** pstack has no issue or ticket linkage. No playbook requires `Closes #N` or an
  issue reference in a commit or PR. Intent travels as prose, not as a tracker ID.

## 6. What the interview adds

**Source.** "LIVE: Poteto (creator of pstack) on shipping 1,000's of PR's a month at SpaceX",
Matt Pocock's YouTube channel, streamed 2026-10-02, 65:36,
https://www.youtube.com/watch?v=MN9dGgmLyso. The transcript was **obtained** in full (about 511
segments) from YouTube's transcript panel. It is ASR text, not an edited transcript. "pstack"
is captioned as "PAC" and Grok Bot as "Grockbot"/"graphbot". Timestamps are caption-segment
starts. Quotes have fillers removed and are otherwise verbatim.

- **Verification first, then trust (16:14–18:01).** She calls verification "the single most
  important skill" (16:21). It gives the agent "hands and eyes", and it is what makes a loop a
  loop. Every app at her company has an auto-maintained verification skill (19:09). This is the
  interview counterpart of `create-verification-skill` and `maintain-verification-skill`.
- **Determinism into scripts, judgment to agents (20:51–24:46).** Agents "would basically
  rebuild the world each time" (23:05), so she moved the deterministic parts into a CLI inside
  the skill. This is `principle-build-the-lever`.
- **The environment is the job (26:14).** Her internal framework "Dune" has restrictive lint
  rules and "really only one way to do something" (30:28). Features live in per-feature
  directories found through a registry, a response to "eight god files" of at least 10k lines
  (31:32). Each observed mistake prompts the question of how to turn it into a lint rule
  (31:52). This is `/correct`.
- **Orchestration topology (34:52–45:07).** There is an outer loop (Slack, Linear, X, email via
  Grok Bot routines) and an inner loop (Cursor Projects, a cloud coordinator agent that
  "doesn't do the work itself", 42:55). Per-report agents duplicate work and miss shared root
  causes, so related reports go to one coordinator (44:38). She runs "more than 10 chiefs of
  staff", each on its own area (52:11).
- **Buffer before fixing (47:43–48:54).** A banned-pattern agent appends findings to a document
  instead of fixing them. She reads it every few days to spot classes, because pure execution
  mode can "miss the big picture".
- **Merge and review (39:43, 49:34–54:10).** The unlock was working backwards from "how do I get
  to the point where my agent can merge its own code?" (39:43). Review becomes **sampling**. She
  reads merged PRs and commit history "in the morning" (53:56), then reverts, modifies, or adds
  lint rules. She fixes the environment rather than the single agent. A one-off is fine, and a
  repeated shortcut means changing the kitchen (50:24–50:57). Full autopilot spawns verifier
  agents per PR that "fuzz" the running app. It is "quite token intensive", and ten verifiers
  can be tuned down to one (53:26).
- **Volume is mostly gardening (46:01).** The 2,000–2,500 PRs are "not obviously like 2,500
  features" (she also says "2,000 or however many", 38:47). The count is self-reported.
- **Limits (56:28–59:21).** Asked by Pocock about one-way-door PRs in regulated domains, she says
  it depends on how well the work can be verified. In verifiable domains, one-way doors "become
  two-way doors in a sense", and for hard-to-verify domains she does not "really have the
  answer". Pocock frames the model as "sampling instead of blocking" (55:40). She concedes it is
  "very hard to get to this point" (51:19) and that the human stays "responsible for the final
  outcome" (14:49).
- **Composing with Pocock's skills (1:00:35–1:04:38).** She calls the two libraries
  complementary. Her example pairs his grill-me-with-docs or wayfinder with pstack's execution
  skills (1:01:56). Both recommend mining past transcripts for repeated corrections and turning
  them into skills or lint rules.

**Confidence.** High that she said these things. They are verbatim ASR at the stated
timestamps. Medium on exact wording, because of ASR errors. The interview describes her Cursor
setup (Projects, Grok Bot, Bugbot), parts of which do not exist in Claude Code.

UNVERIFIED: her earlier talk ("how I shipped 2,500 PRs", X post dated 2026-09-21 per
redreamality.com) was not retrieved. sozai.app hosts a "Part 1" transcript of a Lauren Tan talk,
which I saw only through a summarizer, so none of its quotes are used here. A trust-ladder
ranking attributed to her on LinkedIn (code > lint/types/CI > rules/skills/Bugbot > style guide)
is unverified. It matches `correct`'s order, which *is* verified in source.

## 7. Gaps: what pstack leaves to the environment

pstack names these concerns but delegates them to "the forge" or "the repo's checks":

1. **Gate definitions.** pstack says "Run the repo's lint and typecheck" and "Push with hooks
   on", but it ships no gate list. `standards.toml [gates]` + `standards.py check` supplies it.
2. **Merge method and target.** `shipping.md` hard-codes `gh pr merge --squash` and PRs to
   "trunk". Our contract sets `merge = "rebase"` into `dev`, and the ruleset's
   `allowed_merge_methods` will reject a squash. pstack has no knob for this.
3. **Reviewer identity.** A pstack verdict is a PR comment from "an agent that did not write the
   code", enforced only by instructions. The forge cannot tell an author agent from a verifier
   agent when both use one token. "Different model family" cannot be checked from outside.
4. **The human approval line.** pstack defers to forge-enforced approvals but never sets them.
   `reviews_required`, `require_code_owner_review`, `require_last_push_approval`, and
   conversation resolution are what turn "Never give or bypass an approval" into a real stop.
5. **Gate-loosening protection.** The root countersign is advisory. CODEOWNERS on
   `[roles].guarded` plus CI reading the base branch's `standards.toml` make it binding.
6. **Size limits.** pstack says "Prefer five narrow PRs" with no numbers. `[commits]` and `[pr]`
   limits supply them.
7. **Issue linkage.** No tracker ID is required anywhere (§5). Our repo uses GitHub Issues with
   triage labels (`CLAUDE.md`), and Pocock's `code-review` looks for `#123` in commit messages
   to find the spec.
8. **Deploy and release.** "Always pause" for deploys is an instruction. A protected `release`
   environment with prevent-self-review (`process-control.md`) is the control.
9. **Bypass prevention.** pstack does not police `--no-verify` or force-push. Our `guard` hook
   blocks `--no-verify` and pushes that name a protected branch.
10. **Committed trail.** The decision TSV stays local by default, so the morning audit pstack
    and the interview rely on (§6) depends on git history alone.

## 8. Concrete integration points between pstack and our plugin

1. **"The repo's checks" = `standards.py check`.** `verify` §1 already names it. Point pstack's
   gates lane and pre-push step at it in our `CLAUDE.md` template, so pstack and our skills run
   the same command (pstack's own rule from `correct`: same command locally and in CI).
2. **Expose merge method and base to pstack.** Add one line to the generated `CLAUDE.md`:
   "PRs target `[branches].integration`. Merge with `--<merge>`, never `--squash` unless
   `merge = "squash"`." Shipping's bottom-up landing still works with `--rebase` into `dev`.
3. **Make the verdict a required check, not a comment.** Proposal: a `[review]` key
   (`verdict_check = "verify"`, `verdict_app_id = <id>`). The verifier posts a commit status at
   the head SHA from a separate GitHub App. The ruleset requires it with `integration_id`, the
   same pattern `branch_rules` already uses for `standards`. This binds pstack's "verdict per
   head SHA" to a forge fact, and a new push invalidates it.
4. **Map autopilot modes to `reviews_required`.** If `reviews_required ≥ 1`, Autopilot-full
   cannot merge without a human approval, which pstack will not give. Document that such repos
   use **Autopilot-stack**. Autopilot-full applies only where `reviews_required = 0` and the
   verdict check (item 3) is required.
5. **Guard additions.** Keep blocking `--no-verify` and protected-branch pushes. Allow
   `--force-with-lease` on the agent's own branch, which `autopilot-full.md` step 2 requires.
   Block a bare `--force`.
6. **PR template union.** Ours has Why / What changed / Evidence. pstack adds Scope, Tradeoffs,
   Blast Radius, and Verification. Pocock's `pr` adds "Merge Danger: Door (one-way/two-way)".
   Adopt `## Why`, `## What changed`, `## Scope`, `## Blast Radius` (with Door),
   `## Verification`, so a pstack-written body passes our template unchanged. Add a
   `Closes #N` line to close gap 7.
7. **`/correct` writes into our gates.** Its rule table ("each rule with what enforces it") is
   the agent-instruction counterpart of `standards.toml`. New lint rules land in `[gates].lint`,
   and `/correct` changes to guarded paths go through CODEOWNERS.
8. **Trail placement.** If a run commits `.audit/*.tsv` or `decisions.tsv`, add those paths to
   `[size].exclude`, so the audit trail does not trip size limits and does not get dropped to
   stay under them.
9. **Composition order with Pocock's skills.** grilling/wayfinder → `to-spec` → `to-tickets`
   (labels `ready-for-agent`) → pstack `/poteto-mode` per ticket (Feature or Bug fix) →
   Opening a PR → Pocock `code-review` (Standards and Spec axes against `standards.toml` docs
   and the ticket) alongside pstack `interrogate` (only findings a run proves) → Babysit →
   Shipping under our ruleset. Pocock's in-progress `chief-of-staff` skill mirrors pstack's
   Orchestrate coordinator. It says to work on the environment before feature work.
10. **Claude Code caveats.** No Bugbot, cloud agents, or Automations. Cloud agents map to
    `isolation: "worktree"` (`docs/harness/claude-code.md`), and worktrees share
    `core.hooksPath`, so our hooks still fire there.

**Sources.**
- pstack source, `cursor/plugins` repo, `pstack/` at `bf0c7cd` (local:
  `~/.claude/marketplaces-src/cursor-plugins/pstack`), https://github.com/cursor/plugins/tree/main/pstack
- Pocock, M., Tan, L., "LIVE: Poteto (creator of pstack) on shipping 1,000's of PR's a month at
  SpaceX", YouTube, 2026-10-02, https://www.youtube.com/watch?v=MN9dGgmLyso (ASR transcript)
- mattpocock-skills 1.3.1 (`skills/engineering/{to-tickets,triage,code-review,pr,implement,wayfinder}`,
  `skills/in-progress/chief-of-staff`), https://github.com/mattpocock/skills
- This repo: `standards.toml`, `skills/setup-standards/templates/.githooks/standards.py`,
  `.github/workflows/standards.yml`, `docs/research/process-control.md`
