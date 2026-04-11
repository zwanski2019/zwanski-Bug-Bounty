# Configuration

## `.env`

Copy `.env.example` → `.env` at the **Bug Bounty platform root** (where `server.py` lives).

### Required for AI features

- `OPENROUTER_API_KEY` — default provider for Intel AI tab  
- Optional: `OPENROUTER_API_URL`, `OPENROUTER_MODEL`

### Server

- `PORT` — default `1337`
- `FLASK_ENV`, `SECRET_KEY` — standard Flask

### GitHub (optional)

- `GITHUB_TOKEN`, `GITHUB_REPO` — automation / sync features

### OpenClaw (optional)

- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- `WHATSAPP_SESSION_PATH`
- `DISCORD_BOT_TOKEN`, `DISCORD_CHANNEL_ID`
- Flags such as `OPENCLAW_ENABLED`, `OPENCLAW_AUTO_RECON`, etc. (see `.env.example`)

### Watchdog URLs

- `WATCHDOG_API_URL`, `WATCHDOG_WEB_URL`, `WATCHDOG_CLASSIFIER_URL` — used by `/api/watchdog/status` (see [watchdog.md](watchdog.md))

### Shadow / ghost mode

- `SHADOW_MODE=1` — jitter and rotated client headers on in-pipeline HTTP probes (`shadow_client.py` integration). Use only where policy allows.

### Git auto-sync

- `AUTO_GIT_SYNC=1` — commits/pushes after certain report/finding events. **Recommended only on private forks**; review legal and program rules before enabling.

## `openclaw_bridge.json`

Mobile C2 command allowlists and metadata; served read-only at `GET /api/openclaw/commands`. Adjust to match your OpenClaw deployment.

## Knowledge base

Local RAG uses files under the platform KB path (see `zwanski_kb.py` and server wiring). Keep sensitive notes out of the indexed tree if sharing the repo.

## Production

See [PRODUCTION.md](../../PRODUCTION.md) and [DOCKER.md](../../DOCKER.md) for deployment patterns. WebSocket + workers must match your WSGI/ASGI stack (e.g. Gunicorn + eventlet as documented).
