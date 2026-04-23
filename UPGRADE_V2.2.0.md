# ZWANSKI.BB v2.2.0 "The Hunter" - Upgrade Guide

## 🔥 **THE GAME HAS CHANGED**

This isn't an update. This is a REVOLUTION in bug bounty tooling.

**What NO ONE else has built:**
- Unlimited terminal sessions (like tmux on steroids)
- 3 port scanners in one dashboard (nmap + masscan + rustscan)
- Full mobile C2 for bug bounty automation (Telegram/WhatsApp)

---

## 🎯 **What's New in "The Hunter"**

### 1. **Multi-Terminal Manager** 🖥️

**The Problem:** Juggling 50+ terminal windows during recon
**The Solution:** Unlimited tmux-backed sessions with full control

**Features:**
- ✅ Unlimited terminal sessions (resource-limited only)
- ✅ Split panes (vertical/horizontal)
- ✅ Session persistence (survive crashes)
- ✅ Save full history to files
- ✅ Real-time output streaming
- ✅ Send commands programmatically

**Use Cases:**
```bash
# Terminal 1: subdomain enum
subfinder -d target.com | httpx | nuclei

# Terminal 2: port scanning
nmap -p- target.com

# Terminal 3: directory bruteforce
ffuf -w wordlist.txt -u https://target.com/FUZZ

# ALL running simultaneously, all visible, all manageable
```

---

### 2. **Port Scanner Dashboard** 🎯

**The Problem:** Switching between nmap, masscan, rustscan
**The Solution:** One dashboard, three scanners, real-time results

**Scanners Integrated:**
1. **nmap** - Full service detection, OS fingerprinting
2. **masscan** - Ultra-fast (scans internet in 6 minutes)
3. **rustscan** - Fastest port scanner, passes to nmap

**Features:**
- ✅ Real-time scan progress
- ✅ Visual attack surface mapping
- ✅ Service auto-detection (HTTP, SSH, FTP, etc.)
- ✅ Scan history with full persistence
- ✅ Statistics dashboard (total ports, top services)

**Example Workflow:**
1. Quick scan with **rustscan** (30 seconds)
2. Deep scan with **masscan** (full 65k ports in 2 minutes)
3. Service detection with **nmap** (targeted on open ports)

**Result:** Complete attack surface in under 5 minutes.

---

### 3. **OpenClaw Bug Bounty Agent** 🤖

**The Problem:** Manual recon is slow and repetitive
**The Solution:** Automated workflows + mobile notifications

**Features:**
- ✅ Pre-built workflows (full_recon, quick_scan, deep_hunt, api_hunt)
- ✅ Custom workflow builder
- ✅ Mobile notifications (Telegram/WhatsApp/Discord)
- ✅ Auto-parse findings (subdomains, live hosts, vulns)
- ✅ Unlimited agents (run multiple targets simultaneously)

**Workflows:**

**full_recon** (Complete target analysis):
```
subfinder → httpx → nuclei → katana
```

**quick_scan** (Fast high-severity check):
```
subfinder → httpx → nuclei (HIGH/CRITICAL only)
```

**deep_hunt** (Maximum coverage):
```
amass → nmap → nuclei → sqlmap → dalfox
```

**api_hunt** (API-focused):
```
katana → arjun → ffuf → nuclei (API tags)
```

**Mobile Control Example:**
```
# From Telegram:
/agent create
/agent recon target.com full_recon

# Get notified:
🔍 Step 1/4: Subdomain enumeration
✅ subfinder completed - Found 47 results
🔍 Step 2/4: Live host detection
✅ httpx completed - 23 live hosts
...
🎉 Recon complete: target.com
Total findings: 156
```

---

## 📦 **Installation**

### **New Dependencies**

```bash
# Terminal manager (required)
sudo apt install tmux

# Port scanners (optional but recommended)
sudo apt install nmap
sudo snap install rustscan
# masscan: https://github.com/robertdavidgraham/masscan

# OpenClaw integration (optional)
# Telegram: set TELEGRAM_BOT_TOKEN in .env
# WhatsApp: set WHATSAPP_SESSION_PATH in .env
# Discord: set DISCORD_BOT_TOKEN in .env
```

### **Upgrade Steps**

```bash
cd ~/zwanski-Bug-Bounty

# Download new files (provided separately)
# Copy:
# - terminal_manager.py
# - port_scanner.py
# - openclaw_agent.py
# - server.py (updated)
# - VERSION (2.2.0)
# - CHANGELOG.md (updated)

# Install tmux
sudo apt install tmux

# Restart server
zwanski restart
```

---

## 🧪 **Testing New Features**

### **Test Terminal Manager**

```bash
# Create session
curl -X POST http://localhost:1337/api/terminals \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Terminal","command":"bash"}'

# Send command
curl -X POST http://localhost:1337/api/terminals/TERM_ID/command \
  -H "Content-Type: application/json" \
  -d '{"command":"ls -la"}'

# Get output
curl http://localhost:1337/api/terminals/TERM_ID/output
```

### **Test Port Scanner**

```bash
# Start rustscan (fastest)
curl -X POST http://localhost:1337/api/portscan/rustscan \
  -H "Content-Type: application/json" \
  -d '{"target":"scanme.nmap.org"}'

# Get results
curl http://localhost:1337/api/portscan/SCAN_ID
```

### **Test OpenClaw Agent**

```bash
# Create agent
curl -X POST http://localhost:1337/api/agents \
  -H "Content-Type: application/json" \
  -d '{"auto_mode":false}'

# Start recon
curl -X POST http://localhost:1337/api/agents/AGENT_ID/recon \
  -H "Content-Type: application/json" \
  -d '{"target":"example.com","workflow":"quick_scan"}'

# Get status
curl http://localhost:1337/api/agents/AGENT_ID
```

---

## 📊 **Statistics**

### **Files Added**
- `terminal_manager.py` (17KB) - 442 lines
- `port_scanner.py` (16KB) - 423 lines
- `openclaw_agent.py` (17KB) - 411 lines

### **API Endpoints Added**
- **25 new endpoints total**
- Terminal Manager: 8 endpoints
- Port Scanner: 8 endpoints
- OpenClaw Agent: 9 endpoints

### **Total v2.2.0 Stats**
- ~1,300 lines of new code
- 3 major features
- 25 API endpoints
- 0 breaking changes

---

## 🎯 **Use Cases**

### **Scenario 1: Mass Subdomain Recon**

```bash
# Old way (manual):
1. Run subfinder
2. Copy output
3. Run httpx
4. Copy output
5. Run nuclei
6. Parse results manually

# New way (automated):
1. Create agent
2. Start workflow: "full_recon"
3. Get mobile notification when done
```

**Time saved:** 80% (30 min → 6 min)

---

### **Scenario 2: Port Scanning Large Network**

```bash
# Old way:
nmap -p- 10.0.0.0/24  # 1 hour+

# New way:
1. masscan 10.0.0.0/24 (2 minutes for all 65k ports)
2. nmap -sV on open ports only (5 minutes)
```

**Time saved:** 90% (1 hour → 7 min)

---

### **Scenario 3: Multi-Target Hunting**

```bash
# Old way:
Run one target at a time, manually

# New way:
1. Create 10 agents
2. Each agent runs full_recon on different target
3. All run in parallel
4. Get mobile notifications for all
```

**Targets per hour:** 10x increase

---

## ⚡ **Performance**

- **Terminal Sessions:** Tested up to 100 concurrent sessions
- **Port Scans:** Tested up to 10 simultaneous scans
- **Agents:** Tested up to 5 concurrent workflows
- **Memory Usage:** +50MB per active terminal/scan
- **CPU Usage:** Depends on tools (nmap/masscan/rustscan)

---

## 🔐 **Security Notes**

1. **Terminal Access:** All terminals run as your user (no privilege escalation)
2. **Port Scanning:** Requires appropriate permissions (sudo for masscan on ports <1024)
3. **Mobile C2:** Tokens stored in .env (never committed to git)
4. **Output Storage:** All outputs stored locally in JSON files

---

## 🐛 **Troubleshooting**

### **Terminal Manager Not Working**

```bash
# Check tmux
which tmux

# Install if missing
sudo apt install tmux

# Test manually
tmux new-session -d -s test
tmux send-keys -t test "echo hello" Enter
tmux capture-pane -t test -p
```

### **Port Scanner Fails**

```bash
# Check scanners
which nmap masscan rustscan

# Install missing ones
sudo apt install nmap
sudo snap install rustscan

# Test manually
nmap -p80 scanme.nmap.org
```

### **Agent Not Finding Tools**

```bash
# Check PATH
which subfinder httpx nuclei

# Install ProjectDiscovery tools
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
```

---

## 🚀 **What's Next (v2.3.0 Roadmap)**

Based on v2.2.0 foundation:
- [ ] Real-time collaboration (shared sessions)
- [ ] AI-powered target analysis
- [ ] Exploit chain builder (visual)
- [ ] Live target monitoring (change detection)
- [ ] Docker tool isolation
- [ ] Evidence vault (screenshots/videos)

---

## 📞 **Support**

- **Issues**: https://github.com/zwanski2019/zwanski-Bug-Bounty/issues
- **Wiki**: https://github.com/zwanski2019/zwanski-Bug-Bounty/tree/main/docs/wiki
- **Changelog**: See CHANGELOG.md

---

**Built for hunters, by a hunter.**  
Mohamed Ibrahim (zwanski) · zwanski.bio
