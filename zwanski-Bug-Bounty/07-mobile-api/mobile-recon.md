# Phase 07 — Mobile / API Correlation

> Mobile apps share backends with web apps but often have different (weaker) auth enforcement. The mobile API surface is frequently wider, less documented, and less tested.

---

## 7.1 APK Recon

### Static Analysis

```bash
# Decompile APK
apktool d target.apk -o decompiled_app/

# Decompile to Java (readable)
jadx -d jadx_output/ target.apk

# Search for endpoints
grep -rE "https?://[a-zA-Z0-9._/-]+" jadx_output/ --include="*.java" | grep -v "//.*https" \
  | grep -oE "https?://[a-zA-Z0-9._/-]+" | sort -u > mobile_endpoints.txt

# Search for hardcoded secrets
grep -rE "(api_key|apikey|secret|password|token|bearer|Authorization)['\"]?\s*[:=]\s*['\"][^'\"]{8,}" \
  jadx_output/ --include="*.java" -i | head -50

grep -rE "AKIA[0-9A-Z]{16}" jadx_output/   # AWS access keys
grep -rE "eyJ[a-zA-Z0-9_-]+\." jadx_output/ # JWT tokens hardcoded

# Find API base URLs and version patterns
grep -rE '"(https?://[^"]+)"' jadx_output/ --include="*.java" \
  | grep -E "api\.|/v[0-9]+/" | sort -u

# Find all network config
cat decompiled_app/res/xml/network_security_config.xml 2>/dev/null
```

### Certificate Pinning Bypass

```bash
# Frida-based bypass (most common)
frida-ps -Ua  # list running apps
frida -U -l ssl-pinning-bypass.js -f com.target.app

# Objection (easier)
objection -g com.target.app explore
# Then inside objection shell:
android sslpinning disable

# If Frida is detected:
# Use Magisk + LSposed + TrustMeAlready or custom Frida gadget
```

### Dynamic Analysis Setup

```bash
# 1. Set up Burp proxy on your machine (192.168.1.100:8080)
# 2. Configure Android emulator/device to use this proxy
# 3. Install Burp CA cert as system CA (requires root or Magisk)

# Emulator quick setup:
emulator -avd Pixel_4_API_30 -writable-system -no-snapshot
adb root
adb remount
adb push burp_ca.der /system/etc/security/cacerts/9a5ba575.0
adb shell chmod 644 /system/etc/security/cacerts/9a5ba575.0
```

---

## 7.2 API Correlation — Web vs Mobile

This is where the gold is. The mobile app often calls API endpoints that:
- Don't have rate limiting (mobile apps don't need to brute-force, right?)
- Have weaker auth (the app includes a static API key or device token)
- Expose more data in responses (mobile app needs more fields)
- Skip MFA/2FA requirements
- Allow older deprecated functionality

### Cross-Reference Methodology

```
1. Run Burp while using the mobile app exhaustively
   - Sign up, sign in, all features
   - Every flow → capture all API calls

2. Compare with web API surface:
   - Endpoints in mobile NOT in web → priority test targets
   - Different response fields in mobile vs web → data exposure
   - Different auth requirements → bypass vector
   - Different rate limits → enumeration vector

3. Specific tests:
   - Remove or downgrade auth token on mobile endpoints
   - Try web session tokens on mobile endpoints
   - Try mobile auth tokens on web admin endpoints
   - Send mobile request with a web-crafted body (field additions)
```

### Common Mobile-Specific Findings

```
1. Device token as authentication
   - Mobile sends: X-Device-Token: abc123
   - Token is static or weakly generated
   - Can be extracted from APK, reused for mass requests

2. Mobile API v1 still alive
   - /api/v1/ (old) vs /api/v2/ (current)
   - v1 has no auth for some endpoints
   - Found by comparing JS endpoints vs APK endpoints

3. Over-exposed response fields
   - Web: {"user": {"id": 1, "name": "Mohamed"}}
   - Mobile: {"user": {"id": 1, "name": "Mohamed", "internal_id": "usr_abc123", 
                "admin": false, "plan_id": 5, "payment_token": "..."}}
   - Set admin: true in request body → if honored → privilege escalation

4. Firebase misconfiguration
   - Mobile apps often use Firebase directly
   - Check: target.firebaseio.com/.json (read without auth)
   - Check: Firebase Auth rules (often set to allow all reads in dev, never changed)
   - Extract Firebase config from APK: google-services.json
```

---

## 7.3 Firebase-Specific Recon

```bash
# Extract Firebase project config from APK
grep -r "firebase" jadx_output/ --include="*.java" -i | grep -E "project|apiKey|authDomain"
cat decompiled_app/google-services.json 2>/dev/null

# Test unauthenticated access
FIREBASE_PROJECT="target-app-default"
curl "https://$FIREBASE_PROJECT.firebaseio.com/.json"
curl "https://$FIREBASE_PROJECT.firebaseio.com/users.json"

# If data returned → critical (unauthenticated database read)

# Firebase Storage
curl "https://firebasestorage.googleapis.com/v0/b/$FIREBASE_PROJECT.appspot.com/o"

# Firestore rules test (requires firebase-tools or manual REST API)
# Look for: allow read: if true; (no auth required)
```

---

## 7.4 IPA (iOS) Recon

```bash
# Install ipa
# Decrypt if needed (device dump with frida-ios-dump or ipainstaller)

# Extract and analyze
unzip target.ipa -d ipa_extracted/
strings ipa_extracted/Payload/*.app/target | grep -E "https?://"

# Class-dump for method names (reveals endpoint patterns)
class-dump -H ipa_extracted/Payload/*.app/target -o classdump/

# Search for secrets
grep -rE "(api_key|secret|token|password)" ipa_extracted/ -i

# Info.plist — often has API endpoints and config
plutil -p ipa_extracted/Payload/*.app/Info.plist
```

---

## 7.5 Mobile Recon Checklist

- [ ] APK downloaded and decompiled (apktool + jadx)
- [ ] Hardcoded endpoints extracted
- [ ] Hardcoded secrets searched
- [ ] Certificate pinning bypass set up (Frida/Objection)
- [ ] Full mobile app walked through Burp proxy
- [ ] Mobile API endpoints compared to web API endpoints
- [ ] Mobile-only endpoints identified and tested
- [ ] Firebase config extracted and database tested
- [ ] Auth token comparison (mobile token vs web token access)
- [ ] Response field comparison (mobile returns more fields?)
