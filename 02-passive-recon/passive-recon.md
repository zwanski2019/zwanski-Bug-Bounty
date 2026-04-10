# Phase 02 — Passive Recon

> No packets to the target. Everything here is pre-attack intelligence.

---

## 2.1 GitHub Dorking

The most underutilized passive recon vector. Companies leak credentials, internal endpoints, and architecture details on GitHub constantly.

### Search Operators

```
# Core searches — run for target domain AND company name
org:target-company
"target.com" in:file

# Credentials
org:target-company "api_key"
org:target-company "secret_key"
org:target-company "password" filename:.env
org:target-company "BEGIN RSA PRIVATE KEY"
org:target-company "AKIA" # AWS access key prefix

# Internal endpoints
org:target-company "internal.target.com"
org:target-company "staging" "api"
org:target-company "localhost:8080"
org:target-company "jdbc:" 
org:target-company "mongodb://"
org:target-company "postgres://"

# Slack/Discord webhooks
org:target-company "hooks.slack.com"
org:target-company "discord.com/api/webhooks"

# JWT secrets
org:target-company "jwt_secret"
org:target-company "JWT_SECRET"
org:target-company "signing_key"

# Cloud storage
org:target-company "s3.amazonaws.com"
org:target-company "storage.googleapis.com"
org:target-company "blob.core.windows.net"

# GitHub Actions secrets (people print them by accident)
filename:.github/workflows "secrets."
org:target-company "env:" filename:.yml
```

### Tools
```bash
# GitDorker
python3 gitdorker.py -tf ~/dorks/bhd.txt -q target.com -p token

# truffleHog — scan entire org
trufflehog github --org=target-company --token=$GITHUB_TOKEN

# gitleaks — scan specific repos
gitleaks detect --source=/path/to/cloned/repo -v

# gh-dork (faster manual dorking)
gh search code "target.com api_key" --limit 100
```

### What to do with leaked endpoints:
- Probe them **passively** first (don't auth with leaked creds — just enumerate)
- Check if the endpoint is in scope
- Note staging/dev/UAT endpoints for Phase 06

---

## 2.2 Historical Analysis

### Wayback Machine
```bash
# Get all archived URLs for a domain
curl "http://web.archive.org/cdx/search/cdx?url=*.target.com/*&output=text&fl=original&collapse=urlkey" \
  | grep -E "\.(js|json|config|env|xml|yaml|yml)$" \
  | sort -u

# Look for:
# - Old API endpoints (v1, v2, legacy, deprecated)
# - Old JS files with hardcoded endpoints or keys  
# - Admin panels that may have been "removed" from nav but still exist
# - Config files accidentally committed to web root
```

### crt.sh — Certificate Transparency
```bash
# All subdomains ever issued a cert
curl -s "https://crt.sh/?q=%.target.com&output=json" \
  | jq -r '.[].name_value' \
  | sed 's/\*\.//g' \
  | sort -u > crt_subdomains.txt

# Look for patterns:
# staging*, dev*, uat*, internal*, admin*, api*, corp*, vpn*
# Acquisitions: differentproduct.target.com
# Employee portals: hr.target.com, sso.target.com
```

### Common Crawl / AlienVault OTX
```bash
# OTX passive DNS
curl -s "https://otx.alienvault.com/api/v1/indicators/domain/target.com/passive_dns" \
  | jq -r '.passive_dns[].hostname' | sort -u

# URLScan.io
curl -s "https://urlscan.io/api/v1/search/?q=domain:target.com&size=100" \
  | jq -r '.results[].page.url' | sort -u
```

---

## 2.3 Supply Chain Recon

**Massively underused.** Target's packages, CI/CD pipelines, and build systems are attack surface.

### npm/PyPI Package Discovery
```bash
# Find packages published by the company
# Check package.json in GitHub repos for internal package names
# Look for:
#   "@target-company/some-internal-lib" — private registry leak?
#   Version pinning inconsistencies — dependency confusion possible?

# Check if internal package names exist on public registries
npm view @target-company/internal-lib 2>/dev/null && echo "PACKAGE EXISTS ON PUBLIC npm"
pip index versions target-internal-package 2>/dev/null

# Dependency confusion targets: packages with no public version
# If "@target/auth-utils" doesn't exist on npmjs.com → plant it → RCE on their build
```

### Docker Hub
```bash
# Check if they publish Docker images
# Images often contain: hardcoded endpoints, debug flags, env var templates
hub.docker.com/r/targetcompany/
```

### GitHub Actions / CI Secrets Exposure
```bash
# Look in .github/workflows/*.yml files for:
# - Secrets passed as env vars (sometimes printed in logs)
# - Misconfigured OIDC/cloud auth
# - Third-party actions with write access (supply chain)

# Example dangerous pattern in workflows:
# run: echo ${{ secrets.API_KEY }}  ← will print in logs if misused
# uses: some-third-party/action@main ← unpinned = supply chain risk
```

---

## 2.4 OSINT — People & Infrastructure

### LinkedIn Intelligence
- Search engineering team members → their public posts often reveal stack ("deployed our new Kafka pipeline")
- Job postings → "Experience with Vault, Consul, Kubernetes" = their stack
- Recent hires in security → post-breach hardening signal

### Shodan / Censys (passive, no scanning)
```bash
# Shodan
shodan search "ssl:target.com" --fields ip_str,port,org,hostnames
shodan search 'org:"Target Company" http.title:"admin"'
shodan search 'org:"Target Company" "MongoDB"'

# Censys
censys search 'parsed.names: target.com' --index certificates
censys search 'autonomous_system.name: "Target Company"' --index hosts
```

### ASN Enumeration
```bash
# Find all IP ranges owned by target
# → often reveals infrastructure not covered by subdomain enum
curl -s "https://api.bgpview.io/search?query_term=target+company" | jq .

# Get all prefixes for an ASN
curl -s "https://api.bgpview.io/asn/AS12345/prefixes" | jq -r '.data.ipv4_prefixes[].prefix'
```

---

## 2.5 JS File Analysis (Pre-Active Phase)

If you can access public JS files without auth (marketing site, etc.), do this before active recon:

```bash
# Extract endpoints from JS
# Install: npm i -g js-beautify
curl -s https://target.com/static/app.js | js-beautify | grep -oE '"(/[a-zA-Z0-9/_-]+)"' | sort -u

# LinkFinder
python3 linkfinder.py -i https://target.com -d -o results.html

# secretfinder
python3 SecretFinder.py -i https://target.com/static/app.js -o cli

# Look for:
# /api/v1/admin/* endpoints
# /internal/* endpoints
# GraphQL endpoints (/graphql, /api/graphql, /v1/graphql)
# WebSocket endpoints (wss://)
# Hardcoded API keys (Google Maps, Mapbox, etc. → often over-privileged)
```

---

## 2.6 Passive Recon Checklist

- [ ] GitHub dorking — org name + domain
- [ ] truffleHog / gitleaks on public repos
- [ ] crt.sh subdomain harvest
- [ ] Wayback Machine URL dump → filter for interesting paths
- [ ] OTX / urlscan passive DNS
- [ ] Shodan/Censys ASN lookup
- [ ] npm/PyPI package name check for dependency confusion
- [ ] LinkedIn job postings → stack inference
- [ ] Docker Hub image check
- [ ] Public JS analysis (if accessible without auth)
