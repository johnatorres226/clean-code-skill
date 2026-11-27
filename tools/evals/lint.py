#!/usr/bin/env python3
"""Heuristic clean-code linter for C, C++, Java, and Python.

Detects the mechanically-checkable smells from references/smells-catalog.md so that
human review attention can go to the judgment calls instead.

Usage:
    python3 lint.py <path> [<path> ...]
    python3 lint.py src/ --json
    python3 lint.py src/ --max-function-lines 30 --max-params 4
    python3 lint.py src/ --only F1,G25 --fail-on-findings

This tool is deliberately conservative: it reports things worth a second look, not
verdicts. Every finding cites a catalog ID you can look up.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from types import SimpleNamespace

# --------------------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------------------

DEFAULT_MAX_FUNCTION_LINES = 20
DEFAULT_MAX_PARAMS = 3
DEFAULT_MAX_NESTING = 3
DEFAULT_MAX_LINE_LENGTH = 100
DEFAULT_MAX_FILE_LINES = 500
DEFAULT_MAX_COMPLEXITY = 10

C_LIKE_SUFFIXES = {".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh", ".hxx", ".java"}
PYTHON_SUFFIXES = {".py", ".pyi"}
ALL_SUFFIXES = C_LIKE_SUFFIXES | PYTHON_SUFFIXES

SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "build",
    "dist",
    "target",
    "out",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    "third_party",
    "vendor",
    "generated",
}

# Numbers that are almost never "magic".
ALLOWED_NUMBERS = {"0", "1", "2", "-1", "0.0", "1.0", "0.5", "100", "1000"}

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}

MIN_COMMENTED_CODE_RUN = 2  # one commented line is often prose; two in a row are code
SHORT_NAME_LENGTH = 2  # a function name this short cannot state intent
TRIVIAL_BODY_LINES = 5  # a public function this short documents itself
UNINFORMATIVE_NAMES = {"tmp", "temp", "foo", "bar", "data", "info", "val", "obj", "res"}
FLAG_NAME_RE = re.compile(r"^(is_|has_|should_|use_|enable_|do_|force_|verbose$|debug$)")


# --------------------------------------------------------------------------------------
# Finding model
# --------------------------------------------------------------------------------------


@dataclass
class Finding:
    path: str
    line: int
    code: str  # catalog ID, e.g. "F1"
    severity: str  # high | medium | low
    message: str
    hint: str = ""

    def render(self) -> str:
        location = f"{self.path}:{self.line}"
        head = f"  {location:<48} [{self.code}] {self.message}"
        return head + (f"\n{'':<52}→ {self.hint}" if self.hint else "")


@dataclass
class FunctionInfo:
    """A function/method discovered in a source file."""

    name: str
    line: int
    end_line: int
    params: list[str] = field(default_factory=list)
    body_lines: int = 0
    max_nesting: int = 0
    complexity: int = 1
    return_points: int = 0


# --------------------------------------------------------------------------------------
# Shared text-level analysis
# --------------------------------------------------------------------------------------

TODO_RE = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b(?P<tail>.{0,60})", re.IGNORECASE)
TODO_OWNER_RE = re.compile(r"\b(TODO|FIXME|HACK|XXX)\s*[\(\[]\s*\w", re.IGNORECASE)

# Lines that look like commented-out code rather than prose.
COMMENTED_CODE_RE = re.compile(
    r"""^\s*(?://|\#|/\*)\s*
        (?:
            (?:if|for|while|switch|return|else|elif|try|except|catch|import|from|def|class|public|private|protected|static)\b
          | [A-Za-z_][A-Za-z0-9_\.\[\]]*\s*(?:=[^=]|\+=|-=|\*=|/=)
          | [A-Za-z_][A-Za-z0-9_\.]*\s*\([^)]*\)\s*[;:]?\s*$
        )
    """,
    re.VERBOSE,
)

NUMBER_LITERAL_RE = re.compile(r"(?<![\w.])(-?\d+\.\d+|-?\d+)(?:[eE][-+]?\d+)?(?![\w.])")

STRING_OR_COMMENT_RE = re.compile(
    r"""("(?:\\.|[^"\\])*")|('(?:\\.|[^'\\])*')|(//[^\n]*)|(\#[^\n]*)|(/\*.*?\*/)""",
    re.DOTALL,
)


def strip_strings_and_comments(text: str) -> str:
    """Blank out string literals and comments so scanning does not trip on their contents."""

    def blank(match: re.Match[str]) -> str:
        return re.sub(r"\S", " ", match.group(0))

    return STRING_OR_COMMENT_RE.sub(blank, text)


def comment_markers(path: Path) -> tuple[str, ...]:
    return ("#",) if path.suffix in PYTHON_SUFFIXES else ("//", "*", "/*")


def commented_code_runs(lines: list[str]) -> list[tuple[int, int]]:
    """(first line, length) of each run of consecutive lines that look like commented-out code."""
    runs: list[tuple[int, int]] = []
    start = 0
    for index, line in enumerate(lines, start=1):
        if COMMENTED_CODE_RE.match(line):
            start = start or index
        elif start:
            runs.append((start, index - start))
            start = 0
    if start:
        runs.append((start, len(lines) + 1 - start))
    return runs


def todo_findings(rel: str, lines: list[str], markers: tuple[str, ...]) -> list[Finding]:
    findings: list[Finding] = []
    for index, line in enumerate(lines, start=1):
        todo = TODO_RE.search(line)
        if todo and line.lstrip().startswith(markers) and not TODO_OWNER_RE.search(line):
            findings.append(
                Finding(
                    rel,
                    index,
                    "C1",
                    "low",
                    f"{todo.group(1).upper()} without an owner or exit condition.",
                    "Use TODO(name, date): <what unblocks removal> — or delete it.",
                )
            )
    return findings


def check_common_text(path: Path, lines: list[str], cfg: argparse.Namespace) -> list[Finding]:
    """Checks that apply to every language and need only the raw text."""
    findings: list[Finding] = []
    rel = str(path)
    text = [raw.rstrip("\n") for raw in lines]

    if len(lines) > cfg.max_file_lines:
        findings.append(
            Finding(
                rel,
                1,
                "G8",
                "medium",
                f"File is {len(lines)} lines (limit {cfg.max_file_lines}).",
                "Large files usually hold several concepts. Consider splitting by responsibility.",
            )
        )
    findings += [
        Finding(
            rel,
            index,
            "G24",
            "low",
            f"Line is {len(line)} chars (limit {cfg.max_line_length}).",
            "Extract a named intermediate rather than wrapping.",
        )
        for index, line in enumerate(text, start=1)
        if len(line) > cfg.max_line_length
    ]
    findings += [
        Finding(rel, index, "G12", "low", "Trailing whitespace.", "")
        for index, line in enumerate(text, start=1)
        if line.rstrip() != line
    ]
    findings += [
        Finding(
            rel,
            start,
            "C5",
            "medium",
            f"{length} lines that look like commented-out code.",
            "Delete it. Version control remembers.",
        )
        for start, length in commented_code_runs(text)
        if length >= MIN_COMMENTED_CODE_RUN
    ]
    return findings + todo_findings(rel, text, comment_markers(path))


# Lines that are themselves constant definitions are fine — that is the fix for
# a magic number, so flagging them would punish the correct behavior.
CONST_DEF_RE = re.compile(
    # any declaration marked const/constexpr/final, whatever the naming style
    r"^\s*(?:(?:public|private|protected|static|inline|template\s*<[^>]*>)\s+)*"
    r"(?:const|constexpr|consteval|final)\b.*="
    # SCREAMING_SNAKE or kCamelCase name being assigned
    r"|^\s*(?:(?:public|private|protected|static|final|const|constexpr|inline)\s+)*"
    r"[A-Za-z_][\w:<>,\s\*&\[\]]*\s+(?:[A-Z][A-Z0-9_]*|k[A-Z]\w*)\s*(?:=|\{)"
    r"|^\s*#define\s+\w+"
    # Python module constant, with or without an annotation
    r"|^\s*(?:[A-Z][A-Z0-9_]*|k[A-Z]\w*)\s*(?::\s*[\w\[\], .\"']+)?\s*="
)
ENUM_LINE_RE = re.compile(r"^\s*[A-Za-z_]\w*\s*=\s*-?\d+\s*,?\s*$")
IMPORT_LINE_RE = re.compile(r"^\s*(?:#include|import|from|package|using)\b")  # array sizes, versions: noise


def magic_literals(line: str) -> list[str]:
    """Numeric literals on one scrubbed line that need a name, in order, each once."""
    if not line.strip() or CONST_DEF_RE.search(line) or ENUM_LINE_RE.match(line) or IMPORT_LINE_RE.match(line):
        return []
    for_header = re.match(r"^\s*for\b", line)
    found: list[str] = []
    for match in NUMBER_LITERAL_RE.finditer(line):
        literal = match.group(0)
        # Skip loop bounds like `i < 3` only if very small ints in a for-header.
        loop_bound = for_header and re.fullmatch(r"-?\d{1,2}", literal)
        if literal not in ALLOWED_NUMBERS and not loop_bound and literal not in found:
            found.append(literal)
    return found


def check_magic_numbers(path: Path, text: str) -> list[Finding]:
    """G25: numeric literals whose meaning must be inferred."""
    rel = str(path)
    return [
        Finding(
            rel,
            index,
            "G25",
            "medium",
            f"Magic number {literal}.",
            "Replace with a named constant that states the meaning and unit.",
        )
        for index, line in enumerate(strip_strings_and_comments(text).splitlines(), start=1)
        for literal in magic_literals(line)
    ]


# --------------------------------------------------------------------------------------
# Python analysis (AST-based, accurate)
# --------------------------------------------------------------------------------------

PY_NESTING_NODES = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.With,
    ast.AsyncWith,
    ast.Try,
    ast.ExceptHandler,
)
PY_COMPLEXITY_NODES = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.ExceptHandler,
    ast.BoolOp,
    ast.IfExp,
    ast.Assert,
    ast.comprehension,
)


def python_nesting_depth(node: ast.AST, depth: int = 0) -> int:
    best = depth
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue  # nested defs are measured on their own
        child_depth = depth + 1 if isinstance(child, PY_NESTING_NODES) else depth
        best = max(best, python_nesting_depth(child, child_depth))
    return best


def python_complexity(node: ast.AST) -> int:
    score = 1
    for child in ast.walk(node):
        if isinstance(child, ast.BoolOp):
            score += len(child.values) - 1
        elif isinstance(child, PY_COMPLEXITY_NODES):
            score += 1
        elif isinstance(child, ast.match_case):
            score += 1
    return score


def is_mutable_default(node: ast.AST) -> bool:
    literal = isinstance(node, (ast.List, ast.Dict, ast.Set))
    call = isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"list", "dict", "set"}
    return literal or call


def mutable_default_findings(rel: str, node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[Finding]:
    defaults = node.args.defaults + [d for d in node.args.kw_defaults if d]
    return [
        Finding(
            rel,
            default.lineno,
            "PY-MUT",
            "high",
            f"Mutable default argument in `{node.name}`.",
            "Use None as the default and build the container inside the body.",
        )
        for default in defaults
        if is_mutable_default(default)
    ]


def except_findings(rel: str, node: ast.ExceptHandler) -> list[Finding]:
    findings: list[Finding] = []
    if node.type is None:
        findings.append(
            Finding(
                rel,
                node.lineno,
                "G4",
                "high",
                "Bare `except:` swallows KeyboardInterrupt and SystemExit.",
                "Catch the specific exception type you can actually handle.",
            )
        )
    elif isinstance(node.type, ast.Name) and node.type.id in {"Exception", "BaseException"}:
        findings.append(
            Finding(
                rel,
                node.lineno,
                "G4",
                "medium",
                f"Broad `except {node.type.id}` hides unrelated bugs.",
                "Catch narrowly, or re-raise after handling what you recognize.",
            )
        )
    if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
        findings.append(
            Finding(
                rel,
                node.lineno,
                "G4",
                "high",
                "Exception silently swallowed (`except ...: pass`).",
                "Log with context or re-raise; never discard an error silently.",
            )
        )
    return findings


def none_compare_findings(rel: str, node: ast.Compare) -> list[Finding]:
    return [
        Finding(rel, node.lineno, "G26", "medium", "Comparing to None with == / !=.", "Use `is None` / `is not None`.")
        for op, comparator in zip(node.ops, node.comparators, strict=True)
        if isinstance(op, (ast.Eq, ast.NotEq)) and isinstance(comparator, ast.Constant) and comparator.value is None
    ]


def class_attribute_findings(rel: str, node: ast.ClassDef) -> list[Finding]:
    return [
        Finding(
            rel,
            item.lineno,
            "PY-CLS",
            "high",
            f"Mutable class attribute in `{node.name}` is shared by all instances.",
            "Initialize it in __init__, or use dataclasses.field(default_factory=...).",
        )
        for item in node.body
        if isinstance(item, ast.Assign) and isinstance(item.value, (ast.List, ast.Dict, ast.Set))
    ]


def node_findings(rel: str, node: ast.AST, cfg: argparse.Namespace) -> list[Finding]:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return _python_function_findings(rel, node, cfg) + mutable_default_findings(rel, node)
    if isinstance(node, ast.ExceptHandler):
        return except_findings(rel, node)
    if isinstance(node, ast.Compare):
        return none_compare_findings(rel, node)
    if isinstance(node, ast.ClassDef):
        return class_attribute_findings(rel, node)
    return []


def analyze_python(path: Path, text: str, cfg: argparse.Namespace) -> list[Finding]:
    rel = str(path)
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as err:
        return [Finding(rel, err.lineno or 1, "SYNTAX", "high", f"Could not parse: {err.msg}", "")]
    return [finding for node in ast.walk(tree) for finding in node_findings(rel, node, cfg)]


def param_findings(rel: str, node: ast.FunctionDef | ast.AsyncFunctionDef, cfg: argparse.Namespace) -> list[Finding]:
    args = node.args
    positional = [a.arg for a in args.posonlyargs + args.args]
    if positional and positional[0] in {"self", "cls"}:
        positional = positional[1:]
    param_count = len(positional) + len(args.kwonlyargs)
    if param_count <= cfg.max_params:
        return []
    return [
        Finding(
            rel,
            node.lineno,
            "F1",
            "medium",
            f"`{node.name}` takes {param_count} parameters (limit {cfg.max_params}).",
            "Group the ones that travel together into a parameter object.",
        )
    ]


def is_flag_param(arg: ast.arg) -> bool:
    annotation = getattr(arg, "annotation", None)
    return (isinstance(annotation, ast.Name) and annotation.id == "bool") or bool(FLAG_NAME_RE.match(arg.arg))


def flag_param_findings(rel: str, node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[Finding]:
    """F3: boolean flag parameters (positional ones are the readability problem)."""
    return [
        Finding(
            rel,
            node.lineno,
            "F3",
            "medium",
            f"`{node.name}` takes a positional boolean-looking parameter `{arg.arg}`.",
            "Split into two functions, or make it keyword-only so call sites read clearly.",
        )
        for arg in node.args.posonlyargs + node.args.args
        if arg.arg not in {"self", "cls"} and is_flag_param(arg)
    ]


def python_body_lines(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    end = getattr(node, "end_lineno", node.lineno) or node.lineno
    body_start = node.body[0].lineno if node.body else node.lineno
    # Multi-line string literals (docstrings, templates, SQL) are content, not logic.
    # Counting them would penalize exactly the code that should hold text.
    literal_lines = sum(
        max(0, (getattr(child, "end_lineno", child.lineno) or child.lineno) - child.lineno)
        for child in ast.walk(node)
        if isinstance(child, ast.Constant) and isinstance(child.value, str)
    )
    return max(1, end - body_start + 1 - literal_lines)


def limit_findings(rel: str, node: ast.FunctionDef | ast.AsyncFunctionDef, cfg: argparse.Namespace) -> list[Finding]:
    """Body length, nesting and complexity against the configured limits."""
    body_lines = python_body_lines(node)
    depth = max((python_nesting_depth(stmt, 1) for stmt in node.body), default=0)
    complexity = python_complexity(node)
    checks = [
        (
            body_lines > cfg.max_function_lines,
            "G30",
            f"`{node.name}` body is {body_lines} lines (limit {cfg.max_function_lines}).",
            "Extract the blocks you would otherwise comment; each becomes a named function.",
        ),
        (
            depth > cfg.max_nesting,
            "G34",
            f"`{node.name}` nests {depth} levels deep (limit {cfg.max_nesting}).",
            "Invert preconditions into guard clauses, or extract the inner block.",
        ),
        (
            complexity > cfg.max_complexity,
            "G30",
            f"`{node.name}` has cyclomatic complexity {complexity} (limit {cfg.max_complexity}).",
            "Too many decisions in one place — decompose the conditional.",
        ),
    ]
    return [Finding(rel, node.lineno, code, "medium", message, hint) for hit, code, message, hint in checks if hit]


def naming_findings(rel: str, node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[Finding]:
    findings: list[Finding] = []
    # N1: uninformative names.
    if len(node.name) <= SHORT_NAME_LENGTH and not node.name.startswith("__"):
        findings.append(
            Finding(
                rel,
                node.lineno,
                "N1",
                "medium",
                f"Function name `{node.name}` is too short to state intent.",
                "Name it as a verb phrase describing the one thing it does.",
            )
        )
    # Public functions should have a docstring stating the contract.
    public = not node.name.startswith("_")
    if public and ast.get_docstring(node) is None and python_body_lines(node) > TRIVIAL_BODY_LINES:
        findings.append(
            Finding(
                rel,
                node.lineno,
                "C1",
                "low",
                f"Public function `{node.name}` has no docstring.",
                "Document the contract: params, return, raises. Skip it for trivial functions.",
            )
        )
    # Uninformative local names.
    return findings + [
        Finding(
            rel,
            child.lineno,
            "N1",
            "low",
            f"Uninformative variable name `{child.id}`.",
            "Name it for what it holds at this point in the code.",
        )
        for child in ast.walk(node)
        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store) and child.id in UNINFORMATIVE_NAMES
    ]


def _python_function_findings(
    rel: str, node: ast.FunctionDef | ast.AsyncFunctionDef, cfg: argparse.Namespace
) -> list[Finding]:
    return (
        param_findings(rel, node, cfg)
        + flag_param_findings(rel, node)
        + limit_findings(rel, node, cfg)
        + naming_findings(rel, node)
    )


# --------------------------------------------------------------------------------------
# C / C++ / Java analysis (brace-based)
# --------------------------------------------------------------------------------------

# Matches a plausible function/method definition header ending in `{`.
C_FUNC_RE = re.compile(
    r"""^[ \t]*
        (?P<prefix>(?:(?:public|private|protected|static|final|virtual|inline|explicit|
                       constexpr|const|extern|friend|synchronized|abstract|override|
                       noexcept|template\s*<[^>]*>|\[\[[^\]]*\]\])\s+)*)
        (?P<ret>[A-Za-z_][\w:<>,\s\*&\[\]]*?)\s+
        (?P<name>[A-Za-z_~][\w:]*)\s*
        \((?P<params>[^;]*?)\)\s*
        (?P<trailer>(?:const|noexcept|override|final|throws\s+[\w.,\s]+|->\s*[\w:<>,\s\*&]+|\s)*)
        \{\s*$
    """,
    re.VERBOSE,
)

C_KEYWORDS_NOT_FUNCTIONS = {
    "if",
    "for",
    "while",
    "switch",
    "catch",
    "return",
    "else",
    "do",
    "try",
    "class",
    "struct",
    "enum",
    "union",
    "namespace",
    "sizeof",
    "new",
    "delete",
}

C_COMPLEXITY_RE = re.compile(r"\b(if|for|while|case|catch)\b|\?|&&|\|\|")


def split_params(param_text: str) -> list[str]:
    """Split a C-like parameter list on top-level commas."""
    params: list[str] = []
    depth = 0
    current = ""
    for char in param_text:
        if char in "<([{":
            depth += 1
        elif char in ">)]}":
            depth -= 1
        if char == "," and depth == 0:
            params.append(current.strip())
            current = ""
        else:
            current += char
    if current.strip():
        params.append(current.strip())
    return [p for p in params if p and p not in {"void"}]


def brace_depth(text: str, depth: int, max_depth: int) -> tuple[int, int]:
    """Depth after `text`, and the deepest it reached."""
    for char in text:
        if char == "{":
            depth += 1
            max_depth = max(max_depth, depth)
        elif char == "}":
            depth -= 1
    return depth, max_depth


def scan_c_body(lines: list[str], start: int) -> tuple[int, int, int, int]:
    """(end index, max brace depth, complexity, return count) of the body that opens at `start`."""
    depth = max_depth = returns = 0
    complexity = 1
    for scan in range(start, len(lines)):
        scrubbed = strip_strings_and_comments(lines[scan])
        depth, max_depth = brace_depth(scrubbed, depth, max_depth)
        if scan > start:
            complexity += len(C_COMPLEXITY_RE.findall(scrubbed))
            returns += len(re.findall(r"\breturn\b", scrubbed))
        if depth == 0:
            return scan, max_depth, complexity, returns
    return len(lines) - 1, max_depth, complexity, returns


def find_c_functions(lines: list[str]) -> list[FunctionInfo]:
    """Locate function bodies by matching a header line then balancing braces."""
    functions: list[FunctionInfo] = []
    index = 0
    while index < len(lines):
        match = C_FUNC_RE.match(lines[index])
        if not match or match.group("name").split("::")[-1] in C_KEYWORDS_NOT_FUNCTIONS:
            index += 1
            continue
        end, max_depth, complexity, returns = scan_c_body(lines, index)
        functions.append(
            FunctionInfo(
                name=match.group("name"),
                line=index + 1,
                end_line=end + 1,
                params=split_params(match.group("params")),
                body_lines=end - index,
                max_nesting=max(max_depth - 1, 0),
                complexity=complexity,
                return_points=returns,
            )
        )
        index = end + 1
    return functions


BOOL_PARAM_RE = re.compile(r"\b(bool|boolean|BOOL)\b")
OUT_PARAM_RE = re.compile(r"[\w:<>]+\s*[\*&]\s*\w+\s*$")


C_SUFFIXES = {".c", ".h"}
CPP_SUFFIXES = {".cc", ".cpp", ".cxx", ".hpp", ".hh", ".hxx"}
CPP_HEADER_SUFFIXES = {".hpp", ".hh", ".hxx"}


def c_function_findings(rel: str, func: FunctionInfo, cfg: argparse.Namespace) -> list[Finding]:
    findings: list[Finding] = []
    if len(func.params) > cfg.max_params:
        findings.append(
            Finding(
                rel,
                func.line,
                "F1",
                "medium",
                f"`{func.name}` takes {len(func.params)} parameters (limit {cfg.max_params}).",
                "Group the ones that travel together into a struct/class.",
            )
        )
    flag = next((param for param in func.params if BOOL_PARAM_RE.search(param)), None)
    if flag:
        findings.append(
            Finding(
                rel,
                func.line,
                "F3",
                "medium",
                f"`{func.name}` takes a boolean flag parameter (`{flag.strip()}`).",
                "A flag means the function does two things. Write the two functions.",
            )
        )
    checks = [
        (
            func.body_lines > cfg.max_function_lines,
            "G30",
            f"`{func.name}` body is {func.body_lines} lines (limit {cfg.max_function_lines}).",
            "Extract the blocks you would otherwise comment; each becomes a named function.",
        ),
        (
            func.max_nesting > cfg.max_nesting,
            "G34",
            f"`{func.name}` nests {func.max_nesting} levels deep (limit {cfg.max_nesting}).",
            "Invert preconditions into guard clauses, or extract the inner block.",
        ),
        (
            func.complexity > cfg.max_complexity,
            "G30",
            f"`{func.name}` has cyclomatic complexity ~{func.complexity} (limit {cfg.max_complexity}).",
            "Decompose the conditional; consider polymorphism over a switch (G23).",
        ),
        (
            len(func.name) <= SHORT_NAME_LENGTH and not func.name.startswith("~"),
            "N1",
            f"Function name `{func.name}` is too short to state intent.",
            "Name it as a verb phrase describing the one thing it does.",
        ),
    ]
    return findings + [
        Finding(rel, func.line, code, "medium", message, hint) for hit, code, message, hint in checks if hit
    ]


def catch_findings(src: SimpleNamespace, index: int, scrubbed: str) -> list[Finding]:
    """G4: silently swallowed exceptions."""
    findings: list[Finding] = []
    if re.search(r"catch\s*\([^)]*\)\s*\{\s*\}", scrubbed):
        findings.append(
            Finding(
                src.rel,
                index,
                "G4",
                "high",
                "Exception silently swallowed (empty catch block).",
                "Log with context or rethrow wrapped; never discard an error.",
            )
        )
    if src.suffix == ".java" and re.search(r"\bprintStackTrace\s*\(\s*\)", scrubbed):
        findings.append(
            Finding(
                src.rel,
                index,
                "G4",
                "medium",
                "printStackTrace() instead of structured logging.",
                "Log through the logger with context, or rethrow wrapped.",
            )
        )
    return findings


def c_memory_findings(src: SimpleNamespace, index: int, scrubbed: str) -> list[Finding]:
    """C: manual memory / unchecked calls."""
    if src.suffix not in C_SUFFIXES:
        return []
    findings: list[Finding] = []
    if re.search(r"\bstrcpy\s*\(|\bsprintf\s*\(|\bgets\s*\(|\bstrcat\s*\(", scrubbed):
        findings.append(
            Finding(
                src.rel,
                index,
                "G26",
                "high",
                "Unbounded string function (strcpy/strcat/sprintf/gets).",
                "Use the bounded variant (snprintf, strlcpy) and check the result.",
            )
        )
    nearby = " ".join(src.lines[index : index + 3])
    allocation = re.match(r"^\s*(?:\w+\s*=\s*)?(?:malloc|calloc|realloc)\s*\(", scrubbed)
    if allocation and "if" not in nearby and "NULL" not in nearby:
        findings.append(
            Finding(
                src.rel,
                index,
                "G4",
                "medium",
                "Allocation result may not be checked.",
                "Check for NULL before use; treat allocation failure as an error path.",
            )
        )
    return findings


def cpp_findings(src: SimpleNamespace, index: int, scrubbed: str) -> list[Finding]:
    """C++: raw owning allocation, header-scope using-directives."""
    if src.suffix not in CPP_SUFFIXES:
        return []
    findings: list[Finding] = []
    if re.search(r"(?<!\w)new\s+[A-Za-z_]", scrubbed) and "make_unique" not in scrubbed:
        findings.append(
            Finding(
                src.rel,
                index,
                "CPP-RAII",
                "medium",
                "Raw `new` — ownership is not expressed in the type.",
                "Use std::make_unique / std::make_shared, or a value type.",
            )
        )
    if re.search(r"(?<!\w)delete\s+\w", scrubbed):
        findings.append(
            Finding(
                src.rel,
                index,
                "CPP-RAII",
                "medium",
                "Manual `delete` — leaks on any early return or exception.",
                "Let RAII own the resource (unique_ptr, container, scope guard).",
            )
        )
    if re.search(r"^\s*using\s+namespace\s+", scrubbed) and src.suffix in CPP_HEADER_SUFFIXES:
        findings.append(
            Finding(
                src.rel,
                index,
                "G8",
                "high",
                "`using namespace` at header scope leaks into every includer.",
                "Qualify names, or confine the using-declaration to a .cpp/function scope.",
            )
        )
    return findings


def java_findings(src: SimpleNamespace, index: int, scrubbed: str) -> list[Finding]:
    """Java: returning null, raw types."""
    if src.suffix != ".java":
        return []
    findings: list[Finding] = []
    if re.search(r"(?:^|[;{)]\s*)return\s+null\s*;", scrubbed):
        findings.append(
            Finding(
                src.rel,
                index,
                "G26",
                "medium",
                "Returning null pushes a check onto every caller.",
                "Return Optional, an empty collection, a Special Case object, or throw.",
            )
        )
    if re.search(r"\bnew\s+(?:ArrayList|HashMap|HashSet)\s*\(\s*\)\s*;", scrubbed) and not re.search(r"<", scrubbed):
        findings.append(
            Finding(
                src.rel,
                index,
                "G26",
                "medium",
                "Raw collection type without generics.",
                "Parameterize it so the compiler can check element types.",
            )
        )
    return findings


def c_line_findings(src: SimpleNamespace, index: int, scrubbed: str) -> list[Finding]:
    findings = (
        catch_findings(src, index, scrubbed)
        + c_memory_findings(src, index, scrubbed)
        + cpp_findings(src, index, scrubbed)
        + java_findings(src, index, scrubbed)
    )
    # G29: negative conditionals that read as double negatives.
    if re.search(r"if\s*\(\s*![\w\.\(\)]*(?:not|Not|NOT|_no_|Disabled|Invalid)", scrubbed):
        findings.append(
            Finding(
                src.rel,
                index,
                "G29",
                "low",
                "Negated negative conditional.",
                "Express the predicate positively.",
            )
        )
    return findings


def analyze_c_like(path: Path, lines: list[str], cfg: argparse.Namespace) -> list[Finding]:
    rel = str(path)
    findings = [finding for func in find_c_functions(lines) for finding in c_function_findings(rel, func, cfg)]
    src = SimpleNamespace(rel=rel, suffix=path.suffix, lines=lines)
    for index, raw in enumerate(lines, start=1):
        findings += c_line_findings(src, index, strip_strings_and_comments(raw.rstrip("\n")))
    return findings


# --------------------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------------------


def source_files_under(root: Path) -> list[Path]:
    return [
        candidate
        for candidate in sorted(root.rglob("*"))
        if candidate.suffix in ALL_SUFFIXES
        and candidate.is_file()
        and not any(part in SKIP_DIRS for part in candidate.parts)
    ]


def iter_source_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for entry in paths:
        root = Path(entry)
        if root.is_file():
            files += [root] if root.suffix in ALL_SUFFIXES else []
        else:
            files += source_files_under(root)
    return files


def analyze_file(path: Path, cfg: argparse.Namespace) -> list[Finding]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as err:
        return [Finding(str(path), 1, "IO", "high", f"Could not read: {err}", "")]

    lines = text.splitlines()
    findings = check_common_text(path, lines, cfg)
    findings += check_magic_numbers(path, text)

    if path.suffix in PYTHON_SUFFIXES:
        findings += analyze_python(path, text, cfg)
    else:
        findings += analyze_c_like(path, lines, cfg)

    return findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Heuristic clean-code linter for C, C++, Java, and Python.",
        epilog="Finding codes map to references/smells-catalog.md.",
    )
    parser.add_argument("paths", nargs="+", help="Files or directories to analyze")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    parser.add_argument("--only", default="", help="Comma-separated codes to report (e.g. F1,G25)")
    parser.add_argument("--exclude", default="", help="Comma-separated codes to suppress")
    parser.add_argument("--min-severity", choices=["high", "medium", "low"], default="low")
    parser.add_argument(
        "--fail-on-findings", action="store_true", help="Exit 1 if any finding at/above --min-severity is reported"
    )
    parser.add_argument("--max-function-lines", type=int, default=DEFAULT_MAX_FUNCTION_LINES)
    parser.add_argument("--max-params", type=int, default=DEFAULT_MAX_PARAMS)
    parser.add_argument("--max-nesting", type=int, default=DEFAULT_MAX_NESTING)
    parser.add_argument("--max-line-length", type=int, default=DEFAULT_MAX_LINE_LENGTH)
    parser.add_argument("--max-file-lines", type=int, default=DEFAULT_MAX_FILE_LINES)
    parser.add_argument("--max-complexity", type=int, default=DEFAULT_MAX_COMPLEXITY)
    return parser


def selected(findings: list[Finding], cfg: argparse.Namespace) -> list[Finding]:
    """Findings that pass --only, --exclude and --min-severity, sorted by file, line, severity."""
    only = {c.strip().upper() for c in cfg.only.split(",") if c.strip()}
    exclude = {c.strip().upper() for c in cfg.exclude.split(",") if c.strip()}
    severity_cutoff = SEVERITY_ORDER[cfg.min_severity]
    kept = [
        f
        for f in findings
        if (not only or f.code.upper() in only)
        and f.code.upper() not in exclude
        and SEVERITY_ORDER[f.severity] <= severity_cutoff
    ]
    return sorted(kept, key=lambda f: (f.path, f.line, SEVERITY_ORDER[f.severity]))


def print_summary(findings: list[Finding]) -> None:
    if not findings:
        print("No findings. (This checks mechanical smells only — still review by hand.)")
        return
    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding.code] = counts.get(finding.code, 0) + 1
    print("Summary by catalog code (see references/smells-catalog.md):")
    for code, count in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {code:<10} {count}")


def print_report(file_count: int, findings: list[Finding]) -> None:
    print(f"Analyzed {file_count} file(s); {len(findings)} finding(s).\n")
    by_file: dict[str, list[Finding]] = {}
    for finding in findings:
        by_file.setdefault(finding.path, []).append(finding)
    for path, items in by_file.items():
        print(path)
        for item in items:
            print(item.render())
        print()
    print_summary(findings)


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
    cfg = build_parser().parse_args(argv)
    files = iter_source_files(cfg.paths)
    if not files:
        print("No C/C++/Java/Python source files found.", file=sys.stderr)
        return 0
    findings = selected([finding for path in files for finding in analyze_file(path, cfg)], cfg)
    if cfg.json:
        print(
            json.dumps(
                {
                    "files_analyzed": len(files),
                    "finding_count": len(findings),
                    "findings": [asdict(f) for f in findings],
                },
                indent=2,
            )
        )
    else:
        print_report(len(files), findings)
    return 1 if (cfg.fail_on_findings and findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
