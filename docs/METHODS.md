# Methods — corpus acquisition & parsing

How the 2007–2025 CNS abstract corpus is assembled. The pipeline is **era-aware**: each
year is routed to a parser matched to how that year's abstracts were published, then
normalised into one canonical schema. All network responses are cached to disk with
deterministic keys, so re-runs are offline and idempotent.

## 1. Source map

CNS meeting abstracts appear in three venues across three structurally distinct eras
(plus two access workarounds). Per-year venues and identifiers live in
`src/cns_scientometrics/sources.py`.

| Era | Years | Venue | Retrieval | Parser |
|-----|-------|-------|-----------|--------|
| A | 2007, 2010–2015 | BMC Neuroscience | PMC E-utilities (`esearch`→`efetch`), JATS XML | `parse_jats.parse_era_a_articleset` |
| A′ | 2008, 2009 | BMC Neuroscience | **not in PMC** → BMC article HTML | `bmc_html.parse_bmc_html` |
| B | 2016–2020 | BMC Neuroscience | PMC `efetch` of bundled "Part" articles, JATS | `parse_jats.split_bundle` |
| C | 2021 | J. Comp. Neurosci. | PMC `efetch`, JATS | `parse_jats.split_flat_paragraphs` |
| C′ | 2022–2025 | J. Comp. Neurosci. | **Springer-paywalled** → user-supplied PDF | `parse_pdf.parse_pdf` |

## 2. Acquisition by era

**Era A (individual-DOI).** `esearch` enumerates `"BMC Neurosci"[Journal] AND <year>[PDAT]`,
then `efetch` pulls JATS in batches of 100 articles. Because that query returns the *whole*
journal, records are kept only if their DOI matches the CNS supplement pattern
`-S<n>-<CODE>` (`is_supplement_abstract`); regular research articles are dropped. The
abstract code prefix (`P` poster, `O`/`F`/`I` oral, `K`/`L` keynote, `A` front-matter)
sets the record type.

**Era A′ (HTML fallback).** CNS\*2008 (BMC vol 9 S1) and CNS\*2009 (vol 10 S1) individual
abstracts are *not deposited in PMC*. They are scraped instead from their open-access BMC
article pages: the paginated supplement table-of-contents (50 articles/page) yields the
DOIs; each article's title/authors/affiliations come from its JSON-LD and the body from the
`c-article-body` container. A browser User-Agent is required (BMC returns 403 to bots).

**Era B (bundled `<sec>`).** Each year is 1–3 "Part" articles, each holding hundreds of
abstracts as top-level `<sec>` elements. The byline and affiliations are encoded as
*nested `<sec>` titles* (not `<contrib>`/`<aff>` tags), with affiliations glued together
(`1Inst A, USA2Inst B`).

**Era C (flat `<p>`).** The 2021 JCN supplement is one PMC article whose `<body>` is a flat
run of `<p>` elements; abstracts are delimited by header paragraphs (`K1`, `F1`, `O5`,
`P173`).

**Era C′ (PDF).** 2022–2025 JCN supplements are Springer-paywalled (Europe PMC confirms
`inPMC=N, isOpenAccess=N`), so the user supplies the PDFs. `pdftotext` (default flow mode)
reads the two-column layout in reading order; the line stream is segmented on `K/F/O/P`
headers. Bodies are delimited by an `Email:` line (2022–2024) or a literal `Abstract`
heading (2025); Springer cover artifacts and running headers/page numbers are stripped.

## 3. Unified parsing

Eras B and C share a single assembler (`parse_jats._assemble`) that classifies each text
line as author byline, affiliation, `Email`, `References`, or body — tolerant of both
*spaced* (`Name 1 , Name 2`) and *glued* (`Name1,2`) superscript markers. Author cleaning
removes superscript digits, corresponding-author marks (`*`), and soft hyphens, then splits
on commas/semicolons. The PDF parser reuses this author cleaning.

## 4. Canonical schema

Every era emits the same `AbstractRecord` (pydantic, `schema.py`): `abstract_id, year,
meeting_no, type, title, authors[], affiliations[], institutions[], countries[],
body{background,methods,results,full}, references[], doi, pmcid, era, license, source_url`.

## 5. Enrichment, assembly, QA

Affiliations are resolved to institution + ISO country via the ROR affiliation API
(best-effort; misses are logged, not fatal). The assembler deduplicates by `abstract_id`,
writes `corpus.parquet` + `corpus.jsonl`, and emits `qa_report.md` (per-year/era/type
counts, missing-field rates). Era licence is carried on every record (`cc-by` for
2007–2020, `free-to-read` for 2021–2025).

## 6. Reproducibility & caching

All HTTP responses cache to `data/cache/` under **deterministic** keys
(`http_cache.stable_key`, md5 — *not* Python's per-process-salted `hash()`), so a second
run hits disk, not the network. Parsing is covered by an offline `pytest` suite built on
saved JATS/HTML/PDF fixtures.

## 7. Known data-availability findings

- **2008/2009 are absent from PMC** (only recoverable via BMC HTML) — a non-obvious gap.
- **2022–2025 JCN supplements are paywalled** (free-to-read, not OA): bodies require the
  publisher PDF and are not redistributed.
- **CNS\*2026** is unpublished (meeting July 2026).
- A handful of records (~1.3%) have short bodies — mostly keynotes whose PDF page carries a
  figure that interrupts clean text extraction.
