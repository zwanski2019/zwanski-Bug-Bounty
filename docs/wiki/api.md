# HTTP API reference (ZWANSKI.BB)

## Purpose

Operational API reference for dashboard integrations, automation scripts, and troubleshooting.

Base URL: `http://127.0.0.1:1337` (unless `PORT` is changed).

> Not every route is listed - see `server.py` for the full set. This page covers primary integration points.

## Config & tools

| Method | Path | Notes |
|--------|------|--------|
| GET/POST | `/api/config` | Session AI settings |
| GET | `/api/setup/checklist` | First-launch setup wizard checklist |
| POST | `/api/setup/decision` | Persist install/configure/skip decision |
| POST | `/api/setup/complete` | Mark setup wizard completed |
| GET | `/api/tools` | Tool registry / status |
| GET | `/api/prompt-templates` | Prompt templates |

## Execution & tasks

| Method | Path | Notes |
|--------|------|--------|
| POST | `/api/run` | Run registered tool / command |
| GET | `/api/tasks` | List tasks |
| GET | `/api/tasks/<id>` | Task detail |
| POST | `/api/tasks/<id>/abort` | Abort |
| GET | `/api/term/sessions` | Terminal session list (tmux-backed metadata) |
| POST | `/api/term/<id>/kill` | Kill terminal session |

## System

| Method | Path | Notes |
|--------|------|--------|
| GET | `/api/health` | Aggregated tool / integration health |
| GET | `/api/system/health` | Host-oriented health |
| GET | `/api/system/processes` | Process snapshot |
| GET | `/api/control/status` | Control plane status |
| POST | `/api/control/restart` | Restart |
| POST | `/api/control/stop` | Stop |

## Agents & reports

| Method | Path | Notes |
|--------|------|--------|
| POST | `/api/agent/run` | Start pipeline |
| GET | `/api/agent` | List pipelines |
| GET | `/api/agent/<pipeline_id>` | Pipeline status |
| POST | `/api/report/finalize` | Finalize report |

## AI & KB

| Method | Path | Notes |
|--------|------|--------|
| POST | `/api/ai/chat` | Chat completion |
| POST | `/api/ai/analyze` | Analysis |
| POST | `/api/ai/report` | Report-oriented completion |
| POST | `/api/ai/grade` | Grade finding text |
| POST | `/api/ai/rag-analyze` | RAG + analysis |
| POST | `/api/ai/exploit-chain` | Suggest chains from finding |
| POST | `/api/kb/query` | Knowledge base query |

## Maps & bridges

| Method | Path | Notes |
|--------|------|--------|
| GET | `/api/warmap` | Graph data for War map |
| GET | `/api/openclaw/commands` | OpenClaw bridge manifest (`openclaw_bridge.json`) |

## Watchdog

| Method | Path | Notes |
|--------|------|--------|
| GET | `/api/watchdog/info` | Meta |
| GET | `/api/watchdog/status` | Service probes |
| POST | `/api/watchdog/run` | Allowlisted tasks |

## Findings

| Method | Path | Notes |
|--------|------|--------|
| POST | `/api/findings/confirm` | Confirm severity / trigger side effects (e.g. git sync rules) |

## WebSocket

Socket.IO is used for terminal/task streaming (namespace `/`); connect with the same origin as the UI.

## Quick health checks

```bash
curl http://127.0.0.1:1337/api/health
curl http://127.0.0.1:1337/api/system/health
curl http://127.0.0.1:1337/api/watchdog/status
```

## Related pages

- [Dashboard UI](dashboard-ui.md)
- [Watchdog integration](watchdog.md)
- [Troubleshooting runbook](troubleshooting.md)
