"""Best-effort affiliation → institution/country resolution via ROR."""

import json
from pathlib import Path

from .http_cache import cached_get, stable_key
from .schema import AbstractRecord

_ROR = "https://api.ror.org/organizations"


def resolve_affiliation(aff: str, cache_dir: Path) -> tuple[str | None, str | None]:
    """Return (institution_name, ISO country code) for a raw affiliation string.

    Best-effort: returns (None, None) on any miss or error.
    """
    try:
        txt = cached_get(_ROR, {"affiliation": aff}, f"ror_{stable_key(aff)}", cache_dir)
        data = json.loads(txt)
        items = data.get("items", [])
        chosen = next((i for i in items if i.get("chosen")), items[0] if items else None)
        if not chosen:
            return None, None
        org = chosen["organization"]
        return org.get("name"), (org.get("country", {}) or {}).get("country_code")
    except Exception:
        return None, None


def enrich_record(rec: AbstractRecord, cache_dir: Path) -> AbstractRecord:
    insts: list[str] = []
    ctys: list[str] = []
    for aff in rec.affiliations:
        name, cc = resolve_affiliation(aff, cache_dir)
        if name and name not in insts:
            insts.append(name)
        if cc and cc not in ctys:
            ctys.append(cc)
    return rec.model_copy(update={"institutions": insts, "countries": ctys})
