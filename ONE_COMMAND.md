# One-Command Installation Guide

Just like **Ollama**, install and start using zwanski-Bug-Bounty with a single command.

## 🚀 The One-Liner

Copy & paste this — everything else is automatic:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/zwanski2019/zwanski-Bug-Bounty/main/install.sh)
```

**That's it!** The script automatically:
- ✅ Clones the repository
- ✅ Detects Python 3
- ✅ Creates isolated virtual environment
- ✅ Installs dependencies
- ✅ Sets up convenience wrappers
- ✅ Ready to use

No more:
- ❌ Manual git clone
- ❌ Manual pip install
- ❌ Manual venv setup
- ❌ Configuration

## How It Works (Like Ollama)

### Ollama (comparison)
```bash
# Download + install + ready to use
curl https://ollama.ai/install.sh | sh
ollama run llama2
```

### zwanski-Bug-Bounty (same approach)
```bash
# Download + install + ready to use
bash <(curl -fsSL https://raw.githubusercontent.com/zwanski2019/zwanski-Bug-Bounty/main/install.sh)
./oauth-mapper
```

## Installation Methods

### Method 1: Pipe to Bash (Quickest)
```bash
bash <(curl -fsSL https://raw.githubusercontent.com/zwanski2019/zwanski-Bug-Bounty/main/install.sh)
```

### Method 2: Download First, Then Run
```bash
# Download installer
curl -fsSL https://raw.githubusercontent.com/zwanski2019/zwanski-Bug-Bounty/main/install.sh -o install.sh

# Review it if you want
cat install.sh

# Run it
bash install.sh
```

### Method 3: From Git Clone
```bash
git clone https://github.com/zwanski2019/zwanski-Bug-Bounty.git
cd zwanski-Bug-Bounty
bash install.sh
```

## What Gets Installed

```
zwanski-Bug-Bounty/
├── .venv/                      ← Isolated Python environment (auto-created)
├── oauth-mapper                ← Wrapper script (auto-created)
├── subdomain-recon             ← Wrapper script (auto-created)
├── scripts/
│   ├── zwanski-oauth-mapper.py
│   └── zwanski-subdomain-chain.sh
├── requirements.txt
├── setup.sh
└── install.sh                  ← This installer
```

Everything is in one directory. No system-level changes. Completely reversible.

## After Installation

### Start Using Immediately

```bash
# Interactive OAuth mapper
./oauth-mapper

# Or with a target
./oauth-mapper --target https://api.example.com --output findings.json

# Subdomain recon
./subdomain-recon target.com
```

### Command Format

The installer creates wrapper scripts that work from the installation directory:

```bash
# From the installed directory
cd zwanski-Bug-Bounty
./oauth-mapper --help
./subdomain-recon --help
```

## Environment Details

The install.sh script:

1. **Checks Prerequisites**
   - Python 3 must be installed
   - Git must be installed
   - curl must be available

2. **Clones Repository**
   - Downloads from GitHub
   - Or updates if already cloned

3. **Runs Full Setup**
   - Calls `setup.sh` which:
     - Creates `.venv/`
     - Installs dependencies
     - Creates wrapper scripts

4. **Creates Wrappers**
   - `./oauth-mapper` — runs OAuth mapper tool
   - `./subdomain-recon` — runs subdomain recon

## Prerequisites

### Required
- **Python 3.8+** (install via your package manager)
- **Git** (install via your package manager)
- **curl** (usually pre-installed)

### Install Python if Missing

**macOS:**
```bash
brew install python3
```

**Ubuntu/Debian:**
```bash
sudo apt-get update && sudo apt-get install python3
```

**CentOS/RHEL:**
```bash
sudo yum install python3
```

**Windows (WSL2):**
```bash
sudo apt-get update && sudo apt-get install python3
```

Once you have Python 3 and Git, run the one-liner above.

## Where It Installs

By default, the installer puts the repository in your current directory:

```bash
# Current directory becomes the install location
bash <(curl -fsSL ...)
# Creates: ./zwanski-Bug-Bounty/
```

To customize the location:

```bash
# Install in a specific directory
cd ~/my-tools
bash <(curl -fsSL https://raw.githubusercontent.com/zwanski2019/zwanski-Bug-Bounty/main/install.sh)
# Creates: ~/my-tools/zwanski-Bug-Bounty/
```

## Uninstall / Clean Up

Since everything is contained, uninstalling is trivial:

```bash
# Delete the entire directory
rm -rf zwanski-Bug-Bounty/
# Done! No system-level cleanup needed.
```

## Updating

To get the latest version:

```bash
# Just run the installer again
bash <(curl -fsSL https://raw.githubusercontent.com/zwanski2019/zwanski-Bug-Bounty/main/install.sh)
# It will update the existing clone
```

## Docker Alternative

If you prefer containers:

```bash
git clone https://github.com/zwanski2019/zwanski-Bug-Bounty.git
cd zwanski-Bug-Bounty
docker-compose build
docker-compose run --rm zwanski-oauth-mapper
```

## Troubleshooting

### "curl: command not found"
Install curl:
```bash
sudo apt-get install curl  # Ubuntu/Debian
brew install curl          # macOS
```

### "Python 3 not found"
Install Python 3 (see section above)

### "Git not found"
Install Git:
```bash
sudo apt-get install git   # Ubuntu/Debian
brew install git           # macOS
```

### Permission denied on install.sh
The installer automatically handles permissions, but if you manually download it:
```bash
chmod +x install.sh
bash install.sh
```

### Installation hangs
The installer runs setup.sh which can take 1-2 minutes the first time (installing venv). Be patient.

## How It Compares to Ollama

| Feature | Ollama | zwanski-Bug-Bounty |
|---------|--------|-------------------|
| One-command install | ✅ `curl ... \| sh` | ✅ `bash <(curl ...)` |
| No prior setup | ✅ | ✅ |
| Isolated environment | ✅ | ✅ (.venv/) |
| Ready to use immediately | ✅ | ✅ |
| No system pollution | ✅ | ✅ |
| Easy uninstall | ✅ | ✅ |
| Update via installer | ✅ | ✅ |

## Next Steps

1. **Run the one-liner** above
2. **Use the tools:**
   ```bash
   ./oauth-mapper
   ```
3. **Read full documentation:**
   - [QUICKSTART.md](QUICKSTART.md)
   - [PRODUCTION.md](PRODUCTION.md)

## Questions?

- Check [INSTALL.md](INSTALL.md) for detailed troubleshooting
- See [PRODUCTION.md](PRODUCTION.md) for advanced usage
- Open a GitHub issue: https://github.com/zwanski2019/zwanski-Bug-Bounty/issues

---

## Summary

**One command. Everything automated. Just like Ollama.**

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/zwanski2019/zwanski-Bug-Bounty/main/install.sh)
```

That's it. You're ready to hunt. 🎯
