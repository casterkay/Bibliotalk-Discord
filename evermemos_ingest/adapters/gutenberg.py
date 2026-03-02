from __future__ import annotations

import re
from pathlib import Path

import httpx

from ..errors import AdapterError, InvalidInputError
from ..models import PlainTextContent, Source, SourceContent


_START_RE = re.compile(r"\\*\\*\\*\\s*START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK", flags=re.IGNORECASE)
_END_RE = re.compile(r"\\*\\*\\*\\s*END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK", flags=re.IGNORECASE)


def _strip_gutenberg_boilerplate(text: str) -> str:
    lines = text.splitlines()
    start_idx = None
    end_idx = None
    for i, line in enumerate(lines):
        if start_idx is None and _START_RE.search(line):
            start_idx = i + 1
        if _END_RE.search(line):
            end_idx = i
            break
    if start_idx is not None and end_idx is not None and start_idx < end_idx:
        return "\n".join(lines[start_idx:end_idx]).strip()
    return text.strip()


async def load_gutenberg_source(
    *,
    user_id: str,
    external_id: str,
    title: str,
    gutenberg_id: str,
    canonical_url: str | None = None,
    author: str | None = None,
) -> SourceContent:
    if not gutenberg_id.strip().isdigit():
        raise InvalidInputError("gutenberg_id must be numeric")
    book_id = gutenberg_id.strip()

    # Primary plain-text cache location; fallback attempts can be extended later.
    url = f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt"
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, trust_env=False) as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            raise AdapterError(f"Failed to download Gutenberg text (HTTP {resp.status_code})")
        text = resp.text

    stripped = _strip_gutenberg_boilerplate(text)
    source = Source(
        user_id=user_id,
        platform="gutenberg",
        external_id=external_id or book_id,
        title=title,
        canonical_url=canonical_url or f"https://www.gutenberg.org/ebooks/{book_id}",
        author=author,
        raw_meta={"gutenberg_id": book_id},
    )
    return SourceContent(source=source, content=PlainTextContent(text=stripped))

