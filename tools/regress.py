#!/usr/bin/env python3
"""Regression gate: the skills must not get worse in quality or cost than the committed baseline.

  static          free, deterministic, runs in CI on every PR: per-skill token cost (SKILL.md and
                  references), NVIDIA SkillEvaluator quality score, enforcement self-check.
  bench VARIANT   agent tier, run on demand before a release: compares
                  results/bench/VARIANT/summary.json (tools/bench.py report) with the baseline.
  baseline [VARIANT]
                  rewrite tools/evals/baseline.json from the current tree (and VARIANT's summary).
                  Updating the baseline is a reviewed change in its own commit, never a way to
                  make a failing gate pass.

Exit 1 on any regression beyond tolerance. Tolerances live next to the metrics they guard.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / "tools" / "evals" / "baseline.json"
sys.path.insert(0, str(ROOT / "tools"))
from skill_audit import measure  # noqa: E402

# (metric, direction, tolerance, kind). direction "max": higher is worse; "min": lower is worse.
# kind "rel": fraction of the baseline (absorbs run-to-run noise at n=16 per arm); "abs": units.
STATIC_RULES = [("skill_tokens", "max", 0.10, "rel"), ("reference_tokens", "max", 0.10, "rel"),
                ("skillevaluator_score", "min", 2.0, "abs")]
BENCH_RULES = [
    ("phase1.tests_pass", "min", 0.0, "abs"), ("phase1.commits_compliant", "min", 0.05, "abs"),
    ("phase1.protected_branches_written", "max", 0.0, "abs"),
    ("phase1.lint_weighted", "max", 0.25, "rel"), ("phase1.cognitive_total", "max", 0.25, "rel"),
    ("phase1.ruff_violations", "max", 0.50, "rel"), ("phase1.cost_usd", "max", 0.20, "rel"),
    ("phase2.followup_pass", "min", 0.10, "abs"), ("phase2.original_still_pass", "min", 0.05, "abs"),
    ("phase2.cost_usd", "max", 0.20, "rel"),
]


def skillevaluator_score(skill: Path) -> float | None:
    exe = shutil.which("skillevaluator")
    if not exe:
        return None
    out = ROOT / "results" / "skilleval" / skill.name
    subprocess.run([exe, "quality-check", str(skill), "-r", "json", "-o", str(out)], capture_output=True)
    report = out / "skillevaluator-quality.json"
    if not report.exists():
        return None
    return json.loads(report.read_text(encoding="utf-8"))["quality_summary"][0]["overall_score"]


def static_metrics() -> dict:
    metrics = {}
    for skill in sorted((ROOT / "skills").iterdir()):
        refs = list((skill / "references").glob("*.md")) if (skill / "references").exists() else []
        metrics[skill.name] = {
            "skill_tokens": measure(skill / "SKILL.md", skill).tokens,
            "reference_tokens": sum(measure(r, skill).tokens for r in refs),
            "skillevaluator_score": skillevaluator_score(skill),
        }
    return metrics


def worse(current: float, base: float, rule: tuple) -> bool:
    """rule = (direction, tolerance, kind): "max" or "min", and "rel" or "abs" slack."""
    direction, tolerance, kind = rule
    slack = tolerance * abs(base) if kind == "rel" else tolerance
    return current > base + slack if direction == "max" else current < base - slack


def compare(current: dict, base: dict, rules: list) -> list[tuple]:
    """(key, baseline, current, regressed) per rule; regressed is None when a value is missing."""
    rows = []
    for key, *rule in rules:
        cur, ref = current.get(key), base.get(key)
        rows.append((key, ref, cur, None if cur is None or ref is None else worse(cur, ref, rule)))
    return rows


def report(label: str, rows: list[tuple]) -> list[str]:
    failures = []
    for key, ref, cur, bad in rows:
        if bad is None:
            print(f"  {label:<18} {key:<34} skipped (no {'current' if cur is None else 'baseline'} value)")
            continue
        print(f"  {label:<18} {key:<34} {ref:>10.3f} -> {cur:>10.3f}  {'REGRESSED' if bad else 'ok'}")
        if bad:
            failures.append(f"{label}: {key} {ref:.3f} -> {cur:.3f}")
    return failures


def flatten_bench(summary: dict) -> dict:
    """{'phase1': {'cost_usd': {'standards': x}}} -> {'phase1.cost_usd': x} (standards arm)."""
    flat = {f"{phase}.{key}": arms.get("standards")
            for phase in ("phase1", "phase2") for key, arms in summary.get(phase, {}).items()}
    flat["models"] = summary.get("models")
    return flat


def self_check() -> list[str]:
    done = subprocess.run([sys.executable, str(ROOT / "tests" / "test_standards.py")], capture_output=True, text=True)
    return [] if done.returncode == 0 else ["enforcement self-check failed:\n" + done.stdout + done.stderr]


def bench_summary(variant: str) -> dict:
    summary = ROOT / "results" / "bench" / variant / "summary.json"
    return flatten_bench(json.loads(summary.read_text(encoding="utf-8")))


def write_baseline(base: dict, variant: str | None) -> int:
    base["static"] = static_metrics()
    if variant:
        base["bench"] = {"variant": variant, **bench_summary(variant)}
    BASELINE.write_text(json.dumps(base, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {BASELINE.relative_to(ROOT)}")
    return 0


def static_failures(base: dict) -> list[str]:
    failures = self_check()
    for skill, metrics in static_metrics().items():
        failures += report(skill, compare(metrics, base.get("static", {}).get(skill, {}), STATIC_RULES))
    return failures


def bench_failures(base: dict, variant: str) -> list[str]:
    current, baseline = bench_summary(variant), base.get("bench", {})
    failures = []
    if current["models"] != baseline.get("models"):
        failures.append(f"model mismatch: baseline {baseline.get('models')} vs {current['models']} "
                        "(a cross-model comparison is not a regression test)")
    return failures + report(f"bench {variant}", compare(current, baseline, BENCH_RULES))


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    base = json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else {}
    command = argv[0] if argv else "static"
    if command == "baseline":
        return write_baseline(base, argv[1] if len(argv) > 1 else None)
    failures = static_failures(base) if command == "static" else []
    if command == "bench":
        failures = bench_failures(base, argv[1])
    print("\n" + ("REGRESSIONS:\n  " + "\n  ".join(failures) if failures else "no regressions"))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
