
## Local Dashboard

After installation, launch the platform with:

```bash
zwanski start
```

Then open:

```bash
http://localhost:1337
```

Use the AI assistant tab to grade findings, summarize impact, and inspect tool health.

The platform uses OpenRouter by default. In Settings, you can also override the API URL to any compatible chat completion endpoint and provide your own API key.

# zwanski Bug Bounty Methodology
> *By Mohamed Ibrahim (zwanski) — Bug Bounty Switzerland · HackerOne · Bugcrowd*

A practitioner-built, opinionated recon and exploitation methodology focused on **what most hunters skip**.  
Not a tool list. Not a checklist. A thinking framework backed by actual findings.

---

## Why This Is Different

Most public methodologies stop at:  
`subfinder → httpx → nuclei → ???`

This one starts where others end:
- **Business logic before technology** — understand revenue flows and data trust before running a single tool
- **Trust boundary mapping** — find where auth decisions actually happen, not where docs say they happen
- **Second-order chains** — input → stored → async-processed → output is where real criticals live
- **Environment bleed** — staging/UAT/dev environments are a goldmine that most hunters ignore entirely
- **OAuth/OIDC rogue-client chains** — the CVSS 9+ class almost nobody reports correctly
- **AI/LLM attack surface** — a largely unclaimed space in 2025-2026 programs
- **Supply chain recon** — package leaks, GitHub Actions secrets, dependency confusion

---

## Structure

```
00-setup/               → Toolchain, environment, API keys
01-target-profiling/    → Business model, scope analysis, threat model BEFORE tools
02-passive-recon/       → OSINT, GitHub dorking, historical, supply chain
03-active-recon/        → Subdomain enum, port scan, tech fingerprint, API discovery
04-auth-surface/        → OAuth/OIDC mapping, session analysis, MFA bypass vectors
05-vuln-classes/        → Business logic, race conditions, second-order, tenant isolation,
                          GraphQL, WebSockets, AI/LLM surface
06-environment-bleed/   → Staging-prod correlation, CI/CD exposure
07-mobile-api/          → APK/IPA recon, endpoint correlation with web surface
08-reporting/           → Report templates, CVSS guidance, chain documentation
scripts/                → Automation: scope parser, subdomain chain, auth flow mapper
```

---

## Phase Flow

```
TARGET ASSIGNED
      │
      ▼
[01] Profiling ──► Understand the business. What data is valuable? Who are the user tiers?
      │             What's the revenue model? What would embarrass them?
      ▼
[02] Passive ────► No packets to target. OSINT, GitHub, historical, supply chain.
      │
      ▼
[03] Active ─────► Subdomain enum → live hosts → tech stack → API discovery → JS analysis
      │
      ▼
[04] Auth Surface ► OAuth flows, SSO chains, session lifecycle, privilege boundaries
      │
      ▼
[05] Vuln Classes ► Target-specific: pick the classes that match the stack
      │
      ▼
[06] Env Bleed ──► Staging/dev/UAT correlation. Often skipped. Often critical.
      │
      ▼
[07] Mobile/API ─► Cross-reference mobile endpoints with web surface
      │
      ▼
[08] Report ─────► Chain findings, calculate real business impact, draft write-up
```

---

## The Mindset

**1. Assume the perimeter is hardened. Attack the logic.**  
The WAF will catch your `<script>`. The rate limiter will catch your brute force.  
What it won't catch is you abusing a discount code endpoint to apply 100 promo codes to one order.

**2. Find the seams, not the features.**  
Bugs live at integration points: where service A trusts service B's output, where the mobile API and web API share a backend but have different validation layers, where the admin panel was built by a different team.

**3. The "assumed breach" mindset.**  
Start every target by asking: *what can a free-tier / unauthenticated user reach that they shouldn't?*  
Then: *what can a paid-tier user reach that belongs to another tenant?*

**4. Second-order everything.**  
You submitted a payload and nothing happened? Good. Come back tomorrow after the async job processes it. Check the email you receive. Check what gets rendered in the admin panel. Check the PDF export.

**5. The environment is part of the attack surface.**  
`staging.target.com`, `api-dev.target.com`, `uat-portal.target.com` — these are in scope if the root domain is in scope (verify the program's policy). They often run older code, debug flags enabled, and weaker auth.

---

## ⚡ Quick Start (One Command)

### Copy & Paste — Everything Automated

Just like Ollama, install and start using in one command:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/zwanski2019/zwanski-Bug-Bounty/main/install.sh)
```

That's it! The script will:
1. ✅ Clone the repository (or update if exists)
2. ✅ Create isolated Python environment
3. ✅ Install all dependencies
4. ✅ Create convenient wrappers
5. ✅ You're ready to use immediately

### Or Run Locally

```bash
# Download installer
curl -fsSL https://raw.githubusercontent.com/zwanski2019/zwanski-Bug-Bounty/main/install.sh -o install.sh

# Run it
bash install.sh
```

### After Installation

Start using the tools immediately:

```bash
# OAuth/OIDC testing (interactive menu)
./oauth-mapper

# Or with a target
./oauth-mapper --target https://api.example.com

# Subdomain reconnaissance
./subdomain-recon example.com
```

### Full Documentation

- **[QUICKSTART.md](QUICKSTART.md)** — 2-minute guide
- **[INSTALL.md](INSTALL.md)** — Detailed setup & troubleshooting  
- **[PRODUCTION.md](PRODUCTION.md)** — Full production deployment
- **[DOCKER.md](DOCKER.md)** — Container-based setup

---

## Maintained by

**Mohamed Ibrahim** — [`zwanski`](https://github.com/zwanski2019)  
[zwanski.bio](https://zwanski.bio) · Bug Bounty Switzerland · HackerOne · Bugcrowd

---

*PRs welcome. If you found a critical using this methodology, open an issue and share (redacted) — I'll add it to the case studies.*
