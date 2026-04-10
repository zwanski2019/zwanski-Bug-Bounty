# Phase 03 — Active Recon

---

## 3.1 Subdomain Enumeration — Full Chain

Run these in parallel. Each source catches different subdomains.

```bash
TARGET="target.com"

# 1. Passive sources (no DNS queries to target)
subfinder -d $TARGET -all -recursive -o subfinder.txt
amass enum -passive -d $TARGET -o amass_passive.txt
assetfinder --subs-only $TARGET > assetfinder.txt

# 2. Active bruteforce
puredns bruteforce ~/wordlists/subdomains-top1m.txt $TARGET \
  -r ~/resolvers.txt --wildcard-tests 20 -o puredns.txt

# 3. Permutation engine (catches: api2, staging-api, app-v2)
dnsx -l combined_subs.txt -resp -o resolved.txt
gotator -sub combined_subs.txt -perm ~/wordlists/permutations.txt \
  -depth 1 -numbers 3 -md | puredns resolve -r ~/resolvers.txt

# 4. Combine and resolve
cat subfinder.txt amass_passive.txt assetfinder.txt puredns.txt | sort -u > all_subs.txt
puredns resolve all_subs.txt -r ~/resolvers.txt -o resolved_subs.txt

# 5. Probe live hosts
httpx -l resolved_subs.txt -title -status-code -tech-detect \
  -follow-redirects -o live_hosts.txt
```

### Wordlist Strategy

Don't use rockyou.txt for subdomains. Use:
- [assetnote wordlists](https://wordlists.assetnote.io/) — best for API paths and subdomains
- `best-dns-wordlist.txt` from SecLists
- Custom: generate from JS files, API docs, job postings

---

## 3.2 Port Scanning — Targeted

```bash
# Fast scan of all discovered IPs
# First: resolve subdomains to IPs
cat resolved_subs.txt | dnsx -a -resp-only | sort -u > ips.txt

# Scan interesting ports (not all 65535 — be targeted)
naabu -l ips.txt -p 80,443,8080,8443,8888,3000,4000,5000,9000,9090,9200,9300,27017,5432,3306,6379,11211 \
  -rate 1000 -o naabu_results.txt

# Interesting port hits → immediately investigate:
# 9200/9300 → Elasticsearch (unauthenticated? → critical)
# 27017 → MongoDB (unauthenticated? → critical)
# 6379 → Redis (unauthenticated? → RCE via RESP protocol)
# 5432/3306 → Database directly exposed (almost always critical)
# 9090 → Prometheus metrics (internal metrics leak)
# 4040 → Spark Web UI
# 8500 → Consul (service mesh admin)
```

---

## 3.3 Technology Fingerprinting

```bash
# Run on all live hosts
whatweb -i live_hosts.txt --log-json=whatweb.json

# Wappalyzer via CLI
# nuclei tech detection
nuclei -l live_hosts.txt -t ~/nuclei-templates/technologies/ -o tech_detect.txt

# Headers analysis (reveals a lot)
httpx -l live_hosts.txt -include-response-header -o headers.txt
grep -i "x-powered-by\|server:\|x-generator\|x-runtime" headers.txt
```

### Stack-Specific Recon Triggers

| Detected Technology | Immediate Follow-up |
|---|---|
| Spring Boot | Check `/actuator` endpoints |
| Kubernetes | Check for exposed API server, metadata |
| WordPress | `wpscan`, xmlrpc.php, `/wp-json/wp/v2/users` |
| Drupal | `droopescan`, `/?q=admin` |
| Jira | Unauthenticated issue enumeration, SSRF via webhooks |
| Confluence | CVE-2022-26134 (OGNL injection), space enumeration |
| GitLab | Check CE vs EE, public repos, API enumeration |
| Grafana | Default credentials, anonymous access to dashboards |
| Kibana | `/.kibana`, unauthenticated search endpoints |
| Elasticsearch | GET `/` → version, GET `/_cat/indices` → data |
| Keycloak | Master realm admin API |

---

## 3.4 API Discovery

### Endpoint Sources

```bash
# 1. JS file extraction
gospider -s https://target.com -d 3 -c 10 -t 20 -q \
  --blacklist ".(png|jpg|gif|css|woff)" | grep -oE "https?://[^\"' ]+" > urls.txt

# Run linkfinder on every JS file
for js in $(cat urls.txt | grep "\.js$"); do
  python3 linkfinder.py -i $js -o cli 2>/dev/null
done | sort -u > js_endpoints.txt

# 2. API-specific brute force (assetnote wordlists are the best)
ffuf -w ~/wordlists/api_endpoints_assetnote.txt \
  -u https://api.target.com/FUZZ \
  -mc 200,201,204,301,302,400,401,403 \
  -t 50 -o api_fuzz.json

# 3. Common API paths always worth checking
/api/v1/ /api/v2/ /api/v3/
/v1/ /v2/
/rest/
/graphql /api/graphql /v1/graphql
/swagger-ui /swagger-ui.html /api-docs /openapi.json /openapi.yaml
/.well-known/
/internal/
```

### GraphQL Discovery & Introspection

```bash
# Find GraphQL
ffuf -w ~/wordlists/graphql_paths.txt -u https://target.com/FUZZ \
  -mc 200 -t 20

# Run introspection
curl -X POST https://target.com/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"{__schema{types{name fields{name}}}}"}'

# If introspection disabled, try field suggestion bypass
curl -X POST https://target.com/graphql \
  -d '{"query":"{ user { id, __typename } }"}'
# Error messages often reveal valid field names

# Tools
# graphw00f — fingerprint GraphQL engine
# clairvoyance — brute-force field names when introspection disabled
# InQL (Burp extension)
```

### WebSocket Discovery

```bash
# Find WebSocket endpoints in JS files
grep -r "WebSocket\|wss://\|ws://" js_endpoints.txt

# Test with websocat
websocat wss://target.com/ws

# Look for:
# - Missing auth on WebSocket upgrade (token checked on HTTP req but not WebSocket messages)
# - No origin validation → CSWSH (Cross-Site WebSocket Hijacking)
# - Injection in WebSocket message fields (JSON parameter pollution, SQLI)
# - Subscription abuse (subscribe to other users' events by changing user_id)
```

---

## 3.5 Content Discovery

```bash
# Targeted content discovery (after tech fingerprinting)
feroxbuster -u https://target.com \
  -w ~/wordlists/raft-large-directories.txt \
  -x php,asp,aspx,jsp,json,yaml,yml,bak,sql,old \
  -t 50 --smart-scan -o feroxbuster.txt

# Backup file discovery
ffuf -w ~/wordlists/backup_ext.txt \
  -u https://target.com/FUZZ \
  -mc 200 -t 30

# Common backup patterns:
# index.php.bak, config.php~, .config.php.swp
# database.sql, backup.tar.gz, dump.sql
```
