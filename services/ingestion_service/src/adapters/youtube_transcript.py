from __future__ import annotations

from ..domain.errors import AdapterError, UnsupportedSourceError
from ..domain.models import Source, SourceContent, TranscriptContent, TranscriptLine


async def load_youtube_transcript_source(
    *,
    user_id: str,
    external_id: str,
    title: str,
    video_id: str,
    canonical_url: str | None = None,
) -> SourceContent:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise UnsupportedSourceError(
            "youtube-transcript-api is not installed. Install with `pip install 'ingestion_service[ingest]'`."
        ) from exc

    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
    except Exception as exc:  # noqa: BLE001
        raise AdapterError(f"Failed to fetch YouTube transcript for video_id={video_id}: {exc}") from exc

    lines: list[TranscriptLine] = []
    for item in transcript:
        text = item.get("text", "")
        start_s = float(item.get("start", 0.0))
        dur_s = float(item.get("duration", 0.0))
        start_ms = int(start_s * 1000)
        end_ms = int((start_s + dur_s) * 1000) if dur_s else None
        lines.append(TranscriptLine(text=text, start_ms=start_ms, end_ms=end_ms))

    source = Source(
        user_id=user_id,
        platform="youtube",
        external_id=external_id or video_id,
        title=title,
        canonical_url=canonical_url or f"https://www.youtube.com/watch?v={video_id}",
        raw_meta={"youtube_video_id": video_id},
    )
    return SourceContent(source=source, content=TranscriptContent(lines=lines))
