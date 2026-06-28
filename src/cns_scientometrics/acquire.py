"""Acquisition orchestrator — routes each year to its era-specific parser."""

from pathlib import Path

from .bmc_html import acquire_bmc_supplement
from .ncbi import eutils_efetch, eutils_esearch
from .parse_jats import parse_era_a_articleset, split_bundle, split_flat_paragraphs
from .parse_pdf import parse_pdf, pdf_to_text
from .schema import AbstractRecord
from .sources import BMC_HTML_FALLBACK, JCN_PDF_SOURCES, YEARS, YearSource

_BATCH = 100
_PDF_DIR = Path("data/pdfs")
_PDF_TEXT_DIR = Path("data/pdftext")


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
    if year in JCN_PDF_SOURCES:
        _, fname = JCN_PDF_SOURCES[year]
        pdf = _PDF_DIR / fname
        if not pdf.exists():
            return []  # PDF not supplied — degrade gracefully
        text = pdf_to_text(pdf, _PDF_TEXT_DIR)
        return parse_pdf(text, year, src.meeting_no)
    if year in BMC_HTML_FALLBACK:
        return acquire_bmc_supplement(BMC_HTML_FALLBACK[year], year, src.meeting_no, cache_dir)
    if src.era == "A":
        recs: list[AbstractRecord] = []
        ids = _era_a_pmcids(year, cache_dir)
        for i in range(0, len(ids), _BATCH):
            batch = ids[i : i + _BATCH]
            xml = eutils_efetch("pmc", batch, cache_dir).encode("utf-8")
            for rec in parse_era_a_articleset(xml, year, src.meeting_no):
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
