"""Disk-cached HTTP GET with polite retry/backoff."""

import hashlib
from pathlib import Path

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

_UA = "cns-scientometrics/0.1 (mailto:rcfduarte@gmail.com)"


def stable_key(*parts: str) -> str:
    """Deterministic cache key across processes (builtin hash() is salted per run)."""
    return hashlib.md5(" ".join(parts).encode("utf-8")).hexdigest()[:16]


@retry(
    wait=wait_exponential(min=1, max=30),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(httpx.HTTPError),
)
def _raw_fetch(url: str, params: dict | None, user_agent: str | None = None) -> str:
    headers = {"User-Agent": user_agent or _UA}
    with httpx.Client(timeout=60, headers=headers, follow_redirects=True) as c:
        r = c.get(url, params=params)
        r.raise_for_status()
        return r.text


def cached_get(
    url: str,
    params: dict | None,
    cache_key: str,
    cache_dir: Path,
    user_agent: str | None = None,
) -> str:
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    f = cache_dir / f"{cache_key}.cache"
    if f.exists():
        return f.read_text(encoding="utf-8")
    text = _raw_fetch(url, params, user_agent)
    f.write_text(text, encoding="utf-8")
    return text
