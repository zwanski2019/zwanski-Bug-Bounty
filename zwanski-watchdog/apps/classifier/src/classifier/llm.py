"""OpenRouter-backed classifier."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import settings
from .patterns import has_strong_credential_signal, maybe_false_positive
from .prompts import SYSTEM_PROMPT, build_user_prompt
from .schemas import ClassificationResult, LeakType, RawFinding, RecommendedAction

log = structlog.get_logger()


class LLMClassifier:
    """Calls OpenRouter with retries; falls back to heuristic rules."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=45.0)

    async def classify(self, finding: RawFinding) -> ClassificationResult:
        instant = maybe_false_positive(finding)
        if instant:
            return instant

        if not settings.openrouter_api_key:
            return self._offline_result(finding)

        if has_strong_credential_signal(finding):
            log.info("strong_credential_signal", finding_id=finding.id)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(finding)},
        ]
        try:
            data = await self._call_openrouter(messages, settings.openrouter_model)
            content = data["choices"][0]["message"]["content"]
            payload = json.loads(content)
            payload.setdefault("classified_at", datetime.now(timezone.utc).isoformat())
            payload.setdefault("finding_id", finding.id)
            return ClassificationResult.model_validate(payload)
        except Exception as exc:
            log.warning("primary_model_failed", err=str(exc))
            try:
                data = await self._call_openrouter(messages, settings.openrouter_fallback_model)
                content = data["choices"][0]["message"]["content"]
                payload = json.loads(content)
                payload.setdefault("classified_at", datetime.now(timezone.utc).isoformat())
                payload.setdefault("finding_id", finding.id)
                return ClassificationResult.model_validate(payload)
            except Exception as exc2:
                log.error("fallback_failed", err=str(exc2))
                return self._offline_result(finding)

    def _offline_result(self, finding: RawFinding) -> ClassificationResult:
        now = datetime.now(timezone.utc)
        sev = 6.5 if has_strong_credential_signal(finding) else 5.0
        return ClassificationResult(
            finding_id=finding.id,
            is_real_leak=True,
            confidence=0.55,
            leak_type=LeakType.API_KEY if has_strong_credential_signal(finding) else LeakType.OTHER,
            severity_score=sev,
            severity_reasoning="Offline mode — configure OPENROUTER_API_KEY",
            affected_entity=finding.affected_entity,
            affected_entity_confidence=0.4,
            recommended_action=RecommendedAction.NOTIFY_COMPANY,
            pii_detected=False,
            pii_types=[],
            ai_content_detected=False,
            classified_at=now,
            model_used="offline-heuristic",
            tokens_used=0,
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def _call_openrouter(self, messages: list[dict[str, str]], model: str) -> dict:
        res = await self._client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 800,
            },
        )
        res.raise_for_status()
        return res.json()
