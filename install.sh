#!/usr/bin/env bash
# ZWANSKI Bug Bounty Platform — Master Installer
# Installs tools, AI dashboard, and localhost UI.

set -e

REPO="https://github.com/zwanski2019/zwanski-Bug-Bounty.git"
PLATFORM_DIR="${ZWANSKI_INSTALL_DIR:-$HOME/.zwanski-bb}"
BIN_DIR="$HOME/.local/bin"
PORT="1337"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

log()  { echo -e "${GREEN}[+]${NC} $1"; }
info() { echo -e "${CYAN}[i]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[-]${NC} $1"; exit 1; }

has() { command -v "$1" >/dev/null 2>&1; }

install_pkg() {
  if has apt-get; then sudo apt-get install -y -qq "$@";
  elif has brew; then brew install "$@";
  elif has pacman; then sudo pacman -S --noconfirm "$@";
  elif has dnf; then sudo dnf install -y "$@";
  else return 1; fi
}

banner() {
  cat <<'EOF'

╔════════════════════════════════════════════════════════════════╗
║   ZWANSKI Bug Bounty Platform — Master Installer               ║
║   Installs tools, AI dashboard, and localhost UI               ║
╚════════════════════════════════════════════════════════════════╝

EOF
}

banner

if ! has python3; then
  warn "Python 3 is missing. Installing..."
  install_pkg python3 python3-venv python3-pip || err "Python 3 install failed"
fi

if ! has git; then
  warn "Git is missing. Installing..."
  install_pkg git || err "Git install failed"
fi

mkdir -p "$PLATFORM_DIR" "$BIN_DIR"

if [[ -d "$PLATFORM_DIR/.git" ]]; then
  info "Updating existing platform..."
  cd "$PLATFORM_DIR"
  git pull origin main --quiet || warn "git pull failed"
else
  info "Cloning the platform repository..."
  git clone --depth=1 "$REPO" "$PLATFORM_DIR" --quiet || err "Git clone failed"
  cd "$PLATFORM_DIR"
fi

info "Running setup script..."
bash setup.sh

info "Installing dashboard dependencies..."
source "$PLATFORM_DIR/.venv/bin/activate"
pip install -q flask flask-cors requests || warn "Failed to install dashboard dependencies"

# ======================
# ADDITIONAL SECURITY TOOLS
# ======================

info "Checking for additional security tools..."

# Subdominator (RevoltSecurities)
if ! has subdominator; then
  if [[ ! -d "$PLATFORM_DIR/Subdominator" ]]; then
    info "Cloning Subdominator..."
    git clone --depth=1 https://github.com/RevoltSecurities/Subdominator "$PLATFORM_DIR/Subdominator" 2>/dev/null || true
  fi
fi

# NeuroSploit (JoasASantos)
if ! has neurosploit; then
  if [[ ! -d "$PLATFORM_DIR/NeuroSploit" ]]; then
    info "Cloning NeuroSploit..."
    git clone --depth=1 https://github.com/JoasASantos/NeuroSploit "$PLATFORM_DIR/NeuroSploit" 2>/dev/null || true
  fi
fi

# CrawlAI-RAG (AnkitNayak-eth)
if ! has crawlai-rag; then
  if [[ ! -d "$PLATFORM_DIR/CrawlAI-RAG" ]]; then
    info "Cloning CrawlAI-RAG..."
    git clone --depth=1 https://github.com/AnkitNayak-eth/CrawlAI-RAG "$PLATFORM_DIR/CrawlAI-RAG" 2>/dev/null || true
  fi
fi

info "Creating platform launcher..."
cat > "$BIN_DIR/zwanski" <<'ZWN'
#!/usr/bin/env bash
PLATFORM="${ZWANSKI_INSTALL_DIR:-$HOME/.zwanski-bb}"
PORT="${ZWANSKI_PORT:-1337}"
VENV="$PLATFORM/.venv"
DASHBOARD_API="http://localhost:$PORT/api"
if [[ -f "$VENV/bin/activate" ]]; then
  source "$VENV/bin/activate"
fi

dashboard_available(){
  curl -s --fail "$DASHBOARD_API/tasks" >/dev/null 2>&1
}

dashboard_submit(){
  if [[ $# -eq 0 ]]; then
    return 1
  fi
  payload=$(python3 -c 'import json,sys; print(json.dumps({"cmd":" ".join(sys.argv[1:])}))' "$@")
  curl -s -X POST -H 'Content-Type: application/json' -d "$payload" "$DASHBOARD_API/run"
}

case "$1" in
  start|"")
    echo "Starting ZWANSKI dashboard on http://localhost:$PORT"
    python3 "$PLATFORM/server_monitor.py" --port "$PORT"
    ;;
  stop)
    pkill -f "python3 .*server_monitor.py" 2>/dev/null || true
    pkill -f "python3 .*server.py" 2>/dev/null && echo "Dashboard stopped" || echo "Dashboard not running"
    ;;
  status)
    if dashboard_available; then
      curl -s "$DASHBOARD_API/tools" | python3 -c 'import json,sys;data=json.load(sys.stdin);print("Tools installed: {}/{}".format(sum(1 for t in data if t.get("installed")), len(data)))'
    else
      echo "Dashboard offline. Use 'zwanski start' first."
    fi
    ;;
  run)
    shift
    if [[ $# -eq 0 ]]; then
      echo "Usage: zwanski run <command>"
      exit 1
    fi
    if dashboard_available; then
      dashboard_submit "$@"
    else
      exec "$@"
    fi
    ;;
  recon)
    shift
    if dashboard_available; then
      dashboard_submit "subdomain-recon" "$@"
    else
      exec "$PLATFORM/subdomain-recon" "$@"
    fi
    ;;
  oauth)
    shift
    if dashboard_available; then
      dashboard_submit "oauth-mapper" "$@"
    else
      exec python3 "$PLATFORM/oauth-mapper" "$@"
    fi
    ;;
  *)
    cat <<'EOF'
Usage: zwanski [command]

Commands:
  start      Start the localhost dashboard
  stop       Stop the dashboard
  status     Show installed tools status
  recon      Run the subdomain recon chain
  oauth      Run the OAuth mapper
EOF
    ;;
esac
ZWN
chmod +x "$BIN_DIR/zwanski"

ln -sf "$PLATFORM_DIR/oauth-mapper" "$BIN_DIR/oauth-mapper" 2>/dev/null || true
ln -sf "$PLATFORM_DIR/subdomain-recon" "$BIN_DIR/subdomain-recon" 2>/dev/null || true

if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
  info "Adding $BIN_DIR to PATH in shell profiles"
  for profile in "$HOME/.bashrc" "$HOME/.zshrc"; do
    if [[ -f "$profile" ]] && ! grep -q "$BIN_DIR" "$profile" 2>/dev/null; then
      echo "export PATH=\"$BIN_DIR:\$PATH\"" >> "$profile"
    fi
  done
  export PATH="$BIN_DIR:$PATH"
fi

cat > "$PLATFORM_DIR/.zwanski-installed" <<EOF
installed=$(date +%Y-%m-%dT%H:%M:%S%z)
path=$PLATFORM_DIR
dashboard=http://localhost:$PORT
EOF

info "Installation complete."
log "Run 'zwanski start' to launch the dashboard."
log "Open http://localhost:$PORT in your browser after starting."
