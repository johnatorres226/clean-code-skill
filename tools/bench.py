#!/usr/bin/env python3
"""Task benchmark: does an agent with clean-code-standards do better work than one without?

Aider-Polyglot style: Exercism exercises scored by their own unit tests, run by `claude -p` as a
real agent (Read/Write/Edit/Bash) inside a git repo, then asked to commit. Two arms:

  none       plain repo on main, no plugin
  standards  repo adopted via setup-standards (standards.toml, hooks, CLAUDE.md block) + plugin

Metrics per run: tests pass, lint severity of the solution, commit compliance with the standards,
commits landed on protected branches, tokens, cost, turns, and whether a plugin skill was invoked.

  python tools/bench.py fetch
  python tools/bench.py run --reps 2 [--tasks ledger,bowling] [--parallel 4]
  python tools/bench.py report
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "tools" / "evals" / "benchmarks"
OUT = ROOT / "results" / "bench"
# Work dirs must live outside the plugin dir: files under --plugin-dir are protected from edits.
# resolve(): a Windows 8.3 short path (JOHTOR~1) is treated as sensitive and blocks edits
WORK = Path(tempfile.gettempdir()).resolve() / "ccs-bench"
TEMPLATES = ROOT / "skills" / "setup-standards" / "templates"
TASKS = ["ledger", "markdown", "tree-building", "bowling", "forth", "wordy", "poker", "book-store"]
ARMS = ["none", "standards"]
GH = shutil.which("gh") or r"C:\Program Files\GitHub CLI\gh.exe"
PY_DIR = str(Path(sys.executable).parent)
CLAUDE_MD = """## Standards

Rules: `standards.toml`. Hooks enforce them — fix failures, never bypass (`--no-verify`).
- Branch from `dev` as `<type>/<slug>`; never commit or push to `main`/`dev`.
- One concern per commit, Conventional Commit subject, within the size limits.
- Done = `python .githooks/standards.py check` green + evidence. Skill: `verify`.
- Writing or reviewing code: skill `clean-code`. Committing: skill `ship`.
"""

sys.path.insert(0, str(TEMPLATES / ".githooks"))
import standards  # noqa: E402

STANDARDS_CFG = standards.tomllib.loads((TEMPLATES / "standards.toml").read_text(encoding="utf-8"))
SEVERITY = {"high": 3, "medium": 2, "low": 1}


def module(slug: str) -> str:
    return slug.replace("-", "_")


def fetch() -> None:
    for slug in TASKS:
        dest = TASKS_DIR / slug
        dest.mkdir(parents=True, exist_ok=True)
        base = f"repos/exercism/python/contents/exercises/practice/{slug}"
        for name in [f"{module(slug)}.py", f"{module(slug)}_test.py", ".docs/instructions.md",
                     ".docs/instructions.append.md"]:
            done = subprocess.run([GH, "api", f"{base}/{name}", "-H", "Accept: application/vnd.github.raw"],
                                  capture_output=True, text=True, encoding="utf-8")
            if done.returncode == 0:
                (dest / Path(name).name).write_text(done.stdout, encoding="utf-8")
        print(f"fetched {slug}")
    (TASKS_DIR / "SOURCE.md").write_text(
        "Exercises from https://github.com/exercism/python (MIT License, Exercism).\n", encoding="utf-8")


def sh(cwd: Path, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding="utf-8", env=env)


def prepare(slug: str, arm: str, work: Path) -> None:
    # git marks object files read-only; Windows rmtree needs the flag cleared to delete them
    if work.exists():
        shutil.rmtree(work, onexc=lambda f, path, _: (os.chmod(path, stat.S_IWRITE), f(path)))
    work.mkdir(parents=True)
    for f in (TASKS_DIR / slug).iterdir():
        if f.name.endswith(".py"):
            shutil.copy(f, work / f.name)
    docs = "".join((TASKS_DIR / slug / n).read_text(encoding="utf-8")
                   for n in ("instructions.md", "instructions.append.md") if (TASKS_DIR / slug / n).exists())
    (work / "INSTRUCTIONS.md").write_text(docs, encoding="utf-8")
    sh(work, "git", "init", "-q", "-b", "main")
    sh(work, "git", "config", "user.email", "bench@example.com")
    sh(work, "git", "config", "user.name", "bench")
    if arm == "standards":
        shutil.copytree(TEMPLATES / ".githooks", work / ".githooks")
        toml = (TEMPLATES / "standards.toml").read_text(encoding="utf-8")
        (work / "standards.toml").write_text(
            toml.replace('test      = ""', 'test      = "python -m unittest discover -q -p *_test.py"'), encoding="utf-8")
        (work / "CLAUDE.md").write_text(CLAUDE_MD, encoding="utf-8")
    sh(work, "git", "add", "-A")
    sh(work, "git", "commit", "-q", "-m", "chore: init")
    sh(work, "git", "tag", "bench-init")
    if arm == "standards":
        sh(work, "git", "branch", "dev")
        sh(work, "git", "switch", "-q", "dev")
        sh(work, "git", "config", "core.hooksPath", ".githooks")


def prompt(slug: str) -> str:
    return (f"Complete the task described in INSTRUCTIONS.md by editing {module(slug)}.py. "
            f"The tests are in {module(slug)}_test.py (run with `python -m unittest`); do not edit "
            f"them. When you are done, commit your work to git.")


def run_agent(slug: str, arm: str, rep: int) -> dict:
    done_file = OUT / arm / f"{slug}-r{rep}.json"
    if done_file.exists():  # resume: never re-run (and re-pay for) a finished run
        return json.loads(done_file.read_text(encoding="utf-8"))
    work = WORK / arm / f"{slug}-r{rep}"
    (OUT / arm).mkdir(parents=True, exist_ok=True)
    prepare(slug, arm, work)
    cmd = [shutil.which("claude") or "claude", "-p", prompt(slug), "--output-format", "stream-json",
           "--verbose", "--setting-sources", "project", "--strict-mcp-config",  # project = CLAUDE.md only
           "--allowedTools", "Read,Write,Edit,Bash,PowerShell,Glob,Grep,Skill"]
    if arm == "standards":
        cmd += ["--plugin-dir", str(ROOT)]
    env = {**os.environ, "PATH": PY_DIR + os.pathsep + os.environ["PATH"]}
    done = subprocess.run(cmd, cwd=work, capture_output=True, text=True, encoding="utf-8",
                          env=env, timeout=1800)
    (OUT / arm / f"{slug}-r{rep}.stream.jsonl").write_text(done.stdout, encoding="utf-8")
    result = score(slug, arm, work, done.stdout)
    (OUT / arm / f"{slug}-r{rep}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"{arm:<9} {slug:<14} r{rep} pass={result['tests_pass']} lint={result['lint_weighted']} "
          f"compliant={result['commits_compliant']} cost=${result['cost_usd']:.2f}", flush=True)
    return result


def score(slug: str, arm: str, work: Path, stream: str) -> dict:
    events = [json.loads(line) for line in stream.splitlines() if line.startswith("{")]
    final = next((e for e in reversed(events) if e.get("type") == "result"), {})
    tools = [c.get("name") for e in events if e.get("type") == "assistant"
             for c in e.get("message", {}).get("content", []) if c.get("type") == "tool_use"]
    skills = [c.get("input", {}).get("skill") for e in events if e.get("type") == "assistant"
              for c in e.get("message", {}).get("content", [])
              if c.get("type") == "tool_use" and c.get("name") == "Skill"]

    # Anti-tamper: restore the original tests before grading.
    test_file = f"{module(slug)}_test.py"
    shutil.copy(TASKS_DIR / slug / test_file, work / test_file)
    env = {**os.environ, "PATH": PY_DIR + os.pathsep + os.environ["PATH"]}
    tests = sh(work, sys.executable, "-m", "unittest", "-q", test_file.removesuffix(".py"), env=env)

    lint = sh(work, sys.executable, str(ROOT / "tools" / "evals" / "lint.py"), f"{module(slug)}.py", "--json")
    findings = json.loads(lint.stdout)["findings"] if lint.stdout.strip() else []

    shas = sh(work, "git", "rev-list", "--no-merges", "--all", "^bench-init").stdout.split()
    problems = [standards.message_problem(sh(work, "git", "log", "-1", "--format=%B", s).stdout, STANDARDS_CFG)
                or standards.size_problem(sh(work, "git", "show", "--numstat", "--format=", s).stdout, STANDARDS_CFG)
                for s in shas]
    on_protected = sum(1 for b in ("main", "dev")
                       if sh(work, "git", "rev-list", "--count", f"bench-init..{b}").stdout.strip() not in ("", "0"))
    dirty = bool(sh(work, "git", "status", "--porcelain", "--", f"{module(slug)}.py").stdout.strip())
    usage = final.get("usage", {})
    return {
        "task": slug, "arm": arm,
        "valid": not final.get("is_error", True),  # usage-limit / API errors never count
        "tests_pass": tests.returncode == 0,
        "tests_output_tail": (tests.stderr or tests.stdout)[-300:],
        "lint_findings": len(findings),
        "lint_weighted": sum(SEVERITY.get(f["severity"], 1) for f in findings),
        "commits": len(shas),
        "commits_compliant": bool(shas) and not any(problems),
        "commit_problems": [p for p in problems if p],
        "protected_branches_written": on_protected,
        "uncommitted_solution": dirty,
        "turns": final.get("num_turns", 0),
        "tokens": sum(usage.get(k, 0) for k in ("input_tokens", "output_tokens",
                      "cache_creation_input_tokens", "cache_read_input_tokens")),
        "new_tokens": sum(usage.get(k, 0) for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens")),
        "cost_usd": final.get("total_cost_usd") or 0.0,
        "duration_s": round((final.get("duration_ms") or 0) / 1000),
        "tool_calls": len(tools),
        "skills_invoked": skills,
    }


def report() -> None:
    rows = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(OUT.glob("*/*.json"))]
    rows = [r for r in rows if r.get("valid", True)]
    print(f"\n{'metric':<34}" + "".join(f"{a:>12}" for a in ARMS))
    def mean(arm, key, fn=float):
        vals = [fn(r[key]) for r in rows if r["arm"] == arm]
        return sum(vals) / len(vals) if vals else float("nan")
    lines = [
        ("runs", lambda a: sum(1 for r in rows if r["arm"] == a), "{:.0f}"),
        ("tests pass rate", lambda a: mean(a, "tests_pass"), "{:.0%}"),
        ("lint weighted severity (mean)", lambda a: mean(a, "lint_weighted"), "{:.1f}"),
        ("lint-clean solutions", lambda a: mean(a, "lint_findings", lambda v: v == 0), "{:.0%}"),
        ("committed at all", lambda a: mean(a, "commits", lambda v: v > 0), "{:.0%}"),
        ("commits standards-compliant", lambda a: mean(a, "commits_compliant"), "{:.0%}"),
        ("wrote to main/dev directly", lambda a: mean(a, "protected_branches_written", lambda v: v > 0), "{:.0%}"),
        ("solution left uncommitted", lambda a: mean(a, "uncommitted_solution"), "{:.0%}"),
        ("turns (mean)", lambda a: mean(a, "turns"), "{:.1f}"),
        ("new tokens (mean)", lambda a: mean(a, "new_tokens"), "{:,.0f}"),
        ("total tokens incl. cache (mean)", lambda a: mean(a, "tokens"), "{:,.0f}"),
        ("cost USD (mean)", lambda a: mean(a, "cost_usd"), "{:.2f}"),
        ("duration s (mean)", lambda a: mean(a, "duration_s"), "{:.0f}"),
        ("runs invoking a plugin skill", lambda a: mean(a, "skills_invoked", lambda v: bool(v)), "{:.0%}"),
    ]
    for label, fn, fmt in lines:
        print(f"{label:<34}" + "".join(f"{fmt.format(fn(a)):>12}" for a in ARMS))
    print("\nper task: tests pass (none / standards)")
    for slug in TASKS:
        cell = lambda a: f"{sum(r['tests_pass'] for r in rows if r['task'] == slug and r['arm'] == a)}/" \
                         f"{sum(1 for r in rows if r['task'] == slug and r['arm'] == a)}"
        print(f"  {slug:<14} {cell('none'):>6} {cell('standards'):>6}")
    (OUT / "summary.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["fetch", "run", "report"])
    parser.add_argument("--reps", type=int, default=2)
    parser.add_argument("--tasks", default=",".join(TASKS))
    parser.add_argument("--arms", default=",".join(ARMS))
    parser.add_argument("--parallel", type=int, default=4)
    cfg = parser.parse_args(argv)
    if cfg.command == "fetch":
        fetch()
    elif cfg.command == "run":
        jobs = [(t, a, r) for r in range(1, cfg.reps + 1) for t in cfg.tasks.split(",") for a in cfg.arms.split(",")]
        with ThreadPoolExecutor(cfg.parallel) as pool:
            list(pool.map(lambda job: run_agent(*job), jobs))
        report()
    else:
        report()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
