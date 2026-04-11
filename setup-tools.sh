#!/bin/bash
# Install Go-based recon tools (ProjectDiscovery + helpers) for the dashboard & scripts.
# Safe to re-run. Individual tool failures do not stop the rest.

set -u

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${GREEN}[+]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err() { echo -e "${RED}[-]${NC} $1"; exit 1; }

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Installing recon CLI tools (Go)"
echo "═══════════════════════════════════════════════════════════════"
echo ""

if ! command -v go &> /dev/null; then
    warn "Go is not installed. Install it, then re-run this script:"
    warn "  Debian/Ubuntu: sudo apt install golang-go"
    warn "  macOS: brew install go"
    warn "  https://go.dev/dl/"
    exit 0
fi

export PATH="$PATH:$(go env GOPATH)/bin"

go_install() {
    local label="$1"
    shift
    log "Installing $label..."
    if go install -v "$@"; then
        return 0
    fi
    warn "$label install failed (network, proxy, or version) — skip and continue"
    return 0
}

go_install "subfinder" github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go_install "httpx" github.com/projectdiscovery/httpx/cmd/httpx@latest
go_install "nuclei" github.com/projectdiscovery/nuclei/v2/cmd/nuclei@latest
go_install "dnsx" github.com/projectdiscovery/dnsx/cmd/dnsx@latest
go_install "assetfinder" github.com/tomnomnom/assetfinder@latest
go_install "puredns" github.com/d3mondev/puredns@latest
go_install "anew" github.com/tomnomnom/anew@latest

GOPATH=$(go env GOPATH)
GOBIN="$GOPATH/bin"
append_path_line='export PATH="$PATH:'"$GOBIN"'"'
if [[ ":$PATH:" != *":$GOBIN:"* ]]; then
    warn "Adding Go bin ($GOBIN) to PATH in shell profiles (if missing)..."
    for profile in "$HOME/.bashrc" "$HOME/.zshrc"; do
        if [[ -f "$profile" ]] && ! grep -qF "$GOBIN" "$profile" 2>/dev/null; then
            echo "$append_path_line" >> "$profile"
            log "Updated $profile"
        fi
    done
    export PATH="$PATH:$GOBIN"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Done — open a new terminal (or: source ~/.bashrc)"
echo "  Verify:  subfinder -version && httpx -version"
echo "═══════════════════════════════════════════════════════════════"
echo ""
