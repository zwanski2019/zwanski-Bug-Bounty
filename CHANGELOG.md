# Changelog

All notable changes to ZWANSKI Bug Bounty Platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.3.0] - 2026-04-25 "Shannon Fusion"

### 🤖 SHANNON AI AGENT INTEGRATION

Merged zwanski-BB methodology into [Shannon](https://github.com/KeygraphHQ/shannon) — an AI-powered pentest pipeline built on Claude + Temporal. Shannon now runs 8 parallel specialist agents instead of the default 5, with the 3 new agents drawn directly from zwanski-BB's advanced methodology.

#### New Agent Pairs (6 agents)

**OAuth/SSO Agent** (`oauth-sso-vuln` → `oauth-sso-exploit`)
- Full OAuth 2.0 / OIDC / SAML attack surface analysis
- redirect_uri bypass (10+ techniques), rogue client registration, PKCE downgrade
- JWT algorithm confusion (RS256→HS256), alg:none, nOAuth mutable claim hijack
- MFA bypass via social login, Keycloak master realm exposure
- Session lifecycle: logout invalidation, password change invalidation, refresh token reuse
- Source: `04-auth-surface/oauth-sso-mapping.md`

**Environment Bleed Agent** (`env-bleed-vuln` → `env-bleed-exploit`)
- Automated staging/dev/UAT/preprod host discovery via `zwanski-subdomain-chain`
- Spring Boot Actuator (`/actuator/env`, `/actuator/heapdump`), `.git/` exposure
- Swagger/OpenAPI/GraphQL introspection on non-prod hosts
- CI/CD exposure: Jenkins unauthenticated API, GitHub Actions secret leaks in logs
- Subdomain takeover detection (dangling CNAME patterns)
- Staging vs production code divergence mapping
- Source: `06-environment-bleed/staging-prod-correlation.md`

**Second-Order & Race Conditions Agent** (`second-order-vuln` → `second-order-exploit`)
- Second-order injection tracing: profile fields → PDF export, email templates, admin panels, CSV export
- PDF HTML injection → SSRF (wkhtmltopdf / headless Chrome)
- CSV injection for Excel formula execution
- Stored XSS → admin panel targeting with CSRF chain
- Webhook SSRF via user-configured webhook URLs
- Race conditions: check-then-act, coupon/promo reuse, referral abuse, vote limits
- Tenant isolation failure detection (multi-tenant SaaS)
- LLM prompt injection: direct, indirect, and data exfiltration via AI features
- Source: `05-vuln-classes/second-order-and-races.md`

#### Tools Added to Shannon Docker Image
- `zwanski-oauth-mapper` — OAuth/OIDC endpoint mapper (from `scripts/zwanski-oauth-mapper.py`)
- `zwanski-subdomain-chain` — Passive subdomain + staging pipeline (from `scripts/zwanski-subdomain-chain.sh`)
- `httpx` — Live host probing (ProjectDiscovery)

#### New Files
- `shannon-integration/README.md` — Full setup and usage guide
- `shannon-integration/prompts/` — All 6 new agent prompt templates
- `shannon-integration/configs/example-engagement.yaml` — Sanitized config template

### Changed
- `VERSION` bumped to 2.3.0

---

## [2.2.0] - 2026-04-23 "The Hunter"

### 🔥 GAME-CHANGING FEATURES

This is THE update. No one has built this for bug bounty hunters.

#### 🖥️ Multi-Terminal Manager
- **Unlimited Terminal Sessions**: Spin up as many terminals as your system can handle
- **tmux Backend**: Full session persistence, survive crashes/disconnects
- **Split Panes**: Vertical/horizontal splits with independent panes
- **Session Save/Restore**: Export full terminal history to files
- **Real-time Output**: Live terminal streaming via WebSocket
- **Command Injection**: Send commands programmatically to any session
- **API Endpoints**: 8 new endpoints for full terminal control

#### 🎯 Port Scanner Dashboard
- **Triple Scanner Integration**: nmap, masscan, rustscan all in one dashboard
- **Real-time Results**: Watch ports appear as they're discovered
- **Visual Attack Surface**: See your target's open ports at a glance
- **Service Detection**: Auto-identify running services (HTTP, SSH, FTP, etc.)
- **Scan Persistence**: All scans saved with full history
- **Scanner Stats**: Track total scans, open ports, top services
- **API Endpoints**: 8 new endpoints for port scanning automation

**Supported Scanners:**
- **nmap** - Full service detection, aggressive mode, custom port ranges
- **masscan** - Ultra-fast scanning (10,000+ ports/sec)
- **rustscan** - Fastest port scanner, then passes to nmap for service detection

#### 🤖 OpenClaw Bug Bounty Agent
- **Mobile C2 Integration**: Control recon from Telegram/WhatsApp/Discord
- **Automated Workflows**: Pre-built recon pipelines (full_recon, quick_scan, deep_hunt, api_hunt)
- **Real-time Notifications**: Get notified on mobile as findings appear
- **Agent Management**: Create unlimited agents, each with own workflows
- **Finding Aggregation**: Auto-parse tool output into structured findings
- **Custom Workflows**: Build your own multi-tool recon chains
- **API Endpoints**: 9 new endpoints for agent automation

**Pre-built Workflows:**
- **full_recon**: subfinder → httpx → nuclei → katana
- **quick_scan**: subfinder → httpx → nuclei (high/critical only)
- **deep_hunt**: amass → nmap → nuclei → sqlmap → dalfox
- **api_hunt**: katana → arjun → ffuf → nuclei (API-focused)

### Added (Total: 25 new API endpoints)

**Terminal Manager:**
- `GET /api/terminals` - List all sessions
- `POST /api/terminals` - Create new session
- `GET /api/terminals/:id/output` - Get terminal output
- `POST /api/terminals/:id/command` - Send command
- `POST /api/terminals/:id/split` - Split pane
- `DELETE /api/terminals/:id` - Close session
- `POST /api/terminals/:id/save` - Save history
- `GET /api/terminals/stats` - Statistics

**Port Scanner:**
- `GET /api/portscan` - List all scans
- `POST /api/portscan/nmap` - Start nmap scan
- `POST /api/portscan/masscan` - Start masscan
- `POST /api/portscan/rustscan` - Start rustscan
- `GET /api/portscan/:id` - Get scan results
- `DELETE /api/portscan/:id` - Delete scan
- `GET /api/portscan/stats` - Statistics

**OpenClaw Agent:**
- `GET /api/agents` - List all agents
- `POST /api/agents` - Create agent
- `GET /api/agents/:id` - Get agent status
- `POST /api/agents/:id/recon` - Start recon workflow
- `POST /api/agents/:id/stop` - Stop agent
- `GET /api/agents/workflows` - List workflows
- `POST /api/agents/workflows` - Add custom workflow
- `GET /api/agents/stats` - Statistics

### New Files

- `terminal_manager.py` (17KB) - Multi-terminal session manager
- `port_scanner.py` (16KB) - Port scanning dashboard
- `openclaw_agent.py` (17KB) - Bug bounty automation agent

### Technical Details

- **tmux Integration**: Full tmux session control for terminal management
- **Background Scanning**: All port scans run in background threads
- **Real-time Updates**: WebSocket support for live terminal streaming
- **Parser Engine**: Intelligent parsing of tool outputs (nmap XML, masscan JSON, etc.)
- **Workflow Engine**: Extensible system for custom recon workflows
- **Mobile-First**: OpenClaw agent designed for mobile C2 from day one

### Performance

- **Terminal Sessions**: Unlimited (resource-limited only)
- **Concurrent Scans**: Up to 10 simultaneous port scans
- **Agent Workflows**: Process 4-5 tools per workflow automatically
- **Storage**: JSON-based, no database required

### Breaking Changes

None. Fully backward compatible with v2.1.0.

---

## [2.1.0] - 2026-04-23

### Added

#### 🎁 Auto-Update System (Burp Suite/Nuclei-inspired)
- **Version Manager** (`version_manager.py`): Automatic GitHub release checking with semantic version comparison
- **Update Notification Banner**: Inline banner at top of dashboard when updates available
- **Changelog Modal**: View formatted release notes before updating
- **One-Click Update**: Git pull automation with restart prompt
- **Background Checker**: Hourly automatic update checks (non-intrusive)
- **Update API Endpoints**:
  - `GET /api/version` - Check current version and update status
  - `POST /api/update` - Perform git pull update
  - `GET /api/git-status` - Repository status (branch, commits, changes)

#### 🎯 Finding Tracker
- **Full CRUD Operations**: Add, view, update, delete vulnerability findings
- **Finding Management** (`reporting_enhanced.py`): 
  - Auto-generated IDs (format: `ZWBB-YYYYMMDD-NNNN`)
  - Status tracking (new, submitted, triaged, resolved, duplicate, n/a)
  - Platform association (HackerOne, Bugcrowd, Synack, etc.)
- **Advanced Filtering**: By severity, status, target, platform
- **Statistics Dashboard**: Total findings, severity breakdown, status distribution
- **Finding Timeline**: Created/updated timestamps for each finding
- **API Endpoints**:
  - `GET /api/findings` - List findings with filters
  - `POST /api/findings` - Add new finding
  - `GET/PUT/DELETE /api/findings/:id` - Manage specific finding
  - `GET /api/findings/stats` - Finding statistics

#### 📊 CVSS 3.1 Calculator
- **Full CVSS 3.1 Implementation**: Calculate base score and severity
- **Interactive UI**: Dropdown selectors for all 8 metrics
- **Real-time Calculation**: Impact and exploitability sub-scores
- **Vector String Generation**: Standard CVSS vector format
- **Color-Coded Severity**: Visual indicators (Critical=red, High=orange, etc.)
- **API Endpoint**: `POST /api/cvss/calculate` - Calculate CVSS scores

#### 🎯 Scope Manager
- **Program CRUD**: Add, update, delete bug bounty programs
- **Scope Validation** (`scope_manager.py`):
  - Wildcard domain matching (`*.example.com`)
  - Regex pattern support (`regex:.*\.api\..*`)
  - CIDR range support (basic IP matching)
  - Exact domain and URL matching
- **Quick Scope Check**: Validate if target is in/out of scope across all programs
- **Bulk Import**: Parse scope from HackerOne/Bugcrowd text format
- **Program Statistics**: Total programs, active count, scope item counts
- **Multi-Platform Support**: HackerOne, Bugcrowd, Synack, Intigriti, YesWeHack, Bug Bounty Switzerland
- **API Endpoints**:
  - `GET /api/scope/programs` - List programs with filters
  - `POST /api/scope/programs` - Add new program
  - `GET/PUT/DELETE /api/scope/programs/:id` - Manage specific program
  - `POST /api/scope/check` - Validate target scope
  - `POST /api/scope/parse` - Parse scope from text
  - `GET /api/scope/stats` - Scope statistics

#### 📝 Enhanced Reporting
- **Platform-Specific Templates**: Auto-formatted reports for:
  - HackerOne (professional tone, markdown)
  - Bugcrowd (concise, impact-first)
  - Synack (technical, detailed)
  - Intigriti (detailed POC)
  - YesWeHack (structured)
  - Bug Bounty Switzerland (formal, CVSS required)
- **Report Generator** (`reporting_enhanced.py`): Auto-format findings per platform
- **CVSS Integration**: Auto-calculate and include CVSS scores in findings
- **API Endpoints**:
  - `POST /api/report/generate` - Generate platform-specific report
  - `GET /api/report/platforms` - List supported platforms

### Improved

- **UI Navigation**: Added Findings, Scope, and CVSS Calc tabs to sidebar
- **Dashboard Telemetry**: Added version badge to footer with update indicator
- **Error Handling**: Better error messages for API failures
- **Data Persistence**: All findings and programs stored in JSON files
- **Session Management**: Auto-load data when switching to relevant tabs

### Technical Details

- **New Dependencies**: None (pure Python standard library + existing Flask/requests)
- **File Structure**:
  - `version_manager.py` - Version checking and update automation
  - `reporting_enhanced.py` - CVSS calculator, finding tracker, report generator
  - `scope_manager.py` - Scope management and validation
  - `VERSION` - Current version file
  - `.update_cache.json` - Update check cache
  - `findings.json` - Finding storage
  - `scopes.json` - Program scope storage

### Breaking Changes

None. Fully backward compatible with existing installations.

### Upgrade Instructions

1. **Git Pull**: `git pull origin main`
2. **Restart Server**: `zwanski restart` or `python server.py`
3. **No Migration Needed**: New features work alongside existing functionality

---

## [2.0.0] - 2026-04-15

### Added
- Initial release of ZWANSKI.BB Command Center
- War Map visualization
- Agentic recon pipelines
- Arsenal tool management
- Zwanski Watchdog integration
- Intel AI with OpenRouter
- Terminal streaming with xterm
- Setup wizard

---

## Versioning Scheme

- **MAJOR**: Breaking changes, architectural rewrites
- **MINOR**: New features, backward-compatible additions
- **PATCH**: Bug fixes, minor improvements

---

## Links

- [GitHub Repository](https://github.com/zwanski2019/zwanski-Bug-Bounty)
- [Documentation Wiki](https://github.com/zwanski2019/zwanski-Bug-Bounty/tree/main/docs/wiki)
- [API Reference](https://github.com/zwanski2019/zwanski-Bug-Bounty/blob/main/docs/wiki/api.md)
- [Issue Tracker](https://github.com/zwanski2019/zwanski-Bug-Bounty/issues)
