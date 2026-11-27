# Research: code review for a PR-reviewer kit

Scope: what code review catches, which comments help, how to decide which changes need a human, how
current AI reviewers work, and how to measure a reviewer agent. The target is a reviewer kit (agent
definition, risk scoring, PR/MR template, comment conventions, verdict check) that runs on GitHub
and GitLab, or writes the review to a Markdown file. Merge authority and branch controls are in
`process-control.md`; judge rigor is in `quality-and-eval.md` B4. Part I holds findings that have
lasted. Part II holds 2025–2026 practice, which changes fast; every claim there carries a date.
Sources were checked in November 2026. Vendor numbers are vendor claims and are labeled so.

What exists today: ADR 0001 tiers merge authority **by path** (default human, `[roles].auto_merge`
paths merge on `standards` + `verdict`, `[roles].guarded` always human). The verdict is a status
check from a separate GitHub App, never an approval. `skills/clean-code/references/review-rubric.md`
defines the procedure (linter first, then correctness, clarity, structure, tests, what is missing),
five labels (Blocking, Should fix, Consider, Nit, Praise) and the output format.

Note for the design: the kit's three tiers make **agent merge** the default and decide by
consequence. ADR 0001 makes **human** the default and decides by path. The kit needs a new ADR that
supersedes or amends 0001.

# Part I. Findings that have lasted

## 1. What reviews actually catch

**Finding.** About three quarters of review findings are about evolvability, not behavior. Mäntylä
& Lassenius classified 759 defects from 9 industrial and 23 student reviews: 75% did not affect
visible functionality. Beller et al. classified over 1,400 changes made after review in two OSS
projects and found the same 75:25 ratio of maintainability to functional changes. They also found
that 7–35% of review comments are discarded and 10–22% of changes are not triggered by any comment.
Bacchelli & Bird found that developers and managers at Microsoft name finding defects as the main
motive for review. The outcomes are less about defects than expected. Code improvements dominate,
and knowledge transfer and team awareness are large side benefits. Google says the same of itself:
"checking for code correctness is not the primary benefit Google accrues from the process of code
review". Comprehension is the first test.

**Sources.**
- Mäntylä, Lassenius, "What Types of Defects Are Really Discovered in Code Reviews?", IEEE TSE 35(3), 2009, pp. 430–448. doi:10.1109/TSE.2008.71
- Beller, Bacchelli, Zaidman, Juergens, "Modern Code Reviews in Open-Source Projects: Which Problems Do They Fix?", MSR 2014, pp. 202–211. doi:10.1145/2597073.2597082
- Bacchelli, Bird, "Expectations, Outcomes, and Challenges of Modern Code Review", ICSE 2013, pp. 712–721. doi:10.1109/ICSE.2013.6606617
- Winters, Manshreck, Wright (eds.), *Software Engineering at Google*, O'Reilly 2020, ch. 9 "Code Review". https://abseil.io/resources/swe-book/html/ch09.html

**Confidence.** High. Two independent studies, different settings, same ratio.

**Apply here.** A reviewer that reports only bugs misses most of what human review produces. A
reviewer that reports every evolvability point drowns the bugs. Keep the rubric's order
(correctness first) but let the agent raise structure and clarity at Should fix or below. The
functional quarter is what blocks merge.

## 2. Which comments are useful, and how to label them

**Finding.** Bosu, Greiler & Bird built a classifier for useful comments from interviews at
Microsoft and applied it to 1.5M comments from five projects. The share of useful comments a
reviewer makes rises sharply in the first year and then levels off. The more files in a change,
the lower the share of useful comments. Google's reviewer guide asks reviewers to label severity:
"Nit:" (minor, should do), "Optional (or Consider):" and "FYI:". It also asks for comments about the
code, never the developer, and for the *why*. Google treats each comment as a TODO; some need
explicit resolution, others are only informational. Conventional Comments gives a machine-readable
format: `<label> [decorations]: <subject>`, with labels praise, nitpick, suggestion, issue, todo,
question, thought, chore, note, and decorations `(blocking)`, `(non-blocking)`, `(if-minor)`.

**Sources.**
- Bosu, Greiler, Bird, "Characteristics of Useful Code Reviews: An Empirical Study at Microsoft", MSR 2015, pp. 146–156. doi:10.1109/MSR.2015.21
- Google, "How to write code review comments", https://google.github.io/eng-practices/review/reviewer/comments.html
- Conventional Comments, https://conventionalcomments.org/
- UNVERIFIED: "34.5% of comments are not useful" (Bosu et al.). Seen only as a citation in arXiv:1807.04485; the PDF could not be opened.

**Confidence.** High that labels and smaller changes help. Medium on any useful-comment percentage.

**Apply here.** The rubric labels already match Google's intent. Emit them in Conventional Comments
syntax so tools can parse them: Blocking → `issue (blocking):`, Should fix → `suggestion
(non-blocking):` or `todo:`, Consider → `thought:`, Nit → `nitpick (non-blocking):`, Praise →
`praise:`. Add a decoration for the tier trigger, e.g. `issue (blocking, human-review): ...`.

## 3. Size, latency and participation

**Finding.** At Google the median change is 24 lines and median review latency is under 4 hours
(Sadowski et al., see `process-control.md` C). Google's book says small changes "should generally be
limited to about 200 lines of code". Size hurts review quality (Bosu, files per change). Size does
**not** predict speed in open data: Kudrjavets et al. found that PR size and composition do not
relate to time-to-merge over 845,316 GitHub PRs and 401,790 Gerrit/Phabricator reviews. Their other
study puts much of the delay after acceptance, before merge. McIntosh et al. found that low review
coverage and low participation are linked to up to two and five extra post-release defects per
component (Qt, VTK, ITK). Rigby & Bird found review parameters converge across Google, Microsoft,
AMD and OSS, and that review raises the number of files a developer knows by 66–150%.

**Sources.**
- Sadowski et al., "Modern Code Review: A Case Study at Google", ICSE-SEIP 2018. doi:10.1145/3183519.3183525
- Kudrjavets, Nagappan, Rastogi, "Do Small Code Changes Merge Faster? A Multi-Language Empirical Investigation", MSR 2022. arXiv:2203.05045
- Kudrjavets, Kumar, Nagappan, Rastogi, "Mining Code Review Data to Understand Waiting Times Between Acceptance and Merging", MSR 2022. arXiv:2203.05048
- McIntosh, Kamei, Adams, Hassan, "The Impact of Code Review Coverage and Code Review Participation on Software Quality", MSR 2014, pp. 192–201. https://rebels.cs.uwaterloo.ca/papers/msr2014_mcintosh.pdf
- Rigby, Bird, "Convergent Contemporary Software Peer Review Practices", ESEC/FSE 2013, pp. 202–212. doi:10.1145/2491411.2491444

**Confidence.** High that size lowers comment quality. Medium on size and speed: the negative result
contradicts common belief and has not been replicated widely.

**Apply here.** Keep the size limits for review quality, not for speed. Let the reviewer flag
"too large to review well" as its own finding. The agent-merge tier must not mean zero review:
participation matters, and an agent reviewer adds coverage, not a second human.

## 4. Consequence: what makes a change risky

**Finding.** Two separate questions: how likely a change is to break something, and how bad and how
permanent the damage is.

*Likelihood.* Kamei et al.'s just-in-time model uses 14 change features in five groups: diffusion
(subsystems, directories, files, entropy), size (lines added, deleted, total), purpose (is it a
fix), history (developers, age, unique changes) and experience (author, recent, subsystem).
Mockus & Weiss found diffusion and experience essential. Google SRE: "roughly 70% of outages are due
to changes in a live system", and the remedy is progressive rollout, fast detection and safe
rollback.

*Severity and reversibility.* Bezos (2015 letter): some decisions are "one-way doors" that must be
made "methodically, carefully, slowly"; most are "two-way doors" that "can and should be made
quickly". For code, AWS names the usual one-way door: "the most common reason for not being able to
roll back is a change of protocol". A new write format that old code cannot read makes rollback
fail. AWS's fix is two-phase deployment (read both, then write new). GitLab publishes concrete
triggers. A database review is required for schema and data migrations (`db/`, background
migrations), database tooling, complex queries, and bulk writes (`update_all`, `delete_all`,
`destroy_all`). Reviewers check that migrations are reversible, lock-safe on large tables, and fit
time limits. GitLab's production change policy rates changes C1–C4. Any change that causes
production downtime is C1. C1 and C2 need SRE on-call and manager (or platform leadership)
approval and block deploys.

**Sources.**
- Kamei et al., "A Large-Scale Empirical Study of Just-in-Time Quality Assurance", IEEE TSE 39(6), 2013. doi:10.1109/TSE.2012.70
- Mockus, Weiss, "Predicting risk of software changes", Bell Labs Tech. J. 5(2), 2000. doi:10.1002/bltj.2229
- Beyer et al. (eds.), *Site Reliability Engineering*, O'Reilly 2016, ch. 1. https://sre.google/sre-book/introduction/
- Amazon.com 2015 Letter to Shareholders (SEC Exhibit 99.1). https://www.sec.gov/Archives/edgar/data/1018724/000119312516530910/d168744dex991.htm
- Pokkunuri, "Ensuring rollback safety during deployments", Amazon Builders' Library. https://builder.aws.com/content/3F04j2yRAAMBuPSPs50xwXZqg01/ensuring-rollback-safety-during-deployments
- GitLab, "Database review guidelines", https://docs.gitlab.com/development/database_review/
- GitLab Handbook, "Change Management", https://handbook.gitlab.com/handbook/engineering/infrastructure-platforms/change-management/ (C1/C2 rules read from search excerpts; full C3/C4 text not retrieved)

**Confidence.** High that size, diffusion and history predict defects and that format and schema
changes break rollback. Medium on any specific path list: GitLab's is published policy, not a
study. No study validates a "human review" boundary.

**Apply here.** Score two axes separately. A Kamei-style **likelihood** score (size, files,
directories, entropy, fix, file age and churn, author history on these paths) decides how hard the
agent reviews. A **consequence** check (irreversible, data loss, blast radius) decides the tier.
A tiny diff can still be a one-way door: `DROP COLUMN` is one line.

# Part II. Current practice (2025–2026, fast-moving)

## 5. AI reviewers: structure, severity, noise control

**Finding.** All products checked (November 2026) converge on the same shape. The reviewer reads the
diff plus repo context. It posts inline comments and a summary. It rates severity on a short scale
and lets the repo tune what is flagged through a committed file. Most do not approve. Noise is cut
with a strictness knob, a nit cap, path exclusions, and learning from reactions and replies.

| Product (doc date) | Structure | Severity | Noise controls / config | Published numbers (vendor claims) |
|---|---|---|---|---|
| Claude Code Review (managed; docs Nov 2026, launch 2026-03-09) | Several agents find in parallel, a verify step drops false positives, then dedupe and rank; inline comments + summary + `Claude Code Review` check run | 🔴 Important, 🟡 Nit, 🟣 Pre-existing | `REVIEW.md` (read from base/default branch, never from the PR) + `CLAUDE.md`; nit caps, skip paths, "require `file:line` evidence"; levels Quick/Standard/Deep. Never approves or blocks; check concludes neutral; counts in an HTML comment `bughunter-severity` for CI gating. GitHub only; GitLab via own CI | Substantive review comments on 16% → 54% of PRs; >1,000-line PRs: 84% get findings, 7.5 issues avg; <50 lines: 31%, 0.5; "less than 1% of findings are marked incorrect" |
| GitHub Copilot code review (docs Nov 2026; agentic since 2026-03-05) | Overview comment with approval assessment, inline comments, suggested fixes | not documented | `.github/copilot-instructions.md`, path-scoped `*.instructions.md`, `AGENTS.md`; effort Lite/Balanced/Max/Adaptive. Does not count toward required approvals by default; can approve if enabled at repo, org and enterprise | 60M reviews; 71% surface actionable feedback, 29% "says nothing at all"; ~5.1 comments/review; measured by thumbs, and by issues resolved before merge |
| Cursor Bugbot (docs Nov 2026) | Bugs, security, quality in the diff; autofix via cloud agent | not documented | `.cursor/BUGBOT.md` (root always, nested by path; 30k chars/rule, 100k total); learned rules from reactions, replies and human comments, promoted on evidence, disabled on negative signal. GitHub and GitLab | Resolution rate 52% (Jul 2025) → 78.13% over 50,310 PRs (2026-04-08), measured by an LLM judge at merge. Same post: Greptile 63.49%, CodeRabbit 48.96%, Copilot 46.69% |
| CodeRabbit (docs Nov 2026) | Summary + inline; tools (linters) run inside | types Potential issue / Refactor suggestion / Nitpick; severity critical, major, minor, trivial (+ info) | `.coderabbit.yaml`: `profile` quiet/chill (default)/assertive; `path_instructions`, `path_filters`; learnings scope; `auto_approvals.min_blocking_severity`; pre-merge checks off/warning/error | none found first-party |
| GitLab Duo (docs Nov 2026) | Duo Code Review (single pass, Duo Enterprise) or Code Review Flow (agentic, credits); `@GitLabDuo` chat; "Resolve with GitLab Duo" pushes a fix | not documented | `.gitlab/duo/mr-review-instructions.yaml` with `fileFilters` groups; GitLab suggests a CODEOWNERS entry to protect it | none found |
| Greptile (docs Nov 2026) | Inline comments with optional confidence score | `strictness` 1–3 (default 2) | `greptile.json` / `.greptile/`; `commentTypes` logic/syntax/style; learns from 👍/👎 over "2–3 weeks" | Own benchmark (Jul 2025): 82% of 50 bugs caught; see §9 |
| Qodo (blog 2025-01-29) | Two routes: critical problems, and company best practices | severity threshold (default "action required") | dropping priority tiers and asking only for "major problems and bugs" | +50% suggestion acceptance (method not stated) |
| Graphite Agent (docs Nov 2026) | "Focuses on real bugs - not just style" | not documented | custom rules; acceptance-rate dashboard | "<3%" and "<5%" unhelpful comments on different pages; not verified |

**Sources.** Claude Code docs: "Code Review", "Read and request reviews on a pull request",
"Customize Code Review", https://code.claude.com/docs/en/code-review; Anthropic, "Code Review for
Claude Code", 2026-03-09, https://claude.com/blog/code-review. GitHub, "About GitHub Copilot code
review", https://docs.github.com/en/copilot/concepts/agents/code-review; GitHub changelog
2026-03-05 "Copilot code review now runs on an agentic architecture"; GitHub blog, "60 million
Copilot code reviews and counting", 2026-03-05. Cursor, "Bugbot" docs, https://cursor.com/docs/bugbot;
"Bugbot learning", 2026-04-08, https://cursor.com/blog/bugbot-learning. CodeRabbit, "Configuration
reference", https://docs.coderabbit.ai/reference/configuration, and "Findings",
https://docs.coderabbit.ai/change-stack/findings. GitLab, "GitLab Duo in merge requests",
https://docs.gitlab.com/user/project/merge_requests/duo_in_merge_requests/; "Customize review
instructions", https://docs.gitlab.com/user/duo_agent_platform/customize/review_instructions/.
Greptile, "Controlling nitpickiness", https://www.greptile.com/docs/code-review/controlling-nitpickiness.
Qodo, "Effective code suggestions from LLMs: less is more", 2025-01-29. Graphite, "AI reviews",
https://graphite.com/docs/ai-reviews.

**Confidence.** High on mechanisms (first-party docs). **Low on every number**: each vendor picks
its own metric (resolution, acceptance, "actionable", "incorrect"), its own sample and its own
judge. The cross-vendor table in Cursor's post is a competitor's measurement.

**Apply here.** Copy the converged shape: find → verify → rank → post. Use three severities that
map to tiers (Important blocks agent merge; Nit never blocks; Pre-existing is reported, never
blocks). Read review instructions from the **base branch only**, as Claude Code does, so a PR cannot
weaken its own review. Cap nits. Be silent when there is nothing (Copilot's 29%). Expose the verdict
as a machine-readable line, like `bughunter-severity`, for the status check.

## 6. Change requests on human and agent PRs

**Finding (dated 2026).** The AIDev dataset (Li, Zhang, Hassan, 2025-07) covers 456k PRs from five
agents. Agent PRs merge less often than human PRs, though agents are faster. Later studies on it:

- Haider & Zimmermann (MSR 2026) tagged 19,450 review comments on 3,177 agent PRs. Ranked by
  share of comments: feature/implementation 38.5%, refactor/simplify 14%, docs/logs 11.4%, style
  10.3%, reverts and change rejection 10%, tests >5%, dependencies 3.3%, security 2.9%, build 2.5%,
  performance ~1%, CI 0.6%. Security and build themes were more common in **rejected** PRs; docs
  and style in accepted ones.
- Abujadallah et al. (MSR 2026): 46.41% of agent fixes rejected. Four reason groups: incorrect
  implementation (incomplete, wrong approach), failing CI and tests, agent unable to implement, low
  priority.
- Ehsani et al. (MSR 2026), 33k PRs: docs, CI and build tasks merge most; performance and bug fixes
  least. Unmerged PRs are larger, touch more files and fail CI more. Rejection reasons include no
  reviewer engagement, duplicates, unwanted features, and misalignment with the request.
- Peralta et al. (MSR 2026), 717 inspected PRs: only 35.7% of rejections show clear agent failure;
  31.2% are workflow constraints; 33.1% give no reason. Nakashima et al. (preprint 2026-02): 67.9% of
  rejected agent PRs have no explicit feedback; "distrust of AI-generated code" is one of seven
  agent-only rejection modes.
- Sakib et al. (KDD AgenticSE 2026): 38.9% of agent PRs carry at least one security smell, 82.3% of
  smells are supply-chain integrity, hard-coded credentials are 99.6% of critical smells, and review
  missed 81.1% of leaked credentials. Cynthia et al. (2026-01): merged agent bug fixes add
  SonarQube issues, mostly smells, and "merge success does not reliably reflect post-merge code
  quality".

For human PRs the long-standing answer is §1: about 75% evolvability (documentation, structure,
naming), 25% functional (logic, checks, interfaces, resources).

**Sources.**
- Li, Zhang, Hassan, "The Rise of AI Teammates in Software Engineering (SE) 3.0", arXiv:2507.15003, 2025; dataset paper arXiv:2602.09185
- Haider, Zimmermann, "Understanding Dominant Themes in Reviewing Agentic AI-authored Code", MSR 2026. arXiv:2601.19287
- Abujadallah, Arabat, Sayagh, "Understanding the Rejection of Fixes Generated by Agentic Pull Requests", MSR 2026. arXiv:2606.13468
- Ehsani et al., "Where Do AI Coding Agents Fail? An Empirical Study of Failed Agentic Pull Requests in GitHub", MSR 2026. arXiv:2601.15195
- Peralta et al., "Why Are Agentic Pull Requests Merged or Rejected? An Empirical Study", MSR 2026. arXiv:2605.22534
- Nakashima, Ishimoto, Kondo, McIntosh, Kamei, "Why Agentic-PRs Get Rejected: A Comparative Study of Coding Agents", arXiv:2602.04226, 2026
- Sakib, Banik, Jadliwala, "Trust but Verify? Uncovering the Security Debt of Autonomous Coding Agents", KDD 2026 AgenticSE workshop. arXiv:2607.12428
- Cynthia, Muttakin, Roy, "Beyond Bug Fixes: ... Post-Merge Code Quality Issues in Agent-Generated Pull Requests", arXiv:2601.20109, 2026

**Confidence.** Medium. One dataset (AIDev, cutoff 2025-08) underlies all of it, the agents have
changed since, and up to two thirds of rejections have no stated reason. The direction agrees
across five groups: wrong or unwanted implementation first, then CI and tests, then scope.

**Apply here.** Agent PRs need two checks human review rarely runs: "is this what was asked" against
the issue, and "did the agent change things it was not asked to" (the 10% revert theme). Security
is rare in comments but common in code, so scan for secrets and dependency changes by tool, not by
reading.

## 7. Risk-scored automatic approval at scale

**Finding (dated 2025–2026).** Meta's Diff Risk Score (blog 2025-08-06) is a fine-tuned Llama model
that predicts whether a diff will cause a production incident. Meta uses it to let low-risk diffs
land during code freezes: over 10,000 changes landed during one 2024 event "with minimal production
impact". RADAR (preprint 2026-05) auto-reviews diffs through a funnel. It classifies by authorship
and source, applies eligibility gates and static heuristics, then a DRS percentile threshold, LLM
review, and deterministic validation before landing. It has reviewed 535K+ diffs and landed 331K+.
Raising the threshold from the 25th to the 50th percentile raised the approve rate to 60.31%. The
paper reports revert rate at 1/3 and production incidents at 1/50 of non-RADAR diffs. Those diffs
were selected as low-risk, so the comparison is not causal.

**Sources.**
- Meta Engineering, "Diff Risk Score: AI-driven risk-aware software development", 2025-08-06. https://engineering.fb.com/2025/08/06/developer-tools/diff-risk-score-drs-ai-risk-aware-software-development-meta/
- Adams et al. (31 authors, incl. Mockus, Rigby, Nagappan), "Automating Low-Risk Code Review at Meta: RADAR, Risk Calibration, and Review Efficiency", arXiv:2605.30208, 2026 (preprint)

**Confidence.** Medium. One company, self-reported, with selection bias built in. It is still the
only published system that auto-approves by risk at scale.

**Apply here.** RADAR is the closest model for the kit: hard eligibility gates first (which no
score can override), then a score threshold, then the LLM review, then deterministic checks. Start
the threshold conservative and widen it only while reverts per tier stay flat.

## 8. Platform mechanisms, GitHub vs GitLab (docs as of November 2026)

**Finding.** Both platforms can enforce all three tiers. The plan tiers differ.

- **Path ownership.** GitHub: CODEOWNERS in `.github/`, root or `docs/`; last match wins; owners
  need explicit write access; "require review from Code Owners". GitLab (Premium/Ultimate):
  CODEOWNERS in root, `docs/` or `.gitlab/`; sections `[Name]`, optional `^[Name]`, approval count
  `[Name][2]`; "Code Owner approval" on a protected branch.
- **Required approvals.** GitHub: ruleset or branch protection; reviewers need write access.
  GitLab Free: approvals are optional and "don't prevent merging". Required approval rules, prevent
  author approval and prevent committer approval need Premium.
- **Verdict as a check.** GitHub: required status check, which can be pinned to the app that must
  report it. GitLab: external status checks (Ultimate) block merge only with "Status checks must
  succeed". A check pending over 2 minutes fails. On Free, `POST /projects/:id/statuses/:sha` adds a
  job in an `external` stage of the commit's pipeline, and "Pipelines must succeed" gates on the
  pipeline.
- **Auto-merge.** GitHub: merges after required reviews and checks pass; turns off when someone
  without write access pushes. GitLab (Free): waits for pipeline, required approvals and resolved
  threads. It is the feature formerly called "merge when pipeline succeeds"; the push option keeps
  that name.
- **Inline review API.** GitHub: `POST /repos/{o}/{r}/pulls/{n}/reviews` with `event`
  `COMMENT` / `REQUEST_CHANGES` / `APPROVE` (blank = pending) and `comments[]` (`path`, `line`,
  `side`, `start_line`, `body`). It can trigger secondary rate limits. GitLab (Free): draft notes
  with `position` (`base_sha`, `head_sha`, `start_sha`, `new_path`, `new_line`), then `bulk_publish`
  with optional `reviewer_state=requested_changes`, which is not an approval.

**Sources.** GitHub docs: "About code owners", "About protected branches", "Automatically merging a
pull request", "REST API endpoints for pull request reviews", https://docs.github.com. GitLab docs:
"Code Owners" and "Code Owners syntax", "Merge request approvals", "Approval rules", "External
status checks", "Auto-merge", "Draft notes API", "Commits API: set the pipeline status of a
commit", https://docs.gitlab.com. Plan availability for GitHub rulesets: `process-control.md` C.

**Confidence.** High on what each control does. Medium on plan tiers, which move.

**Apply here.** See mapping table (c) below. On GitLab Free the kit can comment, gate on a pipeline
job, and auto-merge, but cannot **require** a human approval. Human-review tier on GitLab needs
Premium, or the kit must fail its own pipeline job until a human sets a label. A label is weaker:
any Developer can set it.

## 9. Evaluating AI reviewers

**Finding (dated 2025–2026).** There are three kinds of evidence, in falling order of rigor.

1. **Known-defect benchmarks.** CR-Bench (preprint 2026-11) recasts 584 SWE-bench issues as review
   tasks (174 verified). It measures Known-Defect Detection Rate and Usefulness Rate with three LLM
   judges. The best agents find about one third of known defects. SWR-Bench (preprint 2025-09, rev.
   2026-06) has 1,000 verified PRs with full context. An LLM judge agrees about 90% with humans.
   Tools catch functional errors better than other kinds, and aggregating several reviews lifts F1
   by up to 43.67%. Greptile's benchmark (Jul 2025) reintroduced 50 historical bug-introducing
   commits from five OSS repos. It counts a catch only if a line comment names the faulty code and
   its impact. It reports no precision. The vendor built, ran and won it.
2. **Production proxies.** Resolution or acceptance rate: did the author change the code before
   merge? (Cursor, Copilot, Graphite, Qodo.) Lin et al. (preprint 2026-07) studied 31,073 CodeRabbit
   comments: 36.4% accepted, 7.3% discussed, 56.3% rejected, mostly for invalid suggestions or
   mismatch with intent.
3. **Text similarity to human comments** (CodeReviewer, FSE 2022). The data is noisy: about 64% of
   sampled training comments were valid (Liu et al., MSR 2025). CRScore (NAACL 2025) is
   reference-free and reaches 0.54 Spearman with human ratings.

Resolution is not correctness. AFCRA (preprint 2026-10) used reviewer feedback to revise vulnerable
code until Sonnet 5 and GPT-5.5 reviewers accepted it. Its success rates were 2.5× and 12.5× those
of the best text-based attacks, and reviewers accepted fixes while the exploit still worked.

**Sources.**
- Pereira, Sinha, Ghosh, Dutta, "CR-Bench-v2: Evaluating the Real-World Utility of AI Code Review Agents", arXiv:2611.02566, 2026
- Zeng et al., "SWR-Bench: Assessing LLM Performance in Real-World Code Review Comment Generation", arXiv:2509.01494, 2025
- Greptile, "AI code review benchmarks", https://www.greptile.com/benchmarks (vendor)
- Lin, Liang, Thongtanunam, Tantithamthavorn, "Is Agentic Code Review Helpful? Mining Developers' Feedback to CodeRabbit Reviews in the Wild", arXiv:2607.03316, 2026
- Li et al., "Automating Code Review Activities by Large-Scale Pre-training" (CodeReviewer), ESEC/FSE 2022. arXiv:2203.09095
- Liu, Lin, Thongtanunam, "Too Noisy To Learn: Enhancing Data Quality for Code Review Comment Generation", MSR 2025. arXiv:2502.02757
- Naik, Alenius, Fried, Rosé, "CRScore: Grounding Automated Evaluation of Code Review Comments in Code Claims and Smells", NAACL 2025. doi:10.18653/v1/2025.naacl-long.457
- Gong, Zhang, Jahangirova, Wang, "Adaptive Code Revision Attacks on AI Pull Request Reviewers", arXiv:2610.05399, 2026
- UNVERIFIED: Martian "Code Review Bench" and its F1 rankings (secondary write-ups only).

**Confidence.** Medium for known-defect methods; they are new and preprints. Low for every vendor
leaderboard.

**Apply here.** Measure recall on known defects, false positives on clean PRs, and resolution in
production. Report each one separately. No single number covers the reviewer. See (d).

# Synthesis for the reviewer kit

## (a) Ranked review checklist

Order = how often it comes up × how bad it is when missed. Items 1–4 can block; 5–9 cannot.

1. **Does it do what was asked?** Compare with the issue: wrong approach, incomplete work, unwanted
   features, or a duplicate of open work. This is the top agent-PR theme (§6) and the functional
   quarter of human review (§1).
2. **Consequence.** Look for migrations, bulk deletes, dropped columns, format or protocol changes
   (two-phase needed?), auth, payments, infra, public API, CI and rules. Any hit names a
   human-review trigger (b). This is rare but the most severe.
3. **Security and supply chain.** Check injection, path traversal, and new or bumped
   dependencies. Secrets and known-vulnerable dependencies are the scanners' job, not the
   reviewer's: review missed 81.1% of leaked credentials (§6). The reviewer confirms any scanner that
   ran passed and reads what they cannot judge.
4. **Tests and CI.** Is CI green? Do the tests fail if the code is wrong? Did the agent weaken or
   delete tests? Failing CI is a top rejection reason (§6).
5. **Scope.** Look for changes nobody asked for (revert them), size, and files touched. Usefulness
   drops with files (§2).
6. **Structure.** Duplication, simplification and one job per unit (`review-rubric.md` step 4).
7. **Docs and contracts.** A changed behavior needs updated docs, logs and changelog.
8. **Clarity.** Names and *why* comments.
9. **Style.** Only what the formatter cannot fix. Cap at five nits, as `nitpick (non-blocking):`.

## (b) Tier signals

Evaluate in this order; the first match wins. Every escalation names its trigger in the review,
e.g. `human-review: db/migrate/20261119_drop_email.rb — DROP COLUMN (irreversible, data loss)`.

| Tier | Signals (any one) | Evidence |
|---|---|---|
| **Human review** | *Path:* migrations and schema (`db/`, `**/migrations/**`, `*.sql`), auth and session and crypto, payments and billing, IaC (`*.tf`, `k8s/`, `helm/`, deploy config), CI and rules (`.github/`, `.gitlab-ci.yml`, `.githooks/`, `standards.toml`, CODEOWNERS, `REVIEW.md`, agent settings), public API specs (`*.proto`, `openapi.*`, exported package surface), and anything in `[roles].guarded`. *Content:* `DROP`/`TRUNCATE`/`DELETE` without `WHERE`, `update_all`/`delete_all`/`destroy_all`, removed columns or fields, changed serialization or wire format, new dependency or lockfile change, credential-like strings, permission or role changes. *Reviewer:* any Important finding in the security or data-loss class, or "could not verify" (no test reaches the changed code) | GitLab DB review triggers; AWS rollback safety; Bezos one-way doors; §6 security and build themes more common in rejected PRs; ADR 0001 guarded paths |
| **Agent merge** | Default. Requires: no open Important finding, all threads resolved, checks green, and likelihood score under threshold. Above the threshold, escalate to human. Score inputs: lines added, files, directories, entropy, fix vs. feature, recent churn on touched files, agent-authored | Kamei JIT features; RADAR funnel; McIntosh participation |
| **Auto-merge** | Only docs (`*.md`, `docs/`), comments, or config with no runtime effect; size under a small cap (start at 50 added lines); not a guarded path; reviewer has 0 Important findings. Starts as an allow-list and is never inferred | Agent docs PRs merge most often (Ehsani et al.); 31% of <50-line PRs still get a finding (Anthropic, vendor) |

Treat a missed escalation as the costly error and an extra escalation as the cheap one. Tune for
recall on the human tier.

**Detection and judgment are separate controls.** Neither human nor agent review reliably finds
security defects by reading: review missed 81.1% of leaked credentials (§6), and an author agent
can revise until an agent reviewer approves vulnerable code (AFCRA, §9). So:

1. **Detect with tools, as required checks.** Secret scanning with push protection, dependency
   review and SAST block the merge on their own, whatever any reviewer says. They do not tire and
   cannot be argued past.
2. **The agent reviewer is a second net.** A security finding escalates to human review. A clean
   agent review is not evidence of safety.
3. **The human judges consequence, not hunts for defects.** On human-tier paths the human answers:
   is this the right design, what breaks if it is wrong, can it be backed out, do we accept the
   risk. The human is outside the author agent's revise-and-resubmit loop, so the author cannot
   optimize against them. That, not better detection, is why these paths stay human.

## (c) GitHub / GitLab mapping

| Kit need | GitHub | GitLab | Plan note |
|---|---|---|---|
| Human approval on consequential paths | CODEOWNERS + ruleset "require review from Code Owners" | CODEOWNERS `[Section][n]` + "Code Owner approval" on protected branch | GL Premium+; GH private repos need a paid plan |
| Approval count, no self-approval | Ruleset required approvals; author can't approve own PR | Approval rules + prevent author/committer approval | GL Premium+ (Free approvals are optional) |
| `verdict` gate | Required status check pinned to the reviewer App | External status check + "Status checks must succeed" (Ultimate); else commit status API job + "Pipelines must succeed" (Free) | GL Ultimate for true external checks |
| Agent and auto merge | Auto-merge after checks and reviews | Auto-merge (formerly MWPS): pipeline, approvals, threads | Both free |
| Inline comments | Pull request reviews API, `event=COMMENT` or `REQUEST_CHANGES` | Draft notes + `bulk_publish` (`reviewer_state=requested_changes`) | GL Free |
| Comments must be addressed | Require conversation resolution | Auto-merge waits for resolved threads | — |
| Bot identity | GitHub App installation token (`process-control.md` E) | Project or group access token bot (not checked here) | — |
| Review rules can't be weakened by the PR | Read `REVIEW.md` from base branch; CODEOWNERS on it | Same; GitLab suggests CODEOWNERS on `.gitlab/duo` | — |
| Markdown-file mode | Write `review.md` with the same sections and the verdict line; no API calls | Same | — |

## (d) Recommended evaluation

1. **Seeded corpus (offline, per release).** Rebuild Greptile's method on our repos and add what
   it lacks. Use 30 or more historical bug-introducing commits (found from fix commits), plus an
   equal number of clean PRs, plus 10 one-way-door PRs (migrations, deletes, CI edits). Metrics:
   known-defect recall (CR-Bench KDDR rule: a line comment names the fault and its impact), false
   findings per clean PR, and human-tier recall (target: 100% of one-way-door PRs escalate).
2. **Judge.** An LLM judge from another model family scores "named the fault" and "actionable".
   Calibrate it on 20 human-labeled items with Cohen's κ (`quality-and-eval.md` B4).
3. **Production proxies (continuous).** Addressed-comment rate per severity, Important findings
   dismissed without change, reverts and incidents per tier per 100 merges (RADAR's outcome
   metrics), and time to merge per tier. ADR 0001 already names reverts as the rollback trigger.
4. **Adversarial arm.** Take 10 known vulnerabilities and let an agent revise against the
   reviewer's feedback for five rounds (AFCRA). Count how many reach "no findings" with the exploit
   intact. Target: zero merge without human review, which holds when security paths are human-tier.
5. **Do not** use BLEU or similarity to human comments, or a vendor leaderboard, as the main measure.

## Citation verification

Method: checked 2026-11-19 by an AI agent (Claude) against DOI or arXiv abstract pages, official
docs and vendor first-party pages, using WebFetch and WebSearch. PDFs of Beller 2014, Bosu 2015 and
Rigby & Bird 2013 could not be read, so those claims are checked against abstracts only.

| Source as cited | Verdict | Correct citation | Note |
|---|---|---|---|
| Mäntylä, Lassenius, TSE 2009 | verified | IEEE TSE 35(3):430–448. doi:10.1109/TSE.2008.71 | 75% of defects evolvability; 388 industrial + 371 student defects. |
| Beller et al., MSR 2014, "~75/25 evolvability vs functional" | corrected | MSR 2014, pp. 202–211. doi:10.1145/2597073.2597082 | Paper says "maintainability-related" vs functional, 75:25, confirming Mäntylä's evolvability ratio. Subtype percentages not checked. |
| Bacchelli, Bird, ICSE 2013 | verified | ICSE 2013, pp. 712–721. doi:10.1109/ICSE.2013.6606617 | Abstract-level claims only; no per-category percentages used. |
| Bosu, Greiler, Bird, MSR 2015 | verified | MSR 2015, pp. 146–156. doi:10.1109/MSR.2015.21 | Experience and files findings from the abstract. |
| "34.5% of comments not useful" (Bosu et al.) | unverifiable | — | Only seen as a citation in arXiv:1807.04485. |
| Google eng-practices, comments page | verified | https://google.github.io/eng-practices/review/reviewer/comments.html | Nit / Optional (Consider) / FYI labels quoted. |
| *Software Engineering at Google*, ch. 9 | verified | https://abseil.io/resources/swe-book/html/ch09.html | Three approvals; "about 200 lines"; correctness not the primary benefit. |
| Conventional Comments | verified | https://conventionalcomments.org/ | Labels and decorations as listed. |
| Sadowski et al., ICSE-SEIP 2018 | verified | doi:10.1145/3183519.3183525 | Numbers verified in `process-control.md`. |
| Kudrjavets, Nagappan, Rastogi, MSR 2022 (small changes) | verified | arXiv:2203.05045 | 845,316 PRs; size does not relate to time-to-merge. |
| Kudrjavets et al., MSR 2022 (waiting times) | verified | arXiv:2203.05048 | Abstract via search; 29–63% speedup estimate not used. |
| McIntosh et al., MSR 2014 | verified | MSR 2014, pp. 192–201 | Up to 2 and 5 extra post-release defects. |
| Rigby, Bird, ESEC/FSE 2013 | verified | doi:10.1145/2491411.2491444 | Convergence and 66–150% from the abstract. |
| Kamei et al., TSE 2013; Mockus, Weiss 2000 | verified | doi:10.1109/TSE.2012.70; doi:10.1002/bltj.2229 | Checked in `process-control.md`; feature groups from the paper. |
| Google SRE book ch. 1 | verified | https://sre.google/sre-book/introduction/ | "roughly 70% of outages are due to changes in a live system". |
| Amazon 2015 shareholder letter | verified | SEC Exhibit 99.1, 2016 filing | One-way / two-way door wording quoted. |
| Pokkunuri, Amazon Builders' Library | verified | builder.aws.com (moved from aws.amazon.com/builders-library) | Protocol change is the most common rollback blocker. |
| GitLab database review guidelines | verified | https://docs.gitlab.com/development/database_review/ | Triggers and checks as listed. |
| GitLab handbook C1–C4 | unverifiable | handbook.gitlab.com/.../change-management/ | C1 downtime rule and C1/C2 approvals from search excerpts; page body not retrieved; C3/C4 not used. |
| Claude Code Review docs | verified | https://code.claude.com/docs/en/code-review (+ pull-requests, customize) | Severity markers, base-branch REVIEW.md, neutral check, severity line. |
| Anthropic Code Review blog, 2026-03-09 | verified | https://claude.com/blog/code-review | 16→54%, 84%/7.5, 31%/0.5, <1% incorrect. Vendor claims. |
| GitHub Copilot code review docs; 60M blog 2026-03-05 | verified | docs.github.com/en/copilot/concepts/agents/code-review; github.blog | 71% / 29% / 5.1 per review. Vendor claims. |
| Cursor Bugbot docs; "Bugbot learning" 2026-04-08 | verified | cursor.com/docs/bugbot; cursor.com/blog/bugbot-learning | 78.13% over 50,310 PRs; earlier posts give 70% and 76%. Vendor claims. |
| CodeRabbit configuration and findings docs | verified | docs.coderabbit.ai | No option named `request_changes_workflow` in the current reference. |
| GitLab Duo in MRs; review instructions | verified | docs.gitlab.com | `mr-review-instructions.yaml` details from official-page search excerpt, not a full fetch. |
| Greptile docs; Greptile benchmark (Jul 2025) | corrected | greptile.com/docs; greptile.com/benchmarks | Copilot's per-repo results sum to 26/50 (52%), not the stated 54%. No precision reported. |
| Qodo blog, 2025-01-29 | verified | qodo.ai/blog/effective-code-suggestions-llms-... | +50% acceptance; method not stated. |
| Graphite "<3%" / "<5%" unhelpful rate | unverifiable | — | Two first-party pages disagree; neither gives a method. |
| Li, Zhang, Hassan, arXiv:2507.15003; AIDev arXiv:2602.09185 | verified | arXiv | 456k PRs (v1); 932,791 in dataset paper. |
| Haider, Zimmermann, MSR 2026 | verified | arXiv:2601.19287 | Theme shares from the paper's table. |
| Abujadallah et al., MSR 2026 | verified | arXiv:2606.13468 | Categories not ranked by frequency in the abstract. |
| Ehsani et al., MSR 2026 | verified | arXiv:2601.15195 | "Each failed CI check lowers merge odds ~15%" seen only secondhand; not used. |
| Peralta et al., MSR 2026 | verified | arXiv:2605.22534 | 35.7 / 31.2 / 33.1%. |
| Nakashima et al., 2026 | verified | arXiv:2602.04226 | Preprint; 67.9% no explicit feedback. |
| Sakib et al., KDD 2026 AgenticSE | verified | arXiv:2607.12428 | 38.9%, 82.3%, 99.6%, 81.1%. |
| Cynthia et al., 2026 | verified | arXiv:2601.20109 | 1,210 merged Python bug-fix PRs. |
| Meta DRS blog, 2025-08-06 | verified | engineering.fb.com | >10,000 changes in a freeze; no SEV-reduction figure given. |
| Adams et al., RADAR, 2026 | verified | arXiv:2605.30208 | Preprint; abstract figures; exclusion lists not checked. |
| GitHub and GitLab platform docs (§8) | verified | docs.github.com; docs.gitlab.com | GitHub CODEOWNERS plan availability not stated on the page read. |
| CR-Bench, SWR-Bench, AFCRA | verified | arXiv:2611.02566; 2509.01494; 2610.05399 | All preprints. |
| CodeReviewer (FSE 2022); Too Noisy (MSR 2025); CRScore (NAACL 2025) | verified | arXiv:2203.09095; arXiv:2502.02757; doi:10.18653/v1/2025.naacl-long.457 | ~64% valid comments; 0.54 Spearman. |
| Martian Code Review Bench | unverifiable | — | Secondary write-ups only. |
| Stripe, Shopify published review-risk policies | unverifiable | — | No first-party policy found; not cited. |
