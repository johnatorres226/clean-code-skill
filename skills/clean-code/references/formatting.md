# Formatting

Formatting is communication. It is also the cheapest kind of quality to obtain, because a tool
can do it — which means there is no excuse for a codebase without one, and no excuse for humans
arguing about it in review.

**The rule that matters most: agree once, automate it, and never discuss it again.** A consistent
"wrong" style beats an inconsistent "right" one. Put the formatter in a pre-commit hook and in CI.

## Contents

- [Automate first](#automate-first)
- [Vertical formatting](#vertical-formatting)
- [Horizontal formatting](#horizontal-formatting)
- [Team rules over personal rules](#team-rules-over-personal-rules)
- [File and project organization](#file-and-project-organization)

## Automate first

| Language | Formatter | Linter | Also worth having |
|---|---|---|---|
| C / C++ | `clang-format` | `clang-tidy`, `cppcheck` | `include-what-you-use`, sanitizers |
| Java | `google-java-format` / `spotless` | Checkstyle, SpotBugs, Error Prone | PMD |
| Python | `ruff format` (or `black`) | `ruff` (or flake8+pylint) | `mypy`, `pyright` |

`scripts/setup_toolchain.sh` drops working configs from `assets/` into a project and prints the
pre-commit wiring. Run it once per repo.

## Vertical formatting

**The newspaper metaphor.** A source file should read like a news article: the name at the top
tells you whether you're in the right place, the first section gives the high-level story, and
detail increases as you descend. You should be able to stop reading at any point and have a
coherent, complete-at-that-level understanding.

**File length.** Most files should be a few hundred lines; 500 is a reasonable ceiling and 1000 is
a smell. Small files are easier to name, navigate, review, and merge. A large file is almost
always several concepts that have not been separated yet.

**Vertical openness between concepts.** Blank lines separate thoughts. Each group of lines that
forms one idea gets one blank line after it. Removing them makes the code a wall.

```python
package_name_pattern = re.compile(r"^[a-z][a-z0-9_]*$")

def parse(text: str) -> Manifest:
    header = _parse_header(text)
    _validate_version(header.version)

    entries = [_parse_entry(line) for line in _body_lines(text)]
    _reject_duplicates(entries)

    return Manifest(header, entries)
```

**Vertical density implies association.** Lines that belong together stay together — no stray
blank lines or comments splitting a tightly coupled group. Density and openness are two halves of
the same signal: *closeness means relatedness.*

**Vertical distance: declare close to use.**

- **Local variables** at the top of their first use, as close as the language allows. In C89 they
  had to go at the top of the block; in C99+, C++, Java, and Python, put them where they're used.
- **Instance variables** at the top of the class (Java/C++ convention) — one well-known place, so
  readers never hunt.
- **Loop control variables** inside the loop statement.
- **Dependent functions**: the caller *above* the callee, so the reader flows downward. This
  is the stepdown rule from `functions.md`, expressed as layout.
- **Conceptually affine functions** (`assertTrue`/`assertFalse`, the four overloads of `write`)
  stay adjacent even without a call relationship.

Vertical distance is a real cost: if a reader has to scroll or jump files to understand one
function, that function's dependencies are too far away.

**Vertical ordering within a file** — a defensible default:

```
1. License / file-level doc comment
2. Includes / imports (grouped, ordered)
3. Constants and type declarations
4. Public entry points, in order of importance
5. Private helpers, in stepdown order beneath their callers
```

Java convention places all fields at the top; C++ convention places `public:` before `private:`
for the same reason — readers care about the interface first. Python has no enforced order, so
put module constants first, then public functions/classes, then private (`_`-prefixed) helpers.

## Horizontal formatting

**Line length.** Pick a limit and enforce it. Common choices: 80 (C/C++ traditional, forces
smaller functions), 100 (Java/Python pragmatic middle, and Google's Java default), 120 (upper
bound; beyond this side-by-side diffs and code review become painful). Never rely on wrapping.

A line that will not fit is usually a line doing too much. Break it by extracting a named
intermediate, not by adding a continuation with awkward alignment.

**Horizontal openness.** Use spaces to show which operators bind tighter and to separate distinct
things.

```java
// assignment operator gets space (separates two sides);
// function name and its paren do not (they're one thing)
int lineSize = line.length();
totalChars  += lineSize;

// multiplication binds tighter than addition — show it
return b * b - 4 * a * c;
```

**Do not align columns artificially.** Aligning a block of declarations or assignments looks tidy
until one name grows and the formatter reflows twenty lines, wrecking your diff and blame. Let
the formatter decide.

```java
// avoid
private   Socket        socket;
private   InputStream   input;
private   OutputStream  output;

// prefer
private Socket socket;
private InputStream input;
private OutputStream output;
```

**Indentation.** Indent to reveal scope; never collapse a scope onto one line to save space.
Spaces vs. tabs matters far less than consistency — but pick per-ecosystem: 4 spaces for Python
(PEP 8, non-negotiable), 4 for Java, 2 or 4 for C/C++ (project choice). Never mix.

```java
// avoid — a scope hidden on one line
if (level > MAX) { level = MAX; }
while (!done) doWork();

// prefer
if (level > MAX) {
    level = MAX;
}
```

**Braces.** Use them even for one-line bodies. The cost is one line; the benefit is that adding a
second statement later cannot silently escape the conditional. (This is not hypothetical — it has
caused shipped security bugs.)

**Dummy scopes.** Avoid empty loop bodies; if you truly need one, make the emptiness loud:
```c
while (dis.read(buf, 0, readBufferSize) != -1)
    ;   /* intentionally empty: draining the stream */
```

## Team rules over personal rules

A codebase should look as if one careful person wrote it, even with twenty authors. That means
the *team's* choices override yours: brace placement, import ordering, comment style, naming
casing, test layout.

Encode the decisions in machine-readable config checked into the repo — `.clang-format`,
`.editorconfig`, `checkstyle.xml`, `pyproject.toml` — so the rules travel with the code and new
contributors inherit them automatically. Then review can be about design instead of whitespace.

When editing a file whose local style differs from the project standard, match the file, not the
standard, unless you are reformatting the whole file in a dedicated commit. A half-converted file
is worse than either style.

## File and project organization

**One primary concept per file.** In Java this is enforced (one public class per file); in C++ and
Python it is a discipline. A file named `utils.py` that has grown to 900 lines is several missing
modules.

**Header/implementation split (C/C++).** The header is the contract and should be readable on its
own: include what it needs, expose nothing it doesn't have to, forward-declare rather than include
where possible, and use include guards or `#pragma once` consistently.

```cpp
// ring_buffer.hpp — the contract, no implementation noise
#pragma once
#include <cstddef>
#include <cstdint>
#include <optional>

namespace io {

/// Fixed-capacity single-producer single-consumer byte buffer.
class RingBuffer {
public:
    explicit RingBuffer(std::size_t capacity);

    /// Returns false if the buffer is full; never blocks.
    bool push(std::uint8_t byte) noexcept;

    /// Returns std::nullopt if empty; never blocks.
    std::optional<std::uint8_t> pop() noexcept;

    std::size_t size() const noexcept;

private:
    std::vector<std::uint8_t> storage_;
    std::size_t head_ = 0;
    std::size_t tail_ = 0;
};

}  // namespace io
```

**Import/include ordering.** Group and separate with blank lines, in a fixed order:

```cpp
#include "ring_buffer.hpp"   // 1. this file's own header, first — proves it self-includes

#include <cstdint>           // 2. C++ standard library
#include <vector>

#include <fmt/format.h>      // 3. third-party

#include "io/log.hpp"        // 4. this project
```

```python
import os                    # 1. standard library
import sys

import numpy as np           # 2. third-party
import requests

from myapp.billing import Invoice   # 3. first-party
```

Let the tool do it: `clang-format`'s `IncludeCategories`, `ruff`'s isort rules, Checkstyle's
`ImportOrder`. All three are in `assets/`.

**Test file placement.** Mirror the source tree so the test for `billing/invoice.py` is at
`tests/billing/test_invoice.py` (or `src/test/java/.../InvoiceTest.java`). Predictable location
means tests actually get found and updated.

## Related heuristics

`smells-catalog.md`: **G24** follow standard conventions, **G1** multiple languages in one source
file, **G11** inconsistency, **G10** vertical separation.
