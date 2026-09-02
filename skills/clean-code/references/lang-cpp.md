# Clean C++

The universal principles hold. What changes is that C++ gives you the tools to make correctness
automatic — and the freedom to ignore them. **RAII is the load-bearing idea**: if resources own
themselves, correctness under early return and under exceptions is free, and the code needs no
cleanup blocks at all.

> Writing plain C? Read `lang-c.md` instead. This file repeats the rules shared between the two
> languages, so you do not need both.

## Contents

- [RAII and the Rule of Zero](#raii-and-the-rule-of-zero)
- [Value semantics and const correctness](#value-semantics-and-const-correctness)
- [Prefer algorithms to loops](#prefer-algorithms-to-loops)
- [Interfaces and types](#interfaces-and-types)
- [Worked example](#worked-example)
- [Rules shared with C](#rules-shared-with-c-duplicated-deliberately)
- [Toolchain](#toolchain)


## RAII and the Rule of Zero

RAII is the central idea. Every resource — memory, files, locks, sockets, handles — is owned by an
object whose destructor releases it. Then correctness under early return *and* under exceptions is
automatic, and the code has no cleanup blocks at all.

**Rule of Zero:** if your class composes only RAII members, write no destructor, no copy
constructor, no assignment operator, no move operations. The compiler generates correct ones.

```cpp
class Session {                   // no destructor needed: every member cleans itself up
    std::unique_ptr<Connection> connection_;
    std::vector<Message>        pending_;
    std::string                 user_id_;
};
```

**Rule of Five:** if you *must* write one of destructor / copy ctor / copy assign / move ctor /
move assign, you almost certainly need all five. That is a strong signal you should be wrapping
the raw resource in its own tiny RAII type instead, and returning to the Rule of Zero.

```cpp
// A minimal RAII wrapper — the one place that manages the raw handle
class FileDescriptor {
public:
    explicit FileDescriptor(int fd) noexcept : fd_(fd) {}
    ~FileDescriptor() { if (fd_ >= 0) ::close(fd_); }

    FileDescriptor(const FileDescriptor&)            = delete;
    FileDescriptor& operator=(const FileDescriptor&) = delete;
    FileDescriptor(FileDescriptor&& other) noexcept : fd_(std::exchange(other.fd_, -1)) {}
    FileDescriptor& operator=(FileDescriptor&& other) noexcept {
        if (this != &other) { if (fd_ >= 0) ::close(fd_); fd_ = std::exchange(other.fd_, -1); }
        return *this;
    }

    int get() const noexcept { return fd_; }

private:
    int fd_;
};
```

**Ownership in the type system:**

| Intent | Type |
|---|---|
| Unique ownership | `std::unique_ptr<T>` |
| Shared ownership (rare — justify it) | `std::shared_ptr<T>` |
| Non-owning, must exist | `T&` or `const T&` |
| Non-owning, may be absent | `T*` (never delete it) or `std::optional<std::reference_wrapper<T>>` |
| Non-owning view of a sequence | `std::span<T>`, `std::string_view` |
| Value | `T` — the default; copies are cheap more often than you think |

**Never `new`/`delete` in application code.** `std::make_unique<T>(...)` and `std::make_shared`
exist so you never have to.

**Function signatures should announce ownership:**
```cpp
void observe(const Widget& w);                    // borrows, won't keep
void consume(std::unique_ptr<Widget> w);          // takes ownership
std::unique_ptr<Widget> create(WidgetSpec spec);  // gives ownership
void render(std::span<const Vertex> vertices);    // borrows a range, no copy
```
A reader learns the lifetime rules from the signature alone. That is the goal.

## Value semantics and const correctness

```cpp
class Invoice {
public:
    // const on every method that doesn't mutate — free documentation, compiler-enforced
    Money total() const noexcept;
    bool  is_paid() const noexcept;

    // take by value + move when you're going to store it
    void set_reference(std::string reference) { reference_ = std::move(reference); }

private:
    std::string reference_;
    Money       total_{};
};
```

Other rules that pay for themselves:
- **`explicit` on single-argument constructors** — stops surprise implicit conversions.
- **Brace initialization** (`int n{value};`) — catches narrowing at compile time.
- **`[[nodiscard]]`** on functions whose result must not be ignored.
- **`noexcept`** where genuinely true — enables move optimizations in containers.
- **`enum class`, never plain `enum`** — scoped and non-convertible.
- **Prefer `constexpr` to `#define`** — typed, scoped, debuggable.
- **Structured bindings** for tuple-ish returns: `auto [ok, value] = parse(text);`

## Prefer algorithms to loops

A named algorithm states intent; a hand-written loop makes the reader reconstruct it. Algorithms
are also correct at the boundaries, which hand-rolled loops frequently are not.

```cpp
// bad — the reader must decode the intent, and the boundary is easy to get wrong
bool found = false;
for (size_t i = 0; i < items.size(); ++i) {
    if (items[i].id == target) { found = true; break; }
}

// good
const bool found = std::ranges::any_of(items, [target](const Item& i) { return i.id == target; });
```

```cpp
// composition without intermediate allocations
auto active_names = users
    | std::views::filter([](const User& u) { return u.is_active(); })
    | std::views::transform(&User::name);
```

Reach for `std::ranges::sort`, `find_if`, `accumulate`, `transform`, `partition`, `unique`,
`all_of`/`any_of`/`none_of` before writing a loop. When you do write one, prefer range-for.

## Interfaces and types

**Make illegal states unrepresentable.** This is the highest-leverage design principle the type
system offers.

```cpp
// bad — every caller must check, and the invariant lives in a comment
struct Connection {
    int    socket;      // -1 when disconnected
    bool   connected;   // must agree with socket; nothing enforces it
    std::string host;   // meaningless when disconnected
};

// good — the disconnected state simply cannot hold host data
struct Disconnected {};
struct Connected { FileDescriptor socket; std::string host; };
using Connection = std::variant<Disconnected, Connected>;
```

**Strong typedefs for units** — the compiler catches what a code review will not:
```cpp
using Milliseconds = std::chrono::milliseconds;
void set_timeout(Milliseconds timeout);      // set_timeout(5) won't compile; set_timeout(5s) will
```

**Prefer free functions to member functions** when a function doesn't need private access — it
reduces the class's surface (G8) and improves reusability.

**Interfaces:** pure abstract base classes for runtime polymorphism, concepts/templates for
compile-time. Keep abstract interfaces small, give them a virtual destructor, and don't put data
in them.

```cpp
class Clock {
public:
    virtual ~Clock() = default;
    virtual std::chrono::system_clock::time_point now() const = 0;
};
```
That three-line interface is what makes every time-dependent test deterministic.

## Worked example

**Before**
```cpp
std::vector<Order>* process(std::vector<Order>* in, int mode, char* err) {
    std::vector<Order>* out = new std::vector<Order>();
    for (int i = 0; i < in->size(); i++) {
        Order o = in->at(i);
        if (o.status == 1) {
            if (mode == 0) o.total = o.total * 1.2;
            else o.total = o.total * 0.8;
            out->push_back(o);
        }
    }
    if (out->size() == 0) { strcpy(err, "no orders"); }
    return out;
}
```
Problems: leaks (who deletes the result?), raw `new`, a null-able error buffer with no size, magic
numbers, a flag argument, a signed/unsigned comparison warning, an unnecessary copy per iteration,
and no way to test it in isolation.

**After**
```cpp
enum class PricingTier { Premium, Discount };

constexpr double kPremiumMultiplier  = 1.20;
constexpr double kDiscountMultiplier = 0.80;

[[nodiscard]] constexpr double multiplier_for(PricingTier tier) noexcept {
    return tier == PricingTier::Premium ? kPremiumMultiplier : kDiscountMultiplier;
}

/// Returns the confirmed orders from `orders`, repriced for `tier`.
/// Returns an empty vector when none are confirmed.
[[nodiscard]] std::vector<Order> price_confirmed_orders(std::span<const Order> orders,
                                                        PricingTier tier) {
    const double multiplier = multiplier_for(tier);

    std::vector<Order> priced;
    priced.reserve(orders.size());
    for (const Order& order : orders) {
        if (order.status != OrderStatus::Confirmed) continue;
        Order repriced = order;
        repriced.total *= multiplier;
        priced.push_back(std::move(repriced));
    }
    return priced;      // no leak possible; move/RVO makes it free
}
```
The error out-parameter disappeared because "no confirmed orders" is not an error — it is an
empty result (`define the normal flow`, `error-handling.md`). `std::span` accepts any contiguous
range without copying. `multiplier_for` is a pure function you can test in one line.

## Rules shared with C (duplicated deliberately)

These apply to both languages. They are repeated in `lang-c.md` so that a single-language
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

**Build with warnings as errors.** This is the cheapest quality gate in existence.
```
-Wall -Wextra -Wpedantic -Wshadow -Wconversion -Wsign-conversion
-Wnon-virtual-dtor -Wold-style-cast -Woverloaded-virtual -Wnull-dereference
-Wdouble-promotion -Wformat=2 -Werror
```
MSVC: `/W4 /permissive- /WX`.

**Sanitizers in CI** — they find what tests and review do not:
```
-fsanitize=address,undefined     # unit tests
-fsanitize=thread                # concurrency suite (separate build)
```

**Static analysis:** `clang-tidy` with `bugprone-*`, `cppcoreguidelines-*`, `modernize-*`,
`performance-*`, `readability-*`; plus `cppcheck` and `include-what-you-use`.

**Formatting:** `clang-format` with a checked-in `.clang-format` (see `assets/.clang-format`),
run in a pre-commit hook.

**Testing:** GoogleTest or Catch2. Build the test suite with sanitizers enabled.

Run `bash scripts/setup_toolchain.sh cpp .` to install working configs.
