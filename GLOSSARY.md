# Clean-code standards

An environment contract for agentic development: what acceptable work is, how it is reviewed, and
who may merge it, independent of the agent harness that does the work.

## Review

**Tier**:
The review a change gets, decided by its consequence: Auto-merge, Agent merge or Human review.
_Avoid_: level, risk level, merge mode

**Auto-merge**:
The tier for a trivial change with no runtime consequence; the reviewer passes it and it merges.
_Avoid_: fast path

**Agent merge**:
The default tier: the reviewer agent publishes its review and the change merges once every
blocking finding is resolved.
_Avoid_: agent review

**Human review**:
The tier for a change that touches critical infrastructure, can lose data, or cannot be backed
out; a senior must approve it.
_Avoid_: manual review, escalation tier

**Trigger**:
A named path, content pattern or finding that puts a change in Human review.
_Avoid_: rule, flag

**Consequence**:
What a change can break if it is wrong, and whether it can be undone.
_Avoid_: risk (risk also covers likelihood, which never sets the tier)

**Finding**:
One problem a reviewer reports, tied to a location and evidence.
_Avoid_: comment, issue

**Verdict**:
The reviewer's single decision on a change: its tier, whether it may merge, and why.
_Avoid_: approval

**Release**:
The promotion of already-reviewed tickets from the integration branch to the release branch,
approved as a whole from its release notes, not line by line.
_Avoid_: deploy, release review

## Roles

**Implementer**:
The agent writing the code for a ticket; it owns that ticket's comments.
_Avoid_: coder, worker, author agent

**Reviewer**:
The agent that reviews a change and issues the verdict.
_Avoid_: review bot, checker

**Tracker**:
The agent that keeps the tracker in order (creates and links tickets, sets labels and state,
updates the map) and never comments.
_Avoid_: issue bot, PM agent

An agent's comment names its role in brackets on its first line; an untagged comment is a human's.

## Roadmap

**Layer**:
One stage of the agent's working loop that this plugin governs, such as code review or release.
_Avoid_: phase, milestone, module

## Work tracking

**Ticket**:
One unit of work that ships as one PR within the size limits and fits in one session.
_Avoid_: issue, task, story

**Map**:
The index of a whole effort: its destination, the decisions made so far, and links to its tickets.
_Avoid_: epic, roadmap issue

**Spec**:
A description of a feature from the user's point of view, before it is split into tickets.
_Avoid_: PRD, requirements doc

**Standalone ticket**:
A ticket that is not part of a multi-ticket spec, such as a bug fix; it is live as soon as it
merges and is released on its own by default.
_Avoid_: hotfix (that is a fix branched from the release branch)

**Enabling ticket**:
The last ticket of a spec, which turns the spec on; until it merges, the spec's code is merged but
inactive.
_Avoid_: launch ticket, flag flip

**Spec branch**:
A branch that collects a spec's tickets before they reach the integration branch; allowed only
when the spec's partial work cannot stay inactive.
_Avoid_: feature branch (that is a ticket's branch)

_Issue_ is not a domain term: it names only the tracker's container, which may hold a ticket, a
map or a spec.
