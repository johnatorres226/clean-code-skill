#!/usr/bin/env python3
"""Enforce the repo's standards.toml. Stdlib only; one file so it can be vendored into .githooks/.

  check [--fast]       run the gates (fast: format + lint only)
  staged               pre-commit: block commits on protected branches and oversized commits
  commit-msg FILE      commit-msg: Conventional Commit format
  pre-push             pre-push: block pushes to protected branches, bad branch names; run check
  range BASE [--no-size] [--branch NAME] [--body-file F]
                       CI: every commit in BASE..HEAD passes message + size; the PR is within
                       limit, its branch is <type>/<slug>, it does not mix holdout tests with
                       code, and its body links a ticket. A protected head (a release) skips
                       the PR rules: it is a promotion (docs/adr/0003)
  tier BASE [--pr N] [--branch NAME]
                       lowest review tier BASE...HEAD may take (docs/adr/0002), with the
                       human-review triggers that set it; with --pr, human review fails until
                       a senior approves the head commit. A release takes [release].approval
  release BASE         CI, release PRs: every commit came through a merged PR whose review
                       checks passed, then the [release.gates] run
  guard                Claude Code PreToolUse hook: block bypasses of the above (exit 2)
  codeowners           print CODEOWNERS from [roles]
  ruleset BRANCH       print the GitHub ruleset JSON for a protected branch
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import shlex
import subprocess
import sys
import tomllib
from pathlib import Path

FAST_GATES = ("format", "lint")
SHELL_OPS = {"&&", "||", ";", "|"}
ALWAYS_ALLOWED_MSG = re.compile(r"^(Merge |Revert |fixup! |squash! |amend! )")


def git(*args: str) -> str:
    # git output is UTF-8; the locale default (cp1252 on Windows) crashes on it
    return subprocess.run(["git", *args], capture_output=True, encoding="utf-8", errors="replace",
                          check=True).stdout.strip()


def load() -> dict | None:
    try:
        root = Path(git("rev-parse", "--show-toplevel"))
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    path = root / "standards.toml"
    return tomllib.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def fail(msg: str) -> int:
    print(f"standards: {msg}", file=sys.stderr)
    return 1


def message_problem(msg: str, cfg: dict) -> str | None:
    subject = msg.strip().splitlines()[0] if msg.strip() else ""
    if ALWAYS_ALLOWED_MSG.match(subject):
        return None
    types = "|".join(cfg["commits"]["types"])
    if not re.match(rf"^({types})(\([\w./-]+\))?!?: \S", subject):
        return f"'{subject}' is not '<type>(<scope>): <subject>' with type in [{types.replace('|', ', ')}]"
    if len(subject) > cfg["commits"]["max_subject"]:
        return f"subject is {len(subject)} chars (max {cfg['commits']['max_subject']})"
    return None


def added_lines(numstat: str, exclude: list[str]) -> tuple[int, int]:
    """(added lines, files with additions) from `git diff --numstat`.

    Deletions are free: a size limit must never block cleanup. Excluded globs and binaries skip."""
    lines = files = 0
    for row in numstat.splitlines():
        added, deleted, path = row.split("\t", 2)
        if added in ("-", "0") or any(fnmatch.fnmatch(path, g) for g in exclude):
            continue
        lines += int(added)
        files += 1
    return lines, files


def size_problem(numstat: str, cfg: dict, limit_key: str = "commits") -> str | None:
    limits = cfg[limit_key]
    lines, files = added_lines(numstat, cfg.get("size", {}).get("exclude", []))
    if lines > limits["max_added_lines"]:
        return f"{lines} added lines (max {limits['max_added_lines']}) — split it"
    if files > limits.get("max_files", files):
        return f"{files} files (max {limits['max_files']}) — split it"
    return None


def cmd_check(cfg: dict, fast: bool) -> int:
    return run_gates({n: c for n, c in cfg.get("gates", {}).items() if not fast or n in FAST_GATES})


def run_gates(gates: dict) -> int:
    for name, command in gates.items():
        if not command:
            continue
        print(f"standards: gate {name}: {command}", flush=True)
        # gates resolve `python` to the interpreter running this script
        env = {**os.environ, "PATH": os.path.dirname(sys.executable) + os.pathsep + os.environ["PATH"]}
        if subprocess.run(command, shell=True, env=env).returncode != 0:
            return fail(f"gate '{name}' failed")
    return 0


def cmd_staged(cfg: dict) -> int:
    branch = git("branch", "--show-current")
    if branch in cfg["branches"]["protected"]:
        return fail(f"no direct commits to '{branch}'; branch from '{cfg['branches']['integration']}'")
    problem = size_problem(git("diff", "--cached", "--numstat"), cfg)
    return fail(f"staged commit: {problem}") if problem else cmd_check(cfg, fast=True)


def cmd_commit_msg(cfg: dict, path: str) -> int:
    problem = message_problem(Path(path).read_text(encoding="utf-8"), cfg)
    return fail(problem) if problem else 0


def branch_problem(branch: str, cfg: dict) -> str | None:
    b = cfg["branches"]
    if branch in b["protected"]:
        return f"push to protected branch '{branch}' — open a PR instead"
    if not branch.startswith(tuple(b["prefixes"])):
        return f"branch '{branch}' must start with one of {b['prefixes']}"
    return None


def cmd_pre_push(cfg: dict, stdin: str) -> int:
    for line in stdin.splitlines():
        remote_ref = line.split()[2]
        problem = branch_problem(remote_ref.removeprefix("refs/heads/"), cfg)
        if problem:
            return fail(problem)
    return cmd_check(cfg, fast=False)


def head_problem(branch: str, cfg: dict) -> str | None:
    """A PR's source branch: <type>/<slug>, or a protected branch being released (dev -> main)."""
    return None if branch in cfg["branches"]["protected"] else branch_problem(branch, cfg)


ISSUE_LINK = re.compile(r"\b(close[sd]?|fix(e[sd])?|resolve[sd]?|refs?)\s+#\d+", re.IGNORECASE)


def link_problem(body: str | None, cfg: dict) -> str | None:
    if body is None or not cfg["pr"].get("require_issue"):
        return None
    return None if ISSUE_LINK.search(body) else "PR description must link its ticket (e.g. 'Closes #12')"


def holdout_problem(files: list[str], cfg: dict) -> str | None:
    """Acceptance tests are an oracle the implementer must not move: change them in their own PR."""
    held = [f for f in files if f.startswith(tuple(cfg.get("tests", {}).get("holdout", [])))]
    if held and len(held) < len(files):
        return f"changes holdout tests ({held[0]}) and code together: change acceptance tests in their own PR"
    return None


def is_release(branch: str | None, cfg: dict) -> bool:
    """A PR whose head is protected promotes reviewed work (dev -> main); it is not a ticket."""
    return branch in cfg["branches"]["protected"]


def pr_problem(cfg: dict, base: str, opts: dict) -> str | None:
    if is_release(opts["branch"], cfg):
        return None  # every commit passed these rules in its ticket PR; `release` checks that
    files = git("diff", "--name-only", f"{base}...HEAD").split()
    return (opts["branch"] and head_problem(opts["branch"], cfg)) or holdout_problem(files, cfg) \
        or link_problem(opts["body"], cfg) \
        or (opts["size"] and size_problem(git("diff", "--numstat", f"{base}...HEAD"), cfg, "pr")) or None


def cmd_range(cfg: dict, base: str, opts: dict) -> int:
    for sha in git("rev-list", "--no-merges", f"{base}..HEAD").split():
        problem = message_problem(git("log", "-1", "--format=%B", sha), cfg) or             (opts["size"] and size_problem(git("show", "--numstat", "--format=", sha), cfg))
        if problem:
            return fail(f"commit {sha[:8]}: {problem}")
    problem = pr_problem(cfg, base, opts)
    return fail(f"PR: {problem}") if problem else 0


def matching(path: str, patterns: list[str]) -> str | None:
    """First pattern that matches: plain = prefix from the root, wildcard = glob ("**/" any depth)."""
    for pattern in patterns:
        if "*" not in pattern and path.startswith(pattern):
            return pattern
        if "*" in pattern and (fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch("/" + path, pattern)):
            return pattern
    return None


def added_by_file(diff: str) -> dict[str, list[str]]:
    """Added lines per file from `git diff -U0`; deleted files have none."""
    added: dict[str, list[str]] = {}
    path = None
    for line in diff.splitlines():
        if line.startswith("+++ "):
            path = line.removeprefix("+++ b/") if line.startswith("+++ b/") else None
        elif path and line.startswith("+"):
            added.setdefault(path, []).append(line[1:])
    return added


def first_content_hit(lines: list[str], patterns: list[str]) -> str | None:
    for line in lines:
        hit = next((m.group(0) for p in patterns if (m := re.search(p, line))), None)
        if hit:
            return hit
    return None


def human_triggers(files: list[str], added: dict[str, list[str]], cfg: dict) -> list[str]:
    review = cfg.get("review", {})
    paths = review.get("human_paths", []) + cfg["roles"]["guarded"] + cfg.get("tests", {}).get("holdout", [])
    triggers = [f"human-review: {f} — path {p}" for f in files if (p := matching(f, paths))]
    hits = {f: first_content_hit(lines, review.get("human_content", [])) for f, lines in added.items()}
    return triggers + [f"human-review: {f} — content '{hit}'" for f, hit in hits.items() if hit]


def tier_floor(files: list[str], added: dict[str, list[str]], cfg: dict) -> tuple[str, list[str]]:
    """The lowest tier a change may take; the reviewer may only raise it."""
    triggers = human_triggers(files, added, cfg)
    if triggers:
        return "human-review", triggers
    small = sum(map(len, added.values())) <= cfg.get("review", {}).get("auto_merge_max_lines", 0)
    allowed = cfg["roles"].get("auto_merge", [])
    if files and small and all(matching(f, allowed) for f in files):
        return "auto-merge", []
    return "agent-merge", []


def release_floor(floor: tuple[str, list[str]], cfg: dict) -> tuple[str, list[str]]:
    """Release approval is a project setting (docs/adr/0003): human, tiered or auto. `tiered`
    sees path and content triggers only; enabling a spec is the reviewer's call to escalate."""
    approval = cfg.get("release", {}).get("approval", "human")
    if approval == "human":
        return "human-review", ["human-review: release — [release].approval = human"]
    return ("agent-merge", []) if approval == "auto" else floor


def cmd_tier(cfg: dict, base: str, opts: dict) -> int:
    files = git("diff", "--name-only", f"{base}...HEAD").split()
    floor = tier_floor(files, added_by_file(git("diff", "-U0", "--no-color", f"{base}...HEAD")), cfg)
    tier, triggers = release_floor(floor, cfg) if is_release(opts["branch"], cfg) else floor
    show("\n".join([*triggers, f"tier: {tier}"]))
    problem = opts["pr"] and tier == "human-review" and approval_problem(opts["pr"], cfg)
    return fail(problem) if problem else 0


def gh_api(path: str):
    """GitHub REST GET through the gh CLI ({owner}/{repo} come from the remote); None on any error."""
    done = subprocess.run(["gh", "api", path], capture_output=True, encoding="utf-8", errors="replace")
    return json.loads(done.stdout) if done.returncode == 0 else None


def latest_approvers(reviews: list[dict], head: str) -> list[str]:
    """Users whose latest review approves this exact commit; a push or a dismissal voids it."""
    latest = {r["user"]["login"]: r for r in reviews if r["state"] != "COMMENTED"}
    return [user for user, r in latest.items() if r["state"] == "APPROVED" and r["commit_id"] == head]


def is_senior(login: str, cfg: dict) -> bool:
    for entry in cfg["roles"]["senior"]:
        org, _, team = entry.removeprefix("@").partition("/")
        if not team and org.lower() == login.lower():
            return True
        if team and (gh_api(f"orgs/{org}/teams/{team}/memberships/{login}") or {}).get("state") == "active":
            return True
    return False


def approval_problem(pr: str, cfg: dict) -> str | None:
    head = (gh_api(f"repos/{{owner}}/{{repo}}/pulls/{pr}") or {}).get("head", {}).get("sha")
    reviews = gh_api(f"repos/{{owner}}/{{repo}}/pulls/{pr}/reviews?per_page=100") or []
    if head and any(is_senior(user, cfg) for user in latest_approvers(reviews, head)):
        return None
    return "human review: a senior must approve the head commit " \
        "(team seniors need a workflow token that can read the org)"


TIER_CHECK = "tier"  # the CI job that runs `tier --pr`; a required check on protected branches


def review_checks(cfg: dict) -> list[str]:
    review = cfg.get("review", {})
    return [TIER_CHECK] + ([review["check"]] if review.get("app_id") else [])


def check_passed(sha: str, name: str) -> bool:
    runs = gh_api(f"repos/{{owner}}/{{repo}}/commits/{sha}/check-runs?check_name={name}") or {}
    return any(run.get("conclusion") == "success" for run in runs.get("check_runs", []))


def proof_problem(sha: str, cfg: dict) -> str | None:
    """Proof of review (docs/adr/0003): the commit came through a merged PR whose checks passed."""
    integration = cfg["branches"]["integration"]
    prs = gh_api(f"repos/{{owner}}/{{repo}}/commits/{sha}/pulls") or []
    pr = next((p for p in prs if p.get("merged_at") and p["base"]["ref"] == integration), None)
    if pr is None:
        return f"commit {sha[:8]} reached {integration} without a merged PR"
    missing = [c for c in review_checks(cfg) if not check_passed(pr["head"]["sha"], c)]
    return f"commit {sha[:8]}: PR #{pr['number']} has no passing '{missing[0]}' check" if missing else None


def cmd_release(cfg: dict, base: str) -> int:
    for sha in git("rev-list", "--no-merges", f"{base}..HEAD").split():
        problem = proof_problem(sha, cfg)
        if problem:
            return fail(f"release: {problem}")
    return run_gates(cfg.get("release", {}).get("gates", {}))


def segments(command: str):
    """The command's words, then the words of every quoted string in it (sh -c "...", eval '...')."""
    try:
        words = shlex.split(command)
    except ValueError:
        words = command.split()
    yield words
    for word in words:
        if " " in word:
            yield from segments(word)


def hooks_bypass(words: list[str]) -> bool:
    # Pointing core.hooksPath at the standards hooks (setup) is fine; any other use skips them.
    setup = words[:3] == ["git", "config", "core.hooksPath"] and len(words) == 4 \
        and words[3].rstrip("/").endswith(".githooks")
    return not setup and any("core.hooksPath" in w for w in words)


def guard_problem(command: str, cfg: dict) -> str | None:
    for words in segments(command):
        if hooks_bypass(words):
            return "overriding core.hooksPath skips the standards hooks; fix the failure instead"
        if "git" not in words:
            continue
        after = words[words.index("commit") + 1:] if "commit" in words else []
        commit_flags = after[:next((i for i, w in enumerate(after) if w in SHELL_OPS), len(after))]
        if "--no-verify" in words or any(re.fullmatch(r"-[a-zA-Z]*n[a-zA-Z]*", w) for w in commit_flags):
            return "--no-verify bypasses the standards hooks; fix the failure instead"
        if "push" in words:
            protected = cfg["branches"]["protected"]
            targets = [w.split(":")[-1].removeprefix("refs/heads/") for w in words[words.index("push") + 1:]]
            hit = [t for t in targets if t in protected]
            if hit:
                return f"push to protected branch '{hit[0]}' — open a PR (skill: ship)"
    return None


def cmd_guard(cfg: dict, stdin: str) -> int:
    command = json.loads(stdin).get("tool_input", {}).get("command", "")
    problem = guard_problem(command, cfg)
    if problem:
        print(f"standards: {problem}", file=sys.stderr)
        return 2  # exit 2 = block the tool call and show stderr to the agent
    return 0


def codeowners(cfg: dict) -> str:
    """Seniors own the human-review paths (docs/adr/0002) and nothing else, so code-owner review
    gates only those. Content triggers cannot be expressed here; the `tier` check carries them."""
    seniors = " ".join(cfg["roles"]["senior"])
    paths = cfg.get("review", {}).get("human_paths", []) + cfg["roles"]["guarded"] \
        + cfg.get("tests", {}).get("holdout", [])
    lines = [f"{p if '*' in p else '/' + p} {seniors}" for p in paths]
    return "\n".join(["# Generated by `standards.py codeowners` from standards.toml.", *lines, ""])


GITHUB_ACTIONS_APP_ID = 15368  # `gh api /apps/github-actions`: only Actions may post the "standards" check
ADMIN_ROLE_ID = 5  # not in GitHub's docs; confirm the bypass list reads "Repository admin" on first apply


def required_checks(cfg: dict) -> list[dict]:
    checks = [{"context": name, "integration_id": GITHUB_ACTIONS_APP_ID} for name in ("standards", TIER_CHECK)]
    review = cfg.get("review", {})
    if review.get("app_id"):  # the reviewer agent's own App: no other identity can post the verdict
        checks.append({"context": review["check"], "integration_id": review["app_id"]})
    return checks


def branch_rules(method: str, cfg: dict) -> list[dict]:
    rules = [{"type": "deletion"}, {"type": "non_fast_forward"},
             {"type": "pull_request", "parameters": {
                 "required_approving_review_count": cfg["pr"]["reviews_required"],
                 "dismiss_stale_reviews_on_push": True, "require_code_owner_review": True,
                 # last-push approval would demand an approval even on agent-merged paths
                 "require_last_push_approval": cfg["pr"]["reviews_required"] > 0,
                 "required_review_thread_resolution": True,
                 "allowed_merge_methods": [method]}},
             {"type": "required_status_checks", "parameters": {
                 "strict_required_status_checks_policy": True,
                 "required_status_checks": required_checks(cfg)}}]
    return rules + ([{"type": "required_linear_history"}] if method == "rebase" else [])


def ruleset(branch: str, cfg: dict) -> dict:
    """GitHub ruleset for one protected branch (integration: rebase + linear; release: merge)."""
    method = cfg["branches"]["merge"] if branch == cfg["branches"]["integration"] else "merge"
    bypass = [{"actor_id": ADMIN_ROLE_ID, "actor_type": "RepositoryRole", "bypass_mode": "pull_request"}]
    return {"name": f"standards-{branch}", "target": "branch", "enforcement": "active",
            "conditions": {"ref_name": {"include": [f"refs/heads/{branch}"], "exclude": []}},
            "bypass_actors": bypass if cfg["roles"].get("admin_bypass") else [],
            "rules": branch_rules(method, cfg)}


def flag_value(args: list[str], flag: str) -> str | None:
    return args[args.index(flag) + 1] if flag in args else None


def read_file(path: str | None) -> str | None:
    return Path(path).read_text(encoding="utf-8") if path else None


def show(text: str) -> int:
    print(text.rstrip("\n"))
    return 0


COMMANDS = {
    "check": lambda cfg, args: cmd_check(cfg, fast="--fast" in args),
    "staged": lambda cfg, args: cmd_staged(cfg),
    "commit-msg": lambda cfg, args: cmd_commit_msg(cfg, args[0]),
    "pre-push": lambda cfg, args: cmd_pre_push(cfg, sys.stdin.read()),
    "range": lambda cfg, args: cmd_range(cfg, args[0], {
        "size": "--no-size" not in args, "branch": flag_value(args, "--branch"),
        "body": read_file(flag_value(args, "--body-file"))}),
    "tier": lambda cfg, args: cmd_tier(cfg, args[0], {
        "pr": flag_value(args, "--pr"), "branch": flag_value(args, "--branch")}),
    "release": lambda cfg, args: cmd_release(cfg, args[0]),
    "guard": lambda cfg, args: cmd_guard(cfg, sys.stdin.read()),
    "codeowners": lambda cfg, args: show(codeowners(cfg)),
    "ruleset": lambda cfg, args: show(json.dumps(ruleset(args[0], cfg), indent=2)),
}


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    cfg = load()
    if cfg is None:
        return 0  # repo has not adopted standards.toml — never impose on it
    cmd, args = (argv[0], argv[1:]) if argv else ("check", [])
    if cmd not in COMMANDS:
        print(__doc__)
        return 2
    return COMMANDS[cmd](cfg, args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
