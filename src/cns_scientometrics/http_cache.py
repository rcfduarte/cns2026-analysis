"""Disk-cached HTTP GET with polite retry/backoff."""

from pathlib import Path

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

_UA = "cns-scientometrics/0.1 (mailto:rcfduarte@gmail.com)"


@retry(
    wait=wait_exponential(min=1, max=30),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(httpx.HTTPError),
)
def _raw_fetch(url: str, params: dict | None, user_agent: str | None = None) -> str:
    with httpx.Client(timeout=60, headers={"User-Agent": user_agent or _UA}, follow_redirects=True) as c:
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
