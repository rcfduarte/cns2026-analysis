"""NCBI E-utilities helpers (esearch / efetch) over the disk cache."""

import os
from pathlib import Path

from lxml import etree

from .http_cache import cached_get, stable_key

_EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def _key() -> dict:
    k = os.environ.get("NCBI_API_KEY")
    return {"api_key": k} if k else {}


def eutils_esearch(db: str, term: str, retmax: int, cache_dir: Path) -> list[str]:
    params = {"db": db, "term": term, "retmax": str(retmax), "retmode": "xml", **_key()}
    xml = cached_get(
        f"{_EUTILS}/esearch.fcgi", params, f"esearch_{db}_{stable_key(term)}", cache_dir
    )
    root = etree.fromstring(xml.encode("utf-8"))
    return [e.text for e in root.findall(".//IdList/Id")]


def eutils_efetch(db: str, ids: list[str], cache_dir: Path) -> str:
    params = {"db": db, "id": ",".join(ids), "retmode": "xml", **_key()}
    return cached_get(
        f"{_EUTILS}/efetch.fcgi", params, f"efetch_{db}_{stable_key(*ids)}", cache_dir
    )
