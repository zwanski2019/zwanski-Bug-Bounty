# Dashboard UI (ZWANSKI.BB)

Default URL: `http://127.0.0.1:1337` (or `PORT` from `.env`).

## Top HUD

Live telemetry: CPU, RAM, network delta, active tasks, tool summary, War map node count.

## Sidebar tabs

### Command

- **War map** — Canvas graph built from `GET /api/warmap` (hosts, ports, edges parsed from tool streams).
- Primary actions: **Run scan**, **Restart** (calls control API).

### Telemetry

- System health fallback polling (`/api/system/health`, `/api/system/processes`).
- Process and resource views for the host running the dashboard.

### Agentic

- Start and monitor the multi-phase agent pipeline (`/api/agent/run`, `/api/agent/...`).
- Activity log and phase status.

### Arsenal

- Registered tools, command preview, Subdomain chain / OAuth mapper shortcuts.
- Executes via `/api/run` with server-side command wiring.

### Watchdog

- Status for optional **Zwanski Watchdog** stack (API, Web, Classifier) when running locally.
- Buttons queue **allowlisted** shell tasks; output streams in **Terminal**.
- See [watchdog.md](watchdog.md).

### Terminal

- xterm.js + Socket.IO multiplexed task output.
- Use **Multiplex all tasks** to follow every job, or focus on the current task id.

### Intel AI

- Chat (`/api/ai/chat`), grading (`/api/ai/grade`), RAG-assisted analysis (`/api/ai/rag-analyze`, `/api/kb/query`), exploit-chain hints (`/api/ai/exploit-chain`).
- Requires `OPENROUTER_API_KEY` (or compatible endpoint in Config).

### Reports

- Finalize report draft (`/api/report/finalize`) with target, optional pipeline id, platform.

### Config

- Session overrides for OpenRouter URL, model, key (persisted via `/api/config`).
- Notes for `SHADOW_MODE`, `AUTO_GIT_SYNC`, manual git push.

## Keyboard / UX tips

- After launching a Watchdog or long-running dev server, switch to **Terminal** to read logs.
- War map refreshes with warmap polling in the client; keep the Command tab open during active scans for best updates.
