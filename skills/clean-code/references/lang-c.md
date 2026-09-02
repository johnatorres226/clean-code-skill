# Clean C

The universal principles hold. What changes is that C gives you no safety net: no destructors, no
exceptions, no namespaces, no generics, no visibility control. Every one of those absences must be
filled by a **convention you apply without exception** — a convention followed 90% of the time is
worse than none, because readers stop trusting it.

In C, cleanliness and correctness are the same discipline.

> Writing C++? Read `lang-cpp.md` instead. It repeats the rules shared between the two languages,
> so you do not need both files. The one C section worth reading anyway is
> [worked example](#worked-example) — the `goto cleanup` pattern is the problem RAII solves, and
> seeing it makes RAII land properly.

## Contents

- [Conventions that substitute for language features](#conventions-that-substitute-for-language-features)
- [Ownership and lifetime](#ownership-and-lifetime)
- [Headers and modularity](#headers-and-modularity)
- [Worked example](#worked-example)
- [Rules shared with C++](#rules-shared-with-c-duplicated-deliberately)
- [Toolchain](#toolchain)

## Conventions that substitute for language features

C has no namespaces, no destructors, no exceptions, no generics, and no visibility control. Every
one of those absences must be filled by a *convention you apply without exception*, because a
convention applied 90% of the time is worse than none — readers stop trusting it.

**Namespacing by prefix.** Every exported symbol carries its module's prefix. This is not
verbosity, it is the only namespace you have.

```c
/* ring_buffer.h */
typedef struct ring_buffer ring_buffer;

ring_buffer *ring_buffer_create(size_t capacity);
void         ring_buffer_destroy(ring_buffer *rb);
int          ring_buffer_push(ring_buffer *rb, uint8_t byte);
int          ring_buffer_pop(ring_buffer *rb, uint8_t *out_byte);
size_t       ring_buffer_size(const ring_buffer *rb);
```
Note the shape: `module_noun_verb`, the type first, `const` on read-only receivers, `out_` on
output parameters.

**`static` everything not exported.** A non-`static` function in a `.c` file is part of your
public API whether you meant it or not.

**One error convention per module, stated in the header.**
```c
/* All functions in this module return 0 on success or a negative errno value
 * on failure. Output parameters are untouched on failure. */
```

**Typed enums, not `#define`.** The compiler can check an `enum`; it cannot check a macro.
```c
/* bad */
#define STATE_IDLE 0
#define STATE_BUSY 1

/* good */
typedef enum { STATE_IDLE, STATE_BUSY, STATE_ERROR } device_state;
```

**Functions, not macros**, wherever a function works. Macros have no scope, no types, and
double-evaluate their arguments. If you must use one, parenthesize everything and SCREAM the name.

**`const` correctness.** `const` on every pointer parameter you don't modify. It documents intent
and the compiler enforces it.

**Fixed-width types at boundaries.** `uint32_t`, not `unsigned int`, anywhere the size matters
(protocols, file formats, hardware). Use `size_t` for sizes and counts, `ptrdiff_t` for
differences.

## Ownership and lifetime

Memory bugs are design bugs. The design decision you must make and document, for every pointer
crossing a boundary, is: **who frees this, and when is it valid?**

Encode it in the name and state it in the comment:

| Convention | Meaning |
|---|---|
| `_create` / `_destroy` | Caller owns the returned object; must call the paired destroy |
| `_acquire` / `_release` | Refcounted |
| returns `const char *` | Borrowed; valid only while the owner lives; do not free |
| `_dup` / `_strdup` suffix | Returns a copy the caller owns |
| `out_*` parameter | Filled on success; caller owns the contents |
| `_borrow` / `_peek` | Returns an interior pointer; invalidated by any mutation |

```c
/**
 * @brief Returns the buffer's label.
 * @return Borrowed pointer valid until the next call to ring_buffer_set_label()
 *         or ring_buffer_destroy(). Do not free. Never NULL.
 */
const char *ring_buffer_label(const ring_buffer *rb);
```

**Make destroy functions null-safe and idempotent** — it lets cleanup paths run unconditionally,
which is what makes the `goto cleanup` idiom clean:

```c
void ring_buffer_destroy(ring_buffer *rb) {
    if (!rb) return;                 /* mirrors free(NULL): always safe */
    free(rb->storage);
    free(rb);
}
```

**Zero-initialize aggregates** so partially-constructed objects are safe to destroy:
`struct document doc = {0};`

**Check every allocation and every return value.** Mark functions whose results must not be
ignored:
```c
int config_parse(const char *text, struct config *out)
    __attribute__((warn_unused_result));
```

## Headers and modularity

**The header is the contract; keep it minimal.** Opaque types are the strongest form of
encapsulation C offers — put the struct definition in the `.c` file and callers physically cannot
depend on your layout:

```c
/* widget.h */
#ifndef WIDGET_H
#define WIDGET_H
#include <stddef.h>

typedef struct widget widget;   /* opaque: layout is private */

widget *widget_create(const char *label);
void    widget_destroy(widget *w);
#endif /* WIDGET_H */
```
```c
/* widget.c */
#include "widget.h"
struct widget { char *label; size_t width; };    /* private layout */
```

Rules: include guards (or `#pragma once`) on every header; each header includes exactly what it
needs and nothing more; forward-declare rather than include where possible; never put `static`
functions or variable definitions in a header; each `.c` includes its own header first, which
proves the header is self-contained.

## Worked example

**Before** — one function doing four things, duplicated cleanup, magic numbers, unchecked calls:

```c
int proc(char *f, int m) {
    FILE *fp = fopen(f, "r");
    char *b = malloc(65536);
    if (!fp) { free(b); return -1; }
    if (!b) { fclose(fp); return -1; }
    int n = fread(b, 1, 65536, fp);
    b[n] = 0;
    int c = 0;
    for (int i = 0; i < n; i++) {
        if (b[i] == '\n') c++;
    }
    if (m == 1) c = c * 2;
    fclose(fp); free(b);
    return c;
}
```

**After** — named things, one responsibility per function, single cleanup path, documented
contract, no flag argument:

```c
/* text_stats.h */
#ifndef TEXT_STATS_H
#define TEXT_STATS_H
#include <stddef.h>

/** Reads `path` and reports its line count in `*out_lines`.
 *  @return 0 on success, or a negative errno value on failure.
 *          On failure `*out_lines` is untouched. */
int text_stats_count_lines(const char *path, size_t *out_lines);
#endif
```

```c
/* text_stats.c */
#include "text_stats.h"

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>

#define TEXT_STATS_MAX_FILE_BYTES (64u * 1024u)

static size_t count_newlines(const char *text, size_t length) {
    size_t lines = 0;
    for (size_t i = 0; i < length; i++) {
        if (text[i] == '\n') lines++;
    }
    return lines;
}

static int read_all(FILE *file, char *buffer, size_t capacity, size_t *out_length) {
    const size_t read_bytes = fread(buffer, 1, capacity - 1, file);
    if (ferror(file)) return -EIO;
    buffer[read_bytes] = '\0';
    *out_length = read_bytes;
    return 0;
}

int text_stats_count_lines(const char *path, size_t *out_lines) {
    if (!path || !out_lines) return -EINVAL;

    int    rc     = -EIO;
    FILE  *file   = NULL;
    char  *buffer = NULL;
    size_t length = 0;

    file = fopen(path, "rb");
    if (!file) { rc = -errno; goto cleanup; }

    buffer = malloc(TEXT_STATS_MAX_FILE_BYTES);
    if (!buffer) { rc = -ENOMEM; goto cleanup; }

    rc = read_all(file, buffer, TEXT_STATS_MAX_FILE_BYTES, &length);
    if (rc != 0) goto cleanup;

    *out_lines = count_newlines(buffer, length);   /* assign only on success */
    rc = 0;

cleanup:
    free(buffer);
    if (file) fclose(file);
    return rc;
}
```

What changed: a real name and contract, `size_t` for a count, error codes distinguishable by
cause, no buffer overrun (`capacity - 1` plus explicit NUL), the doubling flag gone (a caller who
wants doubling can double), and the counting logic now a pure function that is trivial to test.

---

## Rules shared with C++ (duplicated deliberately)

These apply to both languages. They are repeated in `lang-cpp.md` so that a single-language
task never has to load both files.

- **`const` correctness.** Mark every pointer parameter and every method that does not mutate.
  It is documentation the compiler enforces, and it costs nothing.
- **Fixed-width types at boundaries.** `uint32_t`, not `unsigned int`, anywhere the size matters
  (protocols, file formats, hardware registers). `size_t` for sizes and counts, `ptrdiff_t` for
  differences.
- **Typed enums, not `#define`.** The compiler can check an `enum`; it cannot check a macro.
- **Functions, not macros**, wherever a function works. Macros have no scope, no types, and
  double-evaluate their arguments.
- **Warnings as errors.** `-Wall -Wextra -Wpedantic -Wshadow -Wconversion -Werror` is the cheapest
  quality gate that exists. See [Toolchain](#toolchain).
- **Sanitizers in CI.** `-fsanitize=address,undefined` on the unit suite, `-fsanitize=thread` on
  the concurrency suite. A passing test that leaks or races is not passing.

## Toolchain

**Build with warnings as errors.**
```
-Wall -Wextra -Wpedantic -Wshadow -Wconversion -Wsign-conversion
-Wnull-dereference -Wdouble-promotion -Wformat=2 -Wstrict-prototypes -Werror
```

**Sanitizers in CI:** `-fsanitize=address,undefined` on unit tests; `-fsanitize=thread` on the
concurrency suite (separate build).

**Static analysis:** `clang-tidy` (`bugprone-*`, `cert-*`, `readability-*`), `cppcheck`.

**Formatting:** `clang-format` with a checked-in `.clang-format` (see `assets/.clang-format`).

**Testing:** Unity, CMocka, or Criterion. Always run the suite under Valgrind or ASan — in C, a
passing test that leaks or corrupts memory is not a passing test.

Run `bash scripts/setup_toolchain.sh c .` to install working configs.
