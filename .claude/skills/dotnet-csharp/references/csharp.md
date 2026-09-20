# C# Language Reference

Source: https://learn.microsoft.com/en-us/dotnet/csharp/tour-of-csharp/

## Table of Contents
1. [Language Overview](#overview)
2. [Type System](#type-system)
3. [Object-Oriented Programming](#oop)
4. [Functional Techniques](#functional)
5. [Async Programming](#async)
6. [LINQ](#linq)
7. [Modern C# Features (C# 9–14)](#modern)
8. [Common Patterns](#patterns)

---

## 1. Language Overview {#overview}

C# is a strongly-typed, component-oriented language on the .NET platform. Key characteristics:
- **Unified type system**: All types (including primitives) inherit from `object`
- **Memory safety**: Garbage collected; `unsafe` code opt-in only
- **Cross-platform**: Runs on Windows, Linux, macOS via .NET runtime
- **Interoperable**: P/Invoke for native libs; COM interop on Windows

```csharp
// Top-level statements (C# 9+) — no explicit Main needed
Console.WriteLine("Hello, World!");
```

---

## 2. Type System {#type-system}

### Value Types vs Reference Types
```csharp
// Value types — stack allocated, copied on assignment
int x = 42;
bool flag = true;
struct Point { public int X, Y; }

// Reference types — heap allocated, reference copied
string s = "hello";
class Person { public string Name { get; set; } }
```

### Nullable Types
```csharp
int? nullableInt = null;           // nullable value type
string? nullableStr = null;        // nullable reference type (requires <Nullable>enable)

// Null-coalescing
string result = nullableStr ?? "default";
string result2 = nullableStr ?? throw new ArgumentNullException();

// Null-conditional
int? len = nullableStr?.Length;
```

### Records (C# 9+)
```csharp
// Immutable by default, value-based equality
record Person(string FirstName, string LastName);

// With-expressions for non-destructive mutation
var person = new Person("John", "Doe");
var renamed = person with { FirstName = "Jane" };

// Mutable record struct (C# 10+)
record struct Point(double X, double Y);
```

### Generics
```csharp
public class Stack<T>
{
    private readonly List<T> _items = new();
    public void Push(T item) => _items.Add(item);
    public T Pop()
    {
        var last = _items[^1];
        _items.RemoveAt(_items.Count - 1);
        return last;
    }
}

// Constraints
public T Max<T>(T a, T b) where T : IComparable<T> =>
    a.CompareTo(b) >= 0 ? a : b;
```

---

## 3. Object-Oriented Programming {#oop}

### Classes and Inheritance
```csharp
public abstract class Shape
{
    public abstract double Area { get; }
    public virtual string Describe() => $"Shape with area {Area:F2}";
}

public sealed class Circle : Shape
{
    public double Radius { get; }
    public Circle(double radius) => Radius = radius;
    public override double Area => Math.PI * Radius * Radius;
}
```

### Interfaces
```csharp
public interface IRepository<T> where T : class
{
    Task<T?> GetByIdAsync(int id);
    Task<IEnumerable<T>> GetAllAsync();
    Task AddAsync(T entity);
    Task UpdateAsync(T entity);
    Task DeleteAsync(int id);
}
```

### Properties and Indexers
```csharp
public class Temperature
{
    private double _celsius;
    
    public double Celsius
    {
        get => _celsius;
        set => _celsius = value < -273.15
            ? throw new ArgumentOutOfRangeException()
            : value;
    }
    
    public double Fahrenheit
    {
        get => _celsius * 9 / 5 + 32;
        set => Celsius = (value - 32) * 5 / 9;
    }
}
```

---

## 4. Functional Techniques {#functional}

### Pattern Matching
```csharp
// Switch expression (C# 8+)
string Classify(object obj) => obj switch
{
    int n when n < 0 => "negative",
    int n when n == 0 => "zero",
    int => "positive integer",
    string s => $"string of length {s.Length}",
    null => "null",
    _ => "unknown"
};

// Property patterns
string Describe(Point p) => p switch
{
    { X: 0, Y: 0 } => "origin",
    { X: 0 } => "on Y axis",
    { Y: 0 } => "on X axis",
    _ => $"({p.X}, {p.Y})"
};

// List patterns (C# 11+)
string DescribeList(int[] nums) => nums switch
{
    [] => "empty",
    [var single] => $"one element: {single}",
    [var first, .., var last] => $"starts {first}, ends {last}"
};
```

### Delegates and Events
```csharp
// Func and Action
Func<int, int, int> add = (a, b) => a + b;
Action<string> print = Console.WriteLine;

// Events
public class Button
{
    public event EventHandler<ClickEventArgs>? Clicked;
    protected virtual void OnClicked(ClickEventArgs e) =>
        Clicked?.Invoke(this, e);
}
```

---

## 5. Async Programming {#async}

```csharp
// Basic async/await
public async Task<string> FetchDataAsync(string url)
{
    using var client = new HttpClient();
    return await client.GetStringAsync(url);
}

// Parallel async with WhenAll
public async Task<int[]> FetchAllAsync(IEnumerable<string> urls)
{
    var tasks = urls.Select(url => FetchLengthAsync(url));
    return await Task.WhenAll(tasks);
}

// Cancellation token pattern
public async Task<string> SearchAsync(string query, CancellationToken ct = default)
{
    await Task.Delay(100, ct);  // pass ct to all async calls
    return $"Results for {query}";
}

// ValueTask for hot paths (avoids allocation when result is synchronous)
public async ValueTask<int> GetCachedAsync(string key)
{
    if (_cache.TryGetValue(key, out int val)) return val;
    return await FetchFromDbAsync(key);
}

// Async streams (C# 8+)
public async IAsyncEnumerable<int> GenerateAsync([EnumeratorCancellation] CancellationToken ct = default)
{
    for (int i = 0; i < 100; i++)
    {
        await Task.Delay(10, ct);
        yield return i;
    }
}

// Consuming async streams
await foreach (var item in GenerateAsync(cancellationToken))
{
    Console.WriteLine(item);
}
```

**Common Pitfalls:**
- Never use `.Result` or `.Wait()` — causes deadlocks in sync contexts
- Always pass `CancellationToken` through the call chain
- Use `ConfigureAwait(false)` in library code (not needed in ASP.NET Core)
- `async void` only for event handlers; use `async Task` everywhere else

---

## 6. LINQ {#linq}

```csharp
var numbers = Enumerable.Range(1, 100);

// Query syntax
var evens = from n in numbers
            where n % 2 == 0
            select n * n;

// Method syntax (more common)
var result = numbers
    .Where(n => n % 2 == 0)
    .Select(n => n * n)
    .Take(10)
    .ToList();

// Grouping
var grouped = people
    .GroupBy(p => p.Department)
    .Select(g => new { Dept = g.Key, Count = g.Count(), Avg = g.Average(p => p.Salary) });

// Joins
var joined = from o in orders
             join c in customers on o.CustomerId equals c.Id
             select new { o.OrderDate, c.Name };

// Aggregation
var stats = new
{
    Count = numbers.Count(),
    Sum = numbers.Sum(),
    Min = numbers.Min(),
    Max = numbers.Max(),
    Avg = numbers.Average()
};

// Any / All / Contains
bool anyAdults = people.Any(p => p.Age >= 18);
bool allAdults = people.All(p => p.Age >= 18);
```

**Performance tips:**
- Use `AsNoTracking()` with EF Core for read-only queries
- Prefer `FirstOrDefault` over `SingleOrDefault` when uniqueness isn't critical
- `ToList()` / `ToArray()` materializes — be careful with large datasets
- Use `IQueryable<T>` over `IEnumerable<T>` for DB queries (enables server-side filtering)

---

## 7. Modern C# Features (C# 9–14) {#modern}

### C# 9
- **Records**: `record Person(string Name, int Age);`
- **Init-only setters**: `public string Name { get; init; }`
- **Top-level statements**: No `Main` method needed
- **Pattern matching enhancements**: `not`, `and`, `or`

### C# 10
- **Global using**: `global using System.Collections.Generic;`
- **File-scoped namespaces**: `namespace MyApp;` (no braces)
- **Record structs**: `record struct Point(int X, int Y);`

### C# 11
- **Raw string literals**: `"""multi-line with "quotes"""""`
- **Required members**: `public required string Name { get; set; }`
- **Generic attributes**: `class ValidateAttribute<T> : Attribute`
- **List patterns**: `if (list is [1, 2, ..])`

### C# 12
- **Primary constructors** (for classes): `class Person(string name) { ... }`
- **Collection expressions**: `int[] arr = [1, 2, 3];`
- **Alias any type**: `using Point = (int X, int Y);`

### C# 13
- **`params` collections**: `void Print(params IEnumerable<string> items)`
- **`\e` escape sequence** for ESC character
- **`Lock` type** for thread synchronization

### C# 14 (preview)
- **Extensions**: Extend types in new ways
- **Field-backed properties**: `public string Name { get; set field; }`

---

## 8. Common Patterns {#patterns}

### Builder Pattern
```csharp
public class QueryBuilder
{
    private string _table = "";
    private readonly List<string> _conditions = new();
    
    public QueryBuilder From(string table) { _table = table; return this; }
    public QueryBuilder Where(string condition) { _conditions.Add(condition); return this; }
    public string Build() => $"SELECT * FROM {_table}" +
        (_conditions.Any() ? " WHERE " + string.Join(" AND ", _conditions) : "");
}

// Usage
var query = new QueryBuilder().From("Users").Where("Active = 1").Where("Age > 18").Build();
```

### Options Pattern
```csharp
public class SmtpOptions
{
    public const string SectionName = "Smtp";
    public string Host { get; set; } = "";
    public int Port { get; set; } = 587;
    public bool UseSsl { get; set; } = true;
}

// Registration
services.Configure<SmtpOptions>(config.GetSection(SmtpOptions.SectionName));

// Injection
public class EmailService(IOptions<SmtpOptions> options)
{
    private readonly SmtpOptions _smtp = options.Value;
}
```

### Result Pattern (avoid exceptions for control flow)
```csharp
public class Result<T>
{
    public bool IsSuccess { get; }
    public T? Value { get; }
    public string? Error { get; }
    
    private Result(bool success, T? value, string? error) =>
        (IsSuccess, Value, Error) = (success, value, error);
    
    public static Result<T> Ok(T value) => new(true, value, null);
    public static Result<T> Fail(string error) => new(false, default, error);
}
```
