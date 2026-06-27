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


# Verified bundle PMCIDs (filled during execution from live supplement pages).
_ERA_C_IDS = {
    2021: ("PMC8687879",),
}

YEARS: dict[int, YearSource] = {}
YEARS |= {y: _mk(y, "A", "cc-by") for y in range(2007, 2016)}
YEARS |= {y: _mk(y, "B", "cc-by") for y in range(2016, 2021)}
YEARS |= {y: _mk(y, "C", "free-to-read", _ERA_C_IDS.get(y, ())) for y in range(2021, 2026)}
