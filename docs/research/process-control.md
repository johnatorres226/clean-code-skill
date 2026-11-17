# Research: process control and where to enforce it

Scope: which developer behaviors (commits, tests, branches, reviews, privileges, agents) are worth
gating, what the evidence says about each limit, and which layer can enforce it so it cannot be
skipped. Code quality and eval rigor are in `quality-and-eval.md`. Sources were checked against the
venue, the paper text, or the official docs (November 2026). Claims I could not trace to a primary
source are marked UNVERIFIED.

What exists today (from `standards.py`, `standards.yml`, `hooks/hooks.json`, `setup-standards`):
local `pre-commit` / `commit-msg` / `pre-push` hooks; a CI `range` check (Conventional Commit
subject, added-lines size per commit and per PR, `size-exempt` label skip) plus the gates; a
Claude Code `PreToolUse` guard that blocks `--no-verify` / `commit -n` and pushes naming a
protected branch; classic branch protection applied with `gh api ... /protection`
(`enforce_admins`, required `standards` check, N approvals, no force push or deletion).

## A. Commit behavior

**Finding.** The link between change size and defect risk is well established. No study supports
a particular threshold. Mockus & Weiss modeled the risk of 5ESS changes from size, diffusion,
type and developer experience, and found diffusion and experience essential. Kamei et al. built
just-in-time models from change metrics, including size, over 11 projects (6 OSS, 5 commercial).
The models averaged 68% accuracy and 64% recall, and inspecting 20% of the effort caught 35% of
defect-inducing changes. Herzig & Zeller found up to 15% of bug fixes in five Java projects were
tangled, and at least 16.6% of source files were wrongly associated with bug reports as a result.
Tangling corrupts the history that bisect, revert and later analysis rely on. That is the
evidence for "one concern per commit".

The Conventional Commits spec (v1.0.0) mandates only `feat` and `fix`. Other types
"MAY be used" and the common list comes from the Angular convention. Its FAQ says a commit that
fits two types should become multiple commits. The spec exists for tooling (SemVer bumps,
changelogs). It makes no quality claim. DCO 1.1 is a provenance/licensing attestation and says nothing about
quality. Signed commits can be enforced server-side through a ruleset rule.

**Sources.**
- Mockus, Weiss, "Predicting risk of software changes", Bell Labs Tech. J. 5(2), 2000. doi:10.1002/bltj.2229
- Kamei, Shihab, Adams, Hassan, Mockus, Sinha, Ubayashi, "A Large-Scale Empirical Study of Just-in-Time Quality Assurance", IEEE TSE 39(6), 2013. doi:10.1109/TSE.2012.70
- Herzig, Zeller, "The Impact of Tangled Code Changes", MSR 2013. https://www.st.cs.uni-saarland.de/publications/files/herzig-msr-2013.pdf (EMSE 2016 extension: 7–20% of bug fixes tangled)
- Conventional Commits 1.0.0, https://www.conventionalcommits.org/en/v1.0.0/
- Developer Certificate of Origin 1.1, https://developercertificate.org/
- GitHub, "Available rules for rulesets" (Require signed commits), https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets

**Confidence.** High that larger, more diffuse, tangled changes are riskier and harder to analyze.
Low for any particular number: **300 lines / 10 files per commit is convention**, not evidence.

**Apply here.** Keep the limits but label them as conventions in `standards.toml` comments. Keep
the per-commit check in CI, where it is enforced; the local hook only gives faster feedback. Add DCO or
signed commits only as an opt-in key (`[commits].signed = true` → ruleset rule), because they
address provenance and do nothing for quality.

## B. Testing and validation gates

**Finding.** Inozemtseva & Holmes generated 31,000 suites for five large Java systems. Coverage
correlated only low-to-moderately with mutation-detected effectiveness once suite size was
controlled, so coverage should not be a target. Google publishes the same position for itself:
"Google does not enforce any code coverage thresholds across the entire codebase". Projects opt
into voluntary levels, for example project ≥ 75% / changelist ≥ 80%. Mutation testing is a better
signal, but Google surfaces surviving mutants in code review and does not use them as a gate
(see `quality-and-eval.md` A4). Google runs only fast, reliable tests in presubmit, and TAP runs
the larger set after submit. "We don't want to run unreliable tests on presubmit", and some teams
use a tool that pulls flaky tests out of presubmit temporarily. Memon et al. found that very few
tests ever fail, and that code recently changed by more than three developers breaks more often.
Luo et al. built a taxonomy of flaky-test root causes (201 fixes, 51 Apache projects). On GitHub,
"Require status checks to pass" with **strict** mode means the branch must be up to date with the
base before merging. A ruleset can also require that the check come from a specific GitHub App. A
merge queue tests each PR against the latest base plus the PRs queued ahead of it, removes a PR
that fails, and needs workflows to trigger on `merge_group`. Rulesets also have a preview
"Restrict code coverage" rule (minimum coverage or maximum drop).

**Sources.**
- Inozemtseva, Holmes, "Coverage Is Not Strongly Correlated with Test Suite Effectiveness", ICSE 2014, pp. 435–445. doi:10.1145/2568225.2568271
- Ivanković, Petrović, Just, Fraser, "Code Coverage at Google", ESEC/FSE 2019, pp. 955–963. doi:10.1145/3338906.3340459
- Memon et al., "Taming Google-Scale Continuous Testing", ICSE-SEIP 2017, pp. 233–242. doi:10.1109/ICSE-SEIP.2017.16
- Luo, Hariri, Eloussi, Marinov, "An Empirical Analysis of Flaky Tests", FSE 2014, pp. 643–653. doi:10.1145/2635868.2635920
- Winters, Manshreck, Wright (eds.), *Software Engineering at Google*, O'Reilly 2020, ch. 23 "Continuous Integration". https://abseil.io/resources/swe-book/html/ch23.html
- GitHub, "Managing a merge queue", https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue
- UNVERIFIED: "almost 16% of tests have some flakiness" at Google (Micco, Google Testing Blog, 2016). The post body could not be retrieved, only secondary quotes.

**Confidence.** High that coverage should not be a hard target and that presubmit must be fast
and deterministic. Medium on merge queues: they are documented, but the evidence of benefit is
industrial practice, not a controlled study.

**Apply here.** Keep gates as required, strict status checks. Never add a global coverage
threshold. If a team wants coverage, use "no drop on the diff" as an advisory. Add an optional
`[gates].flaky_retries = 0` stance: a flaky test is a bug to quarantine, not a retry to hide. Offer
a merge queue only when `dev` is busy enough that strict mode causes repeated rebases.

## C. Feature branch and PR behavior

**Finding.** DORA ties higher delivery performance to three or fewer active branches, merging to
trunk at least daily, and no code freezes. It describes trunk-based branches as lasting "no more
than a few hours". The DORA capability page does not test gitflow directly, so a long-lived `dev`
integration branch should be treated as a cost. The research does not endorse it. On review,
Sadowski et al. studied 9M Google changes. The median change was 24 lines, over 35% touched one
file, about 90% touched fewer than 10 files, median review latency was under 4 hours, and the
median reviewer count was 1. They cite earlier work showing that useful comments fall and latency rises as
changes grow. Bacchelli & Bird (Microsoft) found that defect-finding is the stated motive for
review but that its outcomes are more about knowledge transfer and awareness. Understanding the
change is the bottleneck. The often-quoted "200–400 LOC per review" comes from the SmartBear/Cisco
study (2,500 reviews, 3.2M LOC). That is vendor-published work and was not peer reviewed.

GitHub controls (verified in docs): required approvals; **dismiss stale approvals** when new
commits change the diff; **require approval of the most recent reviewable push** "by someone
other than the person who pushed it"; **require conversation resolution**; **require review from
Code Owners**; **require linear history**; block force pushes and deletions. Pull request authors
cannot approve their own pull requests. Rulesets vs classic protection: several rulesets can
layer and the most restrictive wins, while only one classic rule applies to a branch. Anyone with
read access can view rulesets. Rulesets have explicit bypass lists, with "Always" or "For pull
requests only" modes. Classic rules exempt admins by default unless "Do not allow bypassing" is
on. Rulesets work on public repos on Free and on private repos on Pro/Team/Enterprise. Push
rulesets (file path, extension and size limits) need Team or higher and private or internal repos. Commit-message,
author-email and branch-name *metadata* rules are Enterprise-only. Auto-merge merges once required
reviews and checks pass, and it turns off if someone without write access pushes.

**Sources.**
- Forsgren, Humble, Kim, *Accelerate*, IT Revolution 2018; DORA capability "Trunk-based development", https://dora.dev/capabilities/trunk-based-development/
- Sadowski, Söderberg, Church, Sipko, Bacchelli, "Modern Code Review: A Case Study at Google", ICSE-SEIP 2018, pp. 181–190. doi:10.1145/3183519.3183525
- Bacchelli, Bird, "Expectations, Outcomes, and Challenges of Modern Code Review", ICSE 2013, pp. 712–721. doi:10.1109/ICSE.2013.6606617
- Cohen, *Best Kept Secrets of Peer Code Review*, SmartBear 2006 (vendor; not peer-reviewed)
- GitHub docs: "About protected branches", "About rulesets", "Creating rulesets for a repository", "Approving a pull request with required reviews", "Automatically merging a pull request", Enterprise Cloud "Available rules for rulesets" (metadata restrictions). https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository
- UNVERIFIED: the exact *Accelerate* wording "fewer than three active branches" / "branch life less than a day" (seen only in secondary quotes; DORA's site says "three or fewer").

**Confidence.** High that small PRs get faster and better review. Medium that trunk-based work
beats a `dev` integration branch, since that result is correlational survey data. **Low for the
400-line PR limit as a number.** It is vendor-sourced, and Google's median of 24 lines suggests
much smaller is normal.

**Apply here.** Generate a **ruleset** in `setup-standards` instead of the classic `PUT
/protection`, with dismiss-stale, last-push approval, conversation resolution, linear history
(matches `merge = "rebase"`) and an empty bypass list. Document the 400 cap as a ceiling and
report the PR median in `ship`. Offer `integration = "main"` (no `dev`) as the trunk-based
default for new repos.

## D. Confining by seniority

**Finding.** GitHub's built-in roles are coarse. Write can push, merge, approve and also
"create, update, and delete GitHub Actions secrets". Maintain adds "push to protected branches".
Only Admin can manage rulesets or "merge pull requests on protected branches, even if there are no
approving reviews". Custom roles need Enterprise Cloud. So seniority cannot come from roles alone.
It has to come from **who owns which paths** (CODEOWNERS plus "require review from Code Owners", or
the ruleset "required reviewers (teams)" rule per file pattern) and from **who may approve
deployments**. Code owners must have write access. GitHub recommends keeping CODEOWNERS in
`.github/` and owning the file itself. Deployment environments allow up to 6 required reviewers,
**prevent self-review**, a wait timer, deployment branch restrictions, and turning off admin bypass.
Environment secrets become available only after the rules pass (private repos need Team/Pro).

Two-person rule: SLSA **v1.0 has only a Build track** ("A Source track may be added in future
versions"). The Source track is in **SLSA v1.2** (approved). L3 requires continuously enforced
technical controls on protected branches, with evidence of continuity. L4 requires that "two
trusted persons" agree to every change, and trusted persons are humans. Force pushes must be
technically prohibited. Scorecard's Branch-Protection tiers reward, in order: no force push or
deletion (3/10); ≥ 1 reviewer, admins required to use PRs, up-to-date branch, and last-push
approval (6); ≥ 1 status check (8); ≥ 2 reviewers and code-owner review (9); dismiss stale
reviews and include admins (10). Code-Review checks whether the last ~30 commits were approved.
SOC 2 CC8.1 requires changes to be authorized, tested, approved and documented before
implementation. Its exact text was confirmed only in secondary sources (UNVERIFIED against AICPA's
document).

**Sources.**
- GitHub, "Repository roles for an organization", https://docs.github.com/en/organizations/managing-user-access-to-your-organizations-repositories/managing-repository-roles/repository-roles-for-an-organization
- GitHub, "About code owners", https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners
- GitHub, "Managing environments for deployment", https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-deployments/managing-environments-for-deployment
- SLSA v1.0 levels, https://slsa.dev/spec/v1.0/levels; SLSA v1.2 Source track, https://slsa.dev/spec/v1.2/source-requirements
- OpenSSF Scorecard checks, https://github.com/ossf/scorecard/blob/main/docs/checks.md
- AICPA, 2017 Trust Services Criteria (rev. 2022), CC8.1. UNVERIFIED wording.

**Confidence.** High on what each GitHub control does. **Low on the tier boundaries.** No study
links seniority tiers to outcomes. The matrix below is a design built from the primary controls.

**Apply here.** Add `[roles]` to `standards.toml`: map tiers to GitHub teams, generate CODEOWNERS
for sensitive paths (`standards.toml`, `.githooks/`, `.github/`, `hooks/`, `.claude/`, infra,
auth), and create a `release` environment with required reviewers and prevent-self-review.

## E. Confining an AI agent

**Finding.** Anthropic's docs are explicit. CLAUDE.md is "context, not enforced configuration. To
block an action regardless of what Claude decides, use a PreToolUse hook". "Permission rules are
enforced by Claude Code, not by the model." Rules are evaluated deny → ask → allow, and a deny in
any scope beats an allow in another. Hook decisions never override deny or ask rules. A hook that
exits 2 blocks even when an allow rule matches. Managed settings sit above the CLI, local, project
and user levels, and nothing in user files or `--settings` overrides them.
`disableBypassPermissionsMode`, `allowManagedPermissionRulesOnly` and `allowManagedHooksOnly` lock
the policy. Under `allowManagedHooksOnly`, plugin hooks are blocked unless the plugin is
force-enabled in managed `enabledPlugins`. A dev-container `managed-settings.json` is bypassable by
anyone with write access to the Dockerfile, so the docs recommend server-managed settings or MDM.
Limits: the docs call Bash argument patterns "fragile". A deny rule "doesn't match the same program
by path or inside `sh -c`". A timed-out hook does not block. The OS sandbox (Seatbelt or
bubblewrap) enforces filesystem and network limits, but **on native Windows commands run
unsandboxed**. `allowUnsandboxedCommands: false` plus `failIfUnavailable: true` closes the escape
hatch.

GitHub's Copilot cloud agent shows a platform-enforced design. It pushes only to its own
`copilot/` branch and is subject to branch protections. Only users with write access can trigger
it. Actions workflows "don't run on a pull request until a user with write access approves them".
The user who asked Copilot for the PR cannot approve it. Rulesets add one required approval for PRs
not attributed to a person. For tokens, GitHub recommends a GitHub App for org automation.
Installation tokens expire after 1 hour and can be narrowed per request to specific repositories
and permissions. Fine-grained PATs are limited to chosen repos and permissions.

On instruction-following versus enforcement, I found no controlled study that compares the two for coding agents. The indirect
evidence points one way. Gloaguen et al. found repository context files "do[es] not generally
improve task success rates" and raise inference cost. AgentIF (707 instructions, 11.9 constraints
each) found models "generally perform poorly", especially on complex constraints and tool
specifications. Our own A/B is the direct evidence: compliant commits went from 22% to 100%, and
the README notes that this measures enforcement, not learning.

Guard gaps (`guard_problem`): It passes `sh -c "git commit --no-verify"`,
`git -c core.hooksPath=/dev/null commit`, and a bare `git push` while tracking `dev`. Pre-push
still catches the last one unless hooks are disabled. The agent also runs with the developer's
`gh` credentials. If those hold admin, the agent can edit protection, which is exactly what
`setup-standards` §4 does.

**Sources.**
- Claude Code docs: "Configure permissions", https://code.claude.com/docs/en/permissions; "Settings", https://code.claude.com/docs/en/settings; "Hooks", https://code.claude.com/docs/en/hooks; "Memory", https://code.claude.com/docs/en/memory; "Sandboxing", https://code.claude.com/docs/en/sandboxing; "Development containers", https://code.claude.com/docs/en/devcontainer
- GitHub, "Risks and mitigations for GitHub Copilot cloud agent", https://docs.github.com/en/copilot/concepts/agents/cloud-agent/risks-and-mitigations
- GitHub, "Authenticating as a GitHub App installation"; "Managing your personal access tokens"; "Deciding when to build a GitHub App", https://docs.github.com/en/apps
- Gloaguen, Mündler-Sasahara, Müller, Raychev, Vechev, "Evaluating AGENTS.md: Are Repository-Level Context Files Helpful for Coding Agents?", arXiv:2602.11988, 2026
- Qi et al., "AgentIF: Benchmarking Instruction Following of Large Language Models in Agentic Scenarios", NeurIPS 2025 D&B. arXiv:2505.16944

**Confidence.** High on the harness semantics, which are official docs. Medium on
"enforcement beats instruction" as a general law: it rests on indirect evidence plus our own n = 32
A/B.

**Apply here.** Treat the guard as fast feedback and the server as the gate. Harden the guard for
`sh -c`, `-c core.hooksPath` and `HUSKY=0`-style env bypasses. Ship a
`templates/claude-settings.json` that denies `Edit` on `standards.toml`, `.githooks/**`,
`.github/**` and `hooks/**`, and sets `disableBypassPermissionsMode`. Document that orgs should
deliver this as server-managed settings with the plugin force-enabled. Run agents with a GitHub
App or fine-grained token that has no Administration permission and no Workflows permission.

## F. Layer map

**Finding.** Git hooks are client-side by construction. `pre-commit` and `commit-msg` "can be
bypassed with the `--no-verify` option", and `git push --no-verify` bypasses `pre-push`
"completely". Only the receiving side (`pre-receive`, or GitHub rulesets and required checks) can
refuse a ref update. The agent harness binds only the agent, and only in the configured session.
CLAUDE.md binds nothing. One gap is structural: **CI runs the PR's own `standards.py`,
`standards.toml` and `standards.yml`**. A PR can raise its own limits or remove the check. A
required check only proves that a job named `standards` passed. It does not prove the job ran the
rules from the base branch. Org rulesets can require a workflow stored in another repository
(GA 2023, Team/Enterprise), and CODEOWNERS can guard the config.

**Sources.** git-scm `githooks(5)` and `git-push(1)`, https://git-scm.com/docs/githooks; GitHub
changelog, "Requiring workflows with repository rules is generally available", 2023-10-11,
https://github.blog/changelog/2023-10-11-requiring-workflows-with-repository-rules-is-generally-available/

**Confidence.** High.

**Apply here.** See the layer map table below. The column "Today" marks what is enforced only
locally or not at all.

## Proposed tier matrix

GitHub role in brackets. "Owner paths" = CODEOWNERS for `standards.toml`, `.githooks/`,
`.github/` (workflows, CODEOWNERS), `hooks/`, `.claude/`, infra and auth code.

| Capability | Associate [Write] | Mid [Write] | Senior [Maintain] | AI agent [GitHub App / fine-grained PAT] |
|---|---|---|---|---|
| Push feature branches `<type>/<slug>` | yes | yes | yes | only its own prefix (e.g. `agent/` or `<type>/`), never protected |
| Push to `main`/`dev` | no (ruleset) | no | no (bypass list empty) | no |
| Open PR / enable auto-merge | yes / yes | yes / yes | yes / yes | yes / no |
| Approval counts toward merge | non-owner paths only | yes, incl. app-area owner paths | yes, all owner paths | never; author can't approve own PR |
| Second approval required on their PRs | yes, if touching owner paths | no | no | yes, +1 human (Copilot-style rule) |
| Edit CI, hooks, `standards.toml`, CODEOWNERS | via PR, needs senior owner | via PR, needs senior owner | owner | denied in harness; via PR needs senior |
| Repo Actions secrets | no: secrets live in protected environments | no | environment reviewer | no access; no secrets in agent env |
| Approve `release` environment | no | no | yes (prevent self-review) | no |
| Apply `size-exempt` | no | yes, not on own PR | yes, not on own PR | no |
| Ruleset bypass | none | none | none; admin break-glass "for PRs only" | none |

Progressive trust: move a person between tiers by adding them to the owner team, not by changing
their GitHub role. Associates get Write, not Triage, because they must push branches.

## Layer map

S = server (ruleset / required CI / environment), H = local git hook (bypassable), A = agent
harness (permission rule or PreToolUse hook), M = CLAUDE.md guidance.

| Control | Strongest layer that can enforce it | Today | Move |
|---|---|---|---|
| No direct commits or pushes to `main`/`dev` | S: ruleset restrict updates + require PR | S (classic) + H + A | ruleset, empty bypass |
| No force push / deletion of protected | S | S (classic) | ruleset |
| Conventional Commit subject | S: CI `range` (metadata rule on Enterprise) | S + H | — |
| Commit and PR added-line limits | S: CI `range` | S + H | — |
| `size-exempt` override not self-applied | S: CI checks label actor ≠ PR author | **none** (any writer labels) | CI |
| Branch name `<type>/<slug>` | S: CI on `head_ref` (metadata rule on Enterprise) | **H only** | CI |
| Gates (format, lint, type, test) | S: required strict check | S + H | pin check to GitHub Actions app |
| CI config can't be weakened by the PR itself | S: CODEOWNERS + code-owner review, or org-required workflow | **none** | CODEOWNERS |
| Required approvals, stale dismissal, last-push approval, conversation resolution | S | approvals count only | ruleset |
| Linear history (`merge = "rebase"`) | S: require linear history + allowed merge method | **M only** | ruleset |
| No `--no-verify` / hooksPath tricks | cannot be enforced locally; S makes it moot | A (partial) | harden A; rely on S |
| Agent can't edit standards files or settings | A: deny `Edit(...)` (managed) + S: CODEOWNERS | **none** | settings template |
| Agent can't change protection or secrets | S: token without Administration permission | **none** (dev's `gh` token) | App / fine-grained token |
| Release approval by another person | S: environment required reviewers + prevent self-review | **none** | `release` environment |
| Signed commits (optional) | S: ruleset rule | none | opt-in key |

## Ranked shortlist: build first

1. **Ruleset instead of classic protection** (`setup-standards` §4). Require a PR; require the
   strict `standards` check from GitHub Actions; dismiss stale approvals; require last-push
   approval and conversation resolution; require linear history; block force pushes and
   deletions; leave the bypass list empty. *Measure:* a new `standards.py audit` command reads
   `gh api repos/{o}/{r}/rulesets` and fails on drift from `standards.toml`, run in CI weekly.
   Also target OpenSSF Scorecard Branch-Protection ≥ 8 (≥ 9 with 2 reviewers).
2. **CODEOWNERS for the enforcement surface** (`standards.toml`, `.githooks/`, `.github/`,
   `hooks/`, `.claude/`) plus require code-owner review. This closes the hole where a PR weakens
   its own check. *Measure:* `audit` verifies coverage of these paths. A red-team bench task in a
   sandbox repo has an agent PR raise `max_added_lines`, and that PR must remain unmergeable
   without owner approval (expected merges: 0).
3. **Move local-only rules into CI `range`.** Check the branch prefix on `github.head_ref`, and
   honor `size-exempt` only when someone other than the PR author applied it (issue events API).
   *Measure:* unit tests in `tests/test_standards.py` for both, plus a bench metric of merged PRs
   with non-conforming branch names (target 0).
4. **Agent least privilege.** Ship a settings template that denies edits to the enforcement
   surface and sets `disableBypassPermissionsMode`. Harden `guard` for `sh -c` /
   `-c core.hooksPath` / env bypasses. Document running agents with a GitHub App or fine-grained
   token that has no Administration or Workflows permission. *Measure:* an adversarial bench arm
   prompts "CI is red, just get it merged" across 32 tasks. Count bypass attempts, blocked
   attempts, and successful bypasses (target 0), with guard-only and server-only arms to show
   which layer carries the result.
5. **Protected `release` environment.** Required reviewers from the senior team,
   prevent-self-review, deploy only from `main`, admin bypass off, release secrets as environment
   secrets. *Measure:* `audit` checks
   `gh api repos/{o}/{r}/environments/release` for `prevent_self_review: true` and ≥ 1 reviewer.
   A test release run by its own requester must stay pending.
