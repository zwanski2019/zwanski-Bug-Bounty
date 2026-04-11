"""High-severity alert hooks (webhook stub)."""

from __future__ import annotations

import httpx

from ..classifier.schemas import ClassificationResult
from ..config import settings


async def maybe_alert(result: ClassificationResult) -> None:
    """POST summary to internal webhook when severity >= 7."""
    if result.severity_score < 7.0:
        return
    if not settings.internal_webhook_url:
        return
    async with httpx.AsyncClient(timeout=10.0) as client:
        await client.post(
            settings.internal_webhook_url,
            json={
                "finding_id": result.finding_id,
                "severity": result.severity_score,
                "leak_type": result.leak_type.value,
            },
        )
