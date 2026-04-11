"""Fast path regex checks before LLM."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from .schemas import ClassificationResult, LeakType, RawFinding, RecommendedAction

_AWS = re.compile(r"AKIA[0-9A-Z]{16}")
_GH = re.compile(r"ghp_[A-Za-z0-9]{36}")
_STRIPE = re.compile(r"sk_live_[A-Za-z0-9]{24,}")


def maybe_false_positive(finding: RawFinding) -> ClassificationResult | None:
    """Return a definite false-positive classification or None to continue."""
    text = finding.raw_content
    if len(text) < 8:
        return _fp(finding, "too_short")
    return None


def has_strong_credential_signal(finding: RawFinding) -> bool:
    """Hint for logging only — LLM still refines when API key is configured."""
    text = finding.raw_content
    if _AWS.search(text) or _GH.search(text) or _STRIPE.search(text):
        return True
    return "BEGIN RSA PRIVATE KEY" in text or "BEGIN OPENSSH PRIVATE KEY" in text


def _fp(finding: RawFinding, reason: str) -> ClassificationResult:
    now = datetime.now(timezone.utc)
    return ClassificationResult(
        finding_id=finding.id,
        is_real_leak=False,
        confidence=0.95,
        leak_type=LeakType.OTHER,
        severity_score=0.2,
        severity_reasoning=reason,
        affected_entity=finding.affected_entity,
        affected_entity_confidence=0.1,
        recommended_action=RecommendedAction.FALSE_POSITIVE,
        pii_detected=False,
        pii_types=[],
        ai_content_detected=False,
        classified_at=now,
        model_used="rules",
        tokens_used=0,
    )
