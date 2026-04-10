#!/bin/bash
# zwanski-Bug-Bounty — Automated Installation & Setup Script
# Installs all dependencies and configures the toolkit for first use.

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[+]${NC} $1"; }
info() { echo -e "${BLUE}[i]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err() { echo -e "${RED}[-]${NC} $1"; exit 1; }

# ─────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║        zwanski-Bug-Bounty Installation & Setup Script         ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# ─────────────────────────────────────────────
# Check Python version
# ─────────────────────────────────────────────
info "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    err "Python 3 is not installed. Please install Python 3.8 or newer."
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
info "Found Python $PYTHON_VERSION"

# ─────────────────────────────────────────────
# Check pip
# ─────────────────────────────────────────────
info "Checking pip..."
if ! command -v pip3 &> /dev/null; then
    err "pip3 is not installed. Please install pip3."
fi
log "pip3 is available"

# ─────────────────────────────────────────────
# Determine script directory
# ─────────────────────────────────────────────
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
info "Installation directory: $SCRIPT_DIR"

# ─────────────────────────────────────────────
# Install Python dependencies
# ─────────────────────────────────────────────
info "Installing Python dependencies..."
if [[ -f "$SCRIPT_DIR/requirements.txt" ]]; then
    pip3 install -r "$SCRIPT_DIR/requirements.txt" --quiet
    log "Python dependencies installed"
else
    warn "requirements.txt not found — installing requests manually"
    pip3 install requests urllib3 --quiet
    log "Essential packages installed"
fi

# ─────────────────────────────────────────────
# Make scripts executable
# ─────────────────────────────────────────────
info "Setting up permissions..."
if [[ -d "$SCRIPT_DIR/scripts" ]]; then
    chmod +x "$SCRIPT_DIR/scripts"/*.sh 2>/dev/null || true
    chmod +x "$SCRIPT_DIR/scripts"/*.py 2>/dev/null || true
    log "Scripts are now executable"
else
    warn "scripts/ directory not found"
fi

# ─────────────────────────────────────────────
# Verify installation
# ─────────────────────────────────────────────
info "Verifying installation..."

OAUTH_MAPPER="$SCRIPT_DIR/scripts/zwanski-oauth-mapper.py"
if [[ -f "$OAUTH_MAPPER" ]]; then
    if python3 -m py_compile "$OAUTH_MAPPER" 2>/dev/null; then
        log "OAuth mapper is functional"
    else
        warn "OAuth mapper has syntax issues"
    fi
else
    warn "OAuth mapper script not found"
fi

SUBDOMAIN_CHAIN="$SCRIPT_DIR/scripts/zwanski-subdomain-chain.sh"
if [[ -f "$SUBDOMAIN_CHAIN" ]]; then
    log "Subdomain chain script is present"
else
    warn "Subdomain chain script not found"
fi

# ─────────────────────────────────────────────
# Summary & Next Steps
# ─────────────────────────────────────────────
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                  Installation Complete!                        ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo ""
echo "1. OAuth Mapper (Interactive):"
echo "   python3 $OAUTH_MAPPER"
echo ""
echo "2. OAuth Mapper (CLI):"
echo "   python3 $OAUTH_MAPPER --target https://target.com"
echo ""
echo "3. Subdomain Recon:"
echo "   bash $SUBDOMAIN_CHAIN target.com"
echo ""
echo "For detailed usage, run:"
echo "   python3 $OAUTH_MAPPER --help"
echo ""
echo "Optional: Install external recon tools"
echo "   bash setup-tools.sh  (if available)"
echo ""
info "Setup complete. You're ready to go!"
echo ""
