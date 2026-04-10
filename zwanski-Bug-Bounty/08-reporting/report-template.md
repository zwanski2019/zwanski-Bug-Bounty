# Phase 08 — Reporting

---

## 8.1 Report Template

```markdown
## [VULN CLASS]: [One-line description]

**Severity:** Critical / High / Medium / Low  
**CVSS Score:** X.X (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:N)  
**CWE:** CWE-XXX  
**Affected Endpoint:** `POST /api/v1/endpoint`

---

### Summary

[2-3 sentences. What is the vulnerability, where is it, and what's the real-world impact.
Lead with the impact, not the technical detail.]

Example:
"An attacker can register a malicious OAuth client without authentication via the dynamic
client registration endpoint, then use the resulting client_id to craft phishing URLs that
harvest legitimate user authorization codes. Successful exploitation grants persistent access
to any user account that clicks the crafted link."

---

### Technical Details

[Full technical explanation. Include:]
- Root cause
- Why the validation fails
- What the server trusts incorrectly

---

### Steps to Reproduce

1. Navigate to `https://target.com/oauth/register`
2. Send the following request:

\`\`\`http
POST /oauth/register HTTP/1.1
Host: target.com
Content-Type: application/json

{
  "client_name": "Legitimate App",
  "redirect_uris": ["https://attacker.com/callback"],
  "grant_types": ["authorization_code"]
}
\`\`\`

3. Note the returned `client_id`: `abc123`
4. Craft authorization URL:
   `https://target.com/oauth/authorize?client_id=abc123&response_type=code&redirect_uri=https://attacker.com/callback`
5. When victim navigates to this URL and authorizes, the authorization code is delivered to attacker's server
6. Exchange code for access token: [show the exchange request]

**Observed result:** Access token issued for victim account  
**Expected result:** Request should fail — attacker-controlled redirect_uri should not be permitted

---

### Proof of Concept

[Screenshot or request/response pair showing the vulnerability]
[Redact any real user data — use test accounts]

---

### Impact

[Business impact. What can an attacker actually do? Who is affected?]

Example:
"Any user of the platform can be targeted. The attacker needs only to send the crafted URL
via any channel (email, social media, forum post). No user interaction beyond clicking the
link and authorizing the application (which appears legitimate due to the target's own OAuth
consent screen) is required. All API scopes available to the user (profile, email, data access)
are accessible to the attacker for the lifetime of the access token."

---

### Remediation

[Specific, actionable. Not just "fix the vulnerability".]

1. **Require authentication** for the `/oauth/register` endpoint, or disable dynamic registration if not required
2. **Whitelist allowed redirect_uri patterns** rather than accepting arbitrary URLs
3. **Implement client verification** before issuing client credentials

---

### References

- RFC 7591 — OAuth 2.0 Dynamic Client Registration Protocol (Section 2)
- [OWASP OAuth Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/OAuth2_Cheat_Sheet.html)
- [PortSwigger: OAuth authentication vulnerabilities](https://portswigger.net/web-security/oauth)
```

---

## 8.2 Chain Documentation

When multiple issues combine into one finding, document the chain:

```markdown
### Attack Chain

\`\`\`
Step 1: Discover open dynamic client registration
        POST /oauth/register → returns client_id (no auth required)
        
        ↓
        
Step 2: Register client with attacker redirect_uri
        client_id: abc123
        redirect_uri: https://attacker.com/capture
        
        ↓
        
Step 3: Craft victim-targeted authorization URL
        /oauth/authorize?client_id=abc123&scope=read:all
        
        ↓
        
Step 4: Victim clicks → authorizes (consent screen shows target's branding)
        
        ↓
        
Step 5: Authorization code delivered to attacker server
        
        ↓
        
Step 6: Exchange code → access token
        Full account access with scope=read:all
\`\`\`

**Individual issues:**
- Open dynamic client registration: Medium (no auth required, but no direct impact alone)
- No redirect_uri whitelist: Medium
- Combined: Critical (CVSS 9.6 — full account takeover without victim credentials)
```

---

## 8.3 CVSS Guidance

Common mistakes in CVSS scoring:

| Metric | Common Error | Correct Thinking |
|---|---|---|
| Attack Vector | Set to Network when it should be | AV:N = exploitable remotely without LAN access |
| Privileges Required | PR:N when some account is needed | Free-tier account = PR:L (low), Admin = PR:H |
| User Interaction | UI:N when victim must click something | Clicking a URL = UI:R |
| Scope | Always set S:U | S:C when impact crosses privilege boundaries (e.g., attacker's client → victim's account) |
| Impact | Overestimate all three to C:H/I:H/A:H | Be honest — the program will push back if overscored |

---

## 8.4 Severity Framing for Maximum Impact

### Low-impact finding → frame as business risk:
```
Bad:  "CORS misconfiguration allows any origin"
Good: "The CORS policy on /api/v1/user allows any authenticated origin to make 
       credentialed cross-origin requests. An attacker controlling any subdomain 
       (including one they take over) can exfiltrate the authenticated user's 
       complete profile and API tokens."
```

### Chained finding → quantify the chain:
```
Bad:  "Open redirect + OAuth code leakage"
Good: "Chaining the open redirect on /redirect (Medium, unpatched since 2023) 
       with the OAuth redirect_uri wildcard match allows authorization code theft 
       without any JavaScript execution. Full account takeover is achievable in 
       under 60 seconds with a single click from the victim."
```

### Disputed finding → pre-empt the pushback:
```
Add a section: "Why this is not a duplicate / why this is in scope"
Cite: program policy exact text, similar accepted findings on Hacktivity,
      the specific behavior difference from the disputed finding
```
