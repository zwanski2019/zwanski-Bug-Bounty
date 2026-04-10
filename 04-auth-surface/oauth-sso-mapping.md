# Phase 04 — Auth Surface Mapping

> Auth is where most critical findings live. Map it completely before probing it.

---

## 4.1 OAuth / OIDC — Full Attack Surface

### Step 1: Enumerate all OAuth flows

```bash
# Find all /authorize endpoints
# Common patterns:
GET /oauth/authorize
GET /auth/oauth/authorize  
GET /connect/{provider}
GET /login/{provider}
GET /api/v1/oauth/authorize

# Find registered OAuth apps (often disclosed in API docs or JS)
GET /api/oauth/apps
GET /.well-known/openid-configuration     # OIDC discovery endpoint
GET /oauth/.well-known/openid-configuration
GET /auth/realms/{realm}/.well-known/openid-configuration  # Keycloak
```

### Step 2: Map the flow parameters

For every OAuth flow, capture:

| Parameter | Attack Vector |
|---|---|
| `redirect_uri` | Open redirect → token theft |
| `state` | CSRF if absent/weak |
| `response_type` | `token` vs `code` → implicit flow risks |
| `scope` | Scope escalation |
| `client_id` | Rogue client registration |
| `code_challenge_method` | PKCE bypass if absent |

### Step 3: redirect_uri Bypass Techniques

```
# Exact match bypass attempts:
https://target.com/callback              # baseline
https://target.com/callback?x=1         # query param appended
https://target.com/callback/../evil.com  # path traversal
https://target.com.evil.com/callback    # subdomain confusion
https://target.com%2F@evil.com          # URL encoding
https://target.com%0d%0a.evil.com       # CRLF injection
https://target.com\/evil.com            # backslash
https://evil.com%23.target.com          # fragment confusion

# Subdomain-based redirect_uri bypass:
# If wildcard redirect_uri is *.target.com:
# Find an open redirect on any subdomain of target.com
# Chain: open redirect on sub.target.com → token exfiltrated to attacker
```

### Step 4: Rogue Client Registration Chain

**This is the CVSS 9+ class.** If the OAuth server allows dynamic client registration:

```bash
# 1. Check for open dynamic registration
POST /oauth/register
Content-Type: application/json

{
  "client_name": "legit-looking-app",
  "redirect_uris": ["https://attacker.com/callback"],
  "grant_types": ["authorization_code"],
  "response_types": ["code"],
  "scope": "openid profile email"
}
# → Server returns client_id + client_secret
# → You now have a legitimate OAuth client with attacker redirect_uri
# → Craft phishing link targeting real users
# → Their token arrives at your server

# 2. Check if registered clients get overprivileged scopes
# 3. Check if client registration requires auth (often doesn't)
# 4. Check for scope escalation in registration payload
```

### Step 5: Token Analysis

```bash
# Decode JWT without verification
echo "eyJ..." | cut -d. -f2 | base64 -d 2>/dev/null | jq .

# Check claims:
# - "alg": "none" vulnerability
# - Weak secret (crack with hashcat)
# - Missing "aud" (audience) validation
# - Long expiry on access tokens
# - Sensitive data in payload (PII, internal IDs)

# Algorithm confusion (RS256 → HS256)
# If server uses RS256, try signing with public key as HMAC secret
# Public key available at:
GET /.well-known/jwks.json
GET /oauth/jwks
GET /api/auth/keys
```

### Step 6: PKCE Downgrade

```bash
# If PKCE is optional (not enforced):
# Start flow without code_challenge parameter
# If server accepts → PKCE bypass
# Combine with redirect_uri manipulation → auth code interception

# Check if code_verifier validation is actually performed:
# 1. Get auth code legitimately (with PKCE)
# 2. Exchange code but modify code_verifier
# 3. If access token returned → PKCE not validated server-side
```

---

## 4.2 SSO Mapping

### SAML Targets
```
GET /sso/saml/metadata
GET /saml/metadata
GET /api/v1/saml/metadata

# Attack vectors:
# - XML Signature Wrapping (XSW)
# - SAML Response replay (check if timestamp validated)
# - NameID manipulation → impersonate arbitrary users
# - XXE in SAML XML parser
```

### Keycloak-Specific
```bash
# Realm enumeration
GET /auth/realms/{realm}/.well-known/openid-configuration
GET /auth/admin/realms/master    # Master realm admin API — critical if accessible
GET /auth/realms/master/protocol/openid-connect/token

# Common misconfigs:
# Master realm accessible from internet (finding: 150 CHF at Baloise-style targets)
# Direct access grants enabled
# Client credentials with overprivileged scopes
# User registration open on non-public realm
```

---

## 4.3 Session Analysis

### Token Storage & Transmission
- JWT in localStorage → XSS → ATO
- Session cookie missing `HttpOnly` → XSS readable
- Session cookie missing `Secure` → MitM (lower severity but chain-able)
- Session cookie missing `SameSite` → CSRF
- Session fixation → set session ID before auth, check if it persists post-login

### Session Lifecycle Bugs
```
1. Does logout actually invalidate the server-side session?
   → POST /logout, then replay previous session token
   → If requests succeed → server-side session not invalidated

2. Password change → does it invalidate other sessions?
   → Change password on session A, check if session B still works
   → If yes → session persistence after credential change

3. Token refresh chains
   → If refresh token is long-lived (30d+) and not rotated → refresh token theft = persistent ATO
   → Check if refresh tokens can be used multiple times
```

---

## 4.4 MFA Bypass Vectors

```
1. Rate limiting on OTP endpoint
   → Brute force 6-digit TOTP (1,000,000 combinations, but valid window = ~30s)
   → More practical: check if OTP endpoint rate limited independently

2. MFA skip via direct navigation
   → POST /api/login → get partial-auth session
   → Try hitting /api/dashboard directly without completing MFA
   → Check if partial-auth session has hidden access

3. Backup code enumeration
   → If backup codes are short (8 chars), rate limiting absent → brute force

4. Account recovery bypasses MFA
   → Password reset flow → does it require MFA? (often doesn't)
   → If you can trigger password reset without MFA → MFA bypass

5. OAuth login bypasses MFA
   → User has MFA on password login
   → Can they log in via "Login with Google" without triggering MFA?
   → If yes → social login = MFA bypass

6. API endpoint MFA inconsistency
   → Web UI requires MFA
   → Mobile API endpoint for same action does not
   → Test: curl the API endpoint with web session token post-partial-auth
```

---

## 4.5 Auth Checklist

- [ ] All OAuth/OIDC endpoints enumerated
- [ ] `redirect_uri` bypass attempts (10+ techniques)
- [ ] Dynamic client registration check
- [ ] PKCE enforcement check  
- [ ] JWT algorithm confusion (RS256 → HS256)
- [ ] `alg: none` check
- [ ] JWT secret strength check (if HMAC)
- [ ] Session invalidation on logout
- [ ] Session invalidation on password change
- [ ] MFA bypass via OAuth social login
- [ ] MFA bypass via password reset
- [ ] API endpoint MFA consistency check
- [ ] Keycloak master realm (if applicable)
- [ ] SAML XSW (if applicable)
