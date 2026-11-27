"""Research-backed code-quality metrics for a Python file. Eval tooling only (deps: `uv sync`).

  maintainability_index  Oman & Hagemeister 1992 (radon's variant, 0-100, higher is better).
                         Its comment term rewards comment density — criticized by Heitlager,
                         Kuipers & Visser 2007 — so a skill that deletes redundant comments lowers it.
  mi_structural          the same formula with the comment term removed: the primary MI here
  comment_ratio          (comment + docstring lines) / sloc
  cc_max / cc_mean       McCabe 1976 cyclomatic complexity per function
  cognitive_max / _total Campbell 2018 (SonarSource); validated vs. human understandability,
                         Muñoz Barón, Wyrich & Wagner, ESEM 2020
  halstead_volume        Halstead 1977
  sloc                   source lines of code (no blanks/comments)
  runtime_ms             median of 20 in-process test-suite runs (startup excluded)
  ruff_violations        fixed, isolated ruff rule set (pyflakes, pycodestyle, bugbear, simplify,
                         pylint-refactor, naming, return) — repo config never leaks in
"""
from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

from cognitive_complexity.api import get_cognitive_complexity
from radon.complexity import cc_visit
from radon.metrics import h_visit, mi_compute, mi_parameters, mi_visit
from radon.raw import analyze

RUFF_RULES = "E,F,W,B,SIM,C4,PLR,N,RET"


def ruff_violations(path: Path) -> int:
    ruff = Path(sys.executable).parent / "ruff"
    done = subprocess.run([str(ruff), "check", "--isolated", "--no-cache", "--select", RUFF_RULES,
                           "--output-format", "json", str(path)], capture_output=True, text=True)
    return len(json.loads(done.stdout or "[]"))


def measure(path: Path) -> dict:
    src = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return {"parse_error": True}
    funcs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    cc = [b.complexity for b in cc_visit(src)] or [0]
    cog = [get_cognitive_complexity(f) for f in funcs] or [0]
    raw = analyze(src)
    return {
        "sloc": raw.sloc,
        "maintainability_index": round(mi_visit(src, multi=True), 1),
        "mi_structural": round(mi_compute(*mi_parameters(src, count_multi=True)[:3], 0), 1),
        "comment_ratio": round((raw.comments + raw.multi) / max(raw.sloc, 1), 3),
        "cc_max": max(cc),
        "cc_mean": round(sum(cc) / len(cc), 2),
        "cognitive_max": max(cog),
        "cognitive_total": sum(cog),
        "halstead_volume": round(h_visit(src).total.volume, 1),
        "ruff_violations": ruff_violations(path),
    }


RUNTIME_SNIPPET = """
import os, statistics, sys, time, unittest
times = []
for _ in range(20):
    suite = unittest.defaultTestLoader.loadTestsFromName(sys.argv[1])  # a suite empties itself after a run
    start = time.perf_counter()
    unittest.TextTestRunner(stream=open(os.devnull, "w")).run(suite)
    times.append(time.perf_counter() - start)
print(statistics.median(times) * 1000)
"""


def runtime_ms(work: Path, test_module: str, env: dict | None = None) -> float | None:
    done = subprocess.run([sys.executable, "-c", RUNTIME_SNIPPET, test_module], cwd=work, env=env,
                          capture_output=True, text=True, timeout=600)
    try:
        return round(float(done.stdout.strip().splitlines()[-1]), 3)
    except (ValueError, IndexError):
        return None


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    for arg in sys.argv[1:]:
        print(arg, json.dumps(measure(Path(arg))))
