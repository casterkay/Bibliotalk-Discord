from __future__ import annotations

import asyncio
import json
import subprocess
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from ..adapters.rss_feed import FeedEntry, parse_feed
from ..domain.errors import AdapterError


@dataclass(frozen=True, slots=True)
class DiscoveredVideo:
    video_id: str
    title: str
    source_url: str
    published_at: datetime | None
    channel_name: str | None
    raw_meta: dict[str, Any]


def _parse_published_at(value: Any) -> datetime | None:
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=UTC)
        except (OSError, OverflowError, ValueError):
            return None
    if isinstance(value, str) and len(value) == 8 and value.isdigit():
        try:
            return datetime.strptime(value, "%Y%m%d").replace(tzinfo=UTC)
        except ValueError:
            return None
    return None


def _parse_yt_dlp_entries(payload: dict[str, Any]) -> list[DiscoveredVideo]:
    entries = payload.get("entries") or []
    videos: list[DiscoveredVideo] = []
    for item in entries:
        if not isinstance(item, dict):
            continue
        video_id = item.get("id")
        if not isinstance(video_id, str) or not video_id:
            continue
        title = str(item.get("title") or video_id)
        source_url = str(item.get("url") or f"https://www.youtube.com/watch?v={video_id}")
        if not source_url.startswith("http"):
            source_url = f"https://www.youtube.com/watch?v={video_id}"
        videos.append(
            DiscoveredVideo(
                video_id=video_id,
                title=title,
                source_url=source_url,
                published_at=_parse_published_at(item.get("timestamp") or item.get("upload_date")),
                channel_name=(str(item.get("channel")) if item.get("channel") else None),
                raw_meta=item,
            )
        )
    return videos


def compute_discovery_delta(
    entries: list[DiscoveredVideo],
    *,
    last_seen_video_id: str | None,
    last_published_at: datetime | None,
) -> list[DiscoveredVideo]:
    pending: list[DiscoveredVideo] = []
    for entry in entries:
        if last_seen_video_id and entry.video_id == last_seen_video_id:
            break
        if (
            last_published_at
            and entry.published_at is not None
            and entry.published_at <= last_published_at
        ):
            break
        pending.append(entry)
    pending.reverse()
    return pending


async def _run_yt_dlp(subscription_url: str) -> dict[str, Any]:
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-single-json",
        "--no-warnings",
        subscription_url,
    ]

    def _invoke() -> dict[str, Any]:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise AdapterError(proc.stderr.strip() or "yt-dlp discovery failed")
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise AdapterError("failed to parse yt-dlp discovery output") from exc

    return await asyncio.to_thread(_invoke)


def _from_feed_entries(entries: list[FeedEntry]) -> list[DiscoveredVideo]:
    videos: list[DiscoveredVideo] = []
    for entry in entries:
        if not entry.video_id:
            continue
        videos.append(
            DiscoveredVideo(
                video_id=entry.video_id,
                title=entry.title or entry.video_id,
                source_url=entry.url,
                published_at=entry.published_at,
                channel_name=None,
                raw_meta=entry.raw_meta,
            )
        )
    return videos


async def discover_subscription(
    subscription_url: str,
    *,
    last_seen_video_id: str | None = None,
    last_published_at: datetime | None = None,
    yt_dlp_loader: Callable[[str], Awaitable[dict[str, Any]]] | None = None,
    rss_loader: Callable[[str], Awaitable[list[FeedEntry]]] | None = None,
) -> list[DiscoveredVideo]:
    yt_dlp_loader = yt_dlp_loader or _run_yt_dlp
    rss_loader = rss_loader or parse_feed

    try:
        payload = await yt_dlp_loader(subscription_url)
        entries = _parse_yt_dlp_entries(payload)
    except AdapterError:
        entries = _from_feed_entries(await rss_loader(subscription_url))

    return compute_discovery_delta(
        entries,
        last_seen_video_id=last_seen_video_id,
        last_published_at=last_published_at,
    )
