# CNS Corpus Foundation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible, cached, era-aware pipeline that turns CNS/OCNS meeting abstracts (2007–2024/25) into one clean canonical per-abstract dataset (Parquet + JSONL) plus a QA report.

**Architecture:** Three era-specific acquisition paths (PMC individual-DOI, BMC bundled Part-articles, JCN single-article) feed a single JATS-aware parser that emits a validated canonical record. An author/affiliation normalizer enriches records via ROR/OpenAlex (best-effort). A corpus assembler writes Parquet + JSONL + a per-year QA report. Parsing is tested on saved JATS fixtures (no network); live acquisition is cached idempotently to disk.

**Tech Stack:** Python 3.11+, `httpx` (HTTP), `lxml` (JATS XML), `pydantic` v2 (schema), `pandas` + `pyarrow` (Parquet), `tenacity` (retry/backoff), `pytest`. ROR/OpenAlex via REST.

## Global Constraints

- Python floor: **3.11** (`target-version = "py311"`).
- Ruff: line-length **100**, rules `E,W,F,I,B,UP,SIM,RUF`; ignore `E501,B008,RUF001,RUF002,RUF003`; double quotes.
- `.gitignore` MUST keep secret patterns (`.env`, `.mcp.json`, `credentials.json`, `*.key`, `*.pem`, `secrets/`) and ignore `data/` caches + corpus outputs.
- NCBI politeness: ≤3 req/s without API key, ≤10 with; exponential backoff on 429/5xx; set a descriptive `User-Agent` with contact email `rcfduarte@gmail.com`.
- Era licensing carried on every record: Era A (2007–2015) = `cc-by`; Era B (2016–2020) = `cc-by`; Era C (2021–2025) = `free-to-read` (do not redistribute raw body text downstream).
- All external responses cached to `data/raw/` keyed by stable id; pipeline re-runs hit cache, not network.
- Package import root: `cns_scientometrics`.

---

### Task 1: Project scaffold + canonical record schema

**Files:**
- Create: `pyproject.toml`, `src/cns_scientometrics/__init__.py`, `src/cns_scientometrics/schema.py`
- Create: `.github/workflows/lint.yml`
- Test: `tests/test_schema.py`
- Modify: `.gitignore` (append `data/` ignores)

**Interfaces:**
- Produces: `Author(raw_name: str, given: str|None, family: str|None, openalex_id: str|None)`; `AbstractRecord` pydantic model with fields per spec §5 Layer 2: `abstract_id, year, meeting_no, type, title, authors: list[Author], affiliations: list[str], institutions: list[str], countries: list[str], body: dict[str,str|None] (keys background, methods, results, full), references: list[str], figure_caption: str|None, doi: str|None, pmcid: str|None, era: str, license: str, source_url: str`. `type` ∈ {oral, poster, keynote, frontmatter}. `era` ∈ {A,B,C}.
- Produces: `AbstractRecord.model_validate(...)` and `.model_dump()`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_schema.py
import pytest
from cns_scientometrics.schema import AbstractRecord, Author

def test_minimal_record_validates():
    rec = AbstractRecord(
        abstract_id="2015-P173", year=2015, meeting_no=24, type="poster",
        title="A test abstract", authors=[Author(raw_name="Jane Doe", family="Doe", given="Jane")],
        affiliations=["Dept X, Univ Y"], institutions=[], countries=[],
        body={"background": "bg", "methods": "m", "results": "r", "full": "bg m r"},
        references=[], figure_caption=None, doi="10.1186/x", pmcid="PMC4697476",
        era="A", license="cc-by", source_url="https://example.org",
    )
    assert rec.abstract_id == "2015-P173"
    assert rec.body["full"] == "bg m r"

def test_invalid_type_rejected():
    with pytest.raises(ValueError):
        AbstractRecord(
            abstract_id="x", year=2015, meeting_no=24, type="banana", title="t",
            authors=[], affiliations=[], institutions=[], countries=[],
            body={"background": None, "methods": None, "results": None, "full": "t"},
            references=[], figure_caption=None, doi=None, pmcid=None,
            era="A", license="cc-by", source_url="u",
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_schema.py -v`
Expected: FAIL with `ModuleNotFoundError: cns_scientometrics.schema`

- [ ] **Step 3: Write scaffold + implementation**

Create `pyproject.toml` with `[build-system]` (hatchling), `[project]` (name `cns-scientometrics`, deps: `httpx`, `lxml`, `pydantic>=2`, `pandas`, `pyarrow`, `tenacity`; optional `dev`: `pytest`, `ruff`), `[tool.ruff]` per Global Constraints (copy from `~/.claude/templates/python-project/pyproject-ruff-block.toml`), and `[tool.hatch.build.targets.wheel] packages = ["src/cns_scientometrics"]`.

```python
# src/cns_scientometrics/schema.py
from typing import Literal
from pydantic import BaseModel

class Author(BaseModel):
    raw_name: str
    given: str | None = None
    family: str | None = None
    openalex_id: str | None = None

class AbstractRecord(BaseModel):
    abstract_id: str
    year: int
    meeting_no: int
    type: Literal["oral", "poster", "keynote", "frontmatter"]
    title: str
    authors: list[Author] = []
    affiliations: list[str] = []
    institutions: list[str] = []
    countries: list[str] = []
    body: dict[str, str | None]
    references: list[str] = []
    figure_caption: str | None = None
    doi: str | None = None
    pmcid: str | None = None
    era: Literal["A", "B", "C"]
    license: Literal["cc-by", "free-to-read"]
    source_url: str
```

Append to `.gitignore`: `data/raw/`, `data/corpus/`, `data/cache/`.

Copy `.github/workflows/lint.yml` from `~/.claude/templates/python-project/.github/workflows/lint.yml`.

- [ ] **Step 4: Install dev + run test to verify it passes**

Run: `cd /home/neuro/repos/cns-scientometrics && pip install -e ".[dev]" && pytest tests/test_schema.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: project scaffold + canonical AbstractRecord schema"
```

---

### Task 2: Cached HTTP client + NCBI E-utilities helpers

**Files:**
- Create: `src/cns_scientometrics/http_cache.py`, `src/cns_scientometrics/ncbi.py`
- Test: `tests/test_http_cache.py`, `tests/test_ncbi.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `cached_get(url: str, params: dict|None, cache_key: str, cache_dir: Path) -> str` (returns text; writes/reads `cache_dir/<cache_key>.cache`). `eutils_esearch(db: str, term: str, retmax: int) -> list[str]` (returns id list). `eutils_efetch(db: str, ids: list[str]) -> str` (returns XML text). Both use `cached_get` + `tenacity` retry; honor `NCBI_API_KEY` env if present.

- [ ] **Step 1: Write the failing test (cache hit avoids second network call)**

```python
# tests/test_http_cache.py
from pathlib import Path
from cns_scientometrics.http_cache import cached_get

def test_cache_returns_stored_without_refetch(tmp_path, monkeypatch):
    calls = {"n": 0}
    def fake_fetch(url, params):
        calls["n"] += 1
        return "<xml>ok</xml>"
    monkeypatch.setattr("cns_scientometrics.http_cache._raw_fetch", fake_fetch)
    a = cached_get("http://x", None, "k1", tmp_path)
    b = cached_get("http://x", None, "k1", tmp_path)
    assert a == b == "<xml>ok</xml>"
    assert calls["n"] == 1  # second call served from disk
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_http_cache.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement**

```python
# src/cns_scientometrics/http_cache.py
import os
from pathlib import Path
import httpx
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

_UA = "cns-scientometrics/0.1 (mailto:rcfduarte@gmail.com)"

@retry(wait=wait_exponential(min=1, max=30), stop=stop_after_attempt(5),
       retry=retry_if_exception_type(httpx.HTTPError))
def _raw_fetch(url: str, params: dict | None) -> str:
    with httpx.Client(timeout=60, headers={"User-Agent": _UA}) as c:
        r = c.get(url, params=params)
        r.raise_for_status()
        return r.text

def cached_get(url: str, params: dict | None, cache_key: str, cache_dir: Path) -> str:
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    f = cache_dir / f"{cache_key}.cache"
    if f.exists():
        return f.read_text(encoding="utf-8")
    text = _raw_fetch(url, params)
    f.write_text(text, encoding="utf-8")
    return text
```

```python
# src/cns_scientometrics/ncbi.py
import os
from pathlib import Path
from lxml import etree
from .http_cache import cached_get

_EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

def _key() -> dict:
    k = os.environ.get("NCBI_API_KEY")
    return {"api_key": k} if k else {}

def eutils_esearch(db: str, term: str, retmax: int, cache_dir: Path) -> list[str]:
    params = {"db": db, "term": term, "retmax": str(retmax), "retmode": "xml", **_key()}
    xml = cached_get(f"{_EUTILS}/esearch.fcgi", params, f"esearch_{db}_{abs(hash(term))}", cache_dir)
    root = etree.fromstring(xml.encode("utf-8"))
    return [e.text for e in root.findall(".//IdList/Id")]

def eutils_efetch(db: str, ids: list[str], cache_dir: Path) -> str:
    params = {"db": db, "id": ",".join(ids), "retmode": "xml", **_key()}
    return cached_get(f"{_EUTILS}/efetch.fcgi", params, f"efetch_{db}_{abs(hash(tuple(ids)))}", cache_dir)
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/test_http_cache.py -v`
Expected: PASS

- [ ] **Step 5: Add a live smoke test for NCBI (network, opt-in)**

```python
# tests/test_ncbi.py
import os, pytest
from cns_scientometrics.ncbi import eutils_esearch

@pytest.mark.network
def test_esearch_finds_bmc_2015(tmp_path):
    ids = eutils_esearch("pmc", '"BMC Neurosci"[Journal] AND 2015[PDAT]', 600, tmp_path)
    assert len(ids) > 100  # CNS*2015 supplement alone is ~420 abstracts
```

Add to `pyproject.toml`: `[tool.pytest.ini_options] markers = ["network: hits live external APIs"]`. Default test runs use `-m "not network"`.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: cached HTTP client + NCBI E-utilities helpers"
```

---

### Task 3: JATS parser — Era A (one abstract per article)

**Files:**
- Create: `src/cns_scientometrics/parse_jats.py`
- Create: `tests/fixtures/era_a_P173.xml` (saved real PMC JATS for PMC4697476; fetch once and commit a trimmed copy)
- Test: `tests/test_parse_jats.py`

**Interfaces:**
- Consumes: `AbstractRecord`, `Author` from Task 1.
- Produces: `parse_era_a_article(xml: bytes, year: int, meeting_no: int) -> AbstractRecord`. Extracts title from `<article-title>`, authors from `<contrib contrib-type="author">` (`<surname>`/`<given-names>`), affiliations from `<aff>`, body sections by `<sec>` heading (Background/Methods/Results) with `full` = concatenation, abstract type + id from the DOI suffix (`...-P173` → poster, id `P173`; `...-O5` → oral; `...-A1` → frontmatter), `doi`/`pmcid` from `<article-id>`.

- [ ] **Step 1: Create the fixture**

Run once and trim to a single article element:
```bash
python -c "from cns_scientometrics.ncbi import eutils_efetch; from pathlib import Path; \
print(eutils_efetch('pmc', ['PMC4697476'], Path('data/cache')))" > tests/fixtures/era_a_P173.xml
```
Verify the file contains `<article-title>`, `<contrib`, `<sec>` and a `<article-id pub-id-type="doi">...P173</article-id>`.

- [ ] **Step 2: Write the failing test**

```python
# tests/test_parse_jats.py
from pathlib import Path
from cns_scientometrics.parse_jats import parse_era_a_article

def test_parse_era_a_extracts_core_fields():
    xml = Path("tests/fixtures/era_a_P173.xml").read_bytes()
    rec = parse_era_a_article(xml, year=2015, meeting_no=24)
    assert rec.type == "poster"
    assert rec.abstract_id == "2015-P173"
    assert rec.title
    assert len(rec.authors) >= 1
    assert rec.body["full"]
    assert rec.era == "A" and rec.license == "cc-by"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_parse_jats.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 4: Implement `parse_jats.py`**

```python
# src/cns_scientometrics/parse_jats.py
import re
from lxml import etree
from .schema import AbstractRecord, Author

_SEC_MAP = {"background": "background", "methods": "methods", "results": "results"}

def _text(el) -> str:
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip() if el is not None else ""

def _classify(doi: str | None) -> tuple[str, str]:
    # returns (type, code) from DOI suffix like ...-16-S1-P173 / -O5 / -A1
    m = re.search(r"-([OPA])(\d+)$", doi or "")
    if not m:
        return "poster", "P0"
    kind = {"O": "oral", "P": "poster", "A": "frontmatter"}[m.group(1)]
    return kind, f"{m.group(1)}{m.group(2)}"

def parse_era_a_article(xml: bytes, year: int, meeting_no: int) -> AbstractRecord:
    root = etree.fromstring(xml) if isinstance(xml, bytes) else etree.fromstring(xml.encode())
    art = root.find(".//article") if root.tag != "article" else root
    art = art if art is not None else root
    doi = _text(art.find('.//article-id[@pub-id-type="doi"]')) or None
    pmcid = _text(art.find('.//article-id[@pub-id-type="pmcid"]')) or None
    if pmcid and not pmcid.startswith("PMC"):
        pmcid = f"PMC{pmcid}"
    title = _text(art.find(".//title-group/article-title"))
    authors = []
    for c in art.findall('.//contrib[@contrib-type="author"]'):
        sur, giv = _text(c.find(".//surname")), _text(c.find(".//given-names"))
        if sur or giv:
            authors.append(Author(raw_name=f"{giv} {sur}".strip(), given=giv or None, family=sur or None))
    affs = [_text(a) for a in art.findall(".//aff") if _text(a)]
    body = {"background": None, "methods": None, "results": None, "full": None}
    for sec in art.findall(".//body//sec") + art.findall(".//abstract//sec"):
        head = _text(sec.find("./title")).lower()
        for key in _SEC_MAP:
            if key in head:
                body[key] = _text(sec)
    full = " ".join(v for v in (body["background"], body["methods"], body["results"]) if v)
    if not full:  # fall back to whole abstract/body
        full = _text(art.find(".//abstract")) or _text(art.find(".//body"))
    body["full"] = full or title
    kind, code = _classify(doi)
    refs = [_text(r) for r in art.findall(".//ref-list//ref")]
    fig = art.find(".//fig//caption")
    return AbstractRecord(
        abstract_id=f"{year}-{code}", year=year, meeting_no=meeting_no, type=kind,
        title=title, authors=authors, affiliations=affs, institutions=[], countries=[],
        body=body, references=refs, figure_caption=_text(fig) or None,
        doi=doi, pmcid=pmcid, era="A", license="cc-by",
        source_url=f"https://doi.org/{doi}" if doi else "",
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_parse_jats.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: Era A JATS parser (one abstract per article) + fixture"
```

---

### Task 4: Bundled splitter — Era B & C (many abstracts per article)

**Files:**
- Modify: `src/cns_scientometrics/parse_jats.py`
- Create: `tests/fixtures/era_c_bundle_trimmed.xml` (trimmed real JCN/PMC bundle containing ≥2 abstract `<sec>` blocks; e.g. from PMC8687879)
- Test: `tests/test_parse_bundle.py`

**Interfaces:**
- Consumes: `AbstractRecord`, `Author`, `_text`, `_classify`.
- Produces: `split_bundle(xml: bytes, year: int, meeting_no: int, era: str, license: str, source_url: str) -> list[AbstractRecord]`. Each top-level abstract `<sec>` (one with an `<title>` and a body) becomes one record. Abstract id from an internal label (`P###`/`O###`) if present in the section title, else sequential `B###`.

- [ ] **Step 1: Create fixture** — fetch PMC8687879 via `eutils_efetch('pmc', ['PMC8687879'], Path('data/cache'))`, save, then trim to the first 2–3 abstract `<sec>` elements (keep the surrounding `<body>`).

- [ ] **Step 2: Write the failing test**

```python
# tests/test_parse_bundle.py
from pathlib import Path
from cns_scientometrics.parse_jats import split_bundle

def test_split_bundle_yields_multiple_records():
    xml = Path("tests/fixtures/era_c_bundle_trimmed.xml").read_bytes()
    recs = split_bundle(xml, year=2021, meeting_no=30, era="C",
                        license="free-to-read", source_url="https://doi.org/10.1007/s10827-021-00801-9")
    assert len(recs) >= 2
    assert all(r.era == "C" and r.license == "free-to-read" for r in recs)
    assert all(r.body["full"] for r in recs)
    assert all(r.year == 2021 for r in recs)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_parse_bundle.py -v`
Expected: FAIL with `ImportError: cannot import name 'split_bundle'`

- [ ] **Step 4: Implement `split_bundle` in `parse_jats.py`**

```python
def _abstract_sections(art):
    body = art.find(".//body")
    if body is None:
        return []
    secs = body.findall("./sec")
    # an abstract section has a title and at least one paragraph
    return [s for s in secs if s.find("./title") is not None and s.findall(".//p")]

def split_bundle(xml: bytes, year: int, meeting_no: int, era: str,
                 license: str, source_url: str) -> list[AbstractRecord]:
    root = etree.fromstring(xml) if isinstance(xml, bytes) else etree.fromstring(xml.encode())
    art = root.find(".//article") or root
    out = []
    for i, sec in enumerate(_abstract_sections(art), start=1):
        title = _text(sec.find("./title"))
        m = re.search(r"\b([OP])\s?-?(\d+)\b", title)
        if m:
            kind = {"O": "oral", "P": "poster"}[m.group(1)]
            code = f"{m.group(1)}{m.group(2)}"
        else:
            kind, code = "poster", f"B{i:04d}"
        authors = []
        for c in sec.findall('.//contrib[@contrib-type="author"]'):
            sur, giv = _text(c.find(".//surname")), _text(c.find(".//given-names"))
            if sur or giv:
                authors.append(Author(raw_name=f"{giv} {sur}".strip(), given=giv or None, family=sur or None))
        affs = [_text(a) for a in sec.findall(".//aff") if _text(a)]
        full = _text(sec)
        out.append(AbstractRecord(
            abstract_id=f"{year}-{code}", year=year, meeting_no=meeting_no, type=kind,
            title=title, authors=authors, affiliations=affs, institutions=[], countries=[],
            body={"background": None, "methods": None, "results": None, "full": full},
            references=[], figure_caption=None, doi=None, pmcid=None,
            era=era, license=license, source_url=source_url,
        ))
    return out
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_parse_bundle.py -v`
Expected: PASS. (If the real bundle nests author metadata differently, adjust the contrib/aff XPath against the fixture — the section-splitting contract stays the same.)

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: bundled Era B/C splitter (many abstracts per article)"
```

---

### Task 5: Acquisition orchestrator + era routing table

**Files:**
- Create: `src/cns_scientometrics/sources.py` (the per-year venue/era table), `src/cns_scientometrics/acquire.py`
- Test: `tests/test_sources.py`, `tests/test_acquire.py`

**Interfaces:**
- Consumes: `eutils_esearch`, `eutils_efetch`, `parse_era_a_article`, `split_bundle`.
- Produces: `YEARS: dict[int, YearSource]` where `YearSource(year, meeting_no, era, license, identifiers)` — Era A `identifiers` resolved at run time via esearch; Era B `identifiers` = list of Part-article PMCIDs; Era C `identifiers` = single bundle PMCID. `acquire_year(year: int, cache_dir: Path) -> list[AbstractRecord]` routes by era and returns parsed records. `acquire_all(years, cache_dir) -> list[AbstractRecord]`.

- [ ] **Step 1: Write the failing test for the routing table**

```python
# tests/test_sources.py
from cns_scientometrics.sources import YEARS

def test_year_table_covers_all_eras():
    assert YEARS[2015].era == "A" and YEARS[2015].license == "cc-by"
    assert YEARS[2018].era == "B"
    assert YEARS[2021].era == "C" and YEARS[2021].license == "free-to-read"
    assert YEARS[2015].meeting_no == 24
    # span 2007..2024 present
    assert set(range(2007, 2025)).issubset(set(YEARS))
```

- [ ] **Step 2: Run to verify fail**

Run: `pytest tests/test_sources.py -v`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: Implement `sources.py`**

Encode the verified table (spec §2). Meeting numbers: 2007=16 … 2024=33 (meeting_no = year − 1991). Era A: 2007–2015; Era B: 2016–2020; Era C: 2021–2025. Era B/C identifiers are the known bundle PMCIDs (fill from the live supplement pages during execution; leave Era A identifiers empty — resolved by esearch).

```python
# src/cns_scientometrics/sources.py
from dataclasses import dataclass, field

@dataclass(frozen=True)
class YearSource:
    year: int
    meeting_no: int
    era: str
    license: str
    identifiers: tuple[str, ...] = field(default=())

def _mk(year, era, license, ids=()):
    return YearSource(year, year - 1991, era, license, tuple(ids))

YEARS = {y: _mk(y, "A", "cc-by") for y in range(2007, 2016)}
YEARS |= {y: _mk(y, "B", "cc-by") for y in range(2016, 2021)}   # ids filled at execution
YEARS |= {y: _mk(y, "C", "free-to-read") for y in range(2021, 2026)}  # ids filled at execution
```

- [ ] **Step 4: Implement `acquire.py` (era routing)**

```python
# src/cns_scientometrics/acquire.py
from pathlib import Path
from .schema import AbstractRecord
from .sources import YEARS, YearSource
from .ncbi import eutils_esearch, eutils_efetch
from .parse_jats import parse_era_a_article, split_bundle

def _era_a_pmcids(year: int, cache_dir: Path) -> list[str]:
    term = f'"BMC Neurosci"[Journal] AND {year}[PDAT]'
    return eutils_esearch("pmc", term, 1000, cache_dir)

def acquire_year(year: int, cache_dir: Path) -> list[AbstractRecord]:
    src: YearSource = YEARS[year]
    if src.era == "A":
        recs = []
        for pmcid in _era_a_pmcids(year, cache_dir):
            xml = eutils_efetch("pmc", [pmcid], cache_dir).encode("utf-8")
            try:
                rec = parse_era_a_article(xml, year, src.meeting_no)
            except Exception:
                continue
            if rec.type != "frontmatter" and rec.title:
                recs.append(rec)
        return recs
    # Era B/C: fetch each bundle id, split
    recs = []
    src_url = ""
    for pmcid in src.identifiers:
        xml = eutils_efetch("pmc", [pmcid], cache_dir).encode("utf-8")
        recs += split_bundle(xml, year, src.meeting_no, src.era, src.license, src_url)
    return recs

def acquire_all(years, cache_dir: Path) -> list[AbstractRecord]:
    out = []
    for y in years:
        out += acquire_year(y, cache_dir)
    return out
```

- [ ] **Step 5: Write an offline routing test (mock efetch/esearch)**

```python
# tests/test_acquire.py
from pathlib import Path
from cns_scientometrics import acquire

def test_acquire_year_era_a_routes_and_filters(tmp_path, monkeypatch):
    monkeypatch.setattr(acquire, "_era_a_pmcids", lambda y, c: ["PMC1", "PMC2"])
    xml = Path("tests/fixtures/era_a_P173.xml").read_text()
    monkeypatch.setattr(acquire, "eutils_efetch", lambda db, ids, c: xml)
    recs = acquire.acquire_year(2015, tmp_path)
    assert len(recs) == 2
    assert recs[0].era == "A"
```

- [ ] **Step 6: Run tests**

Run: `pytest tests/test_sources.py tests/test_acquire.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: acquisition orchestrator + per-year era routing table"
```

---

### Task 6: Author/affiliation normalization (ROR + OpenAlex, best-effort)

**Files:**
- Create: `src/cns_scientometrics/normalize.py`
- Test: `tests/test_normalize.py`

**Interfaces:**
- Consumes: `AbstractRecord`, `cached_get`.
- Produces: `resolve_affiliation(aff: str, cache_dir: Path) -> tuple[str|None, str|None]` returning `(institution_name, country_code)` via ROR affiliation API (`https://api.ror.org/organizations?affiliation=...`), best-effort (returns `(None, None)` on miss). `enrich_record(rec: AbstractRecord, cache_dir: Path) -> AbstractRecord` fills `institutions`/`countries` from its affiliations.

- [ ] **Step 1: Write the failing test (offline, mocked ROR)**

```python
# tests/test_normalize.py
from cns_scientometrics import normalize
from cns_scientometrics.schema import AbstractRecord

def test_enrich_fills_institutions(monkeypatch, tmp_path):
    monkeypatch.setattr(normalize, "resolve_affiliation",
                        lambda aff, c: ("University of Coimbra", "PT"))
    rec = AbstractRecord(
        abstract_id="2015-P1", year=2015, meeting_no=24, type="poster", title="t",
        authors=[], affiliations=["Univ Coimbra, Portugal"], institutions=[], countries=[],
        body={"background": None, "methods": None, "results": None, "full": "t"},
        references=[], figure_caption=None, doi=None, pmcid=None, era="A",
        license="cc-by", source_url="u")
    out = normalize.enrich_record(rec, tmp_path)
    assert out.institutions == ["University of Coimbra"]
    assert out.countries == ["PT"]
```

- [ ] **Step 2: Run to verify fail**

Run: `pytest tests/test_normalize.py -v`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: Implement**

```python
# src/cns_scientometrics/normalize.py
import json
from pathlib import Path
from .schema import AbstractRecord
from .http_cache import cached_get

def resolve_affiliation(aff: str, cache_dir: Path) -> tuple[str | None, str | None]:
    try:
        txt = cached_get("https://api.ror.org/organizations",
                         {"affiliation": aff}, f"ror_{abs(hash(aff))}", cache_dir)
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
    insts, ctys = [], []
    for aff in rec.affiliations:
        name, cc = resolve_affiliation(aff, cache_dir)
        if name and name not in insts:
            insts.append(name)
        if cc and cc not in ctys:
            ctys.append(cc)
    return rec.model_copy(update={"institutions": insts, "countries": ctys})
```

- [ ] **Step 4: Run test**

Run: `pytest tests/test_normalize.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: best-effort ROR affiliation normalization"
```

---

### Task 7: Corpus assembler + QA report + CLI

**Files:**
- Create: `src/cns_scientometrics/corpus.py`, `src/cns_scientometrics/__main__.py`
- Test: `tests/test_corpus.py`

**Interfaces:**
- Consumes: `AbstractRecord`, `acquire_all`, `enrich_record`.
- Produces: `write_corpus(records: list[AbstractRecord], out_dir: Path) -> dict` writing `out_dir/corpus.parquet`, `out_dir/corpus.jsonl`, and returning a QA summary dict (per-year counts, missing-title rate, missing-body rate, dedup count, per-era counts). `build_qa_report(summary: dict) -> str` (markdown). `python -m cns_scientometrics build --years 2007-2024 --out data/corpus` drives the whole pipeline.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_corpus.py
from pathlib import Path
import pandas as pd
from cns_scientometrics.corpus import write_corpus
from cns_scientometrics.schema import AbstractRecord

def _rec(i, year=2015):
    return AbstractRecord(
        abstract_id=f"{year}-P{i}", year=year, meeting_no=24, type="poster",
        title=f"Title {i}", authors=[], affiliations=[], institutions=[], countries=["PT"],
        body={"background": None, "methods": None, "results": None, "full": f"body {i}"},
        references=[], figure_caption=None, doi=None, pmcid=None, era="A",
        license="cc-by", source_url="u")

def test_write_corpus_outputs_and_qa(tmp_path):
    recs = [_rec(1), _rec(2), _rec(2)]  # one duplicate id
    summary = write_corpus(recs, tmp_path)
    assert (tmp_path / "corpus.parquet").exists()
    assert (tmp_path / "corpus.jsonl").exists()
    df = pd.read_parquet(tmp_path / "corpus.parquet")
    assert len(df) == 2  # dedup on abstract_id
    assert summary["per_year"][2015] == 2
    assert summary["n_dropped_dupes"] == 1
```

- [ ] **Step 2: Run to verify fail**

Run: `pytest tests/test_corpus.py -v`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: Implement `corpus.py`**

```python
# src/cns_scientometrics/corpus.py
import json
from collections import Counter
from pathlib import Path
import pandas as pd
from .schema import AbstractRecord

def write_corpus(records: list[AbstractRecord], out_dir: Path) -> dict:
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    seen, deduped = set(), []
    for r in records:
        if r.abstract_id in seen:
            continue
        seen.add(r.abstract_id); deduped.append(r)
    rows = [r.model_dump() for r in deduped]
    df = pd.json_normalize(rows, max_level=0)
    df.to_parquet(out_dir / "corpus.parquet", index=False)
    with (out_dir / "corpus.jsonl").open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    summary = {
        "n_total": len(deduped),
        "n_dropped_dupes": len(records) - len(deduped),
        "per_year": dict(Counter(r.year for r in deduped)),
        "per_era": dict(Counter(r.era for r in deduped)),
        "missing_title_rate": round(sum(1 for r in deduped if not r.title) / max(len(deduped), 1), 4),
        "missing_body_rate": round(sum(1 for r in deduped if not r.body.get("full")) / max(len(deduped), 1), 4),
    }
    (out_dir / "qa_report.md").write_text(build_qa_report(summary), encoding="utf-8")
    return summary

def build_qa_report(summary: dict) -> str:
    lines = ["# CNS Corpus QA Report", "", f"- Total abstracts: {summary['n_total']}",
             f"- Dropped duplicates: {summary['n_dropped_dupes']}",
             f"- Missing-title rate: {summary['missing_title_rate']}",
             f"- Missing-body rate: {summary['missing_body_rate']}", "", "## Per year", ""]
    for y in sorted(summary["per_year"]):
        lines.append(f"- {y}: {summary['per_year'][y]}")
    lines += ["", "## Per era", ""] + [f"- Era {e}: {n}" for e, n in sorted(summary["per_era"].items())]
    return "\n".join(lines) + "\n"
```

```python
# src/cns_scientometrics/__main__.py
import argparse
from pathlib import Path
from .acquire import acquire_all
from .normalize import enrich_record
from .corpus import write_corpus

def _parse_years(s: str) -> list[int]:
    a, b = s.split("-"); return list(range(int(a), int(b) + 1))

def main():
    ap = argparse.ArgumentParser(prog="cns_scientometrics")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--years", default="2007-2024")
    b.add_argument("--out", default="data/corpus")
    b.add_argument("--cache", default="data/cache")
    b.add_argument("--no-enrich", action="store_true")
    args = ap.parse_args()
    cache = Path(args.cache)
    recs = acquire_all(_parse_years(args.years), cache)
    if not args.no_enrich:
        recs = [enrich_record(r, cache) for r in recs]
    summary = write_corpus(recs, Path(args.out))
    print(summary)

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test**

Run: `pytest tests/test_corpus.py -v`
Expected: PASS

- [ ] **Step 5: Full offline suite + lint**

Run: `pytest -m "not network" -q && ruff check src tests`
Expected: all pass, no lint errors.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: corpus assembler, QA report, and build CLI"
```

---

### Task 8: Live end-to-end build (execution gate, not a unit test)

**Files:**
- Create: `data/corpus/` outputs (gitignored), `docs/notes/build-log-2026-06-27.md` (committed)

**Interfaces:** none new — runs Task 5–7 against live APIs.

- [ ] **Step 1: Fill Era B/C identifiers**

During execution, open each live supplement page (spec §2 URLs), record the bundle PMCIDs for 2016–2025, and fill `YEARS[...].identifiers` in `sources.py`. Commit that change separately: `git commit -m "data: fill Era B/C bundle PMCIDs"`.

- [ ] **Step 2: Build one Era-A year as a smoke run**

Run: `NCBI_API_KEY=... python -m cns_scientometrics build --years 2015-2015 --out data/corpus --no-enrich`
Expected: `n_total` ≈ 350–450; `missing_body_rate` < 0.1. Inspect 5 random records in `corpus.jsonl` for sane title/authors/body.

- [ ] **Step 3: Build one Era-C year as a smoke run**

Run: `python -m cns_scientometrics build --years 2021-2021 --out data/corpus_2021 --no-enrich`
Expected: a few hundred records; spot-check splitting didn't merge/clip abstracts. Adjust `split_bundle` XPath if the real JCN structure differs from the fixture.

- [ ] **Step 4: Full build with enrichment**

Run: `NCBI_API_KEY=... python -m cns_scientometrics build --years 2007-2024 --out data/corpus`
Expected: `n_total` on the order of 5,000–8,000. Review `data/corpus/qa_report.md` for per-year sanity (no year at 0; Era A years ~300–500).

- [ ] **Step 5: Write build log + commit**

Record counts per year, anomalies, and any era-specific parser adjustments in `docs/notes/build-log-2026-06-27.md`.

```bash
git add docs/notes/build-log-2026-06-27.md src/cns_scientometrics/sources.py
git commit -m "data: live corpus build 2007-2024 + build log"
```

---

## Self-Review

- **Spec coverage:** Layer 1 acquisition → Tasks 2,3,4,5,8. Layer 2 canonical schema + normalization + corpus asset → Tasks 1,6,7. Three eras → Tasks 3 (A), 4 (B/C), 5 (routing). QA report → Task 7. Engineering standards (ruff, gitignore, CI) → Task 1. Licensing carried per record → Tasks 3/4/5 + Global Constraints. Analysis modules (A–E), viz, CoSyNe contrast → **deferred to Plans 2 & 3** (out of scope here by design).
- **Placeholder scan:** Era B/C bundle PMCIDs are intentionally resolved at execution (Task 8 Step 1) because they must be verified against live pages — this is an execution action with an exact procedure, not a plan placeholder.
- **Type consistency:** `AbstractRecord`/`Author` field names consistent across Tasks 1,3,4,6,7; `cached_get(url, params, cache_key, cache_dir)` signature consistent in Tasks 2 & 6; `eutils_efetch(db, ids, cache_dir)` consistent in Tasks 2,3,5.

## Follow-on plans (not written yet — need the real corpus shape first)

- **Plan 2 — Analysis:** Module A (CoSyNe keyword bridge), B (BERTopic dynamic topics + LLM labels), C (author/geo networks), D (title-vs-abstract robustness), E (CoSyNe×CNS keyword-axis contrast).
- **Plan 3 — Publishing:** matplotlib/Plotly figures, Datawrapper export (reuse CoSyNe scripts), Substack draft.
