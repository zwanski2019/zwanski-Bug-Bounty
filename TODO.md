# ZWANSKI.BB v2.0 Implementation TODO

## Status: In Progress

### 1. [x] Create .env.example and update config loading to use os.getenv('OPENROUTER_API_KEY')
### 2. [x] Add Control Cluster to ui/index.html header: RUN SCAN, RESTART SYSTEM, AI RECON toggle

### 3. [x] Enhance AI tab: Add Nuclei/HTTP logs textarea + Generate HackerOne Report button (/api/ai/nuclei-report)

### 4. [x] Fix /api/run frontend integration if needed (test nuclei scan)
### 5. [x] Add /api/deploy to server.py (git add/commit/push) + UI button in Settings
### 6. [x] Update AI prompts for Claude-bug-bounty style (nuclei logs -> report)
### 7. [ ] Add System tab for advanced controls (optional)
### 8. [x] Test: Run buttons, restart, AI recon, deploy
### 9. [ ] Auto git commit/push v2.0

