# Installation & Quick Start

## Prerequisites

- Python 3.8 or newer
- pip (Python package installer)
- Git (optional, for cloning the repo)

## Installation (One Command)

### Option 1: Automated Setup Script

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/zwanski2019/zwanski-Bug-Bounty/main/setup.sh)
```

Or locally:
```bash
cd zwanski-Bug-Bounty
bash setup.sh
```

### Option 2: Manual Installation

```bash
# Clone the repository
git clone https://github.com/zwanski2019/zwanski-Bug-Bounty.git
cd zwanski-Bug-Bounty

# Install dependencies
pip3 install -r requirements.txt

# Make scripts executable
chmod +x scripts/*.sh scripts/*.py

# Verify installation
python3 scripts/zwanski-oauth-mapper.py --help
```

## Quick Usage

### OAuth Mapper (Interactive)

```bash
# Interactive guided menu (recommended for beginners)
python3 scripts/zwanski-oauth-mapper.py
```

### OAuth Mapper (CLI)

```bash
# Full scan on a target
python3 scripts/zwanski-oauth-mapper.py --target https://target.com

# Scan with authentication token
python3 scripts/zwanski-oauth-mapper.py --target https://target.com --token YOUR_TOKEN

# Export findings to JSON
python3 scripts/zwanski-oauth-mapper.py --target https://target.com --output findings.json
```

### Subdomain Chain Recon

```bash
# Run full recon pipeline
bash scripts/zwanski-subdomain-chain.sh target.com

# With custom output directory
bash scripts/zwanski-subdomain-chain.sh target.com ./custom_output_dir
```

## Verification

After installation, verify everything works:

```bash
cd zwanski-Bug-Bounty/scripts

# Check OAuth mapper
python3 zwanski-oauth-mapper.py --menu

# Check subdomain script (requires subfinder, amass, etc.)
bash zwanski-subdomain-chain.sh --help
```

## Supported Tools

### Built-in
- **OAuth Mapper**: OAuth/OIDC attack surface discovery
- **Subdomain Chain**: Full passive + active recon pipeline

### External Dependencies (for subdomain recon)

The subdomain chain script requires:
- `subfinder` - passive subdomain finder
- `assetfinder` - source asset discovery
- `puredns` - DNS resolution and wildcard detection
- `httpx` - HTTP probing
- `nuclei` - vulnerability scanning
- `anew` - unique line management
- `curl` - HTTP requests (usually pre-installed)
- `jq` - JSON parsing
- `dnsx` - DNS tool (fallback)

Install with:
```bash
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install -v github.com/tomnomnom/assetfinder@latest
go install -v github.com/d3mondev/puredns@latest
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
go install -v github.com/projectdiscovery/nuclei/v2/cmd/nuclei@latest
go install -v github.com/tomnomnom/anew@latest
go install -v github.com/projectdiscovery/dnsx/cmd/dnsx@latest
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'requests'"

```bash
pip3 install requests
```

### "Permission denied" on scripts

```bash
chmod +x scripts/*.sh scripts/*.py
```

### "Command not found" for external tools

Ensure Go tools are in your `$PATH`:
```bash
export PATH=$PATH:$(go env GOPATH)/bin
echo 'export PATH=$PATH:$(go env GOPATH)/bin' >> ~/.bashrc
```

## Directory Structure

```
zwanski-Bug-Bounty/
├── scripts/
│   ├── zwanski-oauth-mapper.py      # OAuth/OIDC attack surface mapper
│   └── zwanski-subdomain-chain.sh   # Full reconnaissance pipeline
├── requirements.txt                  # Python dependencies
├── setup.sh                          # Automated installation script
└── INSTALL.md                        # This file
```

## Support

For issues or feature requests, visit:
https://github.com/zwanski2019/zwanski-Bug-Bounty

## License

See LICENSE file in the repository.
