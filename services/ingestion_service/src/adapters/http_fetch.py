from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Iterable

import httpx

from ..domain.errors import AdapterError


@dataclass(frozen=True, slots=True)
class FetchConfig:
    timeout_s: float = 90.0
    connect_timeout_s: float = 15.0
    retries: int = 2
    max_bytes: int = 8 * 1024 * 1024
    user_agent: str = "Mozilla/5.0 (compatible; BibliotalkIngestion/1.0)"


def _drop_proxy_env() -> dict[str, str]:
    """Temporarily drop proxy env vars (best-effort) and return previous values."""

    proxy_keys = [
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "NO_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "no_proxy",
    ]
    old_env: dict[str, str] = {}
    for k in proxy_keys:
        v = os.environ.get(k)
        if v is not None:
            old_env[k] = v
            os.environ.pop(k, None)
    return old_env


def _restore_proxy_env(old_env: dict[str, str]) -> None:
    proxy_keys = [
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "NO_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "no_proxy",
    ]
    for k in proxy_keys:
        os.environ.pop(k, None)
    os.environ.update(old_env)


async def fetch_bytes(
    url: str,
    *,
    cfg: FetchConfig | None = None,
    accept: str | None = None,
    extra_headers: dict[str, str] | None = None,
    drop_proxy_env: bool = True,
) -> bytes:
    cfg = cfg or FetchConfig()
    headers = {
        "User-Agent": cfg.user_agent,
    }
    if accept:
        headers["Accept"] = accept
    if extra_headers:
        headers.update(extra_headers)

    old_env: dict[str, str] = {}
    if drop_proxy_env:
        old_env = _drop_proxy_env()

    try:
        timeout = httpx.Timeout(
            cfg.timeout_s,
            connect=cfg.connect_timeout_s,
            read=cfg.timeout_s,
        )
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            trust_env=False,
            headers=headers,
        ) as client:
            last_exc: Exception | None = None
            for attempt in range(cfg.retries + 1):
                try:
                    total = 0
                    out = bytearray()
                    async with client.stream("GET", url) as resp:
                        resp.raise_for_status()
                        async for chunk in resp.aiter_bytes():
                            if not chunk:
                                continue
                            total += len(chunk)
                            if total > cfg.max_bytes:
                                raise AdapterError(
                                    f"Response too large (> {cfg.max_bytes} bytes) for {url}"
                                )
                            out.extend(chunk)
                    return bytes(out)
                except (httpx.ReadTimeout, httpx.ConnectError, httpx.RemoteProtocolError) as exc:
                    last_exc = exc
                    if attempt < cfg.retries:
                        await asyncio.sleep(0.5)
                        continue
                    break
                except httpx.HTTPStatusError as exc:
                    raise AdapterError(
                        f"HTTP {exc.response.status_code} for {url}"
                    ) from exc
                except httpx.HTTPError as exc:
                    last_exc = exc
                    break
            raise AdapterError(f"Fetch failed for {url}: {last_exc}") from last_exc
    finally:
        if drop_proxy_env:
            _restore_proxy_env(old_env)


def decode_bytes(
    data: bytes,
    *,
    encoding_candidates: Iterable[str] = ("utf-8", "utf-8-sig", "latin-1"),
) -> str:
    for enc in encoding_candidates:
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")

