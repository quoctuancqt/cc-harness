---
name: sdlc-planning
description: Run the Planning and Analysis phases of the software development cycle for this .NET solution — scoping and prioritizing work, writing/splitting requirements or user stories, sizing effort, and checking whether an item is ready to move into design/implementation. Use when the user wants to plan a release or iteration, write or split a requirement or ticket, estimate/size work, or check readiness before starting design or coding. Trigger on "plan this", "write a requirement", "write a user story", "split this ticket", "estimate this", "is this ready for dev", "definition of ready".
---

# Planning & Analysis for a Clean Architecture .NET Solution

Covers phases 1 (Planning) and 2 (Analysis) of the software development
cycle. Design, Implementation, Testing & Integration, and Maintenance are
covered by the `architecture`/`system-design`, `dev-workflow`,
`testing-strategy`/`code-review`, and `debug`/`incident-response`/
`deploy-checklist`/`tech-debt`/`documentation` skills respectively — see the
Software Development Cycle section of `CLAUDE.md`.

## Planning: Scoping and Prioritizing

1. State the goal of the release/iteration in one sentence before listing work items.
2. Order candidate work by value vs. cost, not by request order or recency.
3. Confirm capacity (people × time − known unavailability) before committing
   to a scope; don't let a wish list become a commitment.
4. Flag any item that depends on work outside this repo/team — those need
   their dependency resolved or sequenced before planning further.

## Analysis: Requirements and Story Slicing

A requirement is ready to size when it passes INVEST: Independent,
Negotiable, Valuable, Estimable, Small, Testable.

When asked to write or split a requirement/story:
1. State the user-facing value in one sentence ("As a X, I can Y so that Z").
2. Slice by thin end-to-end capability (e.g., "create order with no
   discounts" then "apply discount codes"), not by architecture layer
   ("build the domain model" then "build the API").
3. Flag items that touch more than one bounded context or require a new
   `Infrastructure` dependency (new external service, new EF Core provider)
   — these need an ADR (`architecture` skill) during Design before sizing.
4. Write acceptance criteria as Given/When/Then, phrased so they map directly
   to an integration test in `tests/*.IntegrationTests`.

## Estimation

- Use relative sizing (story points, T-shirt sizes), not hours.
- Anchor new items against a previously completed item of known size, not
  from first principles.
- If an item can't be sized because of unknowns, it isn't ready — scope a
  time-boxed spike instead and size that.

## Definition of Ready (before moving to Design/Implementation)

- Acceptance criteria are Given/When/Then and testable
- Dependencies (other teams, external APIs, migrations) are identified
- No open architecture question — if one exists, resolve it in Design first
- Sized, not left as "unknown"
