# Issue tracker: GitHub

Issues and specs for this repo live as GitHub issues. Use the `gh` CLI for all operations.

## Conventions

- **Create an issue**: `gh issue create --title "..." --body "..."`. Use a heredoc for multi-line bodies.
- **Read an issue**: `gh issue view <number> --json number,title,body,labels,comments`.
- **List issues**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'` with appropriate `--label` and `--state` filters.
- **Make an issue a sub-issue of a parent**: `gh issue create --parent <parent> ...`, or `gh issue edit <parent> --add-sub-issue <child>` afterwards (`gh` 2.94+). Older `gh`: `gh api --method POST repos/<owner>/<repo>/issues/<parent>/sub_issues -F sub_issue_id=<child-db-id>` (database id, as in **Blocking** below). Without sub-issues, put `Part of #<parent>` at the top of the child body.
- **Comment on an issue**: `gh issue comment <number> --body "..."`
- **Apply / remove labels**: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- **Close**: `gh issue close <number> --comment "..."`

Infer the repo from `git remote -v`; `gh` does this automatically when run inside a clone.

## Pull requests as a triage surface

**PRs as a request surface: no.** _(Set to `yes` if this repo treats external PRs as feature requests; `/triage` reads this flag.)_

When set to `yes`, PRs run through the same labels and states as issues, using the `gh pr` equivalents:

- **Read a PR**: `gh pr view <number> --comments` and `gh pr diff <number>` for the diff.
- **List external PRs for triage**: `gh api --paginate 'repos/{owner}/{repo}/pulls?state=open' --jq '.[] | select(.author_association | IN("OWNER","MEMBER","COLLABORATOR") | not) | {number, title, author: .user.login, author_association, labels: [.labels[].name]}'`.
- **Comment / label / close**: `gh pr comment`, `gh pr edit --add-label`/`--remove-label`, `gh pr close`.

GitHub shares one number space across issues and PRs, so a bare `#42` may be either: resolve with `gh pr view 42` and fall back to `gh issue view 42`.

## When a skill says "publish to the issue tracker"

Create a GitHub issue.

## When a skill says "fetch the relevant ticket"

Read it as in **Read an issue** above.

## Wayfinding operations

Used by `/wayfinder`. The **map** is a single issue with **child** issues as tickets.

- **Map**: a single issue labelled `wayfinder:map`, holding the Notes / Decisions-so-far / Fog body. `gh issue create --label wayfinder:map`.
- **Child ticket**: an issue linked to the map as a GitHub sub-issue (see **Make an issue a sub-issue of a parent**). Where sub-issues aren't enabled, add the child to a task list in the map body and put `Part of #<map>` at the top of the child body. Labels: `wayfinder:<type>` (`research`/`prototype`/`grilling`/`task`). Once claimed, the ticket is assigned to the driving dev.
- **Blocking**: GitHub's **native issue dependencies**, the canonical, UI-visible representation. Add an edge with `gh api --method POST repos/<owner>/<repo>/issues/<child>/dependencies/blocked_by -F issue_id=<blocker-db-id>`, where `<blocker-db-id>` is the blocker's numeric **database id** (`gh api repos/<owner>/<repo>/issues/<n> --jq .id`, _not_ the `#number` or `node_id`). GitHub reports `issue_dependencies_summary.blocked_by` (open blockers only, the live gate). Where dependencies aren't available, fall back to a `Blocked by: #<n>, #<n>` line at the top of the child body. A ticket is unblocked when every blocker is closed.
- **Frontier query**: list the map's open children (`gh issue list --state open`, scoped to the map's sub-issues / task list), drop any with an open blocker (`issue_dependencies_summary.blocked_by > 0`, or an open issue in the `Blocked by` line) or an assignee; first in map order wins.
- **Claim**: `gh issue edit <n> --add-assignee @me`, the session's first write.
- **Resolve**: `gh issue comment <n> --body "<answer>"`, then `gh issue close <n>`, then append a context pointer (gist + link) to the map's Decisions-so-far.

## Cleanup operations

Used by the `tracker` agent's clean-up brief. Run `git fetch -q --prune origin` first. The protected
branches come from `[branches].protected` in `standards.toml`.

- **Merged branches**: delete a branch only while its tip is still the commit its merged PR ended
  on, so later work under a reused name survives. Never a protected branch.

  ```bash
  gh pr list --state merged --limit 200 --json headRefName,headRefOid --jq '.[] | "\(.headRefName) \(.headRefOid)"' |
  while read b sha; do
    case " main dev " in *" $b "*) continue;; esac   # protected branches
    [ "$(git rev-parse -q --verify "origin/$b")" = "$sha" ] &&
      gh api -X DELETE "repos/{owner}/{repo}/git/refs/heads/$b" >/dev/null && echo "deleted origin/$b"
    git rev-parse -q --verify "refs/heads/$b" >/dev/null && [ "$(git rev-list --count "$sha..$b" 2>/dev/null)" = 0 ] &&
      git branch -D "$b" >/dev/null 2>&1 && echo "deleted $b"
  done
  ```

  A local branch that is checked out, in a worktree or ahead of its PR stays; report it.
- **Released tickets**: GitHub closes a ticket from `Closes #n` only when the PR merges into the
  default branch, and ticket PRs merge into `dev`. Close each ticket whose closing PR has reached
  `main`:

  ```bash
  gh pr list --state merged --base dev --limit 200 --json mergeCommit,body --jq '.[] | select(.body | test("(?i)(close[sd]?|fix(e[sd])?|resolve[sd]?) #[0-9]+")) | "\(.mergeCommit.oid) \([.body | scan("(?i)(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?) #([0-9]+)")[]] | join(" "))"' |
  while read oid tickets; do
    git merge-base --is-ancestor "$oid" origin/main || continue
    for n in $tickets; do
      [ "$(gh issue view "$n" --json state -q .state)" = OPEN ] && gh issue close "$n" --reason completed && echo "closed #$n"
    done
  done
  ```
- **Idle**: open tickets with no activity in N days, `gh issue list --state open --search "updated:<YYYY-MM-DD"`;
  remote branches with no PR and no commit in N days, `git for-each-ref --sort=committerdate refs/remotes/origin --format='%(committerdate:short) %(refname:lstrip=3)'`.
  Report these; change nothing.
