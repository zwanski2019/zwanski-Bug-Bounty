"""Zwanski Watchdog — AI classifier service."""

from __future__ import annotations

import asyncio
import contextlib

import structlog
import uvicorn
from fastapi import FastAPI

from src.api.routes import router
from src.config import settings
from src.queue.redis_consumer import FindingConsumer
from src.database.postgres import PostgresWriter

structlog.configure(processors=[structlog.processors.JSONRenderer()])
log = structlog.get_logger()

app = FastAPI(title="Zwanski Watchdog Classifier", version="0.1.0")
app.include_router(router)


@app.on_event("startup")
async def startup() -> None:
    writer = PostgresWriter()
    consumer = FindingConsumer(writer)
    app.state.consumer_task = asyncio.create_task(consumer.start())
    log.info("consumer_started", concurrency=settings.classifier_concurrency)


@app.on_event("shutdown")
async def shutdown() -> None:
    task = getattr(app.state, "consumer_task", None)
    if task:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=False)
