# zwanski Bug Bounty Methodology

[![GitHub stars](https://img.shields.io/github/stars/zwanski2019/zwanski-Bug-Bounty?style=for-the-badge&logo=github)](https://github.com/zwanski2019/zwanski-Bug-Bounty/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/zwanski2019/zwanski-Bug-Bounty?style=for-the-badge&logo=github)](https://github.com/zwanski2019/zwanski-Bug-Bounty/network/members)
[![License](https://img.shields.io/github/license/zwanski2019/zwanski-Bug-Bounty?style=for-the-badge)](https://github.com/zwanski2019/zwanski-Bug-Bounty/blob/main/LICENSE)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20WSL-blue?style=for-the-badge)](https://github.com/zwanski2019/zwanski-Bug-Bounty)
[![Tools](https://img.shields.io/badge/tools-45%2B%20integrated-green?style=for-the-badge)](https://github.com/zwanski2019/zwanski-Bug-Bounty)

> *By Mohamed Ibrahim (zwanski) — Bug Bounty Switzerland · HackerOne · Bugcrowd*

A practitioner-built, opinionated recon and exploitation methodology focused on **what most hunters skip**.
Not a tool list. Not a checklist. A thinking framework backed by actual findings — with a full AI-powered localhost dashboard to run it all from one place.

---

## ⚡ Install (One Command)

Just like Ollama — copy, paste, done:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/zwanski2019/zwanski-Bug-Bounty/main/install.sh)
```

The installer will:

1. Detect your OS and package manager
2. Install Go, Node.js, and Python3 if missing
3. Install **45+ bug bounty tools** across 12 categories
4. Download SecLists + Assetnote wordlists + resolvers
5. Set up the Flask API server with OpenRouter AI integration
6. Add `zwanski` CLI to your PATH
7. Auto-open the dashboard at `http://localhost:1337`

---

## 🖥️ Local Dashboard

After installation, start the platform:

```bash
zwanski start
```

Then open `http://localhost:1337` in your browser.

The dashboard includes:

- **Tools Status** — see which of the 45+ tools are installed at a glance
- **Methodology Phases** — interactive checklists per phase with commands
- **Terminal** — run whitelisted tools and see output in-browser
- **AI Assistant** — OpenRouter-powered chat for grading findings, writing reports, and planning attacks
- **Wordlists** — browse installed wordlists and sizes
- **Settings** — set your OpenRouter API key and default model

The AI tab supports any OpenRouter-compatible model. In Settings you can set your API key and switch between:
Gemini Flash (fast, free tier) · Claude 3.5 Sonnet · GPT-4o · Llama 3.1 70B · Mixtral 8x7B and more.

```bash
zwanski start      # launch dashboard + open browser
zwanski stop       # stop the server
zwanski status     # show installed tools count
zwanski update     # pull latest from GitHub
zwanski recon      # run subdomain chain on a target
zwanski oauth      # run OAuth attack surface mapper
```

---

## 📸 Demo

<figure>
  <video controls poster="assets/screenshot.png" width="720">
    <source src="assets/demo.webm" type="video/webm">
    <a href="assets/demo.webm">Download demo.webm</a>
  </video>
  <figcaption>A short walkthrough of the local ZWANSKI dashboard and AI-assisted workflow — tool status, terminal execution, phase checklists, and findings grading.</figcaption>
</figure>

---

## Why This Is Different

Most public methodologies stop at:

```
subfinder → httpx → nuclei → ???
```

This one starts where others end:

- **Business logic before technology** — map revenue flows and data trust before running a single tool
- **Trust boundary mapping** — find where auth decisions actually happen, not where docs say they happen
- **Second-order chains** — input → stored → async-processed → output is where real criticals live
- **Environment bleed** — staging/UAT/dev environments are a goldmine almost everyone ignores
- **OAuth/OIDC rogue-client chains** — the CVSS 9+ class almost nobody reports correctly
- **AI/LLM attack surface** — a largely unclaimed space in 2025–2026 programs
- **Supply chain recon** — package leaks, GitHub Actions secrets, dependency confusion

---

## Tools Installed (45+)

| Category | Tools |
|---|---|
| Subdomain | subfinder, amass, assetfinder, dnsx, puredns, alterx, gotator, chaos, shuffledns |
| HTTP / Crawl | httpx, katana, hakrawler, waybackurls, gau, gospider |
| Ports | naabu, nmap, rustscan |
| Vuln Scan | nuclei + templates, nikto, dalfox, sqlmap, kxss |
| Fuzzing | ffuf, feroxbuster, gobuster, dirsearch |
| Secrets | trufflehog, gitleaks, semgrep, linkfinder, secretfinder |
| OSINT | theHarvester, shodan CLI, spiderfoot |
| Parameters | arjun, paramspider, x8 |
| SSRF | ssrfmap, gopherus, interactsh-client |
| API / GraphQL | graphw00f, clairvoyance |
| Mobile | apktool, jadx, apkleaks, frida-tools, objection |
| Cloud | cloudbrute, s3scanner, aws-cli |
| Utils | anew, qsreplace, gf + patterns, notify, uncover, tlsx, cvemap, mapcidr |
| Wordlists | SecLists, Assetnote (subdomains + API routes), resolvers.txt |

---

## Repo Structure

```
zwanski-Bug-Bounty/
├── install.sh                          ← one-command installer
├── ui/
│   └── index.html                      ← localhost dashboard UI
├── 00-setup/
├── 01-target-profiling/
│   └── scope-analysis.md
├── 02-passive-recon/
│   └── passive-recon.md
├── 03-active-recon/
│   └── active-recon.md
├── 04-auth-surface/
│   └── oauth-sso-mapping.md
├── 05-vuln-classes/
│   └── second-order-and-races.md
├── 06-environment-bleed/
│   └── staging-prod-correlation.md
├── 07-mobile-api/
│   └── mobile-recon.md
├── 08-reporting/
│   └── report-template.md
└── scripts/
    ├── zwanski-subdomain-chain.sh
    └── zwanski-oauth-mapper.py
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

## Quick Reference

```bash
# Run full subdomain recon chain
zwanski-recon target.com

# Run OAuth attack surface mapper
zwanski-oauth --target https://target.com --output results.json

# Subdomain chain (manual)
subfinder -d target.com -all -recursive -silent | anew subs.txt
puredns resolve subs.txt -r ~/.zwanski-bb/wordlists/resolvers.txt -o resolved.txt
httpx -l resolved.txt -title -status-code -tech-detect -o live.txt

# Nuclei critical/high only
nuclei -l live.txt -severity critical,high -exclude-tags intrusive

# Check for open Elasticsearch
curl -sk "http://TARGET:9200/_cat/indices?v"

# OIDC discovery
curl -sk https://target.com/.well-known/openid-configuration | jq .

# Dynamic client registration test
curl -X POST https://target.com/oauth/register \
  -H "Content-Type: application/json" \
  -d '{"client_name":"test","redirect_uris":["https://attacker.com/cb"],"grant_types":["authorization_code"]}'
```

---

## AI Grading

The platform integrates with [OpenRouter](https://openrouter.ai) to give you an AI assistant that:

- Grades findings by severity (CVSS reasoning included)
- Helps write high-impact bug reports
- Suggests attack chains from your recon output
- Reviews OAuth flows and JWT tokens
- Answers methodology questions with attacker POV

Set your key in `zwanski start` → Settings tab, or:

```bash
echo '{"openrouter_key": "sk-or-v1-..."}' > ~/.zwanski-bb/config.json
```

Free models available: Gemini Flash 1.5, Llama 3.1 70B, Mixtral 8x7B — no cost to get started.

---

## Update

```bash
zwanski update
```

Or re-run the installer at any time — it skips already-installed tools.

---

## Maintained by

**Mohamed Ibrahim** — [`zwanski`](https://github.com/zwanski2019)
[zwanski.bio](https://zwanski.bio) · Bug Bounty Switzerland · HackerOne · Bugcrowd

---

*PRs welcome. Found a critical using this methodology? Open an issue and share (redacted) — I'll add it to the case studies.*
