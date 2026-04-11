"""
Ghost / Shadow Mode: rotate User-Agent, common client headers, and jittered delays
before outbound HTTP to reduce trivial WAF fingerprinting (defensive research use).
Controlled via env: SHADOW_MODE=1, SHADOW_MIN_DELAY, SHADOW_JITTER.
"""
from __future__ import annotations

import os
import random
import time
from typing import Any

import requests

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]

ACCEPT_HEADERS = [
    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "application/json,text/plain,*/*",
]

ACCEPT_LANG = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.9,de;q=0.8",
    "en-US,en;q=0.5",
]

SEC_FETCH = [
    {"Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate", "Sec-Fetch-Site": "none"},
    {"Sec-Fetch-Dest": "empty", "Sec-Fetch-Mode": "cors", "Sec-Fetch-Site": "same-origin"},
]


def shadow_enabled() -> bool:
    v = (os.environ.get("SHADOW_MODE") or "").lower()
    return v in ("1", "true", "yes", "on")


def _jitter_sleep() -> None:
    base = float(os.environ.get("SHADOW_MIN_DELAY", "0.35"))
    jitter = float(os.environ.get("SHADOW_JITTER", "1.75"))
    time.sleep(base + random.random() * jitter)


def build_shadow_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    h = dict(extra or {})
    h["User-Agent"] = random.choice(USER_AGENTS)
    h.setdefault("Accept", random.choice(ACCEPT_HEADERS))
    h.setdefault("Accept-Language", random.choice(ACCEPT_LANG))
    sf = random.choice(SEC_FETCH)
    for k, v in sf.items():
        h.setdefault(k, v)
    return h


def shadow_request(method: str, url: str, **kwargs: Any) -> requests.Response:
    if shadow_enabled():
        _jitter_sleep()
        kwargs.setdefault("headers", {})
        if isinstance(kwargs["headers"], dict):
            merged = build_shadow_headers(kwargs["headers"])
            kwargs["headers"] = merged
    return requests.request(method, url, **kwargs)
