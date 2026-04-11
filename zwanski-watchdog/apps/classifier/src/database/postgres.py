"""Async PostgreSQL helpers."""

from __future__ import annotations

import json

import asyncpg

from ..classifier.schemas import ClassificationResult, RawFinding
from ..config import settings


class PostgresWriter:
    """Insert classified findings (new row per scanner emission)."""

    def __init__(self) -> None:
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        self._pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=5)

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()

    async def save_classification(self, raw: RawFinding, result: ClassificationResult) -> None:
        if not self._pool:
            raise RuntimeError("pool not initialized")
        meta = {
            "scanner": raw.model_dump(mode="json"),
            "classification": result.model_dump(mode="json"),
        }
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO findings (
                  scanner_source, raw_content_hash, severity_score, leak_type,
                  affected_entity, status, scanner_url, discovered_at, updated_at, metadata
                ) VALUES ($1,$2,$3::numeric,$4::leak_type,$5,'triaged',$6,$7, now(), $8::jsonb)
                """,
                raw.module_name,
                raw.content_hash,
                str(result.severity_score),
                result.leak_type.value,
                result.affected_entity or raw.affected_entity,
                raw.url,
                raw.discovered_at,
                json.dumps(meta),
            )
