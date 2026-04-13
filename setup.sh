#!/bin/bash
# zwanski-Bug-Bounty — Automated Installation & Setup Script with Virtual Environment
# Creates isolated Python environment and installs all dependencies for first use.

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
echo "║   zwanski-Bug-Bounty Installation & Setup with Virtual Env    ║"
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
# Determine script directory
# ─────────────────────────────────────────────
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="$SCRIPT_DIR/.venv"
info "Installation directory: $SCRIPT_DIR"

# ─────────────────────────────────────────────
# Create Virtual Environment
# ─────────────────────────────────────────────
info "Creating Python virtual environment..."
if [[ -d "$VENV_DIR" ]]; then
    warn "Virtual environment already exists at $VENV_DIR"
else
    python3 -m venv "$VENV_DIR" || err "Failed to create virtual environment"
    log "Virtual environment created at $VENV_DIR"
fi

# ─────────────────────────────────────────────
# Activate virtual environment
# ─────────────────────────────────────────────
info "Activating virtual environment..."
source "$VENV_DIR/bin/activate" || err "Failed to activate virtual environment"
log "Virtual environment activated"

# ─────────────────────────────────────────────
# Upgrade pip in venv
# ─────────────────────────────────────────────
info "Upgrading pip in virtual environment..."
pip install --upgrade pip --quiet 2>/dev/null || warn "Could not upgrade pip (may be ok)"
log "pip is up to date"

# ─────────────────────────────────────────────
# Install Python dependencies in venv
# ─────────────────────────────────────────────
info "Installing Python dependencies in virtual environment..."
if [[ -f "$SCRIPT_DIR/requirements.txt" ]]; then
    pip install -r "$SCRIPT_DIR/requirements.txt" --quiet
    log "Python dependencies installed in venv"
else
    warn "requirements.txt not found — installing requests manually"
    pip install requests urllib3 --quiet
    log "Essential packages installed in venv"
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
# Create convenience wrapper scripts
# ─────────────────────────────────────────────
info "Creating convenience wrapper scripts..."

# OAuth mapper wrapper
cat > "$SCRIPT_DIR/oauth-mapper" << 'EOF'
#!/bin/bash
set -e
SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$( cd "$( dirname "$SCRIPT_PATH" )" && pwd )"
source "$SCRIPT_DIR/.venv/bin/activate"
python3 "$SCRIPT_DIR/scripts/zwanski-oauth-mapper.py" "$@"
EOF
chmod +x "$SCRIPT_DIR/oauth-mapper"
log "Created: ./oauth-mapper"

# Subdomain chain wrapper
cat > "$SCRIPT_DIR/subdomain-recon" << 'EOF'
#!/bin/bash
set -e
SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$( cd "$( dirname "$SCRIPT_PATH" )" && pwd )"
bash "$SCRIPT_DIR/scripts/zwanski-subdomain-chain.sh" "$@"
EOF
chmod +x "$SCRIPT_DIR/subdomain-recon"
log "Created: ./subdomain-recon"

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
echo "║              Installation Complete! ✅                         ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Virtual environment created at: $VENV_DIR"
echo "All dependencies installed in isolated environment."
echo ""
echo "Quick start commands:"
echo ""
echo "1. OAuth Mapper (Interactive):"
echo "   ./oauth-mapper"
echo ""
echo "2. OAuth Mapper (with target):"
echo "   ./oauth-mapper --target https://target.com"
echo ""
echo "3. Subdomain Recon:"
echo "   ./subdomain-recon target.com"
echo ""
echo "Advanced usage:"
echo "   source .venv/bin/activate    # Activate venv manually"
echo "   python3 scripts/zwanski-oauth-mapper.py --help"
echo ""
echo "Optional: Install external recon tools"
echo "   bash setup-tools.sh"
echo ""
info "Setup complete. You're ready to go!"
echo ""
