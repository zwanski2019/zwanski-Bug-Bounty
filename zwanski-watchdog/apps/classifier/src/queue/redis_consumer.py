"""BLPOP consumer for `findings:queue`."""

from __future__ import annotations

import asyncio
import json

import redis.asyncio as redis
import structlog

from ..classifier.llm import LLMClassifier
from ..classifier.schemas import RawFinding
from ..config import settings
from ..alerts.pipeline import maybe_alert
from ..database.postgres import PostgresWriter

log = structlog.get_logger()

QUEUE_KEY = "findings:queue"
DLQ_KEY = "findings:dlq"


class FindingConsumer:
    """Pulls findings, classifies, persists, and optionally alerts."""

    def __init__(self, writer: PostgresWriter) -> None:
        self._writer = writer
        self._redis = redis.from_url(settings.redis_url, decode_responses=True)
        self._llm = LLMClassifier()

    async def start(self) -> None:
        await self._writer.connect()
        concurrency = max(1, settings.classifier_concurrency)
        await asyncio.gather(*(self._worker_loop() for _ in range(concurrency)))

    async def _worker_loop(self) -> None:
        while True:
            item = await self._redis.blpop(QUEUE_KEY, timeout=5)
            if item is None:
                continue
            _, payload = item
            try:
                data = json.loads(payload)
                raw = RawFinding.model_validate(data)
                result = await self._llm.classify(raw)
                await self._writer.save_classification(raw, result)
                await maybe_alert(result)
                log.info("classified", finding_id=raw.id, severity=result.severity_score)
            except Exception as exc:
                log.error("classify_failed", err=str(exc))
                await self._redis.lpush(DLQ_KEY, json.dumps({"error": str(exc), "raw": payload}))
