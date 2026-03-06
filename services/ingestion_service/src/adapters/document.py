from __future__ import annotations

import asyncio
import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

from ..domain.errors import AdapterError, InvalidInputError, UnsupportedSourceError
from ..domain.models import PlainTextContent, Source, SourceContent
from .http_fetch import FetchConfig, fetch_bytes
from .url_tools import canonicalize_http_url, is_http_url


@dataclass(frozen=True, slots=True)
class DocumentConfig:
    max_bytes: int = 25 * 1024 * 1024
    timeout_s: float = 120.0
    connect_timeout_s: float = 20.0
    retries: int = 2


_TEXT_EXTS = {".txt", ".md", ".markdown"}


def _require_markitdown():
    try:
        from markitdown import MarkItDown  # type: ignore

        return MarkItDown
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise UnsupportedSourceError(
            "markitdown is not installed. Install with `pip install 'ingestion_service[docs]'`."
        ) from exc


def _safe_filename_from_url(url: str) -> str:
    parsed = urlparse(url)
    name = Path(unquote(parsed.path or "")).name
    name = Path(name).name
    return name or "download"


def _default_downloads_dir() -> Path:
    return (Path.cwd() / ".ingestion_service" / "downloads").resolve()


async def download_document(
    url: str,
    *,
    cfg: DocumentConfig | None = None,
    downloads_dir: Path | None = None,
) -> Path:
    cfg = cfg or DocumentConfig()
    downloads_dir = downloads_dir or _default_downloads_dir()
    downloads_dir.mkdir(parents=True, exist_ok=True)

    canonical = canonicalize_http_url(url)
    url_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    filename = _safe_filename_from_url(canonical)
    dest = downloads_dir / f"{url_hash}_{filename}"

    try:
        if dest.exists() and dest.stat().st_size > 0:
            return dest
    except OSError:
        pass

    tmp = dest.with_name(dest.name + ".part")
    fetch_cfg = FetchConfig(
        timeout_s=cfg.timeout_s,
        connect_timeout_s=cfg.connect_timeout_s,
        retries=cfg.retries,
        max_bytes=cfg.max_bytes,
    )

    try:
        data = await fetch_bytes(
            canonical,
            cfg=fetch_cfg,
            accept="*/*",
            drop_proxy_env=True,
        )
        tmp.write_bytes(data)
        os.replace(tmp, dest)
        return dest
    except AdapterError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise AdapterError(f"Download failed for {canonical}: {exc}") from exc
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass


def _convert_path_sync(path: Path) -> str:
    if path.suffix.lower() in _TEXT_EXTS:
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return path.read_text(encoding="utf-8", errors="replace")

    MarkItDown = _require_markitdown()
    md = MarkItDown()
    result = md.convert(str(path))
    body = (getattr(result, "text_content", None) or "").strip()
    return body


async def convert_document_path_to_markdown(path: Path) -> str:
    if not path.is_absolute():
        raise InvalidInputError("file_path must be absolute")
    if not path.exists():
        raise InvalidInputError(f"File not found: {path}")

    body = (await asyncio.to_thread(_convert_path_sync, path)).strip()
    if not body:
        raise AdapterError(f"No text extracted from: {path.name}")
    return body


async def load_document_file_source(
    *,
    source: Source,
    path: Path,
) -> SourceContent:
    md = await convert_document_path_to_markdown(path)
    return SourceContent(source=source, content=PlainTextContent(text=md))


async def load_document_url_source(
    *,
    source: Source,
    url: str,
    cfg: DocumentConfig | None = None,
    downloads_dir: Path | None = None,
) -> SourceContent:
    if not is_http_url(url):
        raise InvalidInputError("doc_url must be an http(s) URL")
    local = await download_document(url, cfg=cfg, downloads_dir=downloads_dir)
    md = await convert_document_path_to_markdown(local)
    return SourceContent(source=source, content=PlainTextContent(text=md))

