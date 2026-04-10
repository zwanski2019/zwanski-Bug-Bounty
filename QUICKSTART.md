# zwanski-Bug-Bounty Toolkit

A professional bug bounty reconnaissance toolkit with OAuth/OIDC attack surface mapping and comprehensive subdomain enumeration pipelines.

## ⚡ Quick Start (One Command)

### Install & Setup

```bash
# Clone the repository
git clone https://github.com/zwanski2019/zwanski-Bug-Bounty.git
cd zwanski-Bug-Bounty

# Run the automated setup
bash setup.sh
```

That's it! You're ready to use the tools.

## 🛠️ Tools Included

### 1. **OAuth Attack Surface Mapper** (`zwanski-oauth-mapper.py`)
Map and test OAuth/OIDC endpoints for security vulnerabilities.

**Run interactively:**
```bash
python3 scripts/zwanski-oauth-mapper.py
```

**Or via CLI:**
```bash
python3 scripts/zwanski-oauth-mapper.py --target https://target.com
```

**Features:**
- Interactive guided menu
- OIDC/OAuth discovery
- JWKS key enumeration
- Dynamic client registration testing
- Redirect URI bypass detection
- PKCE enforcement testing
- State parameter/CSRF validation

### 2. **Subdomain Reconnaissance Chain** (`zwanski-subdomain-chain.sh`)
Full passive + active recon pipeline in one command.

```bash
bash scripts/zwanski-subdomain-chain.sh target.com
```

**Phases:**
1. Passive subdomain gathering (subfinder, assetfinder, crt.sh)
2. DNS resolution & wildcard detection (puredns)
3. HTTP probing (httpx)
4. Technology detection (Spring Boot, Elasticsearch, .git)
5. Vulnerability scanning (nuclei)
6. JavaScript endpoint extraction

## 📋 Requirements

- **Python:** 3.8+ with pip
- **Essentials:** curl, jq (usually pre-installed)
- **Optional:** Go 1.16+ (for advanced recon tools)

## 📖 Full Documentation

See [INSTALL.md](INSTALL.md) for:
- Detailed installation steps
- Tool-specific usage
- Troubleshooting
- External tool setup

## 🚀 Example Workflows

### Quick OAuth test
```bash
python3 scripts/zwanski-oauth-mapper.py --target https://example.com --output findings.json
```

### Full target recon
```bash
bash scripts/zwanski-subdomain-chain.sh example.com ./recon_output
python3 scripts/zwanski-oauth-mapper.py --target https://example.com
```

### Authenticated scanning
```bash
python3 scripts/zwanski-oauth-mapper.py --target https://example.com --token YOUR_JWT_TOKEN
```

## 📂 Directory Structure

```
zwanski-Bug-Bounty/
├── scripts/
│   ├── zwanski-oauth-mapper.py       # OAuth/OIDC security tester
│   └── zwanski-subdomain-chain.sh    # Full recon pipeline
├── 01-target-profiling/              # Methodology docs
├── 02-passive-recon/
├── 03-active-recon/
├── 04-auth-surface/
├── 05-vuln-classes/
├── 06-environment-bleed/
├── 07-mobile-api/
├── 08-reporting/
├── requirements.txt                   # Python dependencies
├── setup.sh                           # Automated setup
├── setup-tools.sh                     # Optional tool installer
└── INSTALL.md                         # Detailed docs
```

## 🔧 Installation Variants

### Minimal Setup (Python only)
```bash
bash setup.sh
```

### Full Setup (with Go tools)
```bash
bash setup.sh
bash setup-tools.sh
```

### Manual Setup
```bash
pip3 install -r requirements.txt
chmod +x scripts/*.sh scripts/*.py
```

## ⚙️ Verification

After installation, verify everything works:

```bash
# Test OAuth mapper
python3 scripts/zwanski-oauth-mapper.py --menu

# Check Python dependencies
python3 -c "import requests; print('✓ requests installed')"
```

## 🐛 Troubleshooting

**"ModuleNotFoundError: No module named 'requests'"**
```bash
pip3 install requests
```

**"Permission denied" on scripts**
```bash
chmod +x scripts/*.sh scripts/*.py
```

**Tools not found in subdomain-chain.sh**
```bash
bash setup-tools.sh
```

## 📚 Additional Resources

- **Methodology:** See individual folders (01-target-profiling, etc.) for detailed guides
- **Issues:** GitHub Issues: https://github.com/zwanski2019/zwanski-Bug-Bounty/issues
- **Contributing:** Contributions welcome!

## 📝 License

See LICENSE file for details.

---

**Ready to hunt?** Start with:
```bash
bash setup.sh && python3 scripts/zwanski-oauth-mapper.py
```
