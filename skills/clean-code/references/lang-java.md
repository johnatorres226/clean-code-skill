# Clean Java

Java's verbosity is a real cost, and most "Java-looking" code is ceremony that modern language
features have made unnecessary. Clean Java means: small classes with real responsibilities,
immutability by default, dependencies injected, nulls eliminated at API boundaries, and none of
the boilerplate the language no longer requires.

## Contents

- [Immutability by default](#immutability-by-default)
- [Records and value types](#records-and-value-types)
- [Eliminate null](#eliminate-null)
- [Exceptions](#exceptions)
- [Dependency injection](#dependency-injection)
- [Collections and streams](#collections-and-streams)
- [Sealed types and pattern matching](#sealed-types-and-pattern-matching)
- [Enums that carry behavior](#enums-that-carry-behavior)
- [Equality, hashing, and toString](#equality-hashing-and-tostring)
- [Concurrency](#concurrency)
- [Worked example](#worked-example)
- [Toolchain](#toolchain)

## Immutability by default

Immutable objects are thread-safe for free, cannot be corrupted by a caller, are safe to cache and
share, and cannot be in an invalid state after construction. Make things mutable only when you
have a reason.

```java
// Every field final, all state supplied at construction, defensive copy of the collection.
public final class Order {
    private final OrderId id;
    private final List<LineItem> lines;

    public Order(OrderId id, List<LineItem> lines) {
        this.id = Objects.requireNonNull(id, "id");
        this.lines = List.copyOf(lines);          // copies and makes unmodifiable
    }

    public Money total() {
        return lines.stream().map(LineItem::subtotal).reduce(Money.ZERO, Money::add);
    }

    /** Returns a new Order with `line` appended; this instance is unchanged. */
    public Order withLine(LineItem line) {
        List<LineItem> updated = new ArrayList<>(lines);
        updated.add(line);
        return new Order(id, updated);
    }
}
```

Note `withX()` rather than `setX()` — the name tells the caller a new instance comes back.

## Records and value types

A `record` replaces the constructor / getters / `equals` / `hashCode` / `toString` boilerplate that
used to bury the actual content of a class. Use them for anything whose identity is its value:
DTOs, coordinates, money, IDs, config, query results.

```java
public record LineItem(String sku, int quantity, Money unitPrice) {
    public LineItem {                            // compact constructor: validate invariants
        Objects.requireNonNull(sku, "sku");
        if (quantity <= 0) {
            throw new IllegalArgumentException("quantity must be positive, got " + quantity);
        }
    }

    public Money subtotal() { return unitPrice.times(quantity); }
}
```

**Wrap primitive IDs in types.** `OrderId` and `CustomerId` are both strings underneath and can
never be swapped by accident once they are distinct types. This eliminates a whole bug class that
tests rarely catch.

```java
public record OrderId(String value) {
    public OrderId { Objects.requireNonNull(value); }
    @Override public String toString() { return value; }
}
```

**Use `BigDecimal` (or a `Money` type wrapping it) for money — never `double`.** Binary floating
point cannot represent `0.10`, and the resulting drift shows up in audits, not in tests.

## Eliminate null

Null is the default value that means nothing and crashes everything. Push it out of your APIs.

```java
// bad — every caller must remember, and one won't
public Customer findCustomer(String id) { ... }        // may return null

// good — the type states the possibility, and the compiler makes you handle it
public Optional<Customer> findCustomer(CustomerId id) { ... }
```

Rules for `Optional`:
- Use it as a **return type** for "may legitimately be absent".
- Do **not** use it for fields or parameters — it's not serializable and it's clumsy. For optional
  parameters use overloads or a builder.
- Never call `.get()` without `.isPresent()`; use `orElse`, `orElseThrow`, `map`, `ifPresent`.
- Never return `null` from a method declared to return `Optional`. That is a special circle.

**Return empty collections, never null:** `List.of()`, `Collections.emptyList()`. Callers then
just iterate.

**Guard parameters:** `Objects.requireNonNull(x, "x")` in constructors, or `@NonNull` annotations
with a checker (NullAway, Error Prone) enforcing them at build time.

## Exceptions

**Prefer unchecked exceptions.** Checked exceptions violate Open/Closed: adding a `throws` deep in
the call stack forces edits at every level above, and every intervening signature becomes coupled
to a detail it doesn't care about. Reserve checked exceptions for conditions the immediate caller
can genuinely recover from — a rare situation in application code.

**Give exceptions context:**
```java
throw new PaymentDeclinedException(
        "Charge declined for order %s: gateway code %s".formatted(orderId, code), cause);
```

**Define exceptions by the caller's needs**, and wrap third-party exception zoos into your own
vocabulary at the boundary. See `error-handling.md`.

**Always use try-with-resources:**
```java
try (var connection = pool.acquire();
     var statement  = connection.prepare(SQL)) {
    return statement.executeQuery();
}   // closed on every path, suppressed exceptions preserved
```

**Never swallow.** `catch (Exception e) { }` is a promise that something impossible won't happen.
At minimum log with context; usually, rethrow wrapped.

## Dependency injection

Business logic should not construct its infrastructure. Constructor injection is the default —
it makes dependencies explicit, impossible to forget, and trivially fakeable in tests.

```java
// bad — hidden dependencies on the network and the wall clock; untestable
public class InvoiceService {
    public Invoice issue(Order order) {
        var rates = new HttpRateClient("https://rates.example.com").fetch();
        return new Invoice(order, rates, LocalDate.now());
    }
}

// good — the constructor is an honest list of what this class needs
public class InvoiceService {
    private final RateProvider rates;
    private final Clock clock;

    public InvoiceService(RateProvider rates, Clock clock) {
        this.rates = Objects.requireNonNull(rates);
        this.clock = Objects.requireNonNull(clock);
    }

    public Invoice issue(Order order) {
        return new Invoice(order, rates.current(), LocalDate.now(clock));
    }
}
```

Injecting `java.time.Clock` costs one field and makes every date-dependent test deterministic:
`Clock.fixed(Instant.parse("2026-03-01T00:00:00Z"), ZoneOffset.UTC)`.

Avoid field injection (`@Autowired` on a private field) — it hides dependencies, prevents `final`,
and requires a container to construct the object at all, including in tests.

## Collections and streams

**Program to interfaces:** declare `List`, `Map`, `Set`; instantiate `ArrayList`, `HashMap`.

**Prefer immutable factories:** `List.of(...)`, `Map.of(...)`, `Set.of(...)`, `List.copyOf(...)`.

**Streams for pipelines, loops for side effects.** A stream should read as a description of a
transformation. If it exceeds three or four operations, or contains a lambda with a body of more
than a couple of lines, extract named methods — or use a loop.

```java
// good — reads as a sentence, each step named
Map<Region, Money> revenueByRegion = orders.stream()
        .filter(Order::isSettled)
        .collect(groupingBy(Order::region,
                            reducing(Money.ZERO, Order::total, Money::add)));
```
```java
// bad — a stream doing side effects; a loop says this more honestly
orders.stream().forEach(o -> { audit.record(o); mailer.send(o); });

// better
for (Order order : orders) {
    audit.record(order);
    mailer.send(order);
}
```

Extract lambdas that grow: `.filter(this::isEligibleForDiscount)` beats an inline three-line
lambda, and the method name documents the rule.

## Sealed types and pattern matching

Sealed interfaces plus records give you closed sums with compiler-checked exhaustiveness — often
a better fit than polymorphism when the *set of types is fixed* and the *set of operations keeps
growing* (see `classes-and-design.md`).

```java
public sealed interface PaymentResult permits Approved, Declined, RequiresAction {}

public record Approved(TransactionId id, Money amount) implements PaymentResult {}
public record Declined(String reason)                  implements PaymentResult {}
public record RequiresAction(URI challengeUrl)         implements PaymentResult {}

// Adding a fourth case makes this switch fail to compile — exactly what you want.
String describe(PaymentResult result) {
    return switch (result) {
        case Approved(var id, var amount) -> "Approved %s for %s".formatted(id, amount);
        case Declined(var reason)         -> "Declined: " + reason;
        case RequiresAction(var url)      -> "Action required at " + url;
    };
}
```

This is also how you replace a nullable-result-plus-error-code API with something honest.

## Enums that carry behavior

A Java enum is a full class. Put the behavior with the value rather than switching on it
elsewhere.

```java
public enum PricingTier {
    STANDARD(BigDecimal.ONE),
    PREMIUM(new BigDecimal("1.20")),
    DISCOUNT(new BigDecimal("0.80"));

    private final BigDecimal multiplier;

    PricingTier(BigDecimal multiplier) { this.multiplier = multiplier; }

    public Money apply(Money amount) { return amount.times(multiplier); }
}
```
Every magic multiplier now has a name and exactly one home, and `tier.apply(amount)` reads at
every call site.

## Equality, hashing, and toString

- **Use records** and get all three, correct, for free.
- If you must write `equals`, write `hashCode` in the same edit — the contract is not optional,
  and violating it corrupts every `HashMap` the object touches.
- Base both on the same fields, and prefer immutable fields; a mutable field in a hash key is a
  silent data-loss bug.
- Write a **useful `toString`**: it appears in every log line and test failure. Include the
  identifying fields; **exclude secrets and PII.**

```java
@Override public String toString() {
    return "Customer[id=%s, tier=%s]".formatted(id, tier);   // no email, no token
}
```

## Concurrency

- **Prefer immutability** — an immutable object needs no synchronization at all.
- **Use `java.util.concurrent`**: `ConcurrentHashMap`, `CopyOnWriteArrayList`, `AtomicLong`,
  `ExecutorService`, `CompletableFuture`, `StructuredTaskScope`. Hand-rolled `synchronized`
  loses to the library on both correctness and throughput.
- **Never share mutable state without a plan.** Confine it, copy it, or lock it — and say which
  in a comment on the field.
- **Keep synchronized blocks tiny**, and never call unknown code (a listener, a callback) while
  holding a lock — that's how deadlocks are made.
- **Separate the concurrency from the logic.** A class manages threading or business rules, not
  both.
- **Test it**: jcstress for interleavings, repeated runs under load, more threads than cores.
  Treat any intermittent failure as a real bug, never as flakiness.

## Worked example

**Before** — a service class doing everything, with hidden dependencies and null returns:

```java
public class OrderManager {
    public static final double TAX = 0.08;
    private Connection conn;

    public OrderManager() throws SQLException {
        conn = DriverManager.getConnection(System.getenv("DSN"));
    }

    public String process(String orderId, boolean express) throws Exception {
        PreparedStatement ps = conn.prepareStatement("SELECT * FROM orders WHERE id = ?");
        ps.setString(1, orderId);
        ResultSet rs = ps.executeQuery();
        if (!rs.next()) return null;
        double total = rs.getDouble("total");
        total = total * (1 + TAX);
        if (express) total = total + 15.0;
        new EmailClient().send(rs.getString("email"), "Total: " + total);
        return "OK:" + total;
    }
}
```
Smells: construction of infrastructure in the constructor (F/G), a flag argument (F3), `double`
for money (G26), a magic `15.0` (G25), null return, leaked JDBC resources, four responsibilities
in one method (G30), a stringly-typed result, and nothing testable.

**After**

```java
public record ShippingOption(String name, Money surcharge) {
    public static final ShippingOption STANDARD = new ShippingOption("standard", Money.ZERO);
    public static final ShippingOption EXPRESS  = new ShippingOption("express", Money.of("15.00"));
}

public class OrderPricing {
    private static final BigDecimal TAX_RATE = new BigDecimal("0.08");

    public Money totalFor(Order order, ShippingOption shipping) {
        Money withTax = order.subtotal().times(BigDecimal.ONE.add(TAX_RATE));
        return withTax.add(shipping.surcharge());
    }
}

public class OrderService {
    private final OrderRepository orders;
    private final Notifier notifier;
    private final OrderPricing pricing;

    public OrderService(OrderRepository orders, Notifier notifier, OrderPricing pricing) {
        this.orders   = Objects.requireNonNull(orders);
        this.notifier = Objects.requireNonNull(notifier);
        this.pricing  = Objects.requireNonNull(pricing);
    }

    /**
     * Prices `orderId` for `shipping` and notifies the customer.
     *
     * @return the total charged
     * @throws OrderNotFoundException if no order has that id
     */
    public Money confirm(OrderId orderId, ShippingOption shipping) {
        Order order = orders.findById(orderId)
                            .orElseThrow(() -> new OrderNotFoundException(orderId));
        Money total = pricing.totalFor(order, shipping);
        notifier.sendReceipt(order.customerEmail(), total);
        return total;
    }
}
```

Now: `OrderPricing` is a pure calculation testable in three lines with no mocks; `OrderService`
has one responsibility and three explicit dependencies; the flag argument became a value type that
reads at the call site; money is `BigDecimal`; the surcharge has a name; absence is an exception
rather than a null; and JDBC lives behind `OrderRepository` where it can be faked.

## Toolchain

| Purpose | Tool |
|---|---|
| Format | `google-java-format` via Spotless (`./gradlew spotlessApply`) |
| Style | Checkstyle (`assets/checkstyle.xml`) |
| Bugs | SpotBugs, Error Prone, NullAway |
| Tests | JUnit 5 + AssertJ + Mockito (sparingly) |
| Coverage | JaCoCo, branch coverage; PIT for mutation testing |
| Architecture | ArchUnit — enforce layering and dependency rules as tests |

Fail the build on: compiler warnings (`-Xlint:all -Werror`), Checkstyle violations, SpotBugs
high-priority findings. Rules that are only advisory get ignored.

Run `bash scripts/setup_toolchain.sh java .` for a working starting config.
