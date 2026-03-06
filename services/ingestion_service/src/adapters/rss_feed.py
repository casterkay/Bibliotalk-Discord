from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from ..domain.errors import AdapterError, UnsupportedSourceError
from .url_tools import canonicalize_http_url, is_http_url


@dataclass(frozen=True, slots=True)
class FeedEntry:
    url: str
    title: str | None
    published_at: datetime | None
    raw_meta: dict[str, Any]


def _require_feedparser() -> Any:
    try:
        import feedparser  # type: ignore

        return feedparser
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise UnsupportedSourceError(
            "feedparser is not installed. Install with `pip install 'ingestion_service[web]'`."
        ) from exc


def _entry_link(entry: Any) -> str | None:
    link = getattr(entry, "link", None) or entry.get("link") if isinstance(entry, dict) else None
    if link:
        return str(link)
    links = getattr(entry, "links", None) or entry.get("links") if isinstance(entry, dict) else None
    if not links:
        return None
    for item in links:
        rel = (getattr(item, "rel", None) or item.get("rel", "")).lower()
        href = getattr(item, "href", None) or item.get("href")
        if rel in {"alternate", ""} and href:
            return str(href)
    return None


def _to_datetime(value: Any) -> datetime | None:
    parsed = getattr(value, "published_parsed", None)
    if parsed:
        try:
            return datetime(*parsed[:6], tzinfo=timezone.utc)
        except Exception:
            return None
    raw = getattr(value, "published", None) or getattr(value, "updated", None)
    if isinstance(raw, str):
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            return None
    return None


def _parse_sync(feed_url: str) -> list[FeedEntry]:
    feedparser = _require_feedparser()

    parsed = feedparser.parse(feed_url)
    if getattr(parsed, "bozo", 0):
        # feedparser sets bozo=1 on errors but may still have entries.
        pass

    entries: list[FeedEntry] = []
    for entry in getattr(parsed, "entries", []) or []:
        link = _entry_link(entry)
        if not link or not is_http_url(link):
            continue
        try:
            canon = canonicalize_http_url(link)
        except Exception:
            continue
        title = getattr(entry, "title", None) or (entry.get("title") if isinstance(entry, dict) else None)
        published = _to_datetime(entry)
        entries.append(
            FeedEntry(
                url=canon,
                title=str(title).strip() if title else None,
                published_at=published,
                raw_meta={"feed_url": feed_url},
            )
        )
    return entries


async def parse_feed(feed_url: str, *, max_items: int | None = None) -> list[FeedEntry]:
    try:
        canon_feed = canonicalize_http_url(feed_url)
    except Exception as exc:
        raise AdapterError(f"Invalid rss_url: {feed_url} ({exc})") from exc

    entries = await asyncio.to_thread(_parse_sync, canon_feed)
    # Deterministic ordering: published_at desc (when present), then URL asc.
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    entries.sort(
        key=lambda e: (
            -(e.published_at or epoch).timestamp(),
            e.url,
        )
    )
    if max_items is not None:
        entries = entries[: max(0, int(max_items))]
    return entries
