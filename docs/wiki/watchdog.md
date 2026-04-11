# Zwanski Watchdog (dashboard integration)

The **Watchdog** monorepo ships as `zwanski-watchdog/` inside this repository. It is a **separate product** (scanner → Redis → classifier → Postgres, Next.js web, Fastify API) from the port **1337** dashboard, but the dashboard can **probe** it and **start** common tasks safely.

## Prerequisites

- `zwanski-watchdog/` present next to `server.py`
- Docker (for infra), Go 1.22+ (scanner), Node/pnpm (API + web), Python 3.12+ (classifier) — as described in `zwanski-watchdog/README.md`

## Environment variables

Set in the **Bug Bounty platform** `.env` (not only Watchdog’s):

| Variable | Default | Purpose |
|----------|---------|---------|
| `WATCHDOG_API_URL` | `http://127.0.0.1:4000` | Fastify API base URL |
| `WATCHDOG_WEB_URL` | `http://127.0.0.1:3000` | Next.js web |
| `WATCHDOG_CLASSIFIER_URL` | `http://127.0.0.1:8001` | Classifier service |

## HTTP API (platform)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/watchdog/info` | Paths, install flag, docs link |
| GET | `/api/watchdog/status` | Reachability: API `/health`, web `/`, classifier `/health` |
| POST | `/api/watchdog/run` | Body: `{"task":"<key>"}` — **fixed keys only** (no arbitrary shell) |

### Allowlisted `task` keys

| Key | What it runs (conceptually) |
|-----|-------------------------------|
| `compose_up` | `docker compose up -d` for postgres, redis, elasticsearch, minio, ipfs in `zwanski-watchdog/infra` |
| `compose_down` | `docker compose down` in infra |
| `pnpm_install` | `pnpm install` at Watchdog root |
| `api_dev` | `pnpm --filter @zwanski/api dev` |
| `web_dev` | `pnpm --filter @zwanski/web dev` |
| `classifier_dev` | pip install + `uvicorn` on port 8001 |
| `scanner_dry` | Go scanner dry-run (S3 module) |
| `scanner_help` | Scanner CLI help |

Tasks are executed by the same task runner as Arsenal; open the **Terminal** tab to view stdout/stderr.

## First-time Watchdog flow

1. **Docker infra up** from the Watchdog tab (or follow `zwanski-watchdog/README.md`).
2. Apply DB migration and seed if using the API (`pnpm` commands in Watchdog README).
3. **pnpm install**, then **API dev** / **Web dev** / **Classifier** as needed.
4. Status cards turn **UP** when each service responds.

## Security note

`/api/watchdog/run` never accepts user-supplied shell strings — only the keys above. To add tasks, extend the allowlist in `server.py` and document here.
