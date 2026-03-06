from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from ..domain.errors import AdapterError, InvalidInputError, UnsupportedSourceError
from .http_fetch import FetchConfig, decode_bytes, fetch_bytes
from .url_tools import canonicalize_http_url


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    # Best-effort ISO parsing; keep it dependency-free.
    try:
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


@dataclass(frozen=True, slots=True)
class ExtractedWebPage:
    url: str
    canonical_url: str
    title: str | None
    published_at: datetime | None
    markdown: str
    raw_meta: dict[str, Any]


def _require_trafilatura() -> Any:
    try:
        import trafilatura  # type: ignore

        return trafilatura
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise UnsupportedSourceError(
            "trafilatura is not installed. Install with `pip install 'ingestion_service[web]'`."
        ) from exc


async def fetch_html(url: str, *, cfg: FetchConfig | None = None) -> str:
    data = await fetch_bytes(
        url,
        cfg=cfg,
        accept="text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        drop_proxy_env=True,
    )
    return decode_bytes(data)


async def extract_web_page_markdown(
    url: str,
    *,
    min_words: int = 80,
    fetch_cfg: FetchConfig | None = None,
) -> ExtractedWebPage:
    trafilatura = _require_trafilatura()

    canonical = canonicalize_http_url(url)

    # Prefer trafilatura's fetcher if available; fall back to httpx.
    html: str | None = None
    try:
        html = await asyncio.to_thread(trafilatura.fetch_url, canonical)
    except Exception:
        html = None
    if not html:
        html = await fetch_html(canonical, cfg=fetch_cfg)

    try:
        markdown = await asyncio.to_thread(
            trafilatura.extract,
            html,
            output_format="markdown",
            include_links=True,
            include_tables=True,
            url=canonical,
        )
    except Exception as exc:  # noqa: BLE001
        raise AdapterError(f"trafilatura extract failed for {canonical}: {exc}") from exc

    body = (markdown or "").strip()
    if not body:
        raise AdapterError(f"No content extracted from {canonical}")
    if len(body.split()) < min_words:
        raise AdapterError(f"Extracted content too thin from {canonical} (min_words={min_words})")

    # Metadata is best-effort; tolerate signature differences across versions.
    meta: Any | None = None
    try:
        meta = await asyncio.to_thread(trafilatura.metadata.extract_metadata, html, canonical)
    except TypeError:
        try:
            meta = await asyncio.to_thread(trafilatura.metadata.extract_metadata, html)
        except Exception:
            meta = None
    except Exception:
        meta = None

    title = None
    date_raw = None
    canonical_from_meta = None
    if meta is not None:
        title = getattr(meta, "title", None)
        date_raw = getattr(meta, "date", None)
        canonical_from_meta = getattr(meta, "url", None) or getattr(meta, "source", None)

    canonical_final = canonical
    if canonical_from_meta:
        try:
            canonical_final = canonicalize_http_url(str(canonical_from_meta))
        except InvalidInputError:
            canonical_final = canonical

    published_at = _parse_datetime(str(date_raw)) if date_raw else None
    raw_meta: dict[str, Any] = {
        "extracted_via": "trafilatura",
        "min_words": min_words,
    }
    if title:
        raw_meta["extracted_title"] = title
    if date_raw:
        raw_meta["extracted_date"] = str(date_raw)
    if canonical_final != canonical:
        raw_meta["extracted_canonical_url"] = canonical_final

    return ExtractedWebPage(
        url=url,
        canonical_url=canonical_final,
        title=title,
        published_at=published_at,
        markdown=body,
        raw_meta=raw_meta,
    )
