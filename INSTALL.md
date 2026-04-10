# Installation & Quick Start

## Prerequisites

- Python 3.8 or newer
- Git (for cloning the repo)
- That's it! Everything else is automatic.

## Installation (Copy & Paste)

### Ultra-Fast One-Liner

Copy and paste this single command — everything else happens automatically:

```bash
git clone https://github.com/zwanski2019/zwanski-Bug-Bounty.git && cd zwanski-Bug-Bounty && bash setup.sh && ./oauth-mapper
```

The setup script will:
1. Detect Python 3
2. Create `.venv/` (isolated Python environment)
3. Install dependencies into `.venv/`
4. Create wrapper scripts (`./oauth-mapper`, `./subdomain-recon`)
5. Launch the tool immediately

### What Happens During Setup

```
✓ Checking Python 3.8+
✓ Creating isolated virtual environment (.venv/)
✓ Installing requests + urllib3
✓ Making scripts executable
✓ Creating convenience wrappers
✓ Verifying installation
✓ Ready to use!
```

The entire process takes **1-2 minutes** with zero user input needed.

## Running the Tools

After `bash setup.sh`, you have two convenience wrapper scripts:

### OAuth Mapper

```bash
# Interactive menu (recommended for first-time users)
./oauth-mapper

# Or with target
./oauth-mapper --target https://api.example.com

# Or with output
./oauth-mapper --target https://api.example.com --output findings.json
```

### Subdomain Reconnaissance

```bash
./subdomain-recon target.com
./subdomain-recon target.com ./custom_output_dir
```

## Manual Virtual Environment Control

If you need to manually manage the virtual environment:

### Activate Virtual Environment
```bash
source .venv/bin/activate
# or
source activate.sh
```

Once activated, you can run scripts directly:
```bash
python3 scripts/zwanski-oauth-mapper.py --help
python3 scripts/zwanski-oauth-mapper.py --menu
```

### Deactivate Virtual Environment
```bash
deactivate
```

### Delete Virtual Environment (Clean Uninstall)
```bash
rm -rf .venv/
# Everything is cleaned up, repo files remain
```

## Supported Platforms

| OS | Status | Notes |
|---|--------|-------|
| Linux (Ubuntu/Debian) | ✅ Fully supported | Most common |
| Linux (RHEL/CentOS) | ✅ Fully supported | Install python3-venv if needed |
| macOS | ✅ Fully supported | Install Python 3 from homebrew |
| Windows 10+ | ✅ WSL recommended | Use Windows Subsystem for Linux |
| Docker/Container | ✅ See DOCKER.md | No setup needed |

### Platform-Specific Notes

**Ubuntu/Debian:**
```bash
# If Python 3 not installed
sudo apt-get update
sudo apt-get install python3.11 python3.11-venv

# Then run setup
bash setup.sh
```

**macOS:**
```bash
# If Python 3 not installed
brew install python@3.11

# Then run setup
bash setup.sh
```

**CentOS/RHEL:**
```bash
sudo yum install python3 python3-venv

# Then run setup
bash setup.sh
```

**Windows (WSL2 recommended):**
```bash
# Install WSL2 first, then inside WSL:
sudo apt-get update
sudo apt-get install python3 git

# Then run setup
bash setup.sh
```

## Optional: Install External Recon Tools

If you want the advanced recon tools (subfinder, httpx, nuclei, etc.):

```bash
# Requires Go 1.16+ installed
bash setup-tools.sh
```

This installs Go-based tools for the subdomain chain script. If you don't run this, the subdomain script will have limited functionality but OAuth mapper works 100%.

## Verification

After installation, verify everything works:

```bash
# Show help
./oauth-mapper --help

# Run interactive menu (no target needed)
./oauth-mapper --menu

# Or just run it
./oauth-mapper
```

## Directory Structure After Setup

```
zwanski-Bug-Bounty/
├── .venv/                          ← Isolated Python environment (created by setup.sh)
├── oauth-mapper                    ← Wrapper script (created by setup.sh)
├── subdomain-recon                 ← Wrapper script (created by setup.sh)
├── activate.sh                     ← Helper to activate venv
├── setup.sh                        ← Main installer
├── setup-tools.sh                  ← Optional Go tools installer
├── requirements.txt                ← Python dependencies
├── Dockerfile & docker-compose.yml ← Container deployment
├── scripts/
│   ├── zwanski-oauth-mapper.py
│   └── zwanski-subdomain-chain.sh
├── INSTALL.md (this file)
├── QUICKSTART.md
├── PRODUCTION.md
└── [other folders]
```

## Troubleshooting

### "Python 3 not found"

**Error:** `bash: python3: command not found`

**Solution:**
```bash
# Ubuntu/Debian
sudo apt-get install python3.11

# macOS
brew install python@3.11

# CentOS/RHEL
sudo yum install python3
```

### "Module not found" after setup

**Error:** `ModuleNotFoundError: No module named 'requests'`

**Solution:**
```bash
# Re-run setup to install in venv
bash setup.sh
```

### "Permission denied" on wrapper scripts

**Error:** `bash: ./oauth-mapper: Permission denied`

**Solution:**
```bash
chmod +x ./oauth-mapper ./subdomain-recon
```

(This is done automatically by setup.sh, but in case it missed):

### Virtual environment activation issues

**Error:** `source: file not found`

**Solution:**
```bash
# Ensure you're in the repo directory
cd zwanski-Bug-Bounty

# Activate venv
source .venv/bin/activate

# Or use the helper
bash activate.sh
```

### Docker issues

For container-based setup with zero Python dependency issues, see [DOCKER.md](DOCKER.md):

```bash
docker-compose build
docker-compose run --rm zwanski-oauth-mapper
```

### Custom Python Version

If you have multiple Python versions installed:

```bash
# Specify which python to use
/usr/bin/python3.11 -m venv .venv
bash setup.sh
```

## Uninstall / Clean Up

To completely remove the toolkit:

```bash
# Remove just the virtual environment (keeps repo)
rm -rf .venv/

# Or remove everything
cd ../
rm -rf zwanski-Bug-Bounty/
```

## Getting Help

If something goes wrong:

1. Check [QUICKSTART.md](QUICKSTART.md) for common issues
2. Check [PRODUCTION.md](PRODUCTION.md) for advanced troubleshooting
3. See [DOCKER.md](DOCKER.md) if setup issues persist
4. Open an issue: https://github.com/zwanski2019/zwanski-Bug-Bounty/issues

## Next Steps

After successful setup:

1. **Quick test:**
   ```bash
   ./oauth-mapper --menu
   ```

2. **Scan a target:**
   ```bash
   ./oauth-mapper --target https://target.com
   ```

3. **Read full docs:**
   - [QUICKSTART.md](QUICKSTART.md) — 2-minute guide
   - [PRODUCTION.md](PRODUCTION.md) — Full reference

---

**You're all set!** type `./oauth-mapper` and start hunting. 🎯
