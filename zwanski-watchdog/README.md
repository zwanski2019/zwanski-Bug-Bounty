# Zwanski Watchdog

Open-source **foundation** for an ethical, internet-scale leak **awareness** pipeline: scanner → Redis queue → classifier → PostgreSQL → disclosure workflow.  
Operator: **Mohamed Ibrahim (zwanski) / Zwanski Tech**. License: **MIT** (see `LICENSE`). Ethics: **`COVENANT.md`**.

> **Scope of this repository**  
> This monorepo implements **Phase 1 (partial/full)**, **Phase 2 (core + one S3 module)**, and **Phase 3 (classifier skeleton)** from the Zwanski Watchdog blueprint.  
> **Phases 4–5 are not implemented here.** Many Phase 2 modules (Pastebin scraping, wide port sweeps, unsolicited Firebase probing, etc.) require strict legal review and are **not shipped as automated exploit code**—extend modules only where you have clear authorization.

## Stack

| App | Tech |
|-----|------|
| `apps/web` | Next.js 15, React 19, Tailwind CSS |
| `apps/api` | Fastify 5, Drizzle ORM, PostgreSQL, Zod, JWT, Swagger `/docs` |
| `apps/scanner` | Go 1.22 — Redis queue, dedup, Prometheus metrics, modular scanners |
| `apps/classifier` | Python 3.12, FastAPI, OpenRouter client, asyncpg |
| `packages/shared-types` | Shared TypeScript types |
| `packages/disclosure` | Receipt generator (IPFS + MinIO + PDF + HMAC verify) |
| `packages/config` | Base `tsconfig` + ESLint flat config sketch |
| `infra/` | `docker-compose.yml`, example `fly.toml`, `nginx` sketch |

## Quick start

1. **Infra**

   ```bash
   cd infra && docker compose up -d postgres redis elasticsearch minio ipfs
   ```

2. **Database**

   Apply SQL migration:

   ```bash
   psql "$DATABASE_URL" -f apps/api/src/db/migrations/0000_initial.sql
   ```

   Seed demo users:

   ```bash
   cd apps/api && cp ../../.env.example ../../.env   # adjust paths / vars
   pnpm install   # or npm install at repo root
   pnpm --filter @zwanski/api db:seed
   ```

3. **API**

   ```bash
   pnpm --filter @zwanski/api dev
   # http://localhost:4000/docs
   ```

4. **Web**

   ```bash
   pnpm --filter @zwanski/web dev
   # http://localhost:3000
   ```

5. **Scanner (dry run)**

   ```bash
   cd apps/scanner && go run ./cmd/watchdog --dry-run --modules s3
   ```

6. **Classifier**

   ```bash
   cd apps/classifier && pip install -r requirements.txt && uvicorn main:app --port 8001
   ```

Environment variables: see **`.env.example`** at the monorepo root.

## Legal & safety

- Operate only where you have **permission** and comply with **terms of service** and **local law**.  
- The **COVENANT** (`COVENANT.md`) states responsible disclosure and researcher-protection principles.  
- This codebase is **not** a turnkey “hack the internet” kit—it's a structured starting point for **authorized** research programs.

## CI

GitHub Actions workflow: `.github/workflows/ci.yml` (paths assume this folder lives under your Git repo as `zwanski-watchdog/`).

## Trademark

“Zwanski Watchdog” and associated branding are project names for this OSS effort; adjust for your legal entity as needed.
