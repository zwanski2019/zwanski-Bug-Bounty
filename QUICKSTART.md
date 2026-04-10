# zwanski-Bug-Bounty Toolkit

A professional bug bounty reconnaissance toolkit with OAuth/OIDC attack surface mapping and comprehensive subdomain enumeration pipelines.

## ⚡ Ultra-Quick Start (Copy & Paste)

Just copy and paste this one command — everything else is automatic:

```bash
git clone https://github.com/zwanski2019/zwanski-Bug-Bounty.git && cd zwanski-Bug-Bounty && bash setup.sh && ./oauth-mapper
```

That's it! The setup script will:
- ✅ Create an isolated Python virtual environment
- ✅ Install all dependencies automatically
- ✅ Create convenience wrapper scripts
- ✅ Launch the tool ready to use

## 🛠️ Tools Included

### 1. **OAuth Attack Surface Mapper** (`oauth-mapper`)
Map and test OAuth/OIDC endpoints for security vulnerabilities.

**Run interactively:**
```bash
./oauth-mapper
```

**Or via CLI:**
```bash
./oauth-mapper --target https://target.com
```

**Features:**
- Interactive guided menu (just type the number)
- OIDC/OAuth discovery
- JWKS key enumeration
- Dynamic client registration testing
- Redirect URI bypass detection
- PKCE enforcement testing
- State parameter/CSRF validation

### 2. **Subdomain Reconnaissance** (`subdomain-recon`)
Full passive + active recon pipeline in one command.

```bash
./subdomain-recon target.com
```

**Phases:**
1. Passive subdomain gathering (subfinder, assetfinder, crt.sh)
2. DNS resolution & wildcard detection (puredns)
3. HTTP probing (httpx)
4. Technology detection (Spring Boot, Elasticsearch, .git)
5. Vulnerability scanning (nuclei)
6. JavaScript endpoint extraction

## 📦 What Actually Gets Installed

When you run `bash setup.sh`, it automatically:

1. **Creates .venv/** — Isolated Python environment (no system pollution)
2. **Installs requests** — Only true dependency
3. **Creates wrapper scripts** — `./oauth-mapper` and `./subdomain-recon`
4. **Sets permissions** — Makes everything executable

Everything runs inside the isolated environment — completely safe and reversible (just delete `.venv/`).

## 💻 Three Quick Start Options

### Option 1: Ultra-Fast (Recommended)
```bash
git clone https://github.com/zwanski2019/zwanski-Bug-Bounty.git
cd zwanski-Bug-Bounty
bash setup.sh
./oauth-mapper
```

### Option 2: With Manual Environment Activation
```bash
git clone https://github.com/zwanski2019/zwanski-Bug-Bounty.git
cd zwanski-Bug-Bounty
bash setup.sh
source activate.sh
python3 scripts/zwanski-oauth-mapper.py
```

### Option 3: Docker (No Python Setup Needed)
```bash
git clone https://github.com/zwanski2019/zwanski-Bug-Bounty.git
cd zwanski-Bug-Bounty
docker-compose build
docker-compose run --rm zwanski-oauth-mapper
```

## 🚀 After Installation

### Using OAuth Mapper

**Interactive mode (beginners):**
```bash
./oauth-mapper
```

You'll see a menu with 10 numbered options. Just type the number and press Enter.

**CLI mode (automation):**
```bash
./oauth-mapper --target https://api.example.com --output findings.json
./oauth-mapper --target https://api.example.com --token YOUR_JWT_TOKEN
```

### Using Subdomain Recon

```bash
# Quick scan
./subdomain-recon example.com

# Custom output directory
./subdomain-recon example.com ./my_output/
```

## 📋 Requirements

- **Python:** 3.8+ (installed on most systems)
- **Git:** For cloning repo
- **That's it!** Everything else is automatic.

Optional:
- **Go 1.16+** (only if you want advanced recon tools like subfinder, nuclei)

## 🔧 Environment Management

### Activate Virtual Environment Manually
```bash
source .venv/bin/activate
# or
source activate.sh
```

### Deactivate Virtual Environment
```bash
deactivate
```

### Delete Virtual Environment (Clean Uninstall)
```bash
rm -rf .venv
```

## 📖 Full Documentation

- [INSTALL.md](INSTALL.md) — Detailed troubleshooting
- [PRODUCTION.md](PRODUCTION.md) — Full production guide
- [DOCKER.md](DOCKER.md) — Container deployment

## ⚙️ Verification

After setup, verify everything works:

```bash
# Test OAuth mapper
./oauth-mapper --help

# Test subdomain recon
./subdomain-recon --help  # or ./subdomain-recon (will show usage)
```

## 🐛 Troubleshooting

**"bash: ./oauth-mapper: command not found"**
```bash
bash setup.sh  # Re-run setup
./oauth-mapper
```

**"Python 3 not found"**
```bash
# Install Python
sudo apt-get install python3.11  # Ubuntu/Debian
brew install python3             # macOS
```

**"ModuleNotFoundError: requests"**
```bash
bash setup.sh  # Re-run setup to reinstall in venv
```

**To remove everything cleanly:**
```bash
rm -rf .venv/
# Your repo files remain, venv is deleted
```

## 🎯 Example Workflows

### Quick OAuth Audit
```bash
./oauth-mapper --target https://example.com --output report.json
cat report.json | jq .
```

### Full Target Assessment
```bash
# Scan subdomains
./subdomain-recon example.com

# Test OAuth on discovered hosts
./oauth-mapper --target https://api.example.com
```

### With Authentication
```bash
./oauth-mapper --target https://example.com --token "your_jwt_token_here"
```

## 📊 System Requirements

| Item | Requirement | Status |
|------|-------------|--------|
| Python | 3.8+ | ✅ Auto-detected |
| pip | 3.8+ | ✅ Auto-installed |
| Network | Outbound to targets | ✅ Required |
| Disk | ~50 MB (.venv) | ✅ Small |
| OS | Linux/macOS/Windows (WSL) | ✅ All supported |

## 🎉 You're All Set!

Copy & paste this to get started:

```bash
git clone https://github.com/zwanski2019/zwanski-Bug-Bounty.git && cd zwanski-Bug-Bounty && bash setup.sh && ./oauth-mapper
```

No additional configuration needed. Choose a menu option and start hunting! 🎯
