#!/usr/bin/env bash
#
# Install formatter, linter, and pre-commit configuration for a project.
#
# Usage:
#   bash setup_toolchain.sh <c|cpp|java|python|all> [target-dir]
#
# Copies the matching configs from ../assets into the target directory (never
# overwriting an existing file) and prints the commands to wire them up.
#
# The point is that formatting and mechanical style should be decided once,
# encoded in checked-in config, and enforced automatically — so code review can
# be about design instead of whitespace.

set -euo pipefail

LANG_CHOICE="${1:-}"
TARGET_DIR="${2:-.}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASSETS_DIR="${SCRIPT_DIR}/../assets"

if [[ -z "${LANG_CHOICE}" ]]; then
    echo "Usage: bash setup_toolchain.sh <c|cpp|java|python|all> [target-dir]" >&2
    exit 2
fi

if [[ ! -d "${TARGET_DIR}" ]]; then
    echo "Target directory does not exist: ${TARGET_DIR}" >&2
    exit 1
fi

copy_asset() {
    local source_name="$1"
    local dest_name="${2:-$1}"
    local source_path="${ASSETS_DIR}/${source_name}"
    local dest_path="${TARGET_DIR}/${dest_name}"

    if [[ ! -f "${source_path}" ]]; then
        echo "  !! missing asset: ${source_name}" >&2
        return
    fi
    if [[ -e "${dest_path}" ]]; then
        echo "  skip (exists): ${dest_name}"
        return
    fi
    mkdir -p "$(dirname "${dest_path}")"
    cp "${source_path}" "${dest_path}"
    echo "  wrote: ${dest_name}"
}

setup_c_cpp() {
    echo "C / C++ configuration:"
    copy_asset ".clang-format"
    copy_asset ".clang-tidy"
    copy_asset ".editorconfig"
    cat <<'EOF'

Wire it up:
  clang-format -i $(git ls-files '*.c' '*.h' '*.cc' '*.cpp' '*.hpp')
  clang-tidy -p build $(git ls-files '*.cpp')

Build with warnings as errors — the cheapest quality gate there is:
  -Wall -Wextra -Wpedantic -Wshadow -Wconversion -Wsign-conversion \
  -Wnon-virtual-dtor -Wold-style-cast -Woverloaded-virtual -Wnull-dereference \
  -Wdouble-promotion -Wformat=2 -Werror

Run tests under sanitizers in CI:
  -fsanitize=address,undefined       # unit tests
  -fsanitize=thread                  # concurrency suite (separate build)

Suggested install:
  apt-get install clang-format clang-tidy cppcheck valgrind
EOF
}

setup_java() {
    echo "Java configuration:"
    copy_asset "checkstyle.xml"
    copy_asset ".editorconfig"
    cat <<'EOF'

Wire it up (Gradle):
  plugins {
      id 'checkstyle'
      id 'com.diffplug.spotless' version '6.25.0'
  }
  checkstyle { toolVersion = '10.17.0'; configFile = file('checkstyle.xml') }
  spotless { java { googleJavaFormat() } }
  tasks.withType(JavaCompile) { options.compilerArgs << '-Xlint:all' << '-Werror' }

Then:
  ./gradlew spotlessApply check

Also worth adding: SpotBugs, Error Prone, NullAway, JaCoCo (branch coverage),
and ArchUnit to enforce layering rules as tests.
EOF
}

setup_python() {
    echo "Python configuration:"
    copy_asset "pyproject.toml"
    copy_asset ".editorconfig"
    cat <<'EOF'

Wire it up:
  pip install ruff mypy pytest pytest-cov pre-commit
  ruff format .
  ruff check --fix .
  mypy --strict .
  pytest -q --cov --cov-branch

Note: if the project already has a pyproject.toml, the copy was skipped — merge
the [tool.ruff] and [tool.mypy] sections from assets/pyproject.toml by hand.
EOF
}

setup_precommit() {
    copy_asset ".pre-commit-config.yaml"
    cat <<'EOF'

Enable the hooks (runs the formatters and linters on staged files only):
  pip install pre-commit
  pre-commit install
  pre-commit run --all-files     # first run, to normalize the existing tree

Do the first bulk reformat in its own commit, so it does not pollute the blame
history of real changes.
EOF
}

echo "Setting up clean-code toolchain in: ${TARGET_DIR}"
echo

case "${LANG_CHOICE}" in
    c|cpp|c++)  setup_c_cpp ;;
    java)       setup_java ;;
    python|py)  setup_python ;;
    all)
        setup_c_cpp; echo; setup_java; echo; setup_python
        ;;
    *)
        echo "Unknown language: ${LANG_CHOICE}" >&2
        echo "Expected one of: c, cpp, java, python, all" >&2
        exit 2
        ;;
esac

echo
echo "Pre-commit hooks:"
setup_precommit

cat <<'EOF'

Finally, add the clean-code linter to CI:
  python3 scripts/clean_code_lint.py src/ --min-severity high --fail-on-findings

Start with --min-severity high so the gate is credible, then tighten it once the
existing findings are worked down. A check that is always red gets ignored.
EOF
