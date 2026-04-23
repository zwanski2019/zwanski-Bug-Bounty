# Deployment Checklist - ZWANSKI.BB v2.1.0

## ✅ Pre-Deployment Verification

### Files Created ✅
- [x] `version_manager.py` - Auto-update system
- [x] `reporting_enhanced.py` - Finding tracker + CVSS + reporting
- [x] `scope_manager.py` - Scope management
- [x] `VERSION` - Version file (2.1.0)
- [x] `CHANGELOG.md` - Full changelog
- [x] `UPGRADE_V2.1.0.md` - Upgrade guide
- [x] `IMPLEMENTATION_SUMMARY.md` - Technical summary
- [x] `DEPLOY_CHECKLIST.md` - This file

### Files Modified ✅
- [x] `server.py` - Added imports + 20 API endpoints
- [x] `ui/index.html` - Added 3 tabs + update banner + JS functions

### Module Tests ✅
```bash
✅ All modules imported successfully
Version Manager: 2.1.0
CVSS Calculator: Ready
Finding Tracker: Ready
Scope Manager: Ready
```

---

## 🚀 Deployment Steps

### Step 1: Copy Files to Your Repo
```bash
# Navigate to your actual repo
cd ~/zwanski-Bug-Bounty  # Adjust path as needed

# Copy new files from enhanced version
cp /home/claude/bug-bounty-enhanced/version_manager.py .
cp /home/claude/bug-bounty-enhanced/reporting_enhanced.py .
cp /home/claude/bug-bounty-enhanced/scope_manager.py .
cp /home/claude/bug-bounty-enhanced/VERSION .
cp /home/claude/bug-bounty-enhanced/CHANGELOG.md .
cp /home/claude/bug-bounty-enhanced/UPGRADE_V2.1.0.md .

# Backup and replace modified files
cp server.py server.py.backup
cp ui/index.html ui/index.html.backup
cp /home/claude/bug-bounty-enhanced/server.py .
cp /home/claude/bug-bounty-enhanced/ui/index.html ui/
```

### Step 2: Test Locally
```bash
# Test imports
python3 -c "
from version_manager import version_manager
from reporting_enhanced import cvss_calculator, finding_tracker, report_generator
from scope_manager import scope_manager
print('✅ All imports successful')
"

# Start server
python3 server.py
```

### Step 3: Test in Browser
1. Open http://localhost:1337
2. Wait 2 seconds for update banner
3. Check all tabs appear in sidebar:
   - Command ✓
   - Telemetry ✓
   - Agentic ✓
   - Arsenal ✓
   - **Findings** ← NEW
   - **Scope** ← NEW
   - **CVSS Calc** ← NEW
   - Watchdog ✓
   - Terminal ✓
   - Intel AI ✓
   - Reports ✓
   - Config ✓

4. Test each new tab loads without errors

### Step 4: Test API Endpoints
```bash
# Version check
curl http://localhost:1337/api/version | jq

# Add test finding
curl -X POST http://localhost:1337/api/findings \
  -H "Content-Type: application/json" \
  -d '{"title":"Test Finding","target":"example.com","platform":"HackerOne"}' | jq

# List findings
curl http://localhost:1337/api/findings | jq

# Calculate CVSS
curl -X POST http://localhost:1337/api/cvss/calculate \
  -H "Content-Type: application/json" \
  -d '{"metrics":{"attack_vector":"NETWORK","attack_complexity":"LOW","privileges_required":"NONE","user_interaction":"NONE","scope":"UNCHANGED","confidentiality":"HIGH","integrity":"NONE","availability":"NONE"}}' | jq

# Add scope program
curl -X POST http://localhost:1337/api/scope/programs \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Program","platform":"HackerOne","in_scope":["*.example.com"]}' | jq

# Check scope
curl -X POST http://localhost:1337/api/scope/check \
  -H "Content-Type: application/json" \
  -d '{"target":"api.example.com"}' | jq
```

### Step 5: Git Commit & Push
```bash
# Add all new files
git add version_manager.py reporting_enhanced.py scope_manager.py
git add VERSION CHANGELOG.md UPGRADE_V2.1.0.md
git add server.py ui/index.html

# Check what changed
git status
git diff --cached

# Commit
git commit -m "feat: Add auto-update + finding tracker + CVSS calc + scope manager (v2.1.0)

- Auto-update system with GitHub release checking
- Finding tracker with CRUD operations
- CVSS 3.1 calculator
- Scope manager with validation engine
- Enhanced reporting for 6 platforms
- 20 new API endpoints
- 3 new UI tabs

See CHANGELOG.md for full details"

# Push to GitHub
git push origin main
```

### Step 6: Create GitHub Release
1. Go to: https://github.com/zwanski2019/zwanski-Bug-Bounty/releases/new
2. Click "Choose a tag" → Type `v2.1.0` → Create tag
3. **Release title:** `v2.1.0 - Auto-Update + Finding Tracker + CVSS Calculator`
4. **Description:** (Copy the "Added" section from CHANGELOG.md)
5. Click "Publish release"

### Step 7: Verify Auto-Update Works
1. Wait ~10 minutes
2. Reload dashboard (http://localhost:1337)
3. Update banner should appear with "v2.1.0 available"
4. Click "View changes" → changelog should display
5. Click "Dismiss" → banner should hide

---

## 🧪 Feature Testing

### Finding Tracker
1. Click "Findings" tab
2. Click "+ New Finding"
3. Fill in form, click "Save Finding"
4. Verify finding appears in list
5. Test filters (severity, status, target)
6. Check stats update

### Scope Manager
1. Click "Scope" tab
2. Click "+ New Program"
3. Add program with in-scope assets
4. Test "Quick Scope Check" with matching domain
5. Verify scope validation works (in-scope vs out-of-scope)

### CVSS Calculator
1. Click "CVSS Calc" tab
2. Select metrics (try: AV=Network, AC=Low, PR=None, UI=None, S=Unchanged, C=High, I=None, A=None)
3. Click "Calculate Score"
4. Verify result shows: 7.5 (HIGH)
5. Check vector string: CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N

---

## 📋 Post-Deployment

### Update README.md
Add to Features section:
```markdown
## New in v2.1.0

- **Auto-Update System**: GitHub release checking with one-click updates
- **Finding Tracker**: Professional vulnerability finding management
- **CVSS 3.1 Calculator**: Real-time CVSS base score calculation
- **Scope Manager**: Bug bounty program scope validation
- **Enhanced Reporting**: Platform-specific report generation
```

### Announce Release
- [ ] Post on Twitter/X
- [ ] Update zwanski.bio portfolio
- [ ] Notify any active collaborators

---

## ⚠️ Rollback Plan (if needed)

If something goes wrong:
```bash
# Restore backups
cp server.py.backup server.py
cp ui/index.html.backup ui/index.html

# Remove new files
rm version_manager.py reporting_enhanced.py scope_manager.py
rm VERSION CHANGELOG.md UPGRADE_V2.1.0.md

# Restart server
python3 server.py
```

---

## 📊 Success Criteria

- [x] All Python modules import without errors
- [ ] Server starts without errors
- [ ] All 3 new tabs appear in sidebar
- [ ] Update banner appears (after GitHub release)
- [ ] All 20 API endpoints respond
- [ ] No JavaScript console errors
- [ ] Finding tracker: Add/list/delete works
- [ ] CVSS calculator: Returns correct scores
- [ ] Scope manager: Validates targets correctly

---

## 🎉 Completion

When all checkboxes are marked:
1. Delete `DEPLOY_CHECKLIST.md` (or keep for reference)
2. Celebrate! 🎊
3. Monitor GitHub issues for user feedback

---

**Need help?** Check UPGRADE_V2.1.0.md troubleshooting section
