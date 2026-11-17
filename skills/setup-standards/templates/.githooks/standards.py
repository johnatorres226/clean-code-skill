#!/usr/bin/env python3
"""Enforce the repo's standards.toml. Stdlib only; one file so it can be vendored into .githooks/.

  check [--fast]       run the gates (fast: format + lint only)
  staged               pre-commit: block commits on protected branches and oversized commits
  commit-msg FILE      commit-msg: Conventional Commit format
  pre-push             pre-push: block pushes to protected branches, bad branch names; run check
  range BASE [--no-size] [--branch NAME]
                       CI: every commit in BASE..HEAD passes message + size, PR total within
                       limit, PR branch named <type>/<slug> (a protected head = release PR)
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
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()


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
    for name, command in cfg.get("gates", {}).items():
        if not command or (fast and name not in FAST_GATES):
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


def cmd_range(cfg: dict, base: str, check_size: bool, branch: str | None = None) -> int:
    problem = branch and head_problem(branch, cfg)
    if problem:
        return fail(f"PR: {problem}")
    for sha in git("rev-list", "--no-merges", f"{base}..HEAD").split():
        problem = message_problem(git("log", "-1", "--format=%B", sha), cfg) or \
            (check_size and size_problem(git("show", "--numstat", "--format=", sha), cfg))
        if problem:
            return fail(f"commit {sha[:8]}: {problem}")
    problem = check_size and size_problem(git("diff", "--numstat", f"{base}...HEAD"), cfg, "pr")
    return fail(f"PR: {problem}") if problem else 0


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
    """CODEOWNERS: seniors own the enforcement surface; area teams (mid tier) own their paths."""
    roles = cfg["roles"]
    seniors = " ".join(roles["senior"])
    lines = [f"/{path} {seniors}" for path in roles["guarded"]]
    lines += [f"/{path} {' '.join(teams)} {seniors}" for path, teams in roles.get("areas", {}).items()]
    return "\n".join(["# Generated by `standards.py codeowners` from standards.toml [roles].", *lines, ""])


GITHUB_ACTIONS_APP_ID = 15368  # `gh api /apps/github-actions`: only Actions may post the "standards" check
ADMIN_ROLE_ID = 5  # not in GitHub's docs; confirm the bypass list reads "Repository admin" on first apply


def branch_rules(method: str, cfg: dict) -> list[dict]:
    rules = [{"type": "deletion"}, {"type": "non_fast_forward"},
             {"type": "pull_request", "parameters": {
                 "required_approving_review_count": cfg["pr"]["reviews_required"],
                 "dismiss_stale_reviews_on_push": True, "require_code_owner_review": True,
                 "require_last_push_approval": True, "required_review_thread_resolution": True,
                 "allowed_merge_methods": [method]}},
             {"type": "required_status_checks", "parameters": {
                 "strict_required_status_checks_policy": True,
                 "required_status_checks": [{"context": "standards", "integration_id": GITHUB_ACTIONS_APP_ID}]}}]
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


def show(text: str) -> int:
    print(text.rstrip("\n"))
    return 0


COMMANDS = {
    "check": lambda cfg, args: cmd_check(cfg, fast="--fast" in args),
    "staged": lambda cfg, args: cmd_staged(cfg),
    "commit-msg": lambda cfg, args: cmd_commit_msg(cfg, args[0]),
    "pre-push": lambda cfg, args: cmd_pre_push(cfg, sys.stdin.read()),
    "range": lambda cfg, args: cmd_range(cfg, args[0], check_size="--no-size" not in args,
                                         branch=flag_value(args, "--branch")),
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
