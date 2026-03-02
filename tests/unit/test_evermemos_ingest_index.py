from __future__ import annotations

from evermemos_ingest.index import IngestionIndex


def test_index_roundtrip(tmp_path) -> None:
    db = tmp_path / "index.sqlite3"
    idx = IngestionIndex(db)

    idx.set_source_meta_saved(user_id="u1", group_id="g1", source_fingerprint="fp")
    assert idx.get_source_meta_saved(user_id="u1", group_id="g1") is True

    idx.upsert_segment_status(
        user_id="u1",
        group_id="g1",
        message_id="m1",
        seq=0,
        sha256="s1",
        status="ingested",
    )
    rec = idx.get_segment(user_id="u1", message_id="m1")
    assert rec is not None
    assert rec.message_id == "m1"
    assert rec.sha256 == "s1"
    assert rec.status == "ingested"

