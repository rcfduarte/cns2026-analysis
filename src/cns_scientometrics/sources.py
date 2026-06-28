"""Per-year venue/era routing table for CNS meeting abstracts (spec §2).

Meeting number = year - 1991 (2007 = 16th ... 2024 = 33rd).
Era A 2007-2015 (BMC, one article per abstract, CC-BY);
Era B 2016-2020 (BMC, bundled Part articles, CC-BY);
Era C 2021-2025 (J. Comp. Neurosci., one article per meeting, free-to-read).

Era B/C `identifiers` are bundle PMCIDs filled in at execution after verifying
against the live supplement pages. Era A identifiers stay empty (resolved by
esearch at acquisition time).
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class YearSource:
    year: int
    meeting_no: int
    era: str
    license: str
    identifiers: tuple[str, ...] = field(default=())


def _mk(year: int, era: str, license: str, ids: tuple[str, ...] = ()) -> YearSource:
    return YearSource(year, year - 1991, era, license, tuple(ids))


# Verified bundle PMCIDs (resolved 2026-06-27 from PMC; see docs/notes/build-log).
# Era B = BMC bundled "Part" articles (<sec>-structured); one or more per year.
_ERA_B_IDS = {
    2016: ("PMC5001212",),
    2017: ("PMC5592436", "PMC5592442", "PMC5592441"),  # Parts 1, 2, 3
    2018: ("PMC6205781", "PMC6205774"),  # Parts One, Two
    2019: ("PMC6854655",),
    2020: ("PMC7751124",),
}
# Era C = JCN single-article-per-meeting (flat-paragraph). 2021 is open in PMC; 2022-2025
# are Springer-paywalled (Europe PMC inPMC=N, isOA=N) — ingested from user-supplied PDFs.
_ERA_C_IDS = {
    2021: ("PMC8687879",),
}

# JCN supplement DOIs for the paywalled years, with the expected drop-in PDF filename
# under data/pdfs/. Bodies are extracted from the PDF (same flat K1/F1/P### structure).
JCN_PDF_SOURCES = {
    2022: ("10.1007/s10827-022-00841-9", "cns2022.pdf"),
    2023: ("10.1007/s10827-024-00871-5", "cns2023.pdf"),
    2024: ("10.1007/s10827-024-00889-9", "cns2024.pdf"),
    2025: ("10.1007/s10827-025-00915-4", "cns2025.pdf"),
}

# Years whose abstracts are NOT in PMC — fetched from BMC supplement HTML instead.
BMC_HTML_FALLBACK = {
    2008: "https://bmcneurosci.biomedcentral.com/articles/supplements/volume-9-supplement-1",
    2009: "https://bmcneurosci.biomedcentral.com/articles/supplements/volume-10-supplement-1",
}

YEARS: dict[int, YearSource] = {}
YEARS |= {y: _mk(y, "A", "cc-by") for y in range(2007, 2016)}
YEARS |= {y: _mk(y, "B", "cc-by", _ERA_B_IDS.get(y, ())) for y in range(2016, 2021)}
YEARS |= {y: _mk(y, "C", "free-to-read", _ERA_C_IDS.get(y, ())) for y in range(2021, 2026)}
