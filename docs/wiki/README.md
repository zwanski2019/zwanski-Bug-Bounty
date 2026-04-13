# ZWANSKI.BB Docs Home

In-repo operational documentation for the ZWANSKI.BB platform.

- Source of truth: `docs/wiki/` in this repository
- Optional mirror target: GitHub Wiki tab
- Platform scope: dashboard, APIs, task execution, Watchdog integration, and config

## Start Here

If you are new, follow this order:

1. [Dashboard UI](dashboard-ui.md) - tabs, workflows, and operator controls
2. [Configuration](configuration.md) - `.env`, API keys, feature flags
3. [Watchdog integration](watchdog.md) - infra bring-up and allowlisted actions
4. [HTTP API](api.md) - routes used by UI and integrations
5. [Troubleshooting runbook](troubleshooting.md) - fast resolution paths
6. [Wiki Home page](Home.md) - GitHub Wiki landing page content

## Role-based Navigation

### Operator

- Bring platform online: [Configuration](configuration.md)
- Start Watchdog stack: [Watchdog integration](watchdog.md)
- Validate health endpoints: [HTTP API](api.md)
- Resolve issues quickly: [Troubleshooting runbook](troubleshooting.md)

### Developer

- UI behavior and tab contracts: [Dashboard UI](dashboard-ui.md)
- Route references and payloads: [HTTP API](api.md)
- Environment and feature toggles: [Configuration](configuration.md)

### Security/Research

- Agentic pipeline endpoints: [HTTP API](api.md)
- Tooling and execution controls: [Dashboard UI](dashboard-ui.md)
- Operational constraints: [Watchdog integration](watchdog.md)

## Quality Standard

All wiki pages should include:

- Purpose and scope
- Prerequisites
- Copy-paste quickstart
- Verification checks
- Failure modes and fixes
- Related pages

## Methodology Note

Hunting methodology content remains in the root phase directories (`00-setup/` to `08-reporting/`) and main [README](../../README.md). This wiki documents software operations and platform behavior.
