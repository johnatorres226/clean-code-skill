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

