"""Per-target file-backed knowledge store for RAG-style context (CrawlAI / recon output)."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path


def safe_target_slug(target: str) -> str:
    t = (target or "").strip().lower()
    return re.sub(r"[^a-z0-9._-]", "_", t)[:200] or "unknown"


class TargetKnowledgeBase:
    def __init__(self, root: Path, target: str):
        self.target = target.strip()
        self.dir = root / "data" / "kb" / safe_target_slug(target)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.corpus = self.dir / "corpus.txt"

    def append(self, text: str, source: str = "") -> None:
        if not (text or "").strip():
            return
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        block = f"\n--- {source} @ {stamp} ---\n{text}"
        if not text.endswith("\n"):
            block += "\n"
        with self.corpus.open("a", encoding="utf-8", errors="replace") as f:
            f.write(block)

    def read_corpus(self, max_bytes: int = 400_000) -> str:
        if not self.corpus.exists():
            return ""
        data = self.corpus.read_bytes()
        if len(data) > max_bytes:
            data = data[-max_bytes:]
        return data.decode("utf-8", errors="replace")

    def query(self, q: str, max_chunks: int = 14) -> str:
        text = self.read_corpus()
        if not text.strip():
            return ""
        words = {w.lower() for w in re.findall(r"\w+", q) if len(w) > 2}
        if not words:
            words = {q.strip().lower()} if q.strip() else set()
        chunks = [c.strip() for c in re.split(r"\n--- ", text) if c.strip()]
        scored: list[tuple[int, str]] = []
        for ch in chunks:
            low = ch.lower()
            score = sum(1 for w in words if w in low)
            if score:
                scored.append((score, ch[:1500]))
        scored.sort(key=lambda x: -x[0])
        if not scored:
            return text[-6000:]
        return "\n\n".join(c for _, c in scored[:max_chunks])[:12000]
