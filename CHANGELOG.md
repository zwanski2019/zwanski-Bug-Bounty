# Changelog

All notable changes to ZWANSKI Bug Bounty Platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2026-04-23

### Added

#### 🎁 Auto-Update System (Burp Suite/Nuclei-inspired)
- **Version Manager** (`version_manager.py`): Automatic GitHub release checking with semantic version comparison
- **Update Notification Banner**: Inline banner at top of dashboard when updates available
- **Changelog Modal**: View formatted release notes before updating
- **One-Click Update**: Git pull automation with restart prompt
- **Background Checker**: Hourly automatic update checks (non-intrusive)
- **Update API Endpoints**:
  - `GET /api/version` - Check current version and update status
  - `POST /api/update` - Perform git pull update
  - `GET /api/git-status` - Repository status (branch, commits, changes)

#### 🎯 Finding Tracker
- **Full CRUD Operations**: Add, view, update, delete vulnerability findings
- **Finding Management** (`reporting_enhanced.py`): 
  - Auto-generated IDs (format: `ZWBB-YYYYMMDD-NNNN`)
  - Status tracking (new, submitted, triaged, resolved, duplicate, n/a)
  - Platform association (HackerOne, Bugcrowd, Synack, etc.)
- **Advanced Filtering**: By severity, status, target, platform
- **Statistics Dashboard**: Total findings, severity breakdown, status distribution
- **Finding Timeline**: Created/updated timestamps for each finding
- **API Endpoints**:
  - `GET /api/findings` - List findings with filters
  - `POST /api/findings` - Add new finding
  - `GET/PUT/DELETE /api/findings/:id` - Manage specific finding
  - `GET /api/findings/stats` - Finding statistics

#### 📊 CVSS 3.1 Calculator
- **Full CVSS 3.1 Implementation**: Calculate base score and severity
- **Interactive UI**: Dropdown selectors for all 8 metrics
- **Real-time Calculation**: Impact and exploitability sub-scores
- **Vector String Generation**: Standard CVSS vector format
- **Color-Coded Severity**: Visual indicators (Critical=red, High=orange, etc.)
- **API Endpoint**: `POST /api/cvss/calculate` - Calculate CVSS scores

#### 🎯 Scope Manager
- **Program CRUD**: Add, update, delete bug bounty programs
- **Scope Validation** (`scope_manager.py`):
  - Wildcard domain matching (`*.example.com`)
  - Regex pattern support (`regex:.*\.api\..*`)
  - CIDR range support (basic IP matching)
  - Exact domain and URL matching
- **Quick Scope Check**: Validate if target is in/out of scope across all programs
- **Bulk Import**: Parse scope from HackerOne/Bugcrowd text format
- **Program Statistics**: Total programs, active count, scope item counts
- **Multi-Platform Support**: HackerOne, Bugcrowd, Synack, Intigriti, YesWeHack, Bug Bounty Switzerland
- **API Endpoints**:
  - `GET /api/scope/programs` - List programs with filters
  - `POST /api/scope/programs` - Add new program
  - `GET/PUT/DELETE /api/scope/programs/:id` - Manage specific program
  - `POST /api/scope/check` - Validate target scope
  - `POST /api/scope/parse` - Parse scope from text
  - `GET /api/scope/stats` - Scope statistics

#### 📝 Enhanced Reporting
- **Platform-Specific Templates**: Auto-formatted reports for:
  - HackerOne (professional tone, markdown)
  - Bugcrowd (concise, impact-first)
  - Synack (technical, detailed)
  - Intigriti (detailed POC)
  - YesWeHack (structured)
  - Bug Bounty Switzerland (formal, CVSS required)
- **Report Generator** (`reporting_enhanced.py`): Auto-format findings per platform
- **CVSS Integration**: Auto-calculate and include CVSS scores in findings
- **API Endpoints**:
  - `POST /api/report/generate` - Generate platform-specific report
  - `GET /api/report/platforms` - List supported platforms

### Improved

- **UI Navigation**: Added Findings, Scope, and CVSS Calc tabs to sidebar
- **Dashboard Telemetry**: Added version badge to footer with update indicator
- **Error Handling**: Better error messages for API failures
- **Data Persistence**: All findings and programs stored in JSON files
- **Session Management**: Auto-load data when switching to relevant tabs

### Technical Details

- **New Dependencies**: None (pure Python standard library + existing Flask/requests)
- **File Structure**:
  - `version_manager.py` - Version checking and update automation
  - `reporting_enhanced.py` - CVSS calculator, finding tracker, report generator
  - `scope_manager.py` - Scope management and validation
  - `VERSION` - Current version file
  - `.update_cache.json` - Update check cache
  - `findings.json` - Finding storage
  - `scopes.json` - Program scope storage

### Breaking Changes

None. Fully backward compatible with existing installations.

### Upgrade Instructions

1. **Git Pull**: `git pull origin main`
2. **Restart Server**: `zwanski restart` or `python server.py`
3. **No Migration Needed**: New features work alongside existing functionality

---

## [2.0.0] - 2026-04-15

### Added
- Initial release of ZWANSKI.BB Command Center
- War Map visualization
- Agentic recon pipelines
- Arsenal tool management
- Zwanski Watchdog integration
- Intel AI with OpenRouter
- Terminal streaming with xterm
- Setup wizard

---

## Versioning Scheme

- **MAJOR**: Breaking changes, architectural rewrites
- **MINOR**: New features, backward-compatible additions
- **PATCH**: Bug fixes, minor improvements

---

## Links

- [GitHub Repository](https://github.com/zwanski2019/zwanski-Bug-Bounty)
- [Documentation Wiki](https://github.com/zwanski2019/zwanski-Bug-Bounty/tree/main/docs/wiki)
- [API Reference](https://github.com/zwanski2019/zwanski-Bug-Bounty/blob/main/docs/wiki/api.md)
- [Issue Tracker](https://github.com/zwanski2019/zwanski-Bug-Bounty/issues)
