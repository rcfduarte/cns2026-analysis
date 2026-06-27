"""Acquisition orchestrator — routes each year to its era-specific parser."""

from pathlib import Path

from .ncbi import eutils_efetch, eutils_esearch
from .parse_jats import parse_era_a_article, split_bundle, split_flat_paragraphs
from .schema import AbstractRecord
from .sources import YEARS, YearSource


def _era_a_pmcids(year: int, cache_dir: Path) -> list[str]:
    term = f'"BMC Neurosci"[Journal] AND {year}[PDAT]'
    return eutils_esearch("pmc", term, 1000, cache_dir)


def _parse_bundle(xml: bytes, src: YearSource) -> list[AbstractRecord]:
    """Era B/C bundle: try <sec> splitting, fall back to flat-paragraph segmenting."""
    url = src.identifiers[0] if src.identifiers else ""
    recs = split_bundle(xml, src.year, src.meeting_no, src.era, src.license, url)
    if not recs:
        recs = split_flat_paragraphs(xml, src.year, src.meeting_no, src.era, src.license, url)
    return recs


def acquire_year(year: int, cache_dir: Path) -> list[AbstractRecord]:
    src = YEARS[year]
    if src.era == "A":
        recs: list[AbstractRecord] = []
        for pmcid in _era_a_pmcids(year, cache_dir):
            xml = eutils_efetch("pmc", [pmcid], cache_dir).encode("utf-8")
            try:
                rec = parse_era_a_article(xml, year, src.meeting_no)
            except Exception:
                continue
            if rec.type != "frontmatter" and rec.title:
                recs.append(rec)
        return recs
    recs = []
    for pmcid in src.identifiers:
        xml = eutils_efetch("pmc", [pmcid], cache_dir).encode("utf-8")
        recs += _parse_bundle(xml, src)
    return recs


def acquire_all(years, cache_dir: Path) -> list[AbstractRecord]:
    out: list[AbstractRecord] = []
    for y in years:
        out += acquire_year(y, cache_dir)
    return out
