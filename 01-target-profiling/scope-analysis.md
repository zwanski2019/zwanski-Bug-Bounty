# Phase 01 — Target Profiling

> **Do this before touching a single tool.**  
> Most hunters skip this. It's why they find XSS while you find account takeovers.

---

## 1.1 Business Model Analysis

Before recon, answer these questions manually:

| Question | Why It Matters |
|---|---|
| What is the primary revenue model? (SaaS, marketplace, fintech, e-commerce) | Determines what data is most sensitive and what logic bugs have the highest impact |
| Who are the user tiers? (free, paid, enterprise, admin, internal) | Privilege escalation targets |
| What does the platform integrate with? (Stripe, OAuth providers, Salesforce, Slack) | Integration points = seams = bugs |
| What data is personally identifiable or regulated? (PII, PHI, PCI) | Determines severity multiplier |
| Where is revenue generated? (checkout, subscription renewal, payout, credit system) | Logic bugs here = critical |
| Is there a multi-tenant architecture? | Tenant isolation failures = mass account impact |

**Write this down before proceeding. It changes everything you test.**

---

## 1.2 Scope Analysis

### Read the policy carefully for:
- **Wildcard vs explicit scope** — `*.target.com` vs `app.target.com`
- **Acquisition targets** — recently acquired companies often have different security posture
- **Exclusions with carve-outs** — "3rd party login is OOS" but is the OAuth callback on their own server?
- **Severity/reward thresholds** — some programs don't pay below medium; focus accordingly
- **Disclosure timeline** — affects how you draft reports

### Scope expansion vectors:
```
target.com in scope
  ├── *.target.com (wildcard) → subdomain enum all
  ├── API documentation links → often point to api.target.com (verify in scope)
  ├── Mobile apps → APK/IPA often hit endpoints not on the web surface
  ├── OAuth apps → target's OAuth server may be on auth.target.com
  └── Acquisitions → check Crunchbase, LinkedIn for recent M&A
```

### Acquisition recon:
```bash
# Check for recent acquisitions
# Manual: Crunchbase, LinkedIn company page, press releases
# Their acquired products often have:
#   - Different auth systems
#   - Less hardened infra
#   - The word "legacy" in internal comments you'll find in JS files

# Cross-reference SSL cert SANs for acquisition domains
curl -s "https://crt.sh/?q=%.target.com&output=json" | jq -r '.[].name_value' | sort -u
```

---

## 1.3 Threat Model

Map these **before** you start active recon. This is your attack plan.

### User trust tiers:
```
Unauthenticated
    └─► What can I access/enumerate without an account?
    
Free tier user
    └─► What features/data can I access that I shouldn't?
    └─► Can I escalate to paid features?
    
Paid tier user  
    └─► Can I access other paid users' data? (IDOR, tenant bleed)
    └─► Can I reach admin functionality?
    
Admin / staff
    └─► (If you can reach this tier) What internal tooling is exposed?
```

### Data flow diagram (draw this):
```
User Input → [Validation] → [Processing] → [Storage] → [Output/Display]
                                ↑                           ↑
                         Where does async            Where does stored
                         processing happen?          data resurface?
                         (second-order targets)      (second-order output)
```

### Integration seams:
List every third-party integration you can identify:
- Payment processors → Stripe, Braintree, Adyen
- Auth providers → Auth0, Okta, Cognito, custom OAuth
- Cloud storage → S3, GCS, Azure Blob
- Email → SendGrid, Mailgun, SES
- CDN/WAF → Cloudflare, Akamai, Fastly
- Internal services → Kubernetes ingress, internal APIs, microservices

Each seam is a potential: trust boundary violation, SSRF target, credential leak, or misconfiguration.

---

## 1.4 Competitor Intelligence

Understanding what the target does vs competitors often reveals:
- Features that were "hacked in" quickly (vulnerability-prone)
- Recently launched features (less mature security review)
- Mobile-first functionality (often weaker auth on API layer)

**Tools:**
- [Product Hunt](https://producthunt.com) — launch dates = "new feature = less reviewed"
- [LinkedIn](https://linkedin.com) — find the engineering team, their tech stack posts
- [BuiltWith](https://builtwith.com) — historical tech stack
- [Wayback Machine](https://web.archive.org) — old JS files, old API paths, deprecated endpoints

---

## 1.5 Target Profile Template

Fill this out before Phase 02:

```markdown
## Target: [PROGRAM NAME]
**Platform:** HackerOne / Bugcrowd / BBS / Private
**Scope:** 
**Exclusions:** 
**Max Reward:** 

### Business Model
- Type: SaaS / Fintech / Marketplace / Other
- Revenue: Subscription / Transaction fee / Ads / Other
- Regulated data: PCI / PII / PHI / None

### User Tiers
1. 
2. 
3. 

### Third-Party Integrations
- Auth: 
- Payment: 
- Storage: 
- Other: 

### Stack (initial hypothesis)
- Frontend: 
- Backend: 
- Database: 
- CDN/WAF: 

### High-Value Attack Paths (hypothesis)
1. 
2. 
3. 

### Notes
```
