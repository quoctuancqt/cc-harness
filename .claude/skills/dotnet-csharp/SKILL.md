---
name: dotnet-csharp
description: >
  Expert guidance for C#, ASP.NET Core, and .NET microservices architecture. Use this skill
  whenever the user asks about C# language features, syntax, LINQ, async/await, generics,
  pattern matching, records, or any C# programming question. Also trigger for ASP.NET Core
  topics: Minimal APIs, Razor Pages, MVC, Blazor, SignalR, gRPC, middleware, dependency injection,
  authentication, authorization, Kestrel, or web API design. Trigger for .NET microservices
  architecture questions: Docker containers, service decomposition, API gateways, event-driven
  architecture, resilience patterns (Polly, circuit breakers), service discovery, Domain-Driven
  Design (DDD), CQRS, or containerized .NET deployments. Use this even for broad .NET questions,
  "how do I build X in .NET", architecture decisions between monolith vs microservices, or
  any coding task in the C#/.NET ecosystem.
---

# .NET / C# / ASP.NET Core / Microservices Skill

This skill covers three tightly related areas. Read the relevant reference file(s) for deep guidance:

| Area | Reference File | When to Read |
|------|---------------|--------------|
| C# Language | `references/csharp.md` | Language syntax, features, LINQ, async, patterns |
| ASP.NET Core | `references/aspnetcore.md` | Web APIs, MVC, Blazor, middleware, DI, security |
| Microservices | `references/microservices.md` | Architecture, containers, Docker, resilience, DDD |
| CQRS & MediatR | `references/cqrs-mediatr.md` | CQRS pattern, MediatR setup, commands, queries, pipeline behaviors |

Always read the relevant reference file before answering complex questions. For questions spanning multiple areas, read multiple files.

---

## Quick Decision Guide

**C# language question?** → Read `references/csharp.md`  
**Web app / API / Blazor?** → Read `references/aspnetcore.md`  
**Architecture / containers / distributed systems?** → Read `references/microservices.md`  
**CQRS, MediatR, commands/queries, pipeline behaviors?** → Read `references/cqrs-mediatr.md`  
**Full-stack .NET app?** → Read all four

---

## General .NET Best Practices (always apply)

- Prefer `async`/`await` throughout; avoid `.Result` or `.Wait()` blocking calls
- Use dependency injection (built-in `IServiceCollection`) consistently
- Apply `IOptions<T>` pattern for configuration binding
- Prefer `record` types for immutable data transfer objects (DTOs)
- Use `ILogger<T>` for structured logging — never `Console.WriteLine` in production
- Target the latest stable .NET LTS release unless otherwise constrained
- Validate inputs early; use `FluentValidation` or Data Annotations
- Write unit tests with xUnit; use `Moq` or `NSubstitute` for mocking

---

## Code Style Defaults

Follow Microsoft C# coding conventions:
- PascalCase for types, methods, properties
- camelCase for local variables and parameters
- Prefix interfaces with `I` (e.g. `IUserService`)
- Use `var` when the type is obvious from the right-hand side
- Prefer expression-bodied members for simple getters/methods
- Use nullable reference types (`<Nullable>enable</Nullable>` in csproj)
- Organize `using` directives: System namespaces first, then third-party, then project

---

## When Generating Code

1. Always include relevant `using` statements
2. Show the minimal working example first, then explain
3. For ASP.NET Core, default to Minimal API style unless MVC/Razor is requested
4. For microservices, default to HTTP + message-based communication patterns
5. Include XML doc comments (`///`) on public APIs
6. Highlight any security considerations (e.g., SQL injection, CORS, secrets)
