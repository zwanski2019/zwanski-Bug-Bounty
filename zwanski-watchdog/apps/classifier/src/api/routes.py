"""HTTP surface for health, metrics, and admin utilities."""

from __future__ import annotations

import redis.asyncio as redis
from fastapi import APIRouter, HTTPException
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
from starlette.responses import Response

from ..config import settings

router = APIRouter()

CLASS_TOTAL = Counter("watchdog_classifier_classifications_total", "Classifications processed")


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "classifier"}


@router.get("/metrics")
async def metrics() -> Response:
    data = generate_latest()
    return Response(data, media_type=CONTENT_TYPE_LATEST)


@router.get("/stats")
async def stats() -> dict[str, str]:
    return {"message": "wire prometheus + db aggregates later"}


@router.get("/queue/depth")
async def queue_depth() -> dict[str, int]:
    r = redis.from_url(settings.redis_url)
    try:
        depth = await r.llen("findings:queue")
        return {"depth": int(depth)}
    finally:
        await r.aclose()


@router.post("/queue/retry-dlq")
async def retry_dlq() -> dict[str, str]:
    raise HTTPException(status_code=501, detail="Admin retry not implemented")
