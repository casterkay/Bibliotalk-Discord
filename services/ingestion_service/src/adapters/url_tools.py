from __future__ import annotations

import hashlib
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from ..domain.errors import InvalidInputError


_TRACKING_KEYS = {
    "gclid",
    "fbclid",
    "igshid",
    "mc_cid",
    "mc_eid",
}


def is_http_url(url: str) -> bool:
    u = url.strip().lower()
    return u.startswith("http://") or u.startswith("https://")


def canonicalize_http_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        raise InvalidInputError("URL is empty")
    if not is_http_url(raw):
        raise InvalidInputError(f"Unsupported URL scheme (http/https only): {url}")

    parsed = urlparse(raw)
    scheme = (parsed.scheme or "https").lower()
    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise InvalidInputError(f"Invalid URL (no hostname): {url}")

    netloc = hostname
    if parsed.port and not (
        (scheme == "http" and parsed.port == 80)
        or (scheme == "https" and parsed.port == 443)
    ):
        netloc = f"{hostname}:{parsed.port}"

    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]

    # Remove fragments; keep query but strip common tracking parameters.
    query_pairs = []
    for k, v in parse_qsl(parsed.query, keep_blank_values=True):
        lk = k.lower()
        if lk.startswith("utm_") or lk in _TRACKING_KEYS:
            continue
        query_pairs.append((k, v))
    query = urlencode(query_pairs, doseq=True)

    normalized = urlunparse((scheme, netloc, path, "", query, ""))
    return normalized


def url_external_id(url: str, *, length: int = 16) -> str:
    canon = canonicalize_http_url(url)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:length]


@dataclass(frozen=True, slots=True)
class HostPolicy:
    allowed_hosts: set[str]

    @classmethod
    def for_seed(cls, seed_url: str) -> "HostPolicy":
        parsed = urlparse(seed_url)
        host = (parsed.hostname or "").lower()
        if not host:
            raise InvalidInputError(f"Invalid URL (no hostname): {seed_url}")
        allowed = {host}
        if host.startswith("www."):
            allowed.add(host.removeprefix("www."))
        else:
            allowed.add(f"www.{host}")
        return cls(allowed_hosts=allowed)

    def allows(self, url: str) -> bool:
        try:
            parsed = urlparse(url)
        except Exception:
            return False
        host = (parsed.hostname or "").lower()
        return bool(host) and host in self.allowed_hosts

