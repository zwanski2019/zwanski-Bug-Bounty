#!/bin/bash
# zwanski-Bug-Bounty — One-Command Installer
# Works like Ollama: curl -fsSL https://install.zwanski.io | bash
# Or: bash <(curl -fsSL https://raw.githubusercontent.com/zwanski2019/zwanski-Bug-Bounty/main/install.sh)
# Or download and run locally: bash install.sh

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
echo "║        zwanski-Bug-Bounty — One-Command Installer             ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# ─────────────────────────────────────────────
# Check Python
# ─────────────────────────────────────────────
info "Checking Python..."
if ! command -v python3 &> /dev/null; then
    err "Python 3 not found. Install it first:
  macOS: brew install python3
  Ubuntu/Debian: sudo apt-get install python3
  CentOS/RHEL: sudo yum install python3"
fi
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
log "Python $PYTHON_VERSION found"

# ─────────────────────────────────────────────
# Check Git
# ─────────────────────────────────────────────
info "Checking Git..."
if ! command -v git &> /dev/null; then
    err "Git not found. Install it first:
  macOS: brew install git
  Ubuntu/Debian: sudo apt-get install git
  CentOS/RHEL: sudo yum install git"
fi
log "Git found"

# ─────────────────────────────────────────────
# Determine installation location
# ─────────────────────────────────────────────
INSTALL_DIR="${ZWANSKI_INSTALL_DIR:-.}"
REPO_DIR="$INSTALL_DIR/zwanski-Bug-Bounty"

info "Installation directory: $(cd "$INSTALL_DIR" && pwd)"

# ─────────────────────────────────────────────
# Clone or update repository
# ─────────────────────────────────────────────
if [[ -d "$REPO_DIR/.git" ]]; then
    info "Repository already exists, updating..."
    cd "$REPO_DIR"
    git pull origin main --quiet
    log "Repository updated"
else
    info "Cloning repository..."
    git clone https://github.com/zwanski2019/zwanski-Bug-Bounty.git "$REPO_DIR" --quiet
    cd "$REPO_DIR"
    log "Repository cloned"
fi

# ─────────────────────────────────────────────
# Run setup
# ─────────────────────────────────────────────
info "Running setup..."
bash setup.sh

# ─────────────────────────────────────────────
# Create global symlink (optional)
# ─────────────────────────────────────────────
GLOBAL_BIN="$HOME/.local/bin"
mkdir -p "$GLOBAL_BIN"

if [[ -w "$GLOBAL_BIN" ]]; then
    ln -sf "$(pwd)/oauth-mapper" "$GLOBAL_BIN/oauth-mapper" 2>/dev/null || true
    ln -sf "$(pwd)/subdomain-recon" "$GLOBAL_BIN/subdomain-recon" 2>/dev/null || true
    
    if [[ ":$PATH:" == *":$GLOBAL_BIN:"* ]]; then
        log "Global commands available (add to PATH if needed)"
    else
        warn "To use globally, add to PATH: export PATH=\$PATH:$GLOBAL_BIN"
    fi
fi

# ─────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║              Installation Complete! Ready to Use ✅            ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Start using immediately:"
echo ""
echo "  cd $REPO_DIR"
echo "  ./oauth-mapper"
echo ""
echo "Or from anywhere:"
echo "  $REPO_DIR/oauth-mapper --target https://example.com"
echo ""
echo "Next time, just run:"
echo "  bash <(curl -fsSL https://raw.githubusercontent.com/zwanski2019/zwanski-Bug-Bounty/main/install.sh)"
echo ""
log "All set! Happy hunting! 🎯"
echo ""
