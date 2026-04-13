#!/bin/bash
# zwanski-subdomain-chain.sh
# Full subdomain recon pipeline for a single target
# Usage: ./zwanski-subdomain-chain.sh target.com [output_dir]
# Requires: subfinder, amass, assetfinder, puredns, httpx, nuclei, anew

TARGET=${1:?"Usage: $0 <domain> [output_dir]"}
OUTDIR=${2:-"./recon_$TARGET"}
RESOLVERS="$HOME/tools/resolvers.txt"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log() { echo -e "${GREEN}[+]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err() { echo -e "${RED}[-]${NC} $1"; }

mkdir -p "$OUTDIR"/{passive,active,live,vulns,js}

log "Starting recon for: $TARGET → $OUTDIR"
log "Timestamp: $TIMESTAMP"

# ─────────────────────────────────────────────
# PHASE 1: Passive subdomain gathering
# ─────────────────────────────────────────────
log "Phase 1: Passive subdomain gathering..."

SUBFINDER_COUNT=$(
  subfinder -d "$TARGET" -all -recursive -silent 2>/dev/null \
    | anew "$OUTDIR/passive/subfinder.txt" | wc -l
)
log "  subfinder: ${SUBFINDER_COUNT// /} subdomains"

ASSETFINDER_COUNT=$(
  assetfinder --subs-only "$TARGET" 2>/dev/null \
    | anew "$OUTDIR/passive/assetfinder.txt" | wc -l
)
log "  assetfinder: ${ASSETFINDER_COUNT// /} subdomains"

# crt.sh
log "  Querying crt.sh..."
curl -s "https://crt.sh/?q=%25.$TARGET&output=json" 2>/dev/null \
  | jq -r '.[].name_value' 2>/dev/null \
  | sed 's/\*\.//g' | tr '[:upper:]' '[:lower:]' | sort -u \
  | anew "$OUTDIR/passive/crtsh.txt" | wc -l > "$OUTDIR/passive/.crtsh_count"
CRTSH_COUNT=$(tr -d '[:space:]' < "$OUTDIR/passive/.crtsh_count")
rm -f "$OUTDIR/passive/.crtsh_count"
log "  crt.sh: ${CRTSH_COUNT:-0} subdomains"

# Combine all passive
cat "$OUTDIR/passive/"*.txt | sort -u > "$OUTDIR/passive/combined_passive.txt"
PASSIVE_COUNT=$(wc -l < "$OUTDIR/passive/combined_passive.txt")
log "  Total passive: $PASSIVE_COUNT unique subdomains"

# ─────────────────────────────────────────────
# PHASE 2: DNS resolution + wildcard detection
# ─────────────────────────────────────────────
log "Phase 2: DNS resolution..."

if [[ -f "$RESOLVERS" ]]; then
  puredns resolve "$OUTDIR/passive/combined_passive.txt" \
    -r "$RESOLVERS" --wildcard-tests 20 -q \
    -w "$OUTDIR/active/resolved.txt" 2>/dev/null
else
  warn "No resolvers.txt found at $RESOLVERS — using system DNS"
  cat "$OUTDIR/passive/combined_passive.txt" | dnsx -silent \
    -o "$OUTDIR/active/resolved.txt" 2>/dev/null
fi

RESOLVED_COUNT=$(wc -l < "$OUTDIR/active/resolved.txt")
log "  Resolved: $RESOLVED_COUNT live DNS entries"

# ─────────────────────────────────────────────
# PHASE 3: HTTP probing
# ─────────────────────────────────────────────
log "Phase 3: HTTP probing..."

httpx -l "$OUTDIR/active/resolved.txt" \
  -title -status-code -tech-detect \
  -follow-redirects -threads 50 -silent \
  -o "$OUTDIR/live/live_hosts.txt" 2>/dev/null

LIVE_COUNT=$(wc -l < "$OUTDIR/live/live_hosts.txt")
log "  Live hosts: $LIVE_COUNT"

# Extract just the URLs for further testing
grep -oP 'https?://[^ ]+' "$OUTDIR/live/live_hosts.txt" | sort -u \
  > "$OUTDIR/live/urls.txt"

# ─────────────────────────────────────────────
# PHASE 4: Technology-specific checks
# ─────────────────────────────────────────────
log "Phase 4: Technology-specific probes..."

# Spring Boot Actuator
log "  Checking for Spring Boot Actuator exposure..."
while IFS= read -r url; do
  ACTUATOR=$(curl -sk -o /dev/null -w "%{http_code}" "$url/actuator" 2>/dev/null)
  if [[ "$ACTUATOR" == "200" ]]; then
    warn "  ACTUATOR EXPOSED: $url/actuator"
    echo "$url/actuator" >> "$OUTDIR/vulns/actuator_exposed.txt"
  fi
done < "$OUTDIR/live/urls.txt"

# Elasticsearch open
log "  Checking for exposed Elasticsearch..."
while IFS= read -r host; do
  ES=$(curl -sk -o /dev/null -w "%{http_code}" "http://$host:9200/_cat/indices" 2>/dev/null)
  if [[ "$ES" == "200" ]]; then
    warn "  ELASTICSEARCH OPEN: http://$host:9200"
    echo "http://$host:9200" >> "$OUTDIR/vulns/elasticsearch_open.txt"
  fi
done < "$OUTDIR/active/resolved.txt"

# Git directory exposure
log "  Checking for .git directory exposure..."
while IFS= read -r url; do
  GIT=$(curl -sk -o /dev/null -w "%{http_code}" "$url/.git/HEAD" 2>/dev/null)
  if [[ "$GIT" == "200" ]]; then
    warn "  GIT EXPOSED: $url/.git/"
    echo "$url/.git/" >> "$OUTDIR/vulns/git_exposed.txt"
  fi
done < "$OUTDIR/live/urls.txt"

# ─────────────────────────────────────────────
# PHASE 5: Nuclei — fast vulnerability scan
# ─────────────────────────────────────────────
log "Phase 5: Running nuclei (critical/high only)..."

nuclei -l "$OUTDIR/live/urls.txt" \
  -severity critical,high \
  -t ~/nuclei-templates/ \
  -exclude-tags intrusive \
  -rate-limit 50 \
  -o "$OUTDIR/vulns/nuclei_critica_high.txt" \
  -silent 2>/dev/null

NUCLEI_FINDINGS=$(wc -l < "$OUTDIR/vulns/nuclei_critica_high.txt" 2>/dev/null || echo 0)
log "  Nuclei findings (critical/high): $NUCLEI_FINDINGS"

# ─────────────────────────────────────────────
# PHASE 6: JS endpoint extraction
# ─────────────────────────────────────────────
log "Phase 6: JS endpoint extraction..."

# Get all JS URLs from live hosts
httpx -l "$OUTDIR/live/urls.txt" -links -silent 2>/dev/null \
  | grep "\.js$" | sort -u > "$OUTDIR/js/js_files.txt"

JS_COUNT=$(wc -l < "$OUTDIR/js/js_files.txt")
log "  Found $JS_COUNT JS files"

# Extract endpoints from JS (using grep heuristic — install linkfinder for better results)
while IFS= read -r jsurl; do
  curl -sk "$jsurl" 2>/dev/null \
    | grep -oP '["'"'"'](/[a-zA-Z0-9/_\-\.]+)["'"'"']' \
    | tr -d '"'"'" \
    | sort -u
done < "$OUTDIR/js/js_files.txt" | sort -u > "$OUTDIR/js/extracted_endpoints.txt"

ENDPOINT_COUNT=$(wc -l < "$OUTDIR/js/extracted_endpoints.txt")
log "  Extracted $ENDPOINT_COUNT unique endpoints from JS"

# ─────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  RECON COMPLETE: $TARGET"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Passive subdomains : $PASSIVE_COUNT"
echo "  Resolved           : $RESOLVED_COUNT"
echo "  Live HTTP hosts    : $LIVE_COUNT"
echo "  Nuclei findings    : $NUCLEI_FINDINGS"
echo "  JS endpoints       : $ENDPOINT_COUNT"
echo ""
echo "  Output directory   : $OUTDIR"

if [[ -s "$OUTDIR/vulns/actuator_exposed.txt" ]]; then
  warn "  ⚠  Spring Boot Actuator exposed — CHECK FIRST"
fi
if [[ -s "$OUTDIR/vulns/elasticsearch_open.txt" ]]; then
  warn "  ⚠  Elasticsearch open — CHECK FIRST"
fi
if [[ -s "$OUTDIR/vulns/git_exposed.txt" ]]; then
  warn "  ⚠  .git directory exposed — CHECK FIRST"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
