from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from typing import Any

from ..domain.errors import AdapterError, UnsupportedSourceError
from ..domain.models import Source, SourceContent, TranscriptContent, TranscriptLine


def _parse_published_at(meta: dict[str, Any]) -> datetime | None:
    timestamp = meta.get("timestamp")
    if isinstance(timestamp, (int, float)):
        try:
            return datetime.fromtimestamp(float(timestamp), tz=UTC)
        except (OSError, OverflowError, ValueError):
            return None

    upload_date = meta.get("upload_date")
    if isinstance(upload_date, str) and len(upload_date) == 8 and upload_date.isdigit():
        try:
            return datetime.strptime(upload_date, "%Y%m%d").replace(tzinfo=UTC)
        except ValueError:
            return None

    return None


def _fetch_video_metadata(video_id: str) -> dict[str, Any]:
    url = f"https://www.youtube.com/watch?v={video_id}"
    cmd = [
        "yt-dlp",
        "--skip-download",
        "--dump-single-json",
        "--no-warnings",
        url,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return {"metadata_fetch_error": "yt-dlp is not installed or not on PATH"}
    if proc.returncode != 0:
        return {"metadata_fetch_error": (proc.stderr.strip() or "yt-dlp failed")}

    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"metadata_fetch_error": "failed to parse yt-dlp JSON metadata"}

    return {
        "title": payload.get("title"),
        "channel": payload.get("channel"),
        "channel_id": payload.get("channel_id"),
        "upload_date": payload.get("upload_date"),
        "timestamp": payload.get("timestamp"),
        "duration_s": payload.get("duration"),
        "webpage_url": payload.get("webpage_url"),
    }


async def load_youtube_transcript_source(
    *,
    user_id: str,
    external_id: str,
    title: str,
    video_id: str,
    source_url: str | None = None,
) -> SourceContent:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise UnsupportedSourceError(
            "youtube-transcript-api is not installed. Install with `pip install 'ingestion_service[ingest]'`."
        ) from exc

    try:
        if hasattr(YouTubeTranscriptApi, "get_transcript"):
            transcript = YouTubeTranscriptApi.get_transcript(video_id)  # type: ignore[attr-defined]
        else:
            fetched = YouTubeTranscriptApi().fetch(video_id)
            transcript = (
                fetched.to_raw_data()
                if hasattr(fetched, "to_raw_data")
                else [
                    {
                        "text": getattr(item, "text", ""),
                        "start": float(getattr(item, "start", 0.0)),
                        "duration": float(getattr(item, "duration", 0.0)),
                    }
                    for item in fetched
                ]
            )
    except Exception as exc:
        raise AdapterError(
            f"Failed to fetch YouTube transcript for video_id={video_id}: {exc}"
        ) from exc

    lines: list[TranscriptLine] = []
    for item in transcript:
        text = str(item.get("text", "")).replace("\n", " ").strip()
        if not text:
            continue
        start_s = float(item.get("start", 0.0))
        dur_s = float(item.get("duration", 0.0))
        start_ms = int(start_s * 1000)
        end_ms = int((start_s + dur_s) * 1000) if dur_s else None
        lines.append(TranscriptLine(text=text, start_ms=start_ms, end_ms=end_ms))

    meta = _fetch_video_metadata(video_id)
    resolved_title = str(meta.get("title") or title)
    source = Source(
        user_id=user_id,
        external_id=external_id or video_id,
        title=resolved_title,
        source_url=source_url or f"https://www.youtube.com/watch?v={video_id}",
        channel_name=(str(meta.get("channel")) if meta.get("channel") else None),
        published_at=_parse_published_at(meta),
        raw_meta={
            "youtube_video_id": video_id,
            **meta,
            "transcript_line_count": len(lines),
        },
    )
    return SourceContent(source=source, content=TranscriptContent(lines=lines))
