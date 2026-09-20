# .NET Solution Template

Drop-in Claude Code configuration for a Senior .NET Developer working on a modern
.NET solution. Copy `CLAUDE.md`, `.editorconfig`, `global.json`, `Directory.Build.props`
and `.claude/` into the root of a new or existing solution and adjust the project
names below.

## Tech Stack
- .NET 10 (LTS), C# 13/14, nullable reference types enabled
- ASP.NET Core minimal APIs
- EF Core 10 (provider TBD per project — Npgsql/SQL Server)
- MediatR for CQRS, FluentValidation for input validation
- xUnit + FluentAssertions + Testcontainers for testing, NSubstitute for test doubles

## Architecture (Clean Architecture / DDD)
- `src/Domain` — entities, value objects, domain events, domain exceptions. Zero
  external dependencies (no EF Core, no ASP.NET Core).
- `src/Application` — use cases as MediatR Commands/Queries + handlers, DTOs,
  interfaces implemented by Infrastructure, FluentValidation validators. Depends
  only on Domain.
- `src/Infrastructure` — EF Core `DbContext`, entity configurations, repository
  implementations, external service clients (email, storage, etc.).
- `src/Presentation` (or `src/Api`) — minimal API endpoints, DI composition root,
  middleware. Thin: maps HTTP to MediatR requests, no business logic.
- `tests/` mirrors `src/`: `Domain.UnitTests`, `Application.UnitTests`,
  `Infrastructure.IntegrationTests` (Testcontainers), `Api.IntegrationTests`.

Dependency rule: dependencies point inward only — Presentation/Infrastructure →
Application → Domain. Domain and Application must never reference Infrastructure
or Presentation types.

## Coding Rules
- Records for value objects, DTOs, and MediatR Commands/Queries; primary
  constructors for simple classes
- One public type per file; file-scoped namespaces
- MediatR handlers are `internal sealed`; validation lives in FluentValidation
  validators wired through a pipeline behavior, never inline in handlers
- Async all the way: suffix async methods `Async`, always accept and forward
  `CancellationToken`
- No `DbSet`, migrations, or other EF Core specifics outside `Infrastructure`

## Commands
- `dotnet build` — build the solution
- `dotnet test` — run all tests
- `dotnet format` — apply code style fixes
- `dotnet run --project src/Presentation` — run the API locally
- `dotnet ef migrations add <Name> -p src/Infrastructure -s src/Presentation`
- `dotnet ef database update -p src/Infrastructure -s src/Presentation`

## Testing
- Unit-test Domain and Application with no test doubles for entities/value objects
- Use Testcontainers for Infrastructure/API integration tests that need a real
  database — never mock the database in integration tests
- Run `dotnet test` after any change touching Domain or Application

## Software Development Life Cycle

GitHub Issues/PRs are the board. Use the skill matching the current phase
instead of improvising:

1. **Planning** — establish goals, feasibility, scope, risks, MVP →
   `sdlc-planning` (project skill, below)
2. **Requirement Analysis** — requirements, user stories, acceptance
   criteria → `sdlc-planning`
3. **Design** — system architecture per the Architecture section above;
   architecture decisions (new dependency, DB choice, sync vs async) →
   `architecture` (ADR); non-trivial service/API design → `system-design`
4. **Development (Coding)** — build per the Coding Rules above; C#/ASP.NET
   Core/EF Core/CQRS specifics → `dotnet-csharp`; any git operation → `git-cli`
5. **Testing** — unit/integration tests per the Testing section above;
   expanding coverage → `testing-strategy`; before opening a PR →
   `code-review`
6. **Deployment** — see the Deployment section below; before merging to
   main or cutting a release → `deploy-checklist`
7. **Maintenance & Support** — production bug / "works on staging not prod"
   → `debug`; outage or `sev1`/`sev2` → `incident-response`; prioritizing
   refactors vs new work → `tech-debt`; runbooks/API docs/ADR write-ups →
   `documentation`

Cross-cutting: daily status update from commits/PRs/issues → `standup`.

## Deployment

- CI builds a container image via multi-stage `Dockerfile` (`dotnet publish -c
  Release`), tagged with the commit SHA — never deploy an untagged/`latest` image
- Apply EF Core migrations as a separate pipeline step before the new version
  starts (`dotnet ef database update`); never call `Database.Migrate()` from
  `Program.cs` in production
- Expose `/health` (liveness) and `/health/ready` (readiness, checks DB/
  dependencies) via `Microsoft.Extensions.Diagnostics.HealthChecks`
- Roll out behind health checks (rolling/blue-green); rollback = redeploy the
  previous image tag, not a manual hotfix
- Structured logging (Serilog) and OpenTelemetry traces/metrics from
  `Presentation` and `Infrastructure` — required before a feature is
  considered deployable, not added after an incident

## Important Rules
- NEVER add a project reference from Domain or Application to Infrastructure or Presentation
- IMPORTANT: all Commands/Queries are validated via a shared MediatR pipeline
  behavior, not per-handler `if` checks
- Treat compiler warnings as errors (`Directory.Build.props`) — don't suppress
  with `#pragma` unless the warning is a documented false positive
