from __future__ import annotations

from ingestion_service.adapters.youtube_transcript import _fetch_video_metadata


def test_fetch_video_metadata_handles_missing_yt_dlp(monkeypatch) -> None:
    def missing_binary(*args, **kwargs):
        del args, kwargs
        raise FileNotFoundError("yt-dlp")

    monkeypatch.setattr(
        "ingestion_service.adapters.youtube_transcript.subprocess.run", missing_binary
    )

    meta = _fetch_video_metadata("abc123")

    assert meta["metadata_fetch_error"] == "yt-dlp is not installed or not on PATH"
