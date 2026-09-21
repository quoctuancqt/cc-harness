# cc-harness — .NET Senior Developer Claude Code Template

Reusable Claude Code configuration for .NET solutions built with Clean
Architecture, DDD and CQRS on the latest LTS runtime (.NET 10).

## Usage

Copy these into the root of a new or existing solution:

- `CLAUDE.md` — persona, stack, architecture, rules, a Software Development
  Life Cycle map telling Claude which skill to use at each of the 7 phases,
  and a Deployment section (container build, migrations, health checks)
- `.claude/settings.json` — pre-approved `dotnet`/`git`/`gh` (read-only) commands
- `.claude/skills/` — all 12 skills the harness relies on, vendored locally so
  the template is self-contained (works even without the `engineering`
  plugin or org-synced skills installed on the account that opens it):
  `sdlc-planning` (project-authored), `architecture`, `system-design`,
  `dotnet-csharp`, `git-cli`, `testing-strategy`, `open-code-review-delegate`,
  `deploy-checklist`, `debug`, `incident-response`, `tech-debt`,
  `documentation`, `standup`
- `global.json` — pins the .NET SDK to the 10.x feature band
- `Directory.Build.props` — shared build settings (nullable, analyzers, warnings-as-errors)
- `.editorconfig` — C# formatting and naming conventions

The 7-phase cycle maps like this:

| Phase | Covered by |
| --- | --- |
| 1. Planning | `sdlc-planning` skill |
| 2. Requirement Analysis | `sdlc-planning` skill |
| 3. Design | CLAUDE.md Architecture section + `architecture`, `system-design` skills |
| 4. Development (Coding) | CLAUDE.md Coding Rules section + `dotnet-csharp`, `git-cli` skills |
| 5. Testing | CLAUDE.md Testing section + `testing-strategy`, `open-code-review-delegate` skills |
| 6. Deployment | CLAUDE.md Deployment section + `deploy-checklist` skill |
| 7. Maintenance & Support | `debug`, `incident-response`, `tech-debt`, `documentation` skills |

`standup` is cross-cutting (daily status from commits/PRs/issues). See the
Software Development Life Cycle section of `CLAUDE.md` for the exact
trigger per phase.

`dotnet-csharp`, `architecture`, `system-design`, `git-cli`,
`testing-strategy`, `deploy-checklist`, `debug`, `incident-response`,
`tech-debt`, `documentation`, and `standup` are vendored verbatim from this
account's org-synced skills and the `engineering` plugin (marketplace
`knowledge-work-plugins`) as of 2026-09-20. Re-sync them manually if the
originals get updated. The Mantu-specific `dev-workflow` skill was
deliberately **not** vendored — it targets .NET 8 + a Vue 3/Quasar frontend,
which doesn't match this .NET 10, backend-only template.

`open-code-review-delegate` is vendored verbatim from
[alibaba/open-code-review](https://github.com/alibaba/open-code-review)
(Apache-2.0), file `skills/open-code-review-delegate/SKILL.md`, as of
2026-09-21. It runs OCR's **Delegation Mode**: the `ocr` CLI only does
deterministic file selection and rule resolution (`ocr delegate preview`,
`ocr delegate rule <files>`); Claude performs the actual review itself using
its own reasoning, so no OCR LLM endpoint or API key is configured. Requires
the `ocr` CLI (`npm install -g @alibaba-group/open-code-review`) and Git
&gt;= 2.41 on the machine running Claude Code.

After copying, update `CLAUDE.md`'s project name, EF Core provider (Postgres/SQL
Server/etc.) and any project-specific commands, then scaffold the solution to
match the `src/Domain`, `src/Application`, `src/Infrastructure`,
`src/Presentation`, `tests/` layout it describes.
