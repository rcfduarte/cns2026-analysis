"""Parse CoSyNe program-book text into per-abstract records + resolve institutions.

The CoSyNe data (from the `cosyne-keywords` repo) is one plain-text program book per
year (`cosyne_YYYY.txt`), produced by `pdftotext`. From 2014 on, the abstract section
is well-structured: each abstract is a block that starts with a poster/talk id
(``1-001.`` / ``T-13.`` / ``I-2.``), followed by the title, author names, e-mail
addresses, numbered affiliation footnotes, then the abstract prose. We split on those
ids and keep only blocks that carry both an e-mail line and a paragraph of prose.

The 2004--2013 books are unstructured OCR (truncated author names, no id/e-mail/
affiliation blocks) and cannot be segmented into per-abstract records, so the
per-abstract views cover **2014--2026**. (The whole-corpus keyword-frequency
comparison already spans all years.)

Affiliation footnotes are bare institution names with no country ("Stanford
University", "EPFL", "Champalimaud Research"), so the corpus's `country_of` (which
reads a trailing country token) does not apply. `country_of_institution()` maps the
institution name to an ISO-3166 alpha-2 country with a curated, country-diagnostic
rule set — high precision on the recognizable institutions that make up the bulk of
CoSyNe, with the unresolved tail reported rather than guessed.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

# Poster sessions are Roman (I-, II-, III-, ...) before 2021 and Arabic ("1-001") after; talks
# are "T-n". Every Roman session must start a block, otherwise sessions II/III are swallowed
# into the block before them (pre-fix, only ~28% of 2014-2020 abstracts were recovered).
_ID_HDR = re.compile(r"^((?:\d+-\d{2,3})|(?:T-\d+)|(?:(?:I{1,3}|IV|VI{0,3}|V)-\d+))\.\s")
_EMAIL = re.compile(r"@")
_PAGEMARK = re.compile(
    r"^(COSYNE\s+\d{4}|Program Summary|Poster Session|Session \d+|"
    r"[TI]?-?\d+\s*[-–]\s*[TI]?-?\d+)$",
    re.I,
)
_PROSE_MIN = 120  # chars — a real abstract paragraph line is at least this long
_PROSE_WRAPPED_MIN = 80  # chars — narrower-wrapped abstracts (e.g. invited talks) ...
_PROSE_WRAPPED_LINES = 3  # ... need at least this many such lines
# Author-index line, e.g. "Zoccolan D., 89, 150" (surname, initials, page numbers).
_INDEX_LINE = re.compile(r"^[^\W\d_][^\d,]{0,40}?\s[A-Z](?:\.[A-Z])*\.,\s*\d+(?:,\s*\d+)*\s*$")
_INDEX_RUN = 5  # this many consecutive index lines mark the start of the author index


def _blocks(lines: list[str]) -> list[list[str]]:
    idx = [i for i, ln in enumerate(lines) if _ID_HDR.match(ln.strip())]
    return [lines[a:b] for a, b in zip(idx, [*idx[1:], len(lines)], strict=False)]


def _has_prose(blk: list[str]) -> bool:
    """A real abstract paragraph: one long line, or several moderately long wrapped lines."""
    lens = [len(ln.strip()) for ln in blk]
    return any(n >= _PROSE_MIN for n in lens) or (
        sum(n >= _PROSE_WRAPPED_MIN for n in lens) >= _PROSE_WRAPPED_LINES
    )


def _trim_author_index(blk: list[str]) -> list[str]:
    """Cut a block where the alphabetical author index begins.

    The last abstract of a book has no following id, so it would otherwise absorb the
    whole author index (1,000+ lines of ``Surname I., page`` entries).
    """
    run, start = 0, 0
    for i, ln in enumerate(blk):
        s = ln.strip()
        if not s or _PAGEMARK.match(s):
            continue
        if _INDEX_LINE.match(s):
            if run == 0:
                start = i
            run += 1
            if run >= _INDEX_RUN:
                return blk[:start]
        else:
            run = 0
    return blk


def _affils(blk: list[str]) -> list[str]:
    """Institution footnote lines that follow the author e-mail block."""
    epos = [i for i, ln in enumerate(blk) if _EMAIL.search(ln)]
    if not epos:
        return []
    out, seen = [], set()
    for ln in blk[epos[-1] + 1 :]:
        s = ln.strip()
        if not s:
            continue
        if len(s) >= _PROSE_MIN:  # abstract prose has begun
            break
        if _PAGEMARK.match(s):
            continue
        s = re.sub(r"^\d{1,2}\s+", "", s).strip()  # drop the footnote number
        if not s or s[0].islower():  # continuation of prose, not an affiliation
            break
        key = s.lower()
        if key not in seen:
            seen.add(key)
            out.append(s)
    return out


def parse_programbook(path: Path) -> list[dict]:
    """Return per-abstract records ``{"text", "affiliations"}`` for one program book."""
    lines = Path(path).read_text(encoding="utf-8", errors="ignore").splitlines()
    recs = []
    for blk in _blocks(lines):
        blk = _trim_author_index(blk)
        if any(_EMAIL.search(ln) for ln in blk) and _has_prose(blk):
            recs.append({"text": "\n".join(blk), "affiliations": _affils(blk)})
    return recs


# Accepted-abstract identifiers. Pre-2021 books number posters by Roman poster session
# ("I-1", "II-1", "III-1"); 2021+ switched to Arabic ("1-001", "2-045"). Talks are "T-n".
_ROMAN_ID = re.compile(r"^(I{1,3}|IV|VI{0,3}|V)-(\d{1,3})\.\s", re.M)
_ARAB_ID = re.compile(r"^(\d)-(\d{2,3})\.\s", re.M)
_TALK_ID = re.compile(r"^T-(\d{1,3})\.\s", re.M)


def accepted_counts(data_dir: Path, min_posters: int = 50) -> pd.DataFrame:
    """Per-year accepted-abstract counts (posters + talks) from program-book ids.

    Counts *distinct* poster/talk identifiers (each id appears in both the table of
    contents and the abstract body, so a set dedupes them). Years whose books are
    unstructured OCR yield no parseable ids and are dropped (``min_posters``).
    Columns: ``year``, ``posters``, ``talks``, ``accepted``.
    """
    rows = []
    for f in sorted(Path(data_dir).glob("cosyne_*.txt")):
        m = re.search(r"(\d{4})", f.name)
        if not m:
            continue
        t = f.read_text(encoding="utf-8", errors="ignore")
        posters = {(a, b) for a, b in (mm.groups() for mm in _ROMAN_ID.finditer(t))}
        posters |= {(a, b) for a, b in (mm.groups() for mm in _ARAB_ID.finditer(t))}
        talks = {mm.group(1) for mm in _TALK_ID.finditer(t)}
        if len(posters) >= min_posters:
            rows.append(
                {
                    "year": int(m.group(1)),
                    "posters": len(posters),
                    "talks": len(talks),
                    "accepted": len(posters) + len(talks),
                }
            )
    return pd.DataFrame(rows).sort_values("year").reset_index(drop=True)


def load_cosyne_dir(data_dir: Path) -> pd.DataFrame:
    """Parse every ``cosyne_YYYY.txt`` in a directory into one DataFrame.

    Columns: ``year``, ``text`` (abstract block), ``affiliations`` (list[str]).
    Years with no segmentable abstracts (the 2004--2013 OCR books) contribute nothing.
    """
    rows = []
    for f in sorted(Path(data_dir).glob("cosyne_*.txt")):
        m = re.search(r"(\d{4})", f.name)
        if not m:
            continue
        year = int(m.group(1))
        for r in parse_programbook(f):
            rows.append({"year": year, "text": r["text"], "affiliations": r["affiliations"]})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------
# Institution -> country (curated, country-diagnostic; first match wins, specific first).
# ---------------------------------------------------------------------------------------
_INSTITUTION_RULES: list[tuple[str, str]] = [
    # --- disambiguations that must precede the general rule ---
    ("new york university shanghai", "CN"),
    ("nyu shanghai", "CN"),
    ("max planck florida", "US"),
    ("washington university", "US"),  # WashU St. Louis (before "university of washington")
    # --- United States ---
    ("harvard", "US"), ("massachusetts institute of technology", "US"), ("\bmit\b", "US"),
    ("stanford", "US"), ("columbia univ", "US"), ("center for theoretical neuroscience", "US"),
    ("zuckerman", "US"), ("princeton", "US"), ("yale", "US"), ("new york university", "US"),
    ("\bnyu\b", "US"), ("center for neural science", "US"),
    ("center for computational neuroscience", "US"), ("carnegie mellon", "US"),
    ("university of washington", "US"), ("university of pittsburgh", "US"),
    ("university of chicago", "US"), ("university of california", "US"), ("\bucla\b", "US"),
    ("\bucsd\b", "US"), ("\bucsf\b", "US"), ("uc berkeley", "US"), ("duke univ", "US"),
    ("university of pennsylvania", "US"), ("northwestern", "US"), ("johns hopkins", "US"),
    ("cold spring harbor", "US"), ("\bcshl\b", "US"), ("boston university", "US"),
    ("georgia institute of technology", "US"), ("georgia tech", "US"),
    ("howard hughes", "US"), ("\bhhmi\b", "US"), ("janelia", "US"), ("flatiron", "US"),
    ("albert einstein", "US"), ("university of minnesota", "US"), ("university of oregon", "US"),
    ("salk institute", "US"), ("emory", "US"), ("brown university", "US"), ("baylor", "US"),
    ("stony brook", "US"), ("university of texas", "US"), ("university of rochester", "US"),
    ("caltech", "US"), ("california institute of technology", "US"),
    ("icahn", "US"), ("mount sinai", "US"), ("cornell", "US"), ("rice university", "US"),
    ("university of southern california", "US"), ("rockefeller", "US"),
    ("university of colorado", "US"), ("university of houston", "US"),
    ("national institutes of health", "US"), ("national institute of mental health", "US"),
    ("\bnih\b", "US"), ("\bnimh\b", "US"), ("rutgers", "US"), ("fordham", "US"),
    ("wu tsai", "US"), ("mcgovern institute", "US"), ("massachusetts general", "US"),
    ("cedars-sinai", "US"), ("dartmouth", "US"), ("brandeis", "US"),
    ("university of notre dame", "US"), ("university of michigan", "US"),
    ("pennsylvania state", "US"), ("penn state", "US"), ("university of maryland", "US"),
    ("oregon health", "US"), ("university of utah", "US"), ("allen institute", "US"),
    ("kavli institute for systems neuroscience", "NO"),  # Kavli @ NTNU (before generic kavli)
    ("kempner", "US"), ("simons foundation", "US"), ("vanderbilt", "US"),
    ("university of wisconsin", "US"), ("university of virginia", "US"),
    ("university of arizona", "US"), ("university of florida", "US"),
    ("new york state", "US"), ("weill cornell", "US"), ("\bnjit\b", "US"),
    ("meta reality labs", "US"), ("meta ai", "US"), ("university of connecticut", "US"),
    ("southern methodist", "US"), ("university of arkansas", "US"),
    ("virginia commonwealth", "US"), ("lehigh university", "US"),
    ("university of massachusetts", "US"), ("indiana university", "US"),
    ("ohio state", "US"), ("case western", "US"), ("georgetown", "US"),
    # --- United Kingdom ---
    ("university college london", "GB"), ("\bucl\b", "GB"), ("university of oxford", "GB"),
    ("university of cambridge", "GB"), ("imperial college", "GB"), ("gatsby", "GB"),
    ("sainsbury wellcome", "GB"), ("king's college london", "GB"), ("king’s college london", "GB"),
    ("\bkcl\b", "GB"), ("francis crick", "GB"), ("university of bristol", "GB"),
    ("university of edinburgh", "GB"), ("university of sheffield", "GB"),
    ("university of manchester", "GB"), ("university of nottingham", "GB"),
    ("university of sussex", "GB"), ("university of birmingham", "GB"),
    ("university of glasgow", "GB"), ("university college dublin", "IE"),
    ("deepmind", "GB"),
    # --- Switzerland ---
    ("epfl", "CH"), ("ecole polytechnique federale de lausanne", "CH"),
    ("école polytechnique fédérale de lausanne", "CH"), ("eth zurich", "CH"),
    ("university of geneva", "CH"), ("university of bern", "CH"), ("university of zurich", "CH"),
    ("university of basel", "CH"), ("friedrich miescher", "CH"),
    ("institute of neuroinformatics", "CH"), ("brain mind institute", "CH"),
    ("ophthalmology basel", "CH"),
    # --- Germany ---
    ("tubingen", "DE"), ("tuebingen", "DE"), ("university of bonn", "DE"),
    ("technical university of munich", "DE"), ("technische universitat munchen", "DE"),
    ("ludwig maximilian", "DE"), ("frankfurt institute", "DE"), ("ernst strungmann", "DE"),
    ("humboldt", "DE"), ("technische universitat berlin", "DE"), ("gottingen", "DE"),
    ("goettingen", "DE"), ("johannes gutenberg", "DE"), ("mainz", "DE"), ("bernstein", "DE"),
    ("\brwth\b", "DE"), ("european neuroscience institute", "DE"),
    ("julich", "DE"), ("jülich", "DE"), ("inm-6", "DE"), ("university of bremen", "DE"),
    ("tu berlin", "DE"), ("charite", "DE"), ("charité", "DE"), ("justus liebig", "DE"),
    ("giessen", "DE"), ("university of freiburg", "DE"), ("heidelberg", "DE"),
    ("university of hamburg", "DE"), ("dresden", "DE"), ("caesar", "DE"),
    ("max planck florida", "US"), ("max planck", "DE"),
    # --- Portugal ---
    ("champalimaud", "PT"),
    # --- France ---
    ("ecole normale superieure", "FR"), ("école normale supérieure", "FR"),
    ("sorbonne", "FR"), ("institut pasteur", "FR"), ("\bcnrs\b", "FR"), ("\binserm\b", "FR"),
    ("aix-marseille", "FR"), ("university of bordeaux", "FR"), ("college de france", "FR"),
    ("neurospin", "FR"),
    # --- Israel ---
    ("weizmann", "IL"), ("hebrew university", "IL"), ("technion", "IL"),
    ("tel aviv", "IL"), ("bar-ilan", "IL"), ("bar ilan", "IL"), ("ben-gurion", "IL"),
    ("ben gurion", "IL"),
    # --- Canada ---
    ("mcgill", "CA"), ("universite de montreal", "CA"), ("université de montréal", "CA"),
    ("university of montreal", "CA"), ("\bmila\b", "CA"), ("university of toronto", "CA"),
    ("york university", "CA"), ("university of ottawa", "CA"), ("western university", "CA"),
    ("western ontario", "CA"), ("universite laval", "CA"), ("université laval", "CA"),
    ("university of calgary", "CA"), ("british columbia", "CA"), ("university of waterloo", "CA"),
    ("vector institute", "CA"), ("montreal neurological", "CA"), ("queen's university", "CA"),
    # --- Austria ---
    ("science and technology austria", "AT"), ("\bista\b", "AT"), ("ist, austria", "AT"),
    ("ist austria", "AT"), ("central european university", "AT"), ("university of vienna", "AT"),
    ("medical university of vienna", "AT"),
    # --- Japan ---
    ("riken", "JP"), ("okinawa", "JP"), ("\boist\b", "JP"), ("university of tokyo", "JP"),
    ("kyoto university", "JP"), ("osaka university", "JP"), ("doshisha", "JP"), ("\batr\b", "JP"),
    # --- China ---
    ("tsinghua", "CN"), ("peking university", "CN"), ("chinese academy of sciences", "CN"),
    ("shanghai jiao tong", "CN"), ("beijing normal", "CN"),
    ("university of science and technology of china", "CN"), ("fudan", "CN"),
    ("zhejiang university", "CN"), ("shanghaitech", "CN"), ("westlake university", "CN"),
    # --- South Korea ---
    ("kaist", "KR"), ("korea advanced institute", "KR"), ("seoul national", "KR"),
    ("sungkyunkwan", "KR"), ("\bkist\b", "KR"), ("korea university", "KR"),
    # --- rest of Europe ---
    ("pompeu fabra", "ES"), ("recerca matematica", "ES"), ("autonomous university of madrid", "ES"),
    ("universidad autonoma de madrid", "ES"), ("cajal institute", "ES"),
    ("sissa", "IT"), ("international school for advanced studies", "IT"),
    ("university of padova", "IT"), ("university of padua", "IT"),
    ("istituto italiano di tecnologia", "IT"), ("istituto superiore di sanita", "IT"),
    ("scuola normale superiore", "IT"), ("university of trento", "IT"),
    ("university of amsterdam", "NL"), ("radboud", "NL"), ("donders", "NL"),
    ("vrije universiteit amsterdam", "NL"), ("university of groningen", "NL"),
    ("erasmus", "NL"), ("delft", "NL"),
    ("norwegian university of science", "NO"), ("\bntnu\b", "NO"), ("university of oslo", "NO"),
    ("karolinska", "SE"), ("kth royal", "SE"), ("\bkth\b", "SE"), ("university of leuven", "BE"),
    ("\bku leuven\b", "BE"), ("university of liege", "BE"), ("université de liège", "BE"),
    ("université libre de bruxelles", "BE"), ("catholique de louvain", "BE"),
    ("idibaps", "ES"), ("university of barcelona", "ES"), ("aalto", "FI"), ("university of helsinki", "FI"),
    ("university of copenhagen", "DK"), ("aarhus", "DK"), ("eotvos", "HU"),
    ("university of ljubljana", "SI"), ("champalimaud", "PT"),
    # --- rest of world ---
    ("indian institute of science", "IN"), ("indian institute of technology", "IN"),
    ("\biisc\b", "IN"), ("national university of singapore", "SG"),
    ("nanyang technological", "SG"), ("\ba\\*star\b", "SG"),
    ("universidad nacional autonoma de mexico", "MX"), ("\bunam\b", "MX"),
    ("university of melbourne", "AU"), ("university of sydney", "AU"),
    ("monash", "AU"), ("university of queensland", "AU"), ("australian national", "AU"),
    ("university of sao paulo", "BR"), ("universidade de sao paulo", "BR"),
    # --- city/country fallbacks (last, low-specificity) ---
    ("\bberlin\b", "DE"), ("\bmunich\b", "DE"), ("\bvienna\b", "AT"), ("\bzurich\b", "CH"),
    ("\blausanne\b", "CH"), ("\bgeneva\b", "CH"), ("\bparis\b", "FR"), ("\btokyo\b", "JP"),
    ("\bbeijing\b", "CN"), ("\bshanghai\b", "CN"), ("\bseoul\b", "KR"),
    ("\bamsterdam\b", "NL"), ("\bsingapore\b", "SG"),
]
# The rule strings above are written with ``\b`` word-boundaries but are not raw
# literals, so Python has already turned each ``\b`` into a backspace (0x08); restore
# it to a regex word-boundary before compiling.
_COMPILED_RULES = [(re.compile(p.replace("\b", r"\b"), re.I), iso) for p, iso in _INSTITUTION_RULES]


def country_of_institution(affiliation: str) -> str | None:
    """ISO alpha-2 country for a bare CoSyNe institution string, or ``None``."""
    for pat, iso in _COMPILED_RULES:
        if pat.search(affiliation):
            return iso
    return None


def record_countries_by_institution(affiliations: list[str]) -> list[str]:
    """Distinct ISO countries for one abstract, resolved institution-by-institution."""
    out: list[str] = []
    for a in affiliations:
        c = country_of_institution(a)
        if c and c not in out:
            out.append(c)
    return out
