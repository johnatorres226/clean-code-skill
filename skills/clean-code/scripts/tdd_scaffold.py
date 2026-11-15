#!/usr/bin/env python3
"""Generate a red-green-refactor starting point for a new unit.

Writes a failing test plus a minimal stub, so the first thing you do is run the
suite and watch it fail — which is the step people skip and the step that makes
the rest of TDD trustworthy.

Usage:
    python3 tdd_scaffold.py --lang python --unit RetryPolicy --dir src/myapp
    python3 tdd_scaffold.py --lang java   --unit RetryPolicy --package com.example.retry
    python3 tdd_scaffold.py --lang cpp    --unit RetryPolicy --dir src
    python3 tdd_scaffold.py --lang c      --unit ring_buffer --dir src
    python3 tdd_scaffold.py --lang python --unit Parser --dir src --dry-run
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

LANGUAGES = ("c", "cpp", "java", "python")


def to_snake(name: str) -> str:
    step = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", step).lower()


def to_pascal(name: str) -> str:
    parts = [p for p in re.split(r"[_\s-]+", name) if p]
    # Capitalize the first letter of each part but leave the rest alone, so an
    # already-PascalCase name like "RetryPolicy" survives intact.
    return "".join(part[0].upper() + part[1:] for part in parts)


# --------------------------------------------------------------------------------------
# Templates
# --------------------------------------------------------------------------------------


def python_files(unit: str, directory: Path, test_dir: Path) -> dict[Path, str]:
    module = to_snake(unit)
    cls = to_pascal(unit)

    source = f'''"""{cls}: <one line describing the responsibility>."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class {cls}:
    """<What this represents and what invariants it guarantees.>"""

    def describe(self) -> str:
        """Return a human-readable summary.

        Raises:
            NotImplementedError: Always, until the first test drives it out.
        """
        raise NotImplementedError
'''

    test = f'''"""Behavior specification for {cls}.

RED   → run this, watch it fail for the right reason.
GREEN → write the least code in {module}.py that passes.
REFACTOR → clean both files with the suite green.
"""

from __future__ import annotations

import pytest

from {module} import {cls}


def test_describe_returns_a_summary() -> None:
    # Arrange
    subject = {cls}()

    # Act
    summary = subject.describe()

    # Assert
    assert summary == "TODO: the behavior you actually want"


@pytest.mark.parametrize("value,expected", [
    # Boundary table — fill in: empty, one, many, max, max+1, negative.
])
def test_behavior_at_boundaries(value, expected) -> None:
    pytest.skip("Fill in the boundary table, then delete this skip.")
'''

    return {
        directory / f"{module}.py": source,
        test_dir / f"test_{module}.py": test,
    }


def java_files(unit: str, package: str, src_root: Path, test_root: Path) -> dict[Path, str]:
    cls = to_pascal(unit)
    package_path = Path(*package.split(".")) if package else Path()
    package_decl = f"package {package};\n\n" if package else ""

    source = f'''{package_decl}/** {cls}: <one line describing the responsibility>. */
public final class {cls} {{

    /**
     * Returns a human-readable summary.
     *
     * @return the summary, never {{@code null}}
     */
    public String describe() {{
        throw new UnsupportedOperationException("Not implemented yet");
    }}
}}
'''

    test = f'''{package_decl}import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

/**
 * Behavior specification for {cls}.
 *
 * <p>RED → run this and watch it fail. GREEN → least code that passes.
 * REFACTOR → clean both files with the suite green.
 */
class {cls}Test {{

    @Test
    void describeReturnsASummary() {{
        // Arrange
        {cls} subject = new {cls}();

        // Act
        String summary = subject.describe();

        // Assert
        assertThat(summary).isEqualTo("TODO: the behavior you actually want");
    }}
}}
'''

    return {
        src_root / package_path / f"{cls}.java": source,
        test_root / package_path / f"{cls}Test.java": test,
    }


def cpp_files(unit: str, directory: Path, test_dir: Path) -> dict[Path, str]:
    cls = to_pascal(unit)
    header_name = to_snake(unit)

    header = f'''#pragma once

#include <string>

namespace app {{

/// {cls}: <one line describing the responsibility>.
class {cls} {{
public:
    /// Returns a human-readable summary.
    [[nodiscard]] std::string describe() const;
}};

}}  // namespace app
'''

    source = f'''#include "{header_name}.hpp"

#include <stdexcept>

namespace app {{

std::string {cls}::describe() const {{
    throw std::logic_error("Not implemented yet");
}}

}}  // namespace app
'''

    test = f'''// Behavior specification for {cls}.
//
// RED   -> build and run; watch it fail for the right reason.
// GREEN -> least code in {header_name}.cpp that passes.
// REFACTOR -> clean both files with the suite green.

#include "{header_name}.hpp"

#include <gtest/gtest.h>

TEST({cls}Test, DescribeReturnsASummary) {{
    // Arrange
    const app::{cls} subject;

    // Act
    const std::string summary = subject.describe();

    // Assert
    EXPECT_EQ(summary, "TODO: the behavior you actually want");
}}
'''

    return {
        directory / f"{header_name}.hpp": header,
        directory / f"{header_name}.cpp": source,
        test_dir / f"{header_name}_test.cpp": test,
    }


def c_files(unit: str, directory: Path, test_dir: Path) -> dict[Path, str]:
    module = to_snake(unit)
    guard = f"{module.upper()}_H"

    header = f'''#ifndef {guard}
#define {guard}

#include <stddef.h>

/** Opaque handle. The layout is private to {module}.c. */
typedef struct {module} {module};

/**
 * @brief Creates a {module}.
 * @return Caller-owned handle to release with {module}_destroy(), or NULL on
 *         allocation failure.
 */
{module} *{module}_create(void);

/** @brief Releases a {module}. Safe to call with NULL. */
void {module}_destroy({module} *self);

/**
 * @brief Writes a human-readable summary into `out_buffer`.
 * @param self        Must not be NULL.
 * @param out_buffer  Receives a NUL-terminated summary; must not be NULL.
 * @param capacity    Size of `out_buffer` in bytes; must be > 0.
 * @return 0 on success, or a negative errno value on failure.
 */
int {module}_describe(const {module} *self, char *out_buffer, size_t capacity);

#endif /* {guard} */
'''

    source = f'''#include "{module}.h"

#include <errno.h>
#include <stdlib.h>

struct {module} {{
    int placeholder;
}};

{module} *{module}_create(void) {{
    return calloc(1, sizeof({module}));
}}

void {module}_destroy({module} *self) {{
    free(self); /* free(NULL) is a no-op, so no guard is needed */
}}

int {module}_describe(const {module} *self, char *out_buffer, size_t capacity) {{
    if (!self || !out_buffer || capacity == 0) {{
        return -EINVAL;
    }}
    return -ENOSYS; /* not implemented yet — the first test drives this out */
}}
'''

    test = f'''/* Behavior specification for {module}.
 *
 * RED   -> build and run; watch it fail for the right reason.
 * GREEN -> least code in {module}.c that passes.
 * REFACTOR -> clean both files with the suite green.
 *
 * Run under ASan or Valgrind: a passing test that leaks is not passing.
 */

#include "{module}.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

static void test_describe_returns_a_summary(void) {{
    /* Arrange */
    {module} *subject = {module}_create();
    assert(subject != NULL);
    char buffer[128] = {{0}};

    /* Act */
    const int rc = {module}_describe(subject, buffer, sizeof(buffer));

    /* Assert */
    assert(rc == 0);
    assert(strcmp(buffer, "TODO: the behavior you actually want") == 0);

    {module}_destroy(subject);
}}

static void test_describe_rejects_null_arguments(void) {{
    char buffer[8] = {{0}};
    assert({module}_describe(NULL, buffer, sizeof(buffer)) < 0);
}}

int main(void) {{
    test_describe_returns_a_summary();
    test_describe_rejects_null_arguments();
    puts("all tests passed");
    return 0;
}}
'''

    return {
        directory / f"{module}.h": header,
        directory / f"{module}.c": source,
        test_dir / f"{module}_test.c": test,
    }


# --------------------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a failing test plus a minimal stub to start the TDD cycle.",
    )
    parser.add_argument("--lang", required=True, choices=LANGUAGES)
    parser.add_argument("--unit", required=True,
                        help="Class or module name, e.g. RetryPolicy or ring_buffer")
    parser.add_argument("--dir", default="src", help="Source directory (default: src)")
    parser.add_argument("--test-dir", default=None,
                        help="Test directory (defaults to a sensible per-language location)")
    parser.add_argument("--package", default="",
                        help="Java package, e.g. com.example.retry")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be written without writing it")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    return parser


def default_test_dir(lang: str, source_dir: Path) -> Path:
    if lang == "java":
        return Path("src/test/java")
    if lang == "python":
        return Path("tests")
    return source_dir.parent / "tests" if source_dir.name == "src" else Path("tests")


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
    cfg = build_parser().parse_args(argv)

    source_dir = Path(cfg.dir)
    test_dir = Path(cfg.test_dir) if cfg.test_dir else default_test_dir(cfg.lang, source_dir)

    if cfg.lang == "python":
        files = python_files(cfg.unit, source_dir, test_dir)
    elif cfg.lang == "java":
        src_root = source_dir if source_dir != Path("src") else Path("src/main/java")
        files = java_files(cfg.unit, cfg.package, src_root, test_dir)
    elif cfg.lang == "cpp":
        files = cpp_files(cfg.unit, source_dir, test_dir)
    else:
        files = c_files(cfg.unit, source_dir, test_dir)

    for path, content in files.items():
        if cfg.dry_run:
            print(f"--- {path} " + "-" * max(0, 66 - len(str(path))))
            print(content)
            continue
        if path.exists() and not cfg.force:
            print(f"skip (exists): {path}", file=sys.stderr)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"wrote: {path}")

    if not cfg.dry_run:
        print("\nNext step — RED: run the suite and watch the test fail for the right reason.")
        print({
            "python": "  pytest -q",
            "java": "  ./gradlew test",
            "cpp": "  cmake --build build && ctest --test-dir build --output-on-failure",
            "c": f"  cc -Wall -Wextra -Werror -fsanitize=address,undefined "
                 f"-I{source_dir} {test_dir}/*_test.c {source_dir}/*.c -o /tmp/tests && /tmp/tests",
        }[cfg.lang])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
