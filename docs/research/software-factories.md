# Research: software factories and agent delivery pipelines

Scope: how teams run agents that plan, build, review, merge and ship code with little human
typing, and how they keep quality, a lifecycle and traceability (intent → spec → ticket → PR →
commit → review → deploy). Gate placement in general is covered in `process-control.md`, and code
quality metrics in `quality-and-eval.md`. Sources were checked against the company's own post,
the official docs, or the paper text (November 2026). Claims I could not trace to a primary source
are marked UNVERIFIED. Company posts are self-reports: none publishes defect or revert rates.

## A. Explicit "dark factories"

**Finding.** StrongDM's AI team (three people, founded July 2025) publishes a charter with two
rules: "Code must not be written by humans" and "Code must not be reviewed by humans", plus a
target of $1,000 of tokens per engineer per day. Validation replaces review. They report that
agent-written tests were reward-hacked ("return true" passed narrow tests), so they moved to
**scenarios**: end-to-end user stories "often stored outside the codebase (similar to a 'holdout'
set in model training)", judged by an LLM. Success is a probabilistic **satisfaction** score, the
fraction of trajectories that "likely satisfy the user", not pass/fail. The **Digital Twin
Universe** clones the observable behavior of Okta, Jira, Slack and Google Docs/Drive/Sheets so
scenarios run at high volume and failure modes can be tested safely. Their agent, `attractor`, is
released as markdown specs only. The site defines no lifecycle stages, merge authority or
traceability, and reports no defect data. Simon Willison, who visited the team, questions the
cost (about $20k per engineer per month).

OpenAI's "Harness engineering" post (Lopopolo, 11 Feb 2026) describes an internal product built
over five months with no hand-written code. The post page returned 403 to my fetcher. From search
snippets of the OpenAI page: about 1,500 PRs opened and merged by three engineers driving Codex.
Secondary accounts add about 1M lines, a team growing to seven, about 3.5 PRs per engineer per
day, agent-to-agent review, AGENTS.md kept as a short "table of contents" pointing into `docs/`,
and architecture enforced by custom linters and structural tests (all UNVERIFIED).

Factory.ai documents a "software factory" section. Its Droid review workflow runs `droid exec` in
GitHub Actions on PR open/ready and posts inline comments plus a summary. I found no first-party
claim that Droid approves or merges.

**Sources.**
- StrongDM AI, "Software Factories and the Agentic Moment", 2026-02-06, https://factory.strongdm.ai/ ; techniques, https://factory.strongdm.ai/techniques
- Willison, "How StrongDM's AI team build serious software without even looking at the code", 2026-02-07, https://simonwillison.net/2026/Feb/7/software-factory/
- OpenAI, "Harness engineering: leveraging Codex in an agent-first world", 2026-02-11, https://openai.com/index/harness-engineering/ (not fetched; 403)
- Factory, "Automated Code Review", https://docs.factory.ai/software-factory/code-review-ci

**Confidence.** High on what StrongDM states as its rules. **Low on outcomes**: no
quality, incident or cost-per-feature data is published by either team. Low on OpenAI details
beyond the PR count.

**Apply here.** The useful idea is the **holdout**, not "no review": acceptance tests the
implementing agent cannot see or edit. That needs a protected path, not a new model.

## B. Platform-native agent pipelines

**Finding.** The platforms converge on one shape: the agent writes on its own branch, runs checks,
opens a PR, and **a human merges**.

- **GitHub Copilot cloud agent.** Only write-access users can trigger it. It pushes to one branch
  (`copilot/…` or the PR's branch) and is "subject to any branch protections and required
  checks". Workflows do not run until a write-access user approves. The requester cannot approve
  the PR, and the agent cannot mark it ready, approve or merge. If the PR is under the agent's app
  identity, one extra approval is required. Before finishing, it runs CodeQL, an advisory-database
  dependency check, secret scanning and **Copilot code review** on its own diff. Commits are
  authored by Copilot, co-authored by the requester, signed, and **each commit links to the session
  log**. That is the strongest built-in traceability chain I found.
- **GitHub Agentic Workflows** (GitHub Next, technical preview Feb 2026). Markdown workflows
  compile to a `.lock.yml`. Agents run read-only, and every write goes through declared **safe
  outputs** applied by a separate, scoped job after a threat-detection job scans them. "Pull
  requests are never merged automatically, and humans must always review and approve."
- **OpenAI Codex code review.** Every internal OpenAI PR is reviewed automatically. The team
  "accepted ... modestly reduced recall in exchange for high signal quality". On Codex-generated
  PRs the reviewer commented on 36%, and 46% of those comments led to a code change, against 53% on
  human PRs. Authors warn of overreliance: it is "a support tool, not a replacement".
- **Cursor Bugbot.** Reviews every PR update, with rules in `.cursor/BUGBOT.md` (scoped by
  directory). It publishes a `Cursor Bugbot` check whose findings default to `neutral`:
  "Requiring the status alone does not block merges". Blocking needs a fail-on-unresolved option
  plus branch protection. Autofix starts a cloud agent, capped at 3 attempts per PR.
- **Anthropic Claude Code Review** (9 Mar 2026). A team of agents searches in parallel, verifies
  findings to drop false positives, and ranks by severity. Internally, PRs with substantive review
  comments went from 16% to 54%, and under 1% of findings are marked incorrect. "It won't approve
  PRs — that's still a human call." `claude-code-action` runs on your own runner, triggered by
  `@claude`, issue assignment or explicit prompts.
- **Google Jules** generates a plan for approval before changing code. **Devin** returns "draft PRs
  waiting for review". The docs I reached say nothing on review or merge rules for either.

**Sources.**
- GitHub, "Risks and mitigations for GitHub Copilot cloud agent", https://docs.github.com/en/copilot/concepts/agents/cloud-agent/risks-and-mitigations ; "About Copilot coding agent", https://docs.github.com/en/copilot/concepts/agents/coding-agent/about-coding-agent
- GitHub blog, "Automate repository tasks with GitHub Agentic Workflows", 2026-02-13, https://github.blog/2026-02-13-automate-repository-tasks-with-github-agentic-workflows/ ; docs https://github.github.com/gh-aw/
- Trębacz et al., "A Practical Approach to Verifying Code at Scale", OpenAI Alignment blog, 2025-12-01, https://alignment.openai.com/scaling-code-verification/
- Cursor, "Bugbot", https://cursor.com/docs/bugbot
- Anthropic, "Bringing Code Review to Claude Code", 2026-03-09, https://claude.com/blog/code-review ; https://github.com/anthropics/claude-code-action
- Jules docs, https://jules.google/docs/ ; Devin docs, https://docs.devin.ai/

**Confidence.** High on platform mechanics (official docs). Medium on review-effectiveness
numbers: vendor-internal, measured on their own users, with no independent replication.

**Apply here.** Copy the Copilot model wholesale: agent identity ≠ requester ≠ approver, the
agent's PR needs +1 approval, commits carry a link to the session. Treat the reviewer agent as a
check, not an approver, and be precise about whether its check blocks.

## C. Company reports at scale

**Finding.** **Stripe Minions** (two posts, Feb 2026). A run "starts in a Slack message and ends in
a pull request which passes CI and is ready for human review". Over 1,300 PRs merged per week are
"completely minion-produced, human-reviewed, but containing no human-written code". **Blueprints**
mix deterministic nodes ("Run configured linters", "Push changes", which "don't invoke an LLM at
all") with agent nodes ("Implement task", "Fix CI failures"). Lint runs locally in under five
seconds before push. CI (over three million tests) is capped at **two rounds**, and after that
"we send the branch back to its human operator". Devboxes spin up in about 10 s, are isolated from
production and the internet, and so run without permission prompts. Rules are scoped to
directories in Cursor's format and shared with Claude Code. Toolshed exposes ~500 MCP tools, and
minions get "an intentionally small subset". No failure rates are reported.

**Ramp Inspect.** Ramp's own blog (27 Oct 2026) says Inspect accounted for 74% of merged PRs in the
past month and produces "visually validated and fully reviewed" PRs "for your review". Each session
runs in a sandboxed VM with tests, telemetry, feature flags and screenshots. Ramp gives no quality
metrics, only adoption and "6x" code per person. Earlier 30% and ~50% figures are from secondary
coverage (UNVERIFIED).

**Uber uReview** (Aug 2025) is a reviewer, not an author. Its pipeline is generate → filter
(confidence score, dedup, category suppression) → post. Thresholds are set per assistant, language
and category from developer ratings. It covers over 90% of ~65k weekly diffs. 75% of comments are
rated useful and 65% are addressed, against 51% for human comments. Named failure modes: false
positives cause "tune out", low-value style comments get suppressed, and it cannot judge design.
The post does not say whether it blocks.

**Airbnb** migrated ~3,500 Enzyme test files to RTL in about six weeks against a 1.5-year manual
estimate. Each file went through a step pipeline where every step had to pass validation, with
retries fed by the errors. The 97%-automated figure is secondary (UNVERIFIED).

**Sources.**
- Stripe, "Minions: Stripe's one-shot, end-to-end coding agents" Parts 1–2, https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents , …-part-2
- Ramp, "Introducing Inspect", 2026-10-27, https://ramp.com/blog/introducing-inspect ; "Why we built our own background agent" (Ramp Builders; read via mirror)
- Uber, "uReview", 2025-08-12, https://www.uber.com/blog/ureview/
- Airbnb, "Accelerating Large-Scale Test Migration with LLMs", https://airbnb.tech (Covey-Brandt; excerpts only)

**Confidence.** High on the stated designs. **Low on quality impact**: every number is
throughput or adoption, self-reported.

**Apply here.** Stripe's deterministic-first loop and capped CI rounds map directly onto our hooks
and gates. Uber's precision-first filtering is the design target for a reviewer agent.

## D. Spec-driven and lifecycle frameworks

**Finding.** **GitHub Spec Kit** (MIT, ~150k stars, 1.0 in Oct 2026). Its stages are
`constitution → specify → (clarify) → plan → tasks → implement` (current README adds `converge`).
`specify` numbers features and creates a branch plus `specs/<NNN-name>/spec.md`. `plan` adds
`plan.md`, `research.md`, `data-model.md`, `contracts/`. `tasks` writes `tasks.md` with `[P]`
for parallelizable work. Ambiguity is marked `[NEEDS CLARIFICATION: …]` and must be gone before
the spec is complete. Constitution "Phase -1 gates" (simplicity, anti-abstraction,
integration-first) must pass or be justified in "Complexity Tracking". These are LLM-checked
templates. The traceability claim ("every architectural decision traces back to specific
requirements") has no verifying tooling.

**AWS Kiro.** Each spec has `requirements.md` (EARS notation), `design.md` and `tasks.md`, with
approval gates between phases implied by a "Quick Spec" mode that skips them. Tasks run in
dependency-ordered waves. I found no documented task→requirement ID link.

**AWS AI-DLC** (Raja SP, 31 Jul 2025; open-sourced as `awslabs/aidlc-workflows`). Three phases:
Inception, Construction, Operations. Rituals are **Mob Elaboration** and **Mob Construction**, where
the team validates AI proposals. "Bolts" (hours to days) replace sprints, and "Units of Work"
replace epics. Artifacts live in the repo. AI "defers critical decisions to humans". Traceability
is asserted, not mechanized, and Operations is the least specified phase.

**BMAD Method** (MIT, ~55k stars, v6 stable, v7 alpha). Clarify → Plan → Build and verify → Learn,
with role personas (product, architecture, UX, dev, test) and an unattended "BMad Loop" per epic.
The README I fetched does not define gates.

**Evidence.** Hill (ESEM 2026) tested five vendor claims on 88,052 merged PRs in 119 OSS repos.
After propensity matching, PRs with specification artifacts did not differ in defect introduction
(−0.6 pp, p = 0.133) or rework. Spec quality predicted neither, and specs did not constrain the
scope of AI-tagged changes (p = 0.997). "Developers spec their hardest work." The caveat: the
artifacts were mostly issue links, and no repo in the sample committed SDD-tool output, so the
tools themselves remain untested. A vendor benchmark (Uvik, 50 tickets) and a Kiro-vs-Copilot
study (Strubel et al.) were seen only in summaries (UNVERIFIED).

**Sources.**
- GitHub, Spec Kit, https://github.com/github/spec-kit ; `spec-driven.md`
- Kiro docs, https://kiro.dev/docs/specs/ , https://kiro.dev/docs/specs/feature-specs/
- AWS DevOps blog, "AI-Driven Development Life Cycle", https://aws.amazon.com/blogs/devops/ai-driven-development-life-cycle/
- BMAD Method, https://github.com/bmad-code-org/BMAD-METHOD
- Hill, "Specification Artifacts in Open-Source Pull Request Workflows Do Not Reduce Defects", ESEM 2026, LIPIcs 84. doi:10.4230/LIPIcs.ESEM.2026.84

**Confidence.** High on the stage and artifact definitions. **Low that specs improve quality**:
the only large study is null for spec artifacts in general, and nobody has tested the tools.

**Apply here.** Require a linked issue with acceptance criteria, which is cheap and gives
traceability. Do not gate merges on a spec document. Offer Spec Kit style folders as optional.

## E. Multi-agent coordination

**Finding.** **Gas Town** (Yegge, open-sourced 1 Jan 2026). A Mayor coordinates, ephemeral
"polecats" work in git worktrees, a Witness detects stuck agents, and work is tracked as **Beads**
(a git-backed issue tracker with hash IDs to avoid collisions). "Polecats never push directly to
main". `gt done` files a merge-request bead, and the **Refinery** batches MRs, runs gates on the
stack, merges if green, and on red **bisects** to isolate the failing MR ("Bors-style"). The
README says 4–10 agents "become chaotic" without it.

**Anthropic C compiler** (Carlini, Feb 2026). Sixteen agents, ~2,000 sessions, two weeks, just
under $20k. There was no orchestrator: agents claim a task by committing a lock file to
`current_tasks/`, and git rejects the second claimant. "Merge conflicts are frequent", and agents
resolved them. The verifier must be "nearly perfect, otherwise Claude will solve the wrong
problem". GCC served as a known-good oracle. "New features and bugfixes frequently broke existing
functionality" until CI was added so "new commits can't break existing code". The author is
"uneasy" about "deploying software they've never personally verified".

**Cursor "Scaling long-running autonomous coding"** (Jan 2026). Shared-file locks collapsed:
"Twenty agents would slow down to the effective throughput of two or three". Optimistic
concurrency was more robust, but flat agents became risk-averse and churned. What worked was
planners (with sub-planners), workers that do not coordinate, and a judge per cycle with fresh
restarts. A dedicated integrator "created more bottlenecks than it solved". Workers pushing to one
branch saw "minimal conflicts". Scale: hundreds of agents, a browser of ~1M LoC in about a week.

**Sources.**
- Gas Town, https://github.com/gastownhall/gastown
- Carlini, "Building a C compiler with a team of parallel Claudes", https://www.anthropic.com/engineering/building-c-compiler
- Lin, "Scaling long-running autonomous coding", Cursor, https://cursor.com/blog/scaling-agents

**Confidence.** Medium. These are well-documented single experiments by their builders, often
greenfield and oracle-rich. Code quality is self-described ("nowhere near ... an expert Rust
programmer").

**Apply here.** Parallelism needs one serialized merge point with a full gate run (merge queue),
small independent tasks, and a strong oracle. Locks and a human integrator do not scale.

## F. Evidence on quality and on AI review

**Finding.**
- **METR RCT** (16 experienced OSS developers, 246 tasks, early-2025 tools): AI allowed made them
  **19% slower**, while they believed they were 20% faster. The authors caution against
  generalizing.
- **He et al., MSR 2026** (difference-in-differences, staggered Cursor adoption vs matched
  controls): "a statistically significant, large, but transient increase" in velocity and "a
  substantial and persistent increase in static analysis warnings and code complexity", which in
  turn slows later velocity. The 30% / 41% magnitudes come from secondary summaries.
- **GitClear 2025** (vendor, 211M changed lines, 2020–2024): copy/pasted lines rose from 8.3% to
  12.3%, and "moved" (refactoring) lines fell from 25% to under 10%. This is correlational and AI
  attribution is not shown.
- **DORA 2025** (~5,000 respondents, 90% using AI): AI adoption is now positively associated with
  throughput but "does continue to have a negative relationship with software delivery stability".
  "Working in small batches" and "strong version control practices" are two of its seven AI
  capabilities. Survey, correlational.
- **Agent PR studies.** AIDev (Li, Zhang, Hassan, 456k PRs, five agents): agents are faster but
  "their PRs are accepted less frequently", and their changes are structurally simpler. Per-agent
  rates vary widely by subset and definition. Watanabe et al. (TOSEM): 83.8% of 567 Claude Code
  PRs merged against 91.0% for humans, and 45.1% of merged ones needed changes. Nakashima et al.
  (preprint): 67.9% of rejected agent PRs have no explicit reviewer feedback, and seven rejection
  modes are agent-only, including distrust of AI code.
- **AI review.** Uber (65% addressed vs 51% for humans), OpenAI (46–53% leading to a change) and
  Anthropic (<1% marked incorrect) all report precision-first designs. All are self-reported.

**Sources.**
- Becker, Rush, Barnes, Rein, arXiv:2507.09089, 2025
- He, Miller, Agarwal, Kästner, Vasilescu, "Speed at the Cost of Quality", MSR 2026, arXiv:2511.04427
- GitClear, "AI Copilot Code Quality 2025", https://www.gitclear.com/ai_assistant_code_quality_2025_research
- DORA, *2025 State of AI-assisted Software Development*, https://services.google.com/fh/files/misc/2025_state_of_ai_assisted_software_development.pdf ; https://dora.dev/ai/capabilities-model/
- Li, Zhang, Hassan, arXiv:2507.15003; Watanabe et al., arXiv:2509.14745 (TOSEM); Nakashima, Ishimoto, Kondo, McIntosh, Kamei, arXiv:2602.04226

**Confidence.** High that unguarded agent use raises complexity and warnings (MSR quasi-experiment
plus consistent correlational data). Medium on AI review value: the numbers are consistent but
vendor-run. **No study measures the quality of a no-human-review pipeline.**

**Apply here.** Measure, don't assume: warnings and complexity delta per PR, agent-PR revert rate,
and the addressed rate of reviewer-agent comments.

