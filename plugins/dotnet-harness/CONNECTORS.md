# Connectors

## How tool references work

Some vendored skills (`architecture`, `debug`, `deploy-checklist`,
`incident-response`, `standup`) use `~~category` as a placeholder for whatever
tool you connect in that category. For example, `~~source control` might mean
GitHub, GitLab, or any other VCS with an MCP server.

These skills are **tool-agnostic** — they describe workflows in terms of
categories (source control, monitoring, project tracker, etc.) rather than
specific products. Unlike the upstream `engineering` plugin they were vendored
from, **this plugin's `.mcp.json` doesn't pre-configure any of these
categories** — it only registers `context7` (library docs), which none of
these skills reference. Connect a server per category yourself (via `claude
mcp add` or your account's connector settings) to unlock the related
functionality; without one, the skill falls back to asking you for that
information directly.

## Connectors used by vendored skills

| Category | Placeholder | Included servers | Other options |
|----------|-------------|-----------------|---------------|
| Chat | `~~chat` | — | Slack, Microsoft Teams |
| Source control | `~~source control` | — | GitHub, GitLab, Bitbucket |
| Project tracker | `~~project tracker` | — | Linear, Asana, Atlassian (Jira/Confluence), Shortcut, ClickUp |
| Knowledge base | `~~knowledge base` | — | Notion, Confluence, Guru, Coda |
| Monitoring | `~~monitoring` | — | Datadog, New Relic, Grafana, Splunk |
| Incident management | `~~incident management` | — | PagerDuty, Opsgenie, Incident.io, FireHydrant |
| CI/CD | `~~CI/CD` | — | CircleCI, GitHub Actions, Jenkins, BuildKite |
