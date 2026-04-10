# Production Ready Setup — Complete Guide

This toolkit is now **fully production-ready** with multiple installation and deployment options.

## 📦 What's Included

### Core Tools
- ✅ `zwanski-oauth-mapper.py` — Interactive OAuth/OIDC vulnerability scanner
- ✅ `zwanski-subdomain-chain.sh` — Full recon pipeline (passive + active)

### Installation & Setup
- ✅ `setup.sh` — Automated Python installation
- ✅ `setup-tools.sh` — Optional Go tool installer
- ✅ `requirements.txt` — Python dependencies
- ✅ `Dockerfile` — Container deployment
- ✅ `docker-compose.yml` — Container orchestration

### Documentation
- ✅ `QUICKSTART.md` — 2-minute start guide
- ✅ `INSTALL.md` — Detailed installation & troubleshooting
- ✅ `DOCKER.md` — Docker deployment guide
- ✅ `PRODUCTION.md` — This file

---

## 🚀 Installation (Choose One)

### 1. **Quickest** — One Command Setup (Recommended)

```bash
git clone https://github.com/zwanski2019/zwanski-Bug-Bounty.git
cd zwanski-Bug-Bounty
bash setup.sh
```

Then run:
```bash
python3 scripts/zwanski-oauth-mapper.py
```

### 2. **Docker** — No dependencies, container-based

```bash
git clone https://github.com/zwanski2019/zwanski-Bug-Bounty.git
cd zwanski-Bug-Bounty
docker-compose build
docker-compose run --rm zwanski-oauth-mapper
```

### 3. **Manual** — Full control

```bash
git clone https://github.com/zwanski2019/zwanski-Bug-Bounty.git
cd zwanski-Bug-Bounty
pip3 install -r requirements.txt
chmod +x scripts/*.sh scripts/*.py
python3 scripts/zwanski-oauth-mapper.py
```

---

## 💻 Usage Modes

### Interactive Menu (Recommended for Beginners)
```bash
python3 scripts/zwanski-oauth-mapper.py
```
Guided workflow with numbered options — no prior knowledge needed.

### CLI Mode (Single Command Scan)
```bash
python3 scripts/zwanski-oauth-mapper.py --target https://target.com
```

### CLI with Output Export
```bash
python3 scripts/zwanski-oauth-mapper.py \
  --target https://target.com \
  --token "YOUR_JWT_TOKEN" \
  --output findings.json
```

### Full Recon Pipeline
```bash
bash scripts/zwanski-subdomain-chain.sh target.com ./output_dir
```

---

## ✨ Key Features

**OAuth Mapper**
- ✅ OIDC configuration discovery
- ✅ JWKS enumeration
- ✅ Open dynamic registration detection
- ✅ Redirect URI bypass testing
- ✅ PKCE enforcement validation
- ✅ State parameter CSRF testing
- ✅ JSON export for findings
- ✅ Interactive or CLI mode

**Subdomain Chain**
- ✅ Multi-source passive enumeration (subfinder, assetfinder, crt.sh)
- ✅ DNS resolution with wildcard detection (puredns)
- ✅ Live host probing (httpx)
- ✅ Technology detection (Spring Boot, Elasticsearch, .git)
- ✅ Vulnerability scanning (nuclei)
- ✅ JavaScript endpoint extraction

---

## 🔧 Verification (After Installation)

```bash
# Check Python + requests
python3 -c "import requests; print('✓ Ready')"

# Test OAuth mapper
python3 scripts/zwanski-oauth-mapper.py --help

# Run in test mode (interactive)
python3 scripts/zwanski-oauth-mapper.py
```

---

## 🐳 Container Deployment

### Development
```bash
docker-compose run --rm zwanski-oauth-mapper --menu
```

### Production Scan with Output
```bash
mkdir -p ./output
docker run -it -v $(pwd)/output:/opt/zwanski-bug-bounty/output \
  zwanski/oauth-mapper:latest \
  --target https://target.com \
  --output /opt/zwanski-bug-bounty/output/findings.json
```

See `DOCKER.md` for detailed container documentation.

---

## 📊 Performance & Reliability

| Metric | Value |
|--------|-------|
| Python | 3.8+ ✓ |
| Startup Time | < 2 seconds |
| Dependencies | 2 (requests, urllib3) |
| External Tools | Optional |
| Platform | Linux/macOS/Windows (with WSL) |
| Logging | Full (JSON export) |
| Error Handling | Comprehensive |

---

## 🔒 Security Considerations

- ✅ No credentials stored in code
- ✅ Environment variable support for tokens
- ✅ SSL/TLS verification enabled by default
- ✅ No outbound exfiltration
- ✅ Self-contained — no telemetry

---

## 📝 Configuration

### Environment Variables (Docker)
```bash
TARGET_URL=https://target.com
BEARER_TOKEN=your_jwt_token_here
```

### Command-Line Arguments
```bash
--target       Target URL (required for CLI mode)
--token        Bearer token for auth-protected endpoints
--output       JSON file path for findings
--menu         Force interactive menu mode
--help         Show help message
```

---

## 🐛 Troubleshooting

**"Python 3 not found"**
→ Install: `sudo apt-get install python3.11 python3-pip`

**"ModuleNotFoundError: requests"**
→ Install: `pip3 install requests`

**"Permission denied" on scripts**
→ Fix: `chmod +x scripts/*.sh scripts/*.py`

**"Cannot reach target"**
→ Verify network access & target URL format

**Docker network issues**
→ Use: `docker run --network host ...` (Linux only)

See `INSTALL.md` for more troubleshooting.

---

## 🎯 Common Workflows

### Workflow 1: Quick OAuth Audit
```bash
python3 scripts/zwanski-oauth-mapper.py --target https://app.example.com --output report.json
cat report.json
```

### Workflow 2: Full Target Assessment
```bash
# Subdomain enumeration
bash scripts/zwanski-subdomain-chain.sh example.com ./recon

# OAuth testing on discovered hosts
python3 scripts/zwanski-oauth-mapper.py --target https://api.example.com

# Export findings
python3 scripts/zwanski-oauth-mapper.py \
  --target https://api.example.com \
  --output oauth_findings.json
```

### Workflow 3: CI/CD Integration
```bash
#!/bin/bash
set -e

# Install
pip3 install -r requirements.txt

# Run scan
python3 scripts/zwanski-oauth-mapper.py \
  --target "$TARGET_URL" \
  --token "$BEARER_TOKEN" \
  --output findings.json

# Check findings
python3 -c "import json; f = json.load(open('findings.json')); exit(1 if any(x['severity']=='CRITICAL' for x in f) else 0)"
```

---

## 📊 Sample Output

```
╔════════════════════════════════════════════════════════════════╗
║                  zwanski OAuth Attack Surface Mapper           ║
╠════════════════════════════════════════════════════════════════╝
║ A guided tool for discovering OAuth/OIDC attack surface issues. ║
╚════════════════════════════════════════════════════════════════╝

[+] Found OIDC config: https://api.example.com/.well-known/openid-configuration
    authorization_endpoint: https://api.example.com/oauth/authorize
    token_endpoint: https://api.example.com/oauth/token
    
🔴 [CRITICAL] Open Dynamic Client Registration
   URL    : https://api.example.com/oauth/register
   Detail : Unauthenticated client registration succeeded

────────────────────────────────────────────────────────────────
  FINDINGS
────────────────────────────────────────────────────────────────
  [CRITICAL] Open Dynamic Client Registration — https://api.example.com/oauth/register
  [HIGH] redirect_uri Bypass — Open Redirect to Attacker — https://api.example.com/oauth/authorize?...
```

---

## 📚 Additional Resources

- **GitHub:** https://github.com/zwanski2019/zwanski-Bug-Bounty
- **Issues:** https://github.com/zwanski2019/zwanski-Bug-Bounty/issues
- **Docs:** See individual .md files in repo root

---

## ✅ Production Checklist

- [x] All dependencies documented
- [x] Automated setup scripts
- [x] Docker deployment ready
- [x] Error handling & validation
- [x] Help documentation
- [x] JSON export capability
- [x] Interactive & CLI modes
- [x] Security best practices
- [x] Troubleshooting guide
- [x] Example workflows

---

## 🎉 Ready to Go!

You have a fully production-grade bug bounty toolkit. Choose your installation method above and start hunting!

```bash
# Fastest start:
bash setup.sh && python3 scripts/zwanski-oauth-mapper.py
```
