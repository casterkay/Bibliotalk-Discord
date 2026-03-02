from __future__ import annotations

import pytest

from ingestion_service.domain.models import PlainTextContent, Source, SourceContent
from ingestion_service.pipeline.index import IngestionIndex
from ingestion_service.pipeline.ingest import ingest_sources


class StubEverMemOS:
    def __init__(self) -> None:
        self.memorize_calls: list[dict] = []
        self.meta_calls: list[dict] = []

    async def memorize(self, payload: dict) -> dict:
        self.memorize_calls.append(payload)
        return {"ok": True}

    async def save_conversation_meta(self, *, group_id: str, source_meta: dict) -> dict:
        self.meta_calls.append({"group_id": group_id, "source_meta": source_meta})
        return {"ok": True}


@pytest.mark.asyncio
async def test_ingest_rerun_skips_unchanged_segments(tmp_path) -> None:
    idx = IngestionIndex(tmp_path / "index.sqlite3")
    client = StubEverMemOS()

    src = Source(user_id="u1", platform="local", external_id="e1", title="T")
    sc = SourceContent(source=src, content=PlainTextContent(text="One.\n\nTwo.\n\nThree."))

    r1 = await ingest_sources(sources=[sc], index=idx, client=client)
    assert r1.status == "done"
    first_calls = len(client.memorize_calls)
    assert first_calls > 0

    client.memorize_calls.clear()
    r2 = await ingest_sources(sources=[sc], index=idx, client=client)
    assert r2.sources[0].segments_skipped_unchanged > 0
    assert len(client.memorize_calls) == 0
