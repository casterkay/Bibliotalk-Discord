from __future__ import annotations

import asyncio
import gzip
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Iterable
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree as ET

from ..domain.errors import AdapterError
from .http_fetch import FetchConfig, decode_bytes, fetch_bytes
from .rss_feed import parse_feed
from .url_tools import HostPolicy, canonicalize_http_url, is_http_url


_DENY_SEGMENTS = {
    "tag",
    "tags",
    "category",
    "categories",
    "author",
    "authors",
    "search",
    "about",
    "contact",
    "privacy",
    "terms",
    "feed",
    "rss",
    "atom",
    "sitemap",
    "wp-admin",
    "wp-json",
    "api",
    "login",
    "signin",
    "signup",
}

_DENY_EXTS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".svg",
    ".css",
    ".js",
    ".json",
    ".xml",
    ".pdf",
    ".zip",
    ".gz",
    ".mp3",
    ".mp4",
    ".mov",
}

_DATE_PATH_RE = re.compile(r"/(19|20)\d{2}/\d{1,2}(/\d{1,2})?/", flags=re.IGNORECASE)


def _looks_like_post_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    path = parsed.path or "/"
    if path in {"", "/"}:
        return False
    lower_path = path.lower()
    for ext in _DENY_EXTS:
        if lower_path.endswith(ext):
            return False
    segments = [s for s in lower_path.split("/") if s]
    if any(seg in _DENY_SEGMENTS for seg in segments):
        return False
    if _DATE_PATH_RE.search(lower_path):
        return True
    # Heuristic: a "slug" long enough to be an article.
    slug = segments[-1] if segments else ""
    if len(slug) >= 8 and any(c in slug for c in ("-", "_")):
        return True
    if len(segments) >= 2 and len(slug) >= 10:
        return True
    return False


class _LinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        href = None
        for k, v in attrs:
            if k.lower() == "href" and v:
                href = v
                break
        if href:
            self.hrefs.append(href)


class _HeadLinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_head = False
        self.feed_hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        if t == "head":
            self.in_head = True
            return
        if t == "link" and self.in_head:
            rel = ""
            typ = ""
            href = ""
            for k, v in attrs:
                lk = k.lower()
                if lk == "rel" and v:
                    rel = v.lower()
                elif lk == "type" and v:
                    typ = v.lower()
                elif lk == "href" and v:
                    href = v
            if "alternate" not in rel:
                return
            if "rss+xml" in typ or "atom+xml" in typ:
                self.feed_hrefs.append(href)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "head":
            self.in_head = False


def _sitemap_locs(xml_bytes: bytes) -> tuple[list[str], list[str]]:
    """Return (url_locs, sitemap_locs)."""

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return ([], [])

    def strip_ns(tag: str) -> str:
        return tag.split("}", 1)[-1] if "}" in tag else tag

    urls: list[str] = []
    sitemaps: list[str] = []

    root_tag = strip_ns(root.tag).lower()
    if root_tag == "urlset":
        for url_node in root.findall(".//{*}url"):
            loc = url_node.findtext("{*}loc") or ""
            loc = loc.strip()
            if loc:
                urls.append(loc)
    elif root_tag == "sitemapindex":
        for sm_node in root.findall(".//{*}sitemap"):
            loc = sm_node.findtext("{*}loc") or ""
            loc = loc.strip()
            if loc:
                sitemaps.append(loc)
    return (urls, sitemaps)


@dataclass(frozen=True, slots=True)
class CrawlConfig:
    max_items: int = 50
    max_pages: int = 200
    max_depth: int = 3
    fetch_cfg: FetchConfig = FetchConfig(max_bytes=5 * 1024 * 1024)


async def _autodiscover_feed_urls(seed_url: str, *, cfg: CrawlConfig) -> list[str]:
    html = decode_bytes(await fetch_bytes(seed_url, cfg=cfg.fetch_cfg, accept="text/html,*/*"))
    parser = _HeadLinkExtractor()
    parser.feed(html)
    out: list[str] = []
    for href in parser.feed_hrefs:
        if not href:
            continue
        abs_url = urljoin(seed_url, href)
        if is_http_url(abs_url):
            try:
                out.append(canonicalize_http_url(abs_url))
            except Exception:
                continue
    # Deduplicate deterministically.
    return sorted(set(out))


async def _robots_sitemaps(root: str, *, cfg: CrawlConfig) -> list[str]:
    robots = urljoin(root, "/robots.txt")
    try:
        data = await fetch_bytes(robots, cfg=cfg.fetch_cfg, accept="text/plain,*/*")
        text = decode_bytes(data)
    except Exception:
        text = ""
    sitemaps: list[str] = []
    for line in text.splitlines():
        if line.lower().startswith("sitemap:"):
            loc = line.split(":", 1)[1].strip()
            if loc and is_http_url(loc):
                try:
                    sitemaps.append(canonicalize_http_url(loc))
                except Exception:
                    continue
    if not sitemaps:
        sitemaps.append(urljoin(root, "/sitemap.xml"))
    return sorted(set(sitemaps))


async def _fetch_sitemap_bytes(url: str, *, cfg: CrawlConfig) -> bytes:
    data = await fetch_bytes(url, cfg=cfg.fetch_cfg, accept="application/xml,text/xml,*/*")
    if url.lower().endswith(".gz") or data[:2] == b"\x1f\x8b":
        try:
            return gzip.decompress(data)
        except OSError:
            return data
    return data


async def _sitemap_discover(seed_url: str, *, cfg: CrawlConfig) -> list[str]:
    parsed = urlparse(seed_url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    policy = HostPolicy.for_seed(seed_url)

    frontier = await _robots_sitemaps(root, cfg=cfg)
    seen: set[str] = set()
    out: set[str] = set()

    while frontier and len(seen) < cfg.max_pages and len(out) < cfg.max_items * 5:
        sm = frontier.pop(0)
        if sm in seen:
            continue
        seen.add(sm)
        try:
            xml_bytes = await _fetch_sitemap_bytes(sm, cfg=cfg)
        except Exception:
            continue
        urls, sitemaps = _sitemap_locs(xml_bytes)
        for u in urls:
            if not is_http_url(u):
                continue
            try:
                canon = canonicalize_http_url(u)
            except Exception:
                continue
            if not policy.allows(canon):
                continue
            if _looks_like_post_url(canon):
                out.add(canon)
        for sm_url in sitemaps:
            if not is_http_url(sm_url):
                continue
            try:
                canon_sm = canonicalize_http_url(sm_url)
            except Exception:
                continue
            if policy.allows(canon_sm) and canon_sm not in seen:
                frontier.append(canon_sm)

        frontier.sort()

    urls_sorted = sorted(out)
    if cfg.max_items:
        urls_sorted = urls_sorted[: cfg.max_items]
    return urls_sorted


async def _bfs_discover(seed_url: str, *, cfg: CrawlConfig) -> list[str]:
    policy = HostPolicy.for_seed(seed_url)
    seed = canonicalize_http_url(seed_url)

    queue: list[tuple[str, int]] = [(seed, 0)]
    visited: set[str] = set()
    discovered: set[str] = set()

    while queue and len(visited) < cfg.max_pages and len(discovered) < cfg.max_items:
        url, depth = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)
        if depth > cfg.max_depth:
            continue

        try:
            html = decode_bytes(await fetch_bytes(url, cfg=cfg.fetch_cfg, accept="text/html,*/*"))
        except Exception:
            continue

        if _looks_like_post_url(url):
            discovered.add(url)
            if len(discovered) >= cfg.max_items:
                break

        parser = _LinkExtractor()
        parser.feed(html)
        for href in parser.hrefs:
            if not href:
                continue
            abs_url = urljoin(url, href)
            if not is_http_url(abs_url):
                continue
            try:
                canon = canonicalize_http_url(abs_url)
            except Exception:
                continue
            if not policy.allows(canon):
                continue
            if canon in visited:
                continue
            if urlparse(canon).path.lower().endswith(tuple(_DENY_EXTS)):
                continue
            queue.append((canon, depth + 1))

        # Keep traversal deterministic.
        queue.sort(key=lambda x: (x[1], x[0]))

    return sorted(discovered)[: cfg.max_items]


async def discover_blog_urls(seed_url: str, *, cfg: CrawlConfig | None = None) -> list[str]:
    cfg = cfg or CrawlConfig()
    seed = canonicalize_http_url(seed_url)

    # 1) RSS/Atom autodiscovery (best blog signal).
    try:
        feed_urls = await _autodiscover_feed_urls(seed, cfg=cfg)
        for feed_url in feed_urls:
            entries = await parse_feed(feed_url, max_items=cfg.max_items)
            urls = sorted({e.url for e in entries if _looks_like_post_url(e.url)})
            if urls:
                return urls[: cfg.max_items]
    except Exception:
        pass

    # 2) Sitemap discovery.
    try:
        urls = await _sitemap_discover(seed, cfg=cfg)
        if urls:
            return urls
    except Exception:
        pass

    # 3) Fallback: bounded BFS crawl.
    urls = await _bfs_discover(seed, cfg=cfg)
    if urls:
        return urls

    raise AdapterError(f"No blog URLs discovered from seed: {seed}")


def choose_urls(
    urls: Iterable[str],
    *,
    max_items: int,
) -> list[str]:
    unique = sorted(set(urls))
    return unique[: max(0, int(max_items))]

