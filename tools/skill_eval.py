#!/usr/bin/env python3
"""Evaluate whether the clean-code skill actually changes the code that gets written.

Most skill evaluation is subjective, which is why it rarely happens. This skill is a
lucky exception: it ships a linter, so generated code can be scored objectively by the
skill's own standard. If code written *with* the skill does not lint cleaner than code
written without it, the skill is not working — regardless of how good the prose reads.

That is the whole idea here: grade the output, not the document.

Three modes:

  run      Generate outputs by invoking `claude -p` (needs the Claude CLI on PATH).
  score    Lint whatever is already in a results directory and produce a scorecard.
  compare  Diff two scorecards (before/after a skill change) and report the delta.

Typical loop:
    python3 skill_eval.py run   --skill skills/clean-code --out results/baseline --no-skill
    python3 skill_eval.py run   --skill skills/clean-code --out results/with-skill
    python3 skill_eval.py compare results/baseline results/with-skill
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROMPTS = Path(__file__).resolve().parent / "evals" / "prompts.json"

SEVERITY_WEIGHT = {"high": 3, "medium": 2, "low": 1}


@dataclass
class CaseScore:
    case_id: str
    language: str
    files: int
    findings: int
    weighted: int
    by_code: dict[str, int]
    tokens: int = 0  # all input (incl. cache) + output; 0 when no usage recorded
    cost_usd: float = 0.0

    @property
    def missing(self) -> bool:
        """No output file. NOT the same as clean — a failed generation must never
        score as a success, or a broken run reads as a perfect one."""
        return self.files == 0

    @property
    def clean(self) -> bool:
        return self.files > 0 and self.findings == 0


# --------------------------------------------------------------------------------------
# Prompt handling
# --------------------------------------------------------------------------------------


def load_prompts(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["cases"]


def build_prompt(case: dict, skill_dir: Path | None) -> str:
    if skill_dir is None:
        return case["prompt"]
    return (
        f"Read the skill at {skill_dir}/SKILL.md and follow it, loading whichever "
        f"references it directs you to.\n\nTask: {case['prompt']}"
    )


# --------------------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------------------


def case_command(cli: str, case: dict, run: SimpleNamespace) -> list[str]:
    prompt = (
        build_prompt(case, run.skill_dir) + f"\n\nWrite the complete file. Output ONLY {case['language']} source code, "
        f"with no markdown fences and no commentary."
    )
    # Isolate both arms from the operator's own setup (hooks, plugins, skills, MCP,
    # project CLAUDE.md) so the only difference between runs is the skill itself.
    command = [
        cli,
        "-p",
        prompt,
        "--output-format",
        "json",
        "--setting-sources",
        "",
        "--strict-mcp-config",
        "--disable-slash-commands",
        "--allowedTools",
        "Read,Grep,Glob",
    ]
    if run.skill_dir:
        command += ["--add-dir", str(run.skill_dir)]
    if run.model:
        command += ["--model", run.model]
    return command


def save_reply(out_dir: Path, case: dict, reply: dict) -> None:
    (out_dir / f"{case['id']}.usage.json").write_text(
        json.dumps({key: reply.get(key) for key in ("usage", "total_cost_usd", "num_turns", "duration_ms")}, indent=2),
        encoding="utf-8",
    )
    body = reply["result"].strip()
    if body.startswith("```"):  # strip fences the model may add anyway
        body = "\n".join(body.split("\n")[1:-1])
    target = out_dir / f"{case['id']}.{case['ext']}"
    target.write_text(body, encoding="utf-8")
    print(f"  wrote {target}")


def run_case(cli: str, case: dict, run: SimpleNamespace) -> None:
    print(f"running {case['id']} ...", flush=True)
    try:
        done = subprocess.run(
            case_command(cli, case, run),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=run.timeout_s,
            cwd=run.out_dir,
        )
    except subprocess.TimeoutExpired:
        print(f"  timed out after {run.timeout_s}s", file=sys.stderr)
        return
    if done.returncode != 0:
        print(f"  failed: {done.stderr[:200]}", file=sys.stderr)
        return
    save_reply(run.out_dir, case, json.loads(done.stdout))


def run_cases(prompts: list[dict], run: SimpleNamespace) -> int:
    """run: out_dir, skill_dir (None for the baseline arm), model, timeout_s."""
    run.out_dir.mkdir(parents=True, exist_ok=True)
    cli = shutil.which("claude")

    if not cli:
        print("claude CLI not found on PATH; it is required to run evals.", file=sys.stderr)
        return 2

    for case in prompts:
        run_case(cli, case, run)

    (run.out_dir / "_meta.json").write_text(
        json.dumps(
            {
                "skill": str(run.skill_dir) if run.skill_dir else None,
                "model": run.model,
                "cases": [c["id"] for c in prompts],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return 0


# --------------------------------------------------------------------------------------
# score
# --------------------------------------------------------------------------------------


def lint(paths: list[Path], linter: Path) -> list[dict]:
    if not paths:
        return []
    command = [sys.executable, str(linter), *[str(p) for p in paths], "--json"]
    done = subprocess.run(command, capture_output=True, text=True)
    if not done.stdout.strip():
        return []
    try:
        return json.loads(done.stdout)["findings"]
    except (json.JSONDecodeError, KeyError):
        print(f"warning: could not parse linter output for {paths}", file=sys.stderr)
        return []


def score_dir(results_dir: Path, prompts: list[dict], linter: Path) -> list[CaseScore]:
    scores: list[CaseScore] = []
    for case in prompts:
        matches = sorted(results_dir.glob(f"{case['id']}.*"))
        matches = [m for m in matches if m.suffix != ".json"]
        findings = lint(matches, linter)
        by_code: dict[str, int] = {}
        weighted = 0
        for finding in findings:
            by_code[finding["code"]] = by_code.get(finding["code"], 0) + 1
            weighted += SEVERITY_WEIGHT.get(finding["severity"], 1)
        usage_file = results_dir / f"{case['id']}.usage.json"
        usage = json.loads(usage_file.read_text(encoding="utf-8")) if usage_file.exists() else {}
        counts = usage.get("usage") or {}
        scores.append(
            CaseScore(
                case_id=case["id"],
                language=case["language"],
                files=len(matches),
                findings=len(findings),
                weighted=weighted,
                by_code=by_code,
                tokens=sum(
                    counts.get(k, 0)
                    for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
                ),
                cost_usd=usage.get("total_cost_usd") or 0.0,
            )
        )
    return scores


def write_scorecard(results_dir: Path, scores: list[CaseScore]) -> Path:
    path = results_dir / "scorecard.json"
    scored = [s for s in scores if not s.missing]
    path.write_text(
        json.dumps(
            {
                "total_findings": sum(s.findings for s in scored),
                "total_weighted": sum(s.weighted for s in scored),
                "cases_clean": sum(1 for s in scored if s.clean),
                "cases_scored": len(scored),
                "cases_missing": [s.case_id for s in scores if s.missing],
                "cases_total": len(scores),
                "cases": [asdict(s) for s in scores],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def marker(score: CaseScore) -> str:
    if score.missing:
        return "  MISSING"
    return "" if score.clean else "  <-"


def report_top_codes(scores: list[CaseScore]) -> None:
    all_codes: dict[str, int] = {}
    for s in scores:
        for code, count in s.by_code.items():
            all_codes[code] = all_codes.get(code, 0) + count
    if all_codes:
        print(
            "  most common findings:",
            ", ".join(f"{c}×{n}" for c, n in sorted(all_codes.items(), key=lambda kv: -kv[1])[:6]),
        )


def report_scores(scores: list[CaseScore], label: str) -> None:
    print(f"\n{label}")
    print(f"  {'case':<26} {'files':>5} {'findings':>9} {'weighted':>9} {'tokens':>8}")
    for s in scores:
        print(f"  {s.case_id:<26} {s.files:>5} {s.findings:>9} {s.weighted:>9} {s.tokens:>8}{marker(s)}")
    clean = sum(1 for s in scores if s.clean)
    scored = [s for s in scores if not s.missing]
    missing = [s for s in scores if s.missing]
    print(f"  {'TOTAL':<26} {'':>5} {sum(s.findings for s in scores):>9} {sum(s.weighted for s in scores):>9}")
    print(f"  cases producing lint-clean code: {clean}/{len(scored)} scored")
    if missing:
        print(
            f"  !! {len(missing)} case(s) produced NO output and were excluded: {', '.join(s.case_id for s in missing)}"
        )
        print("     Comparisons across runs are only valid on cases present in both.")
    report_top_codes(scores)


# --------------------------------------------------------------------------------------
# compare
# --------------------------------------------------------------------------------------


def scored_cases(results_dir: Path) -> dict[str, dict]:
    card = json.loads((results_dir / "scorecard.json").read_text(encoding="utf-8"))
    return {c["case_id"]: c for c in card["cases"] if c["files"] > 0}


def sums(cases: dict[str, dict], shared: list[str], key: str) -> int:
    return sum(cases[c].get(key, 0) for c in shared)


def report_totals(before_cases: dict, after_cases: dict, shared: list[str]) -> None:
    clean = (
        sum(1 for c in shared if before_cases[c]["findings"] == 0),
        sum(1 for c in shared if after_cases[c]["findings"] == 0),
    )
    print(f"  {'metric':<34} {'before':>8} {'after':>8} {'delta':>8}")
    for label, key, lower_is_better in [
        ("total findings", "findings", True),
        ("weighted severity", "weighted", True),
        ("cases producing clean code", None, False),
        ("tokens (in + cache + out)", "tokens", True),
    ]:
        b, a = (sums(before_cases, shared, key), sums(after_cases, shared, key)) if key else clean
        delta = a - b
        good = (delta < 0) if lower_is_better else (delta > 0)
        flag = "  better" if delta and good else ("  WORSE" if delta else "")
        print(f"  {label:<34} {b:>8} {a:>8} {delta:>+8}{flag}")
    cost = (sums(before_cases, shared, "cost_usd"), sums(after_cases, shared, "cost_usd"))
    print(f"  {'cost (USD)':<34} {cost[0]:>8.2f} {cost[1]:>8.2f} {cost[1] - cost[0]:>+8.2f}")


def compare(before_dir: Path, after_dir: Path) -> int:
    print(f"\nCOMPARISON  {before_dir.name} -> {after_dir.name}\n")

    # Only cases scored in BOTH runs are comparable. Aggregates over different case
    # sets are meaningless, and would flatter whichever run produced fewer outputs.
    before_cases, after_cases = scored_cases(before_dir), scored_cases(after_dir)
    shared = sorted(set(before_cases) & set(after_cases))
    dropped = sorted((set(before_cases) | set(after_cases)) - set(shared))
    if dropped:
        print(f"  Excluded (not scored in both runs): {', '.join(dropped)}\n")
    if not shared:
        print("  No cases scored in both runs — nothing to compare.")
        return 2
    print(f"  Comparing {len(shared)} case(s) present in both runs.\n")
    report_totals(before_cases, after_cases, shared)

    regressions = [after_cases[c] for c in shared if after_cases[c]["weighted"] > before_cases[c]["weighted"]]
    if regressions:
        print("\n  REGRESSIONS (per-case, weighted severity increased):")
        for c in regressions:
            was = before_cases[c["case_id"]]["weighted"]
            print(f"    {c['case_id']:<26} {was} -> {c['weighted']}")
        print("\n  An aggregate improvement can hide a per-case regression. Read these.")
        return 1

    print("\n  No per-case regressions.")
    return 0


# --------------------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Generate outputs for each eval case")
    p_run.add_argument("--skill", default="skills/clean-code")
    p_run.add_argument("--out", required=True)
    p_run.add_argument("--prompts", default=str(DEFAULT_PROMPTS))
    p_run.add_argument("--model", default=None)
    p_run.add_argument("--timeout", type=int, default=300)
    p_run.add_argument("--no-skill", action="store_true", help="Baseline run: do not give the model the skill")

    p_score = sub.add_parser("score", help="Lint a results directory and write a scorecard")
    p_score.add_argument("results_dir")
    p_score.add_argument("--prompts", default=str(DEFAULT_PROMPTS))
    p_score.add_argument("--linter", default=None)

    p_cmp = sub.add_parser("compare", help="Compare two scorecards")
    p_cmp.add_argument("before_dir")
    p_cmp.add_argument("after_dir")
    return parser


def cmd_score(cfg: argparse.Namespace) -> int:
    prompts = load_prompts(Path(cfg.prompts))
    linter = Path(cfg.linter) if cfg.linter else Path(__file__).resolve().parent / "evals" / "lint.py"
    if not linter.exists():
        print(f"Linter not found: {linter}", file=sys.stderr)
        return 2
    results_dir = Path(cfg.results_dir)
    scores = score_dir(results_dir, prompts, linter)
    report_scores(scores, f"SCORECARD  {results_dir}")
    path = write_scorecard(results_dir, scores)
    print(f"\n  wrote {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
    cfg = build_parser().parse_args(argv)
    if cfg.command == "run":
        skill = None if cfg.no_skill else Path(cfg.skill).resolve()
        run = SimpleNamespace(out_dir=Path(cfg.out), skill_dir=skill, model=cfg.model, timeout_s=cfg.timeout)
        return run_cases(load_prompts(Path(cfg.prompts)), run)
    if cfg.command == "score":
        return cmd_score(cfg)
    return compare(Path(cfg.before_dir), Path(cfg.after_dir))


if __name__ == "__main__":
    raise SystemExit(main())
