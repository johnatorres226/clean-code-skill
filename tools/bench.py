#!/usr/bin/env python3
"""Task benchmark: does an agent with clean-code-standards produce better, cheaper-to-change code?

Aider-Polyglot style: Exercism exercises scored by their own unit tests, run by `claude -p` as a
real agent inside a git repo. Two arms per variant:

  none       plain repo on main, no plugin
  standards  repo adopted via setup-standards (standards.toml, hooks, CLAUDE.md block) + plugin

Three measurements:

  run       phase 1 — solve the task and commit. Tests, research-backed quality metrics
            (tools/evals/quality.py), runtime, commit compliance, tokens, cost, turns.
  followup  phase 2 — change cost. A NEUTRAL agent (no plugin, identical in both arms) applies
            FOLLOWUP.md to each arm's phase-1 code; hidden follow-up tests grade it. Cleaner code
            should be cheaper and safer to change — the claim clean code actually makes.
  judge     blind pairwise review by a different model, both presentation orders; only
            order-consistent verdicts count (position-bias control, Zheng et al. 2023).

  python tools/bench.py run|followup|judge|report --variant NAME [--reps 2] [--tasks a,b]
         [--plugin-dir DIR] [--claude-md FILE] [--parallel 4]

Needs tools/evals/requirements.txt. `report` writes results/bench/<variant>/summary.json.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import stat
import statistics
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "tools" / "evals" / "benchmarks"
TEMPLATES = ROOT / "skills" / "setup-standards" / "templates"
TASKS = ["ledger", "markdown", "tree-building", "bowling", "forth", "wordy", "poker", "book-store"]
ARMS = ["none", "standards"]
GH = shutil.which("gh") or r"C:\Program Files\GitHub CLI\gh.exe"
PY_DIR = str(Path(sys.executable).parent)
JUDGE_MODEL = "claude-sonnet-5-5"  # a different model from the agent under test
DEFAULT_CLAUDE_MD = """## Standards

Rules: `standards.toml`. Hooks enforce them — fix failures, never bypass (`--no-verify`).
- Branch from `dev` as `<type>/<slug>`; never commit or push to `main`/`dev`.
- One concern per commit, Conventional Commit subject, within the size limits.
- Done = `python .githooks/standards.py check` green + evidence. Skill: `verify`.
- Writing or reviewing code: skill `clean-code`. Committing: skill `ship`.
"""

sys.path.insert(0, str(TEMPLATES / ".githooks"))
sys.path.insert(0, str(ROOT / "tools" / "evals"))
import quality  # noqa: E402
from judge import pairwise  # noqa: E402
import standards  # noqa: E402

STANDARDS_CFG = standards.tomllib.loads((TEMPLATES / "standards.toml").read_text(encoding="utf-8"))
SEVERITY = {"high": 3, "medium": 2, "low": 1}


class Cfg:  # set once from the CLI
    variant = "current"
    plugin_dir = ROOT
    claude_md = DEFAULT_CLAUDE_MD

    @classmethod
    def out(cls) -> Path:
        return ROOT / "results" / "bench" / cls.variant

    @classmethod
    def work(cls) -> Path:
        # Outside the plugin dir (files under --plugin-dir are edit-protected) and resolved (a
        # Windows 8.3 short path like JOHTOR~1 is treated as sensitive and blocks edits).
        return Path(tempfile.gettempdir()).resolve() / "ccs-bench" / cls.variant


def module(slug: str) -> str:
    return slug.replace("-", "_")


def sh(cwd: Path, *args: str, env: dict | None = None, timeout: int | None = None):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                          env=env, timeout=timeout)


def py_env() -> dict:
    return {**os.environ, "PATH": PY_DIR + os.pathsep + os.environ["PATH"]}


def fresh_dir(path: Path) -> None:
    # git marks object files read-only; Windows rmtree needs the flag cleared to delete them
    if path.exists():
        shutil.rmtree(path, onexc=lambda f, p, _: (os.chmod(p, stat.S_IWRITE), f(p)))
    path.mkdir(parents=True)


def git_init(work: Path) -> None:
    sh(work, "git", "init", "-q", "-b", "main")
    sh(work, "git", "config", "user.email", "bench@example.com")
    sh(work, "git", "config", "user.name", "bench")


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


# --------------------------------------------------------------------------------------
# Agent invocation and shared scoring
# --------------------------------------------------------------------------------------

def run_claude(cwd: Path, text: str, plugin: bool, model: str | None = None,
               tools: str = "Read,Write,Edit,Bash,PowerShell,Glob,Grep,Skill") -> list[dict]:
    cmd = [shutil.which("claude") or "claude", "-p", text, "--output-format", "stream-json",
           "--verbose", "--setting-sources", "project", "--strict-mcp-config", "--allowedTools", tools]
    if plugin:
        cmd += ["--plugin-dir", str(Cfg.plugin_dir)]
    if model:
        cmd += ["--model", model]
    done = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                          env=py_env(), timeout=1800)
    return [json.loads(line) for line in done.stdout.splitlines() if line.startswith("{")]


def usage(events: list[dict]) -> dict:
    final = next((e for e in reversed(events) if e.get("type") == "result"), {})
    u = final.get("usage", {})
    uses = [c for e in events if e.get("type") == "assistant"
            for c in e.get("message", {}).get("content", []) if c.get("type") == "tool_use"]
    return {
        "valid": not final.get("is_error", True),  # usage-limit / API errors never count
        "turns": final.get("num_turns", 0),
        "tokens": sum(u.get(k, 0) for k in ("input_tokens", "output_tokens",
                      "cache_creation_input_tokens", "cache_read_input_tokens")),
        "new_tokens": sum(u.get(k, 0) for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens")),
        "cost_usd": final.get("total_cost_usd") or 0.0,
        "duration_s": round((final.get("duration_ms") or 0) / 1000),
        "tool_calls": len(uses),
        "skills_invoked": [c.get("input", {}).get("skill") for c in uses if c.get("name") == "Skill"],
        "result_text": str(final.get("result", "")),  # untruncated: the judge parses JSON from it
    }


def tests_pass(work: Path, test_module: str) -> bool:
    return sh(work, sys.executable, "-m", "unittest", "-q", test_module, env=py_env(), timeout=300).returncode == 0


def code_metrics(work: Path, slug: str) -> dict:
    path = work / f"{module(slug)}.py"
    lint = sh(work, sys.executable, str(ROOT / "tools" / "evals" / "lint.py"), path.name, "--json")
    findings = json.loads(lint.stdout)["findings"] if lint.stdout.strip() else []
    return {"lint_findings": len(findings),
            "lint_weighted": sum(SEVERITY.get(f["severity"], 1) for f in findings),
            **quality.measure(path)}


# --------------------------------------------------------------------------------------
# Phase 1: solve and commit
# --------------------------------------------------------------------------------------

def prepare(slug: str, arm: str, work: Path) -> None:
    fresh_dir(work)
    for f in (TASKS_DIR / slug).iterdir():
        if f.name.endswith(".py") and not f.name.startswith("followup"):
            shutil.copy(f, work / f.name)
    docs = "".join((TASKS_DIR / slug / n).read_text(encoding="utf-8")
                   for n in ("instructions.md", "instructions.append.md") if (TASKS_DIR / slug / n).exists())
    (work / "INSTRUCTIONS.md").write_text(docs, encoding="utf-8")
    git_init(work)
    if arm == "standards":
        shutil.copytree(TEMPLATES / ".githooks", work / ".githooks")
        toml = (TEMPLATES / "standards.toml").read_text(encoding="utf-8")
        (work / "standards.toml").write_text(
            toml.replace('test      = ""', 'test      = "python -m unittest discover -q -p *_test.py"'),
            encoding="utf-8")
        (work / "CLAUDE.md").write_text(Cfg.claude_md, encoding="utf-8")
    sh(work, "git", "add", "-A")
    sh(work, "git", "commit", "-q", "-m", "chore: init")
    sh(work, "git", "tag", "bench-init")
    if arm == "standards":
        sh(work, "git", "branch", "dev")
        sh(work, "git", "switch", "-q", "dev")
        sh(work, "git", "config", "core.hooksPath", ".githooks")


def git_metrics(work: Path, slug: str) -> dict:
    shas = sh(work, "git", "rev-list", "--no-merges", "--all", "^bench-init").stdout.split()
    problems = [standards.message_problem(sh(work, "git", "log", "-1", "--format=%B", s).stdout, STANDARDS_CFG)
                or standards.size_problem(sh(work, "git", "show", "--numstat", "--format=", s).stdout, STANDARDS_CFG)
                for s in shas]
    protected = sum(1 for b in ("main", "dev")
                    if sh(work, "git", "rev-list", "--count", f"bench-init..{b}").stdout.strip() not in ("", "0"))
    return {"commits": len(shas), "commits_compliant": bool(shas) and not any(problems),
            "commit_problems": [p for p in problems if p], "protected_branches_written": protected,
            "uncommitted_solution": bool(sh(work, "git", "status", "--porcelain", "--",
                                            f"{module(slug)}.py").stdout.strip())}


def phase1(slug: str, arm: str, rep: int) -> dict:
    out = Cfg.out() / arm / f"{slug}-r{rep}.json"
    if out.exists():  # resume: never re-run (and re-pay for) a finished run
        return json.loads(out.read_text(encoding="utf-8"))
    work = Cfg.work() / arm / f"{slug}-r{rep}"
    prepare(slug, arm, work)
    events = run_claude(work, f"Complete the task described in INSTRUCTIONS.md by editing {module(slug)}.py. "
                              f"The tests are in {module(slug)}_test.py (run with `python -m unittest`); do not "
                              f"edit them. When you are done, commit your work to git.", plugin=arm == "standards")
    test_file = f"{module(slug)}_test.py"
    shutil.copy(TASKS_DIR / slug / test_file, work / test_file)  # anti-tamper before grading
    result = {"task": slug, "arm": arm, "rep": rep, **usage(events),
              "tests_pass": tests_pass(work, test_file[:-3]),
              "runtime_ms": quality.runtime_ms(work, test_file[:-3], py_env()),
              **code_metrics(work, slug), **git_metrics(work, slug)}
    save(out, result, events)
    print(f"p1 {arm:<9} {slug:<14} r{rep} pass={result['tests_pass']} MI={result.get('maintainability_index')} "
          f"cog={result.get('cognitive_total')} ${result['cost_usd']:.2f}", flush=True)
    return result


def save(out: Path, result: dict, events: list[dict]) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".stream.jsonl").write_text("\n".join(json.dumps(e) for e in events), encoding="utf-8")
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")


# --------------------------------------------------------------------------------------
# Phase 2: change cost, by a neutral agent
# --------------------------------------------------------------------------------------

def phase2(slug: str, arm: str, rep: int) -> dict | None:
    out = Cfg.out() / "followup" / arm / f"{slug}-r{rep}.json"
    if out.exists():
        return json.loads(out.read_text(encoding="utf-8"))
    src = Cfg.work() / arm / f"{slug}-r{rep}"
    first = Cfg.out() / arm / f"{slug}-r{rep}.json"
    if not first.exists() or not json.loads(first.read_text(encoding="utf-8")).get("tests_pass"):
        return None  # only code that solved phase 1 is a fair starting point
    m = module(slug)
    work = Cfg.work() / "followup" / arm / f"{slug}-r{rep}"
    fresh_dir(work)
    shutil.copy(src / f"{m}.py", work / f"{m}.py")
    shutil.copy(TASKS_DIR / slug / f"{m}_test.py", work / f"{m}_test.py")
    shutil.copy(TASKS_DIR / slug / "FOLLOWUP.md", work / "FOLLOWUP.md")
    git_init(work)
    sh(work, "git", "add", "-A")
    sh(work, "git", "commit", "-q", "-m", "start")
    events = run_claude(work, f"Implement the requirement in FOLLOWUP.md by changing {m}.py. Keep the existing "
                              f"tests in {m}_test.py passing and do not edit them.", plugin=False)
    shutil.copy(TASKS_DIR / slug / f"{m}_test.py", work / f"{m}_test.py")
    shutil.copy(TASKS_DIR / slug / "followup_test.py", work / "followup_test.py")
    added = deleted = 0
    for row in sh(work, "git", "diff", "--numstat", "HEAD", "--", f"{m}.py").stdout.splitlines():
        a, d, _ = row.split("\t", 2)
        added, deleted = added + int(a), deleted + int(d)
    result = {"task": slug, "arm": arm, "rep": rep, **usage(events),
              "followup_pass": tests_pass(work, "followup_test"),
              "original_still_pass": tests_pass(work, f"{m}_test"),
              "diff_added": added, "diff_deleted": deleted,
              **{f"after_{k}": v for k, v in code_metrics(work, slug).items()}}
    save(out, result, events)
    print(f"p2 {arm:<9} {slug:<14} r{rep} followup={result['followup_pass']} kept={result['original_still_pass']} "
          f"diff=+{added}/-{deleted} ${result['cost_usd']:.2f}", flush=True)
    return result


# --------------------------------------------------------------------------------------
# Blind pairwise judge
# --------------------------------------------------------------------------------------

def ask_judge(prompt: str) -> tuple[str, float]:
    with tempfile.TemporaryDirectory() as tmp:
        result = usage(run_claude(Path(tmp), prompt, plugin=False, model=JUDGE_MODEL, tools=""))
    return result["result_text"], result["cost_usd"]


def judge(slug: str, rep: int) -> dict | None:
    out = Cfg.out() / "judge" / f"{slug}-r{rep}.json"
    if out.exists():
        return json.loads(out.read_text(encoding="utf-8"))
    m = module(slug)
    paths = {arm: Cfg.work() / arm / f"{slug}-r{rep}" / f"{m}.py" for arm in ARMS}
    runs = {arm: Cfg.out() / arm / f"{slug}-r{rep}.json" for arm in ARMS}
    if not all(p.exists() for p in runs.values()) or \
            not all(json.loads(p.read_text(encoding="utf-8")).get("tests_pass") for p in runs.values()):
        return None
    task = (TASKS_DIR / slug / "instructions.md").read_text(encoding="utf-8")[:2500]
    code = {arm: p.read_text(encoding="utf-8") for arm, p in paths.items()}
    result = {"task": slug, "rep": rep, **pairwise(ask_judge, task, code["none"], code["standards"])}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"judge {slug:<14} r{rep} {result['order1']}/{result['order2']} -> {result['winner']}", flush=True)
    return result


# --------------------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------------------

def load(pattern: str) -> list[dict]:
    rows = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(Cfg.out().glob(pattern))]
    return [r for r in rows if r.get("valid", True)]


def mean(rows: list[dict], arm: str | None, key: str) -> float | None:
    vals = [float(r[key]) for r in rows if (arm is None or r["arm"] == arm) and r.get(key) is not None]
    return round(statistics.mean(vals), 3) if vals else None


def paired_p(rows: list[dict], key: str) -> float | None:
    """Sign-flip permutation test on per-task mean differences (standards - none)."""
    diffs = []
    for slug in TASKS:
        a = [r[key] for r in rows if r["task"] == slug and r["arm"] == "none" and r.get(key) is not None]
        b = [r[key] for r in rows if r["task"] == slug and r["arm"] == "standards" and r.get(key) is not None]
        if a and b:
            diffs.append(statistics.mean(b) - statistics.mean(a))
    if not diffs or not any(diffs):
        return None
    rng, observed = random.Random(0), abs(sum(diffs))
    return round(sum(abs(sum(d * rng.choice((-1, 1)) for d in diffs)) >= observed
                     for _ in range(20000)) / 20000, 4)


P1_KEYS = [("tests_pass", "tests pass rate"), ("commits_compliant", "commits compliant"),
           ("protected_branches_written", "wrote to main/dev"), ("lint_weighted", "lint severity"),
           ("mi_structural", "MI structural ↑"), ("maintainability_index", "MI raw (rewards comments) ↑"),
           ("comment_ratio", "comment ratio"), ("cognitive_total", "cognitive complexity"),
           ("cc_max", "max cyclomatic complexity"), ("halstead_volume", "halstead volume"),
           ("ruff_violations", "ruff violations"), ("sloc", "source lines"), ("runtime_ms", "test runtime ms"),
           ("turns", "turns"), ("new_tokens", "new tokens"), ("cost_usd", "cost USD")]
P2_KEYS = [("followup_pass", "follow-up pass rate ↑"), ("original_still_pass", "no regression ↑"),
           ("diff_added", "lines added"), ("diff_deleted", "lines deleted"), ("turns", "turns"),
           ("new_tokens", "new tokens"), ("cost_usd", "cost USD"),
           ("after_mi_structural", "MI structural after ↑"), ("after_cognitive_total", "cognitive after")]


def table(title: str, rows: list[dict], keys: list[tuple[str, str]]) -> dict:
    print(f"\n{title} (n = {sum(r['arm'] == 'none' for r in rows)} / {sum(r['arm'] == 'standards' for r in rows)})")
    print(f"  {'metric':<28}{'none':>11}{'standards':>11}{'p':>8}")
    summary = {}
    for key, label in keys:
        a, b, p = mean(rows, "none", key), mean(rows, "standards", key), paired_p(rows, key)
        summary[key] = {"none": a, "standards": b, "p": p}
        fmt = lambda v: "—" if v is None else f"{v:,.2f}"
        print(f"  {label:<28}{fmt(a):>11}{fmt(b):>11}{'' if p is None else f'{p:.3f}':>8}")
    return summary


def report() -> None:
    p1, p2, judged = load("*/*-r*.json"), load("followup/*/*.json"), load("judge/*.json")
    p1 = [r for r in p1 if r.get("arm") in ARMS]
    summary = {"variant": Cfg.variant, "phase1": table("PHASE 1 — solve", p1, P1_KEYS)}
    if p2:
        summary["phase2"] = table("PHASE 2 — change cost (neutral agent)", p2, P2_KEYS)
    if judged:
        wins = {w: sum(j["winner"] == w for j in judged) for w in ("standards", "none", "tie")}
        print(f"\nBLIND JUDGE ({JUDGE_MODEL}, order-consistent only): {wins} of {len(judged)}; "
              f"mean score none {mean(judged, None, 'score_none')} vs standards {mean(judged, None, 'score_standards')}")
        summary["judge"] = {"wins": wins, "n": len(judged), "score_none": mean(judged, None, "score_none"),
                            "score_standards": mean(judged, None, "score_standards")}
    (Cfg.out() / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["fetch", "run", "followup", "judge", "all", "report"])
    parser.add_argument("--variant", default="current")
    parser.add_argument("--reps", type=int, default=2)
    parser.add_argument("--tasks", default=",".join(TASKS))
    parser.add_argument("--arms", default=",".join(ARMS))
    parser.add_argument("--parallel", type=int, default=4)
    parser.add_argument("--plugin-dir", default=str(ROOT), help="skill version under test (e.g. a worktree)")
    parser.add_argument("--claude-md", default=None, help="file replacing the always-loaded CLAUDE.md block")
    cfg = parser.parse_args(argv)
    Cfg.variant, Cfg.plugin_dir = cfg.variant, Path(cfg.plugin_dir).resolve()
    if cfg.claude_md:
        Cfg.claude_md = Path(cfg.claude_md).read_text(encoding="utf-8")
    tasks, arms, reps = cfg.tasks.split(","), cfg.arms.split(","), range(1, cfg.reps + 1)
    jobs = {
        "run": [(phase1, (t, a, r)) for r in reps for t in tasks for a in arms],
        "followup": [(phase2, (t, a, r)) for r in reps for t in tasks for a in arms],
        "judge": [(judge, (t, r)) for r in reps for t in tasks],
    }
    if cfg.command == "fetch":
        fetch()
        return 0
    for stage in (["run", "followup", "judge"] if cfg.command == "all" else
                  [cfg.command] if cfg.command in jobs else []):
        with ThreadPoolExecutor(cfg.parallel) as pool:
            list(pool.map(lambda job: job[0](*job[1]), jobs[stage]))
    report()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
