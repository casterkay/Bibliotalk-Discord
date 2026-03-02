from __future__ import annotations

from ingestion_service.domain.models import Source
from ingestion_service.pipeline.chunking import chunk_plain_text


def test_chunk_plain_text_is_deterministic() -> None:
    src = Source(user_id="u1", platform="local", external_id="e1", title="T")
    text = "Para 1 line.\n\nPara 2 line.\n\nPara 3 line."

    a = chunk_plain_text(src, text)
    b = chunk_plain_text(src, text)

    assert [s.message_id for s in a] == [s.message_id for s in b]
    assert [s.sha256 for s in a] == [s.sha256 for s in b]
    assert [s.text for s in a] == [s.text for s in b]
