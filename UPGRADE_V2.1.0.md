# ZWANSKI.BB v2.1.0 - Upgrade Guide

## 🎉 What's New

This release adds **auto-update notifications**, **finding tracker**, **CVSS calculator**, **scope manager**, and **enhanced reporting** - transforming ZWANSKI.BB into a complete bug bounty management platform.

---

## 🚀 Quick Upgrade

```bash
cd ~/zwanski-Bug-Bounty  # or wherever you installed
git pull origin main
zwanski restart  # or: python server.py
```

That's it! No database migrations or config changes needed.

---

## ✨ New Features Overview

### 1. **Auto-Update System** (Top Priority!)

**Inspired by Burp Suite, Nuclei, and Metasploit's update workflows.**

- ✅ Automatic GitHub release checking every hour
- ✅ Inline banner notification when updates available
- ✅ One-click update with git pull automation
- ✅ Changelog modal with formatted release notes
- ✅ Git status API (branch, commits ahead/behind, uncommitted changes)

**How it works:**
1. App checks GitHub releases API hourly (non-intrusive background check)
2. When newer version detected → banner slides in at top of dashboard
3. Click "View changes" → see full changelog with markdown formatting
4. Click "Update now" → performs `git pull` + restart prompt
5. Click "Dismiss" → hides banner (localStorage cache)

**API Endpoints:**
- `GET /api/version` - Current version + update status
- `POST /api/update` - Perform git pull
- `GET /api/git-status` - Repository status

**Files:**
- `version_manager.py` - Core version management logic
- `VERSION` - Current version file (2.1.0)
- `.update_cache.json` - Update check cache (auto-generated)

---

### 2. **Finding Tracker**

**Professional finding management with CVSS integration.**

Features:
- ✅ Full CRUD operations (add, view, edit, delete)
- ✅ Auto-generated IDs (`ZWBB-YYYYMMDD-NNNN`)
- ✅ Status tracking (new, submitted, triaged, resolved, duplicate, n/a)
- ✅ Platform association (HackerOne, Bugcrowd, Synack, etc.)
- ✅ Advanced filtering (severity, status, target, platform)
- ✅ Statistics dashboard (total, by severity, by status)
- ✅ Timestamps (created_at, updated_at)

**UI Location:** Sidebar → "Findings" tab

**API Endpoints:**
```bash
GET  /api/findings              # List all findings (with filters)
POST /api/findings              # Add new finding
GET  /api/findings/:id          # Get specific finding
PUT  /api/findings/:id          # Update finding
DELETE /api/findings/:id        # Delete finding
GET  /api/findings/stats        # Statistics
```

**Storage:** `findings.json` (auto-created, JSON format)

**Example Usage:**
```bash
# Create finding via API
curl -X POST http://localhost:1337/api/findings \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Stored XSS in profile bio",
    "target": "example.com",
    "platform": "HackerOne",
    "summary": "User input not sanitized...",
    "impact": "Account takeover possible...",
    "status": "new"
  }'
```

---

### 3. **CVSS 3.1 Calculator**

**Full CVSS 3.1 base score calculator with real-time results.**

Features:
- ✅ All 8 CVSS 3.1 metrics (AV, AC, PR, UI, S, C, I, A)
- ✅ Real-time calculation (base score + severity)
- ✅ Impact and exploitability sub-scores
- ✅ Standard vector string generation
- ✅ Color-coded severity (Critical=red, High=orange, etc.)
- ✅ Auto-integration with finding tracker

**UI Location:** Sidebar → "CVSS Calc" tab

**API Endpoint:**
```bash
POST /api/cvss/calculate
```

**Example Request:**
```bash
curl -X POST http://localhost:1337/api/cvss/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "metrics": {
      "attack_vector": "NETWORK",
      "attack_complexity": "LOW",
      "privileges_required": "NONE",
      "user_interaction": "NONE",
      "scope": "CHANGED",
      "confidentiality": "HIGH",
      "integrity": "HIGH",
      "availability": "HIGH"
    }
  }'
```

**Example Response:**
```json
{
  "base_score": 10.0,
  "severity": "CRITICAL",
  "vector_string": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H",
  "sub_scores": {
    "impact": 6.0,
    "exploitability": 3.9
  }
}
```

---

### 4. **Scope Manager**

**Track bug bounty program scopes and validate targets.**

Features:
- ✅ Program CRUD (add, update, delete programs)
- ✅ Scope validation engine (wildcard, regex, CIDR support)
- ✅ Quick scope check (validate if target is in/out of scope)
- ✅ Bulk import (parse HackerOne/Bugcrowd text format)
- ✅ Multi-platform support (6 major platforms + custom)
- ✅ Statistics dashboard (programs, scope items)

**Scope Patterns Supported:**
- Wildcard: `*.example.com`
- Exact: `api.example.com`
- Regex: `regex:.*\.api\..*`
- CIDR: `192.168.1.0/24` (basic)
- URL: `https://app.example.com`

**UI Location:** Sidebar → "Scope" tab

**API Endpoints:**
```bash
GET  /api/scope/programs        # List programs
POST /api/scope/programs        # Add program
GET  /api/scope/programs/:id    # Get specific program
PUT  /api/scope/programs/:id    # Update program
DELETE /api/scope/programs/:id  # Delete program
POST /api/scope/check           # Validate target
POST /api/scope/parse           # Parse scope text
GET  /api/scope/stats           # Statistics
```

**Storage:** `scopes.json` (auto-created, JSON format)

**Example Usage:**
```bash
# Check if target is in scope
curl -X POST http://localhost:1337/api/scope/check \
  -H "Content-Type: application/json" \
  -d '{"target": "api.example.com"}'
```

---

### 5. **Enhanced Reporting**

**Platform-specific report generation with auto-formatting.**

Supported Platforms:
- HackerOne (professional, markdown)
- Bugcrowd (concise, impact-first)
- Synack (technical, detailed)
- Intigriti (detailed POC)
- YesWeHack (structured)
- Bug Bounty Switzerland (formal, CVSS required)

**API Endpoints:**
```bash
POST /api/report/generate       # Generate platform report
GET  /api/report/platforms      # List supported platforms
```

**Example:**
```bash
curl -X POST http://localhost:1337/api/report/generate \
  -H "Content-Type: application/json" \
  -d '{
    "finding": {
      "title": "Stored XSS",
      "summary": "...",
      "impact": "...",
      "steps": ["1. ...", "2. ..."],
      "cvss": {"base_score": 7.5, "severity": "HIGH"}
    },
    "platform": "HackerOne"
  }'
```

---

## 📦 File Structure (New Files)

```
zwanski-Bug-Bounty/
├── VERSION                    # Version file (2.1.0)
├── CHANGELOG.md              # This changelog
├── version_manager.py        # Auto-update system
├── reporting_enhanced.py     # CVSS + finding tracker + reporting
├── scope_manager.py          # Scope management
├── findings.json             # Finding storage (auto-created)
├── scopes.json              # Scope storage (auto-created)
├── .update_cache.json       # Update cache (auto-created)
└── ui/index.html            # Enhanced UI with new tabs
```

---

## 🔄 Migration Notes

**No migration required!** This is a fully backward-compatible release.

- All existing features work as before
- New features are additive (new tabs, new APIs)
- No configuration changes needed
- No database migrations (uses JSON file storage)

---

## 🧪 Testing the New Features

### Test Auto-Update System
```bash
# Check version
curl http://localhost:1337/api/version

# Force update check
curl http://localhost:1337/api/version?force=true

# Get git status
curl http://localhost:1337/api/git-status
```

### Test Finding Tracker
```bash
# Add finding
curl -X POST http://localhost:1337/api/findings \
  -H "Content-Type: application/json" \
  -d '{"title":"Test XSS","target":"test.com","platform":"HackerOne"}'

# List findings
curl http://localhost:1337/api/findings

# Get stats
curl http://localhost:1337/api/findings/stats
```

### Test CVSS Calculator
```bash
curl -X POST http://localhost:1337/api/cvss/calculate \
  -H "Content-Type: application/json" \
  -d '{"metrics":{"attack_vector":"NETWORK","attack_complexity":"LOW","privileges_required":"NONE","user_interaction":"NONE","scope":"UNCHANGED","confidentiality":"HIGH","integrity":"NONE","availability":"NONE"}}'
```

### Test Scope Manager
```bash
# Add program
curl -X POST http://localhost:1337/api/scope/programs \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Program","platform":"HackerOne","in_scope":["*.example.com"],"out_of_scope":["dev.example.com"]}'

# Check scope
curl -X POST http://localhost:1337/api/scope/check \
  -H "Content-Type: application/json" \
  -d '{"target":"api.example.com"}'
```

---

## 🐛 Troubleshooting

### Update Banner Not Showing
- Check: `curl http://localhost:1337/api/version`
- Clear browser cache (Ctrl+Shift+R)
- Wait 2 seconds after page load (auto-checks on load)

### Missing Tabs
- Hard refresh browser (Ctrl+Shift+R)
- Check browser console for errors
- Ensure `ui/index.html` was updated

### API Errors
- Check Python modules imported: `python3 -c "from version_manager import version_manager; print('OK')"`
- Check server logs for import errors
- Restart server: `zwanski restart`

---

## 🎯 What's Next (v2.2.0 Roadmap)

- [ ] Export findings to CSV/JSON
- [ ] Import findings from other platforms
- [ ] Webhook notifications (Slack/Discord/Telegram)
- [ ] Advanced search across all findings
- [ ] Finding templates (XSS, SQLi, IDOR, etc.)
- [ ] Automated CVSS calculation from finding data
- [ ] Scope validation during recon

---

## 📞 Support

- **Issues**: https://github.com/zwanski2019/zwanski-Bug-Bounty/issues
- **Wiki**: https://github.com/zwanski2019/zwanski-Bug-Bounty/tree/main/docs/wiki
- **API Docs**: https://github.com/zwanski2019/zwanski-Bug-Bounty/blob/main/docs/wiki/api.md

---

**Maintained by Mohamed Ibrahim (zwanski)**  
zwanski.bio · Bug Bounty Switzerland · HackerOne · Bugcrowd
