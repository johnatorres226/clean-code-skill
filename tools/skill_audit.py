#!/usr/bin/env python3
"""Audit a skill's context economy and structural integrity.

Skills fail quietly in two ways: they bloat the always-loaded tier, and they rot
(broken reference links, stale routing tables, orphaned files). Neither shows up
when you read the skill — both show up in every conversation that loads it.

This measures both.

Usage:
    python3 skill_audit.py skills/clean-code
    python3 skill_audit.py skills/clean-code --json
    python3 skill_audit.py skills/clean-code --budget 3000 --fail-on-violation
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

# Rough but stable: English prose with code blocks runs ~1.33 tokens per word.
TOKENS_PER_WORD = 4 / 3

DEFAULT_SKILL_BUDGET = 3000  # always-loaded tier (SKILL.md body)
DEFAULT_REFERENCE_BUDGET = 3500  # any single reference file
MIN_DESCRIPTION_WORDS = 25  # fewer, and the description cannot name its trigger contexts
MIN_SUMMARY_WORDS = 80  # a shorter section is a pointer, not a summary that shadows
MIN_DUPLICATE_WORDS = 25  # shorter repeated paragraphs are boilerplate, not drift risk
REF_LINK = re.compile(r"(?<![\w./-])references/([A-Za-z0-9._\-]+\.md)")  # own refs, not ../other-skill/
SCRIPT_LINK = re.compile(r"scripts/([A-Za-z0-9._\-]+\.(?:py|sh))")


@dataclass
class FileStat:
    path: str
    lines: int
    words: int
    tokens: int


@dataclass
class Issue:
    severity: str  # high | medium | low
    kind: str
    message: str
    hint: str = ""


@dataclass
class AuditResult:
    skill_name: str
    skill_md: FileStat | None = None
    references: list[FileStat] = field(default_factory=list)
    scripts: list[FileStat] = field(default_factory=list)
    assets: list[FileStat] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)

    @property
    def reference_total(self) -> int:
        return sum(r.tokens for r in self.references)


def load_config(skill_dir: Path) -> dict:
    """Read .skill-audit.json: declared, justified exceptions to the default rules.

    Exceptions live in the skill and are reviewable in the diff, rather than being
    silently absorbed by loosening a global threshold. A check that fires on things
    the author already decided about is a check that gets ignored.
    """
    config_path = skill_dir / ".skill-audit.json"
    if not config_path.exists():
        return {}
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        print(f"warning: could not parse {config_path}: {err}", file=sys.stderr)
        return {}


def measure(path: Path, root: Path) -> FileStat:
    text = path.read_text(encoding="utf-8", errors="replace")
    words = len(text.split())
    return FileStat(
        path=str(path.relative_to(root)),
        lines=len(text.splitlines()),
        words=words,
        tokens=int(words * TOKENS_PER_WORD),
    )


# --------------------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------------------


def check_frontmatter(skill_md: Path, result: AuditResult) -> None:
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        result.issues.append(
            Issue(
                "high",
                "frontmatter",
                "SKILL.md has no YAML frontmatter.",
                "Add a --- block with `name` and `description`.",
            )
        )
        return
    end = text.find("---", 3)
    block = text[3:end]
    for required in ("name:", "description:"):
        if required not in block:
            result.issues.append(Issue("high", "frontmatter", f"Frontmatter missing `{required.rstrip(':')}`.", ""))
    match = re.search(r"description:\s*(.+?)(?=\n[a-z_]+:|\Z)", block, re.S)
    if match:
        words = len(match.group(1).split())
        if words < MIN_DESCRIPTION_WORDS:
            result.issues.append(
                Issue(
                    "medium",
                    "frontmatter",
                    f"Description is only {words} words.",
                    "Descriptions are the sole trigger signal — name concrete "
                    "contexts and phrases, not just what the skill does.",
                )
            )


def links(skill_dir: Path) -> list[tuple[Path, str, str]]:
    """(file, folder, target) for every references/ and scripts/ link, in file order."""
    found = []
    for md in sorted(skill_dir.rglob("*.md")):
        text = md.read_text(encoding="utf-8", errors="replace")
        found += [(md, "references", target) for target in REF_LINK.findall(text)]
        found += [(md, "scripts", target) for target in SCRIPT_LINK.findall(text)]
    return found


def check_links(skill_dir: Path, result: AuditResult) -> None:
    """Every referenced file must exist, and every reference must be reachable."""
    found = links(skill_dir)
    for md, folder, target in found:
        if not (skill_dir / folder / target).exists():
            result.issues.append(
                Issue(
                    "high",
                    "broken-link",
                    f"{md.relative_to(skill_dir)} points at missing {folder}/{target}.",
                    "Fix the path or restore the file." if folder == "references" else "",
                )
            )
    linked = {target for _, folder, target in found if folder == "references"}
    for ref in sorted((skill_dir / "references").glob("*.md")):
        if ref.name not in linked:
            result.issues.append(
                Issue(
                    "medium",
                    "orphan",
                    f"references/{ref.name} is never linked from anywhere.",
                    "Unreachable references are pure weight — link it or delete it.",
                )
            )


def check_routing_table(skill_md: Path, skill_dir: Path, result: AuditResult) -> None:
    """The routing table must cover every reference, or triage silently misses files."""
    text = skill_md.read_text(encoding="utf-8")
    routed = set(re.findall(r"\|[^|\n]*`references/([A-Za-z0-9._\-]+\.md)`", text))
    ref_dir = skill_dir / "references"
    if not ref_dir.exists():
        return
    for ref in sorted(ref_dir.glob("*.md")):
        if ref.name not in routed and ref.name not in text:
            result.issues.append(
                Issue(
                    "medium",
                    "unrouted",
                    f"references/{ref.name} is absent from the routing table.",
                    "If it is not in the table, triage will not find it.",
                )
            )


def check_budget(result: AuditResult, config: dict) -> None:
    skill_budget, ref_budget = config["skill_md_budget"], config["reference_budget"]
    partial_access = set(config.get("partial_access_files", []))

    if result.skill_md and result.skill_md.tokens > skill_budget:
        result.issues.append(
            Issue(
                "high",
                "budget",
                f"SKILL.md is {result.skill_md.tokens} tokens (budget {skill_budget}).",
                "This loads on every trigger. Move detail into a reference behind an escalation trigger.",
            )
        )
    for ref in result.references:
        name = Path(ref.path).name
        if ref.tokens <= ref_budget:
            continue
        if name in partial_access:
            # Declared as index+grep access — it is never loaded whole, so its
            # total size is not what a task actually pays.
            continue
        result.issues.append(
            Issue(
                "medium",
                "budget",
                f"{ref.path} is {ref.tokens} tokens (budget {ref_budget}).",
                "Split it, or document a partial-access pattern (index + grep) in SKILL.md "
                "and declare it in .skill-audit.json:partial_access_files.",
            )
        )


def check_escalation_triggers(skill_dir: Path, result: AuditResult, config: dict) -> None:
    """A summary in SKILL.md that duplicates a reference must say when to open it.

    Without that line the summary shadows the reference: it reads as sufficient, so
    the better material never loads.
    """
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    sections = re.split(r"\n## ", text)
    # Sections declared core are always-needed content, not summaries of a reference.
    # They should NOT hand off, so an absent escalation trigger is correct there.
    core = {c.lower() for c in config.get("core_sections", [])}
    ref_stems = (
        {p.stem for p in (skill_dir / "references").glob("*.md")} if (skill_dir / "references").exists() else set()
    )

    for section in sections[1:]:
        title = section.split("\n")[0].lower()
        # Does this section's topic match a reference file name?
        matched = [s for s in ref_stems if any(token in s for token in re.findall(r"[a-z]{4,}", title))]
        if not matched or len(section.split()) < MIN_SUMMARY_WORDS:
            continue
        if any(marker in title for marker in core):
            continue
        has_trigger = re.search(r"Open .{0,40}(reference|`references/)", section)
        if not has_trigger:
            result.issues.append(
                Issue(
                    "medium",
                    "shadowing",
                    f"SKILL.md section '{section.split(chr(10))[0][:44]}' duplicates "
                    f"references/{matched[0]}.md with no escalation trigger.",
                    "Add an 'Open the reference when: ...' line naming what the summary omits.",
                )
            )


def long_paragraphs(md: Path):
    for para in md.read_text(encoding="utf-8", errors="replace").split("\n\n"):
        normalized = " ".join(para.split()).lower()
        if len(normalized.split()) >= MIN_DUPLICATE_WORDS:
            yield normalized


def check_duplication(skill_dir: Path, result: AuditResult, config: dict) -> None:
    """Flag near-identical paragraphs across references (drift risk)."""
    paragraphs: dict[str, list[str]] = {}
    for md in sorted((skill_dir / "references").glob("*.md")):
        for normalized in long_paragraphs(md):
            paragraphs.setdefault(normalized, []).append(md.name)

    declared = [set(pair) for pair in config.get("deliberate_duplication", [])]
    for files in paragraphs.values():
        unique = sorted(set(files))
        if len(unique) > 1 and set(unique) not in declared:
            result.issues.append(
                Issue(
                    "low",
                    "duplication",
                    f"Identical paragraph in {' and '.join(unique)}.",
                    "Intentional duplication is fine (it avoids double loads) but will drift — "
                    "keep the copies short and note that they are deliberate.",
                )
            )


# --------------------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------------------


def measure_dir(directory: Path, root: Path) -> list[FileStat]:
    items = sorted(directory.iterdir()) if directory.exists() else []
    return [measure(item, root) for item in items if item.is_file()]


def audit(skill_dir: Path, skill_budget: int, ref_budget: int) -> AuditResult:
    result = AuditResult(skill_name=skill_dir.name)
    # a skill's own config may raise its SKILL.md budget; the reference budget is global
    config = {"skill_md_budget": skill_budget} | load_config(skill_dir) | {"reference_budget": ref_budget}

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        result.issues.append(Issue("high", "structure", "No SKILL.md found.", ""))
        return result

    result.skill_md = measure(skill_md, skill_dir)
    result.references = measure_dir(skill_dir / "references", skill_dir)
    result.scripts = measure_dir(skill_dir / "scripts", skill_dir)
    result.assets = measure_dir(skill_dir / "assets", skill_dir)

    check_frontmatter(skill_md, result)
    check_links(skill_dir, result)
    check_routing_table(skill_md, skill_dir, result)
    check_budget(result, config)
    check_escalation_triggers(skill_dir, result, config)
    check_duplication(skill_dir, result, config)
    return result


def report(result: AuditResult) -> None:
    print(f"Skill: {result.skill_name}\n")
    print("CONTEXT BUDGET")
    if result.skill_md:
        print(f"  Always loaded (SKILL.md)   {result.skill_md.tokens:>6} tokens ({result.skill_md.lines} lines)")
    print(
        f"  References ({len(result.references):>2} files)      {result.reference_total:>6} tokens (loaded on demand)"
    )
    print(f"  Scripts    ({len(result.scripts):>2} files)      {'—':>6} (executed, never loaded)")
    print(f"  Assets     ({len(result.assets):>2} files)      {'—':>6} (copied, never loaded)")

    if result.references:
        print("\n  Largest references:")
        for ref in sorted(result.references, key=lambda r: -r.tokens)[:5]:
            print(f"    {ref.path:<38} {ref.tokens:>6}")

    if not result.issues:
        print("\nNo issues found.")
        return

    print(f"\nISSUES ({len(result.issues)})")
    for severity in ("high", "medium", "low"):
        items = [i for i in result.issues if i.severity == severity]
        if items:
            print(f"\n  {severity.upper()}")
        for issue in items:
            hint = f"\n      → {issue.hint}" if issue.hint else ""
            print(f"    [{issue.kind}] {issue.message}{hint}")


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
    parser = argparse.ArgumentParser(description="Audit a skill's context economy and structure.")
    parser.add_argument("skill_dir")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--budget", type=int, default=DEFAULT_SKILL_BUDGET, help="Token budget for the always-loaded SKILL.md body"
    )
    parser.add_argument("--reference-budget", type=int, default=DEFAULT_REFERENCE_BUDGET)
    parser.add_argument("--fail-on-violation", action="store_true", help="Exit 1 if any high-severity issue is found")
    cfg = parser.parse_args(argv)

    skill_dir = Path(cfg.skill_dir)
    if not skill_dir.is_dir():
        print(f"Not a directory: {skill_dir}", file=sys.stderr)
        return 2

    result = audit(skill_dir, cfg.budget, cfg.reference_budget)

    if cfg.json:
        print(json.dumps(asdict(result), indent=2))
    else:
        report(result)

    high = [i for i in result.issues if i.severity == "high"]
    return 1 if (cfg.fail_on_violation and high) else 0


if __name__ == "__main__":
    raise SystemExit(main())
