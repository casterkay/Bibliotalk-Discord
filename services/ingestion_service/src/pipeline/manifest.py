from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from ..domain.errors import InvalidInputError, UnsupportedSourceError
from ..domain.models import Source
from ..adapters.url_tools import is_http_url, url_external_id


class ManifestDefaults(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str | None = None
    platform: str | None = None
    chunking: dict[str, Any] | None = None


class ManifestSourceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str | None = None
    platform: str | None = None
    external_id: str | None = None
    title: str
    source_url: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    raw_meta: dict[str, Any] | None = None

    text: str | None = None
    file_path: str | None = None
    doc_url: str | None = None
    web_url: str | None = None
    rss_url: str | None = None
    crawl_seed_url: str | None = None
    max_items: int | None = None
    max_pages: int | None = None
    gutenberg_id: str | int | None = None
    youtube_video_id: str | None = None

    @model_validator(mode="after")
    def _validate_modes(self) -> "ManifestSourceItem":
        modes = [
            bool(self.text),
            bool(self.file_path),
            bool(self.doc_url),
            bool(self.web_url),
            bool(self.rss_url),
            bool(self.crawl_seed_url),
            self.gutenberg_id is not None,
            bool(self.youtube_video_id),
        ]
        if sum(modes) != 1:
            raise InvalidInputError(
                "Each manifest source must set exactly one of: "
                "text, file_path, doc_url, web_url, rss_url, crawl_seed_url, gutenberg_id, youtube_video_id"
            )

        if self.external_id is None or not str(self.external_id).strip():
            if self.gutenberg_id is not None:
                self.external_id = str(self.gutenberg_id)
            elif self.youtube_video_id:
                self.external_id = self.youtube_video_id
            elif self.doc_url:
                if not is_http_url(self.doc_url):
                    raise InvalidInputError("doc_url must be an http(s) URL")
                self.external_id = url_external_id(self.doc_url)
            elif self.web_url:
                if not is_http_url(self.web_url):
                    raise InvalidInputError("web_url must be an http(s) URL")
                self.external_id = url_external_id(self.web_url)
            elif self.rss_url:
                if not is_http_url(self.rss_url):
                    raise InvalidInputError("rss_url must be an http(s) URL")
                self.external_id = url_external_id(self.rss_url)
            elif self.crawl_seed_url:
                if not is_http_url(self.crawl_seed_url):
                    raise InvalidInputError("crawl_seed_url must be an http(s) URL")
                self.external_id = url_external_id(self.crawl_seed_url)
            else:
                raise InvalidInputError("Missing external_id")

        if self.file_path is not None:
            p = Path(self.file_path)
            if not p.is_absolute():
                raise InvalidInputError("file_path must be absolute")
        if self.max_items is not None and self.max_items <= 0:
            raise InvalidInputError("max_items must be > 0")
        if self.max_pages is not None and self.max_pages <= 0:
            raise InvalidInputError("max_pages must be > 0")
        return self


class Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: Literal["1", "2"]
    run_name: str | None = None
    defaults: ManifestDefaults | None = None
    sources: list[ManifestSourceItem]


def load_manifest(path: Path) -> Manifest:
    if not path.is_absolute():
        raise InvalidInputError("Manifest path must be absolute")
    if not path.exists():
        raise InvalidInputError(f"Manifest not found: {path}")

    raw: dict[str, Any]
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise InvalidInputError(
                "PyYAML is required for .yaml manifests. Install with `pip install PyYAML`."
            ) from exc
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    elif path.suffix.lower() == ".json":
        raw = json.loads(path.read_text(encoding="utf-8"))
    else:
        raise InvalidInputError("Manifest must be .yaml/.yml or .json")

    try:
        return Manifest.model_validate(raw)
    except ValidationError as exc:
        raise InvalidInputError(f"Invalid manifest: {exc}") from exc


@dataclass(frozen=True, slots=True)
class ResolvedManifestSource:
    source: Source
    mode: Literal[
        "text",
        "file",
        "doc_url",
        "web_url",
        "rss_url",
        "crawl_seed_url",
        "gutenberg",
        "youtube",
    ]
    text: str | None = None
    file_path: Path | None = None
    doc_url: str | None = None
    web_url: str | None = None
    rss_url: str | None = None
    crawl_seed_url: str | None = None
    max_items: int | None = None
    max_pages: int | None = None
    gutenberg_id: str | None = None
    youtube_video_id: str | None = None


def resolve_manifest_sources(manifest: Manifest) -> list[ResolvedManifestSource]:
    defaults = manifest.defaults or ManifestDefaults()
    out: list[ResolvedManifestSource] = []

    for item in manifest.sources:
        user_id = item.user_id or defaults.user_id
        platform = item.platform or defaults.platform
        if not user_id:
            raise InvalidInputError("Missing user_id (set per-source or in defaults)")
        if not platform:
            raise InvalidInputError("Missing platform (set per-source or in defaults)")

        source = Source(
            user_id=user_id,
            platform=platform,
            external_id=str(item.external_id),
            title=item.title,
            source_url=item.source_url,
            author=item.author,
            published_at=item.published_at,
            raw_meta=item.raw_meta,
        )

        if item.text is not None:
            out.append(
                ResolvedManifestSource(source=source, mode="text", text=item.text)
            )
        elif item.file_path is not None:
            out.append(
                ResolvedManifestSource(
                    source=source, mode="file", file_path=Path(item.file_path)
                )
            )
        elif item.doc_url is not None:
            out.append(
                ResolvedManifestSource(
                    source=source,
                    mode="doc_url",
                    doc_url=item.doc_url,
                )
            )
        elif item.web_url is not None:
            out.append(
                ResolvedManifestSource(
                    source=source,
                    mode="web_url",
                    web_url=item.web_url,
                )
            )
        elif item.rss_url is not None:
            out.append(
                ResolvedManifestSource(
                    source=source,
                    mode="rss_url",
                    rss_url=item.rss_url,
                    max_items=item.max_items,
                )
            )
        elif item.crawl_seed_url is not None:
            out.append(
                ResolvedManifestSource(
                    source=source,
                    mode="crawl_seed_url",
                    crawl_seed_url=item.crawl_seed_url,
                    max_items=item.max_items,
                    max_pages=item.max_pages,
                )
            )
        elif item.gutenberg_id is not None:
            out.append(
                ResolvedManifestSource(
                    source=source, mode="gutenberg", gutenberg_id=str(item.gutenberg_id)
                )
            )
        elif item.youtube_video_id is not None:
            out.append(
                ResolvedManifestSource(
                    source=source,
                    mode="youtube",
                    youtube_video_id=item.youtube_video_id,
                )
            )
        else:  # pragma: no cover
            raise UnsupportedSourceError("Unsupported manifest source input mode")

    return out
