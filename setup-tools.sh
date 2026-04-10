#!/bin/bash
# Optional: Install Go-based external recon tools for subdomain-chain.sh
# Requires: Go 1.16+ (install from https://golang.org/doc/install)

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${GREEN}[+]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err() { echo -e "${RED}[-]${NC} $1"; exit 1; }

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Installing Optional Recon Tools"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Check if Go is installed
if ! command -v go &> /dev/null; then
    err "Go is not installed. Please install Go 1.16+ from https://golang.org/doc/install"
fi

log "Installing projectdiscovery tools..."

# Subfinder
log "Installing subfinder..."
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest

# HTTPx
log "Installing httpx..."
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest

# Nuclei
log "Installing nuclei..."
go install -v github.com/projectdiscovery/nuclei/v2/cmd/nuclei@latest

# DNSx
log "Installing dnsx..."
go install -v github.com/projectdiscovery/dnsx/cmd/dnsx@latest

# Third-party tools
log "Installing assetfinder..."
go install -v github.com/tomnomnom/assetfinder@latest

log "Installing puredns..."
go install -v github.com/d3mondev/puredns@latest

log "Installing anew..."
go install -v github.com/tomnomnom/anew@latest

# Add to PATH
GOPATH=$(go env GOPATH)
if [[ ":$PATH:" != *":$GOPATH/bin:"* ]]; then
    warn "Adding Go bin to PATH..."
    echo 'export PATH=$PATH:'"$GOPATH"'/bin' >> ~/.bashrc
    export PATH=$PATH:$GOPATH/bin
    log "Updated ~/.bashrc with Go bin path"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Installation Complete!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "All tools are now installed. You can use:"
echo "  bash scripts/zwanski-subdomain-chain.sh target.com"
echo ""
