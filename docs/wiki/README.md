# ZWANSKI.BB documentation wiki

In-repo wiki for the **ZWANSKI Bug Bounty** platform (Flask command center + methodology).  
Browse on GitHub: [docs/wiki](https://github.com/zwanski2019/zwanski-Bug-Bounty/tree/main/docs/wiki).

## Pages

| Page | Description |
|------|-------------|
| [Dashboard UI](dashboard-ui.md) | Tabs: Command, Telemetry, Agentic, Arsenal, Watchdog, Terminal, Intel AI, Reports, Config |
| [Watchdog integration](watchdog.md) | Embedded **zwanski-watchdog** monorepo: status API, allowlisted tasks, env vars |
| [HTTP API](api.md) | REST routes for tools, agents, AI, KB, warmap, system health |
| [Configuration](configuration.md) | `.env`, OpenRouter, shadow mode, git sync, OpenClaw |

## Methodology (separate tree)

The phase-based hunting methodology lives in the repo root folders `00-setup/` … `08-reporting/` and in the main [README](../../README.md). This wiki focuses on **running and extending the software**.

## GitHub Wiki (optional)

GitHub’s separate Wiki tab can mirror these files: copy sections into wiki pages and link back here for versioned docs.

## Roadmap ideas

- Per-program vaults and scoped KB collections  
- Saved “playbooks” (tool chains) with one-click run from Arsenal  
- Export warmap snapshot as PNG/SVG for reports  
- Webhook notifications when agent pipeline completes or severity threshold hits  

Contributions: PRs against `docs/wiki/` welcome.
