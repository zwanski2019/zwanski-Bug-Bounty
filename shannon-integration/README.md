# Shannon Integration

This directory contains the Shannon AI pentest agent integration for zwanski-BB.

[Shannon](https://github.com/KeygraphHQ/shannon) is an AI-powered penetration testing agent that uses Claude to autonomously run a 5-phase pentest pipeline. This integration wires zwanski-BB's advanced methodology directly into Shannon's agent layer, giving you 8 parallel specialist agents instead of the default 5.

---

## What Was Added

### 3 New Specialist Agent Pairs (6 agents total)

| Agent | Phase | Coverage |
|---|---|---|
| `oauth-sso-vuln` → `oauth-sso-exploit` | Parallel vuln/exploit | redirect_uri bypass, rogue client registration, PKCE downgrade, JWT alg confusion (RS256→HS256), alg:none, nOAuth mutable claim hijack, SAML XSW/replay, MFA bypass via social login, Keycloak master realm, refresh token abuse |
| `env-bleed-vuln` → `env-bleed-exploit` | Parallel vuln/exploit | Staging/dev/UAT host discovery, Spring Boot Actuator, `.git/` exposure, Swagger/GraphQL introspection, hardcoded test credentials, Jenkins/CircleCI/GitHub Actions leaks, K8s/cloud metadata, subdomain takeover |
| `second-order-vuln` → `second-order-exploit` | Parallel vuln/exploit | PDF→SSRF chains, CSV injection, stored XSS→admin targeting, webhook SSRF, race conditions (check-then-act, coupon reuse, referral abuse, vote limits), tenant isolation failures, LLM prompt injection / indirect injection |

These cover the highest signal-to-noise classes in zwanski-BB methodology — the ones with the **lowest hunter density**.

### Tools Wired Into Docker Image
- `zwanski-oauth-mapper` — OAuth/OIDC endpoint discovery (called by oauth-sso agent)
- `zwanski-subdomain-chain` — Passive subdomain + staging host pipeline (called by env-bleed agent)
- `httpx` — Live host probing for environment bleed discovery

---

## Setup

### Prerequisites
- Shannon installed and working (`./shannon build` succeeds)
- Anthropic API key in `.env`
- An empty git repo for your target workspace

### Quick Start

```bash
# 1. Clone Shannon
git clone https://github.com/KeygraphHQ/shannon
cd shannon

# 2. Add your API key
echo "ANTHROPIC_API_KEY=your-key" > .env

# 3. Copy the new agent prompts into Shannon
cp shannon-integration/prompts/*.txt apps/worker/prompts/

# 4. Apply the TypeScript patches (see patches/ below — or use the pre-patched fork)

# 5. Build the image (includes zwanski scripts)
./shannon build

# 6. Create a target workspace
mkdir repos/mytarget && cd repos/mytarget && git init && git commit --allow-empty -m "init" && cd ../..

# 7. Copy the example config and edit it for your program
cp shannon-integration/configs/example-engagement.yaml apps/worker/configs/mytarget.yaml
# Edit the YAML: add OOS paths, adjust focus subdomains, set rate limits

# 8. Launch the scan
./shannon start \
  -u https://target.com \
  -r mytarget \
  -c ./apps/worker/configs/mytarget.yaml \
  -w mytarget-scan-1
```

### Monitor Progress
```bash
# Tail the workflow log
./shannon logs mytarget-scan-1

# Temporal Web UI (full pipeline state, retry counts, agent metrics)
open http://localhost:8233
```

---

## Prompt Files

| File | Agent | Purpose |
|---|---|---|
| `prompts/vuln-oauth-sso.txt` | `oauth-sso-vuln` | OAuth/OIDC/SAML attack surface analysis |
| `prompts/exploit-oauth-sso.txt` | `oauth-sso-exploit` | OAuth/SSO exploitation |
| `prompts/vuln-env-bleed.txt` | `env-bleed-vuln` | Environment bleed / staging discovery |
| `prompts/exploit-env-bleed.txt` | `env-bleed-exploit` | Environment bleed exploitation |
| `prompts/vuln-second-order.txt` | `second-order-vuln` | Second-order injection + race conditions |
| `prompts/exploit-second-order.txt` | `second-order-exploit` | Second-order exploitation |

---

## Methodology Source

The agent prompts are derived directly from zwanski-BB phases:
- **04-auth-surface/** → `vuln-oauth-sso.txt` / `exploit-oauth-sso.txt`
- **06-environment-bleed/** → `vuln-env-bleed.txt` / `exploit-env-bleed.txt`
- **05-vuln-classes/** → `vuln-second-order.txt` / `exploit-second-order.txt`

---

## Pipeline Overview (with integration)

```
Pre-Recon → Recon → [8 parallel vuln agents] → [8 conditional exploit agents] → Report

Vuln agents (parallel):
  injection-vuln       ← original Shannon
  xss-vuln             ← original Shannon
  auth-vuln            ← original Shannon
  ssrf-vuln            ← original Shannon
  authz-vuln           ← original Shannon
  oauth-sso-vuln       ← zwanski-BB (NEW)
  env-bleed-vuln       ← zwanski-BB (NEW)
  second-order-vuln    ← zwanski-BB (NEW)
```

---

## Config Tips

- Set `max_concurrent_pipelines: 2` for production targets (gentle on rate limits)
- Set `max_concurrent_pipelines: 8` for lab/CTF targets (full parallel)
- Use the `rules.avoid` list to exclude OOS paths
- Use the `rules.focus` list to point agents at the highest-value subdomains
- Never put private program names or target details in this repo
