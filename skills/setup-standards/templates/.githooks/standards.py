#!/usr/bin/env python3
"""Enforce the repo's standards.toml. Stdlib only; one file so it can be vendored into .githooks/.

  check [--fast]       run the gates (fast: format + lint only)
  staged               pre-commit: block commits on protected branches and oversized commits
  commit-msg FILE      commit-msg: Conventional Commit format
  pre-push             pre-push: block pushes to protected branches, bad branch names; run check
  range BASE           CI: every commit in BASE..HEAD passes message + size, PR total within limit
  guard                Claude Code PreToolUse hook: block bypasses of the above (exit 2)
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


def changed_lines(numstat: str, exclude: list[str]) -> tuple[int, int]:
    """(lines, files) from `git diff --numstat`, skipping excluded globs and binaries."""
    lines = files = 0
    for row in numstat.splitlines():
        added, deleted, path = row.split("\t", 2)
        if added == "-" or any(fnmatch.fnmatch(path, g) for g in exclude):
            continue
        lines += int(added) + int(deleted)
        files += 1
    return lines, files


def size_problem(numstat: str, cfg: dict, limit_key: str = "commits") -> str | None:
    limits = cfg[limit_key]
    lines, files = changed_lines(numstat, cfg.get("size", {}).get("exclude", []))
    if lines > limits["max_changed_lines"]:
        return f"{lines} changed lines (max {limits['max_changed_lines']}) — split it"
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


def cmd_range(cfg: dict, base: str) -> int:
    for sha in git("rev-list", "--no-merges", f"{base}..HEAD").split():
        problem = message_problem(git("log", "-1", "--format=%B", sha), cfg) or \
            size_problem(git("show", "--numstat", "--format=", sha), cfg)
        if problem:
            return fail(f"commit {sha[:8]}: {problem}")
    problem = size_problem(git("diff", "--numstat", f"{base}...HEAD"), cfg, "pr")
    return fail(f"PR: {problem}") if problem else 0


def guard_problem(command: str, cfg: dict) -> str | None:
    try:
        words = shlex.split(command)
    except ValueError:
        words = command.split()
    if "git" not in words:
        return None
    if "--no-verify" in words or "-n" in words and "commit" in words:
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


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    cfg = load()
    if cfg is None:
        return 0  # repo has not adopted standards.toml — never impose on it
    cmd, args = (argv[0], argv[1:]) if argv else ("check", [])
    if cmd == "check":
        return cmd_check(cfg, fast="--fast" in args)
    if cmd == "staged":
        return cmd_staged(cfg)
    if cmd == "commit-msg":
        return cmd_commit_msg(cfg, args[0])
    if cmd == "pre-push":
        return cmd_pre_push(cfg, sys.stdin.read())
    if cmd == "range":
        return cmd_range(cfg, args[0])
    if cmd == "guard":
        return cmd_guard(cfg, sys.stdin.read())
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
