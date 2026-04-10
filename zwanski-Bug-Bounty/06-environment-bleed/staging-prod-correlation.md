# Phase 06 — Environment Bleed

> The most consistently skipped phase. Staging environments have the same bugs as prod, less hardening, and different (often no) WAF rules.

---

## 6.1 Staging / UAT / Dev Discovery

### Subdomain Patterns (from crt.sh + wordlist)

```
# High-value environment prefixes to hunt:
staging, stage, stg
uat, uat1, uat2
dev, dev1, dev2, development
test, testing
qa, qa1
demo
sandbox
preview
preprod, pre-prod, pre
beta
canary
release, rc
internal
corp
```

```bash
# Generate and probe
for prefix in staging stage stg uat dev test qa demo sandbox preprod; do
  echo "$prefix.target.com"
  echo "$prefix-api.target.com"
  echo "api-$prefix.target.com"
done | httpx -silent -status-code -title -tech-detect
```

### What to Look For in Staging

1. **Debug endpoints enabled:**
   ```
   /actuator (Spring Boot → full internals exposed)
   /actuator/env → env vars including secrets
   /actuator/heapdump → JVM heap dump → extract secrets
   /_ah/admin (Google App Engine dev)
   /debug
   /.env (if webroot is misconfigured)
   /phpinfo.php
   /server-info
   /server-status (Apache)
   ```

2. **Relaxed auth:**
   - Hardcoded test credentials (`admin/admin`, `test/test123`)
   - Auth bypass via `X-Debug: true` or `X-Environment: staging` headers
   - Test users with elevated privileges that don't exist in prod

3. **Different (weaker) WAF rules:**
   - SQLi, XSS payloads that are blocked in prod may pass in staging
   - Rate limiting often absent or much higher

4. **Source code / internal tooling exposure:**
   - Git repo accessible (`.git/` directory exposed in web root)
   - Swagger/OpenAPI docs enabled (`/swagger-ui`, `/api-docs`, `/openapi.json`)
   - GraphQL introspection enabled
   - Admin panels accessible without production-level auth

---

## 6.2 Prod vs Staging Code Divergence

### The Key Insight

Staging environments often run:
- Older code (the feature branch that prod is on was never merged to staging)
- Debug flags compiled in
- Internal testing endpoints that were never meant to reach prod (but sometimes do anyway)
- Less restrictive CORS policies

### Attack: Find staging → Compare behavior → Apply to prod

```
1. Find staging.target.com
2. Map all endpoints on staging (use Burp spider / active scan)
3. For each endpoint on staging, check if it exists on prod:
   - /api/v1/debug/users → if this is on staging and NOT blocked on prod → found it
   - /api/v1/admin/impersonate → common in staging, sometimes forgotten on prod
   
4. Check HTTP response headers for version differences:
   X-App-Version: 1.2.3-staging  vs  X-App-Version: 1.4.1
   → Older version on staging = older vuln classes
```

---

## 6.3 CI/CD Exposure

### GitHub Actions Attack Vectors

```yaml
# Dangerous pattern 1: pull_request_target with checkout + run
on:
  pull_request_target:
    types: [opened]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          ref: ${{ github.event.pull_request.head.sha }}  # ← checks out attacker code
      - run: npm test  # ← runs attacker's package.json scripts

# If you're an external contributor → open PR → your code runs in privileged context
# → secrets: ${{ secrets.PROD_AWS_KEY }} is available in that context
```

```bash
# Find exposed CI/CD systems
# Jenkins: /jenkins, /jenkins/login, /job/
# CircleCI: app.circleci.com/pipelines/gh/target-org
# Travis CI: travis-ci.com/github/target-org
# GitHub Actions: github.com/target-org/repo/actions → check for public run logs
#   → Logs sometimes contain env var dumps ("echo $SECRET" accidentally)

# Check for Jenkins without auth:
curl -s https://ci.target.com/api/json?pretty=true
```

### Kubernetes / Container Exposure

```bash
# Check for exposed K8s API
curl -k https://target.com:6443/api/v1/namespaces
curl -k https://target.com:8443/api/v1/pods

# Exposed metadata service via SSRF
http://169.254.169.254/latest/meta-data/                    # AWS EC2
http://169.254.169.254/computeMetadata/v1/?recursive=true   # GCP (needs header)
http://169.254.169.254/metadata/instance?api-version=2021-02-01  # Azure

# K8s service account token (if SSRF to pod)
http://169.254.169.254/latest/meta-data/iam/security-credentials/
```

---

## 6.4 Subdomain Takeover

Quick reference for the automated part:

```bash
# nuclei for subdomain takeover
nuclei -l subdomains.txt -t ~/nuclei-templates/takeovers/ -o takeovers.txt

# Manual check: if subdomain resolves to CNAME that doesn't exist in target service
# Common services vulnerable: GitHub Pages, Heroku, Fastly, Azure, AWS S3, Netlify

# For S3:
# bucket-name.s3.amazonaws.com → if bucket doesn't exist → register it

# Verification before claiming:
dig sub.target.com CNAME  # Get the CNAME target
# Check if CNAME target resolves → if NXDOMAIN → claimable
```

---

## 6.5 Environment Bleed Checklist

- [ ] Subdomain brute-force for staging/dev/uat patterns
- [ ] Spring Boot Actuator endpoints on any discovered host
- [ ] `.git/` directory exposure check on web roots
- [ ] Swagger/OpenAPI/GraphQL introspection on non-prod hosts
- [ ] Default/test credentials on staging login pages
- [ ] CI/CD system exposure (Jenkins, CircleCI)
- [ ] GitHub Actions log review for secret exposure
- [ ] K8s API / cloud metadata exposure
- [ ] CORS policy comparison prod vs staging
- [ ] WAF behavior comparison prod vs staging
- [ ] Subdomain takeover check on all discovered subdomains
