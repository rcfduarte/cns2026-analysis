# cns2026-analysis

A reproducible pipeline that assembles a clean, per-abstract corpus of **CNS / OCNS
meeting abstracts** (the annual meeting of the Organization for Computational
Neuroscience) spanning **2007–2025**, and analyses how computational neuroscience has
evolved over two decades — topics, methods, and community structure.

It is a deliberately *deeper* companion to a prior keyword-frequency study of the CoSyNe
conference: where that study tracked a hand-curated keyword list across program-book
text, this project works from **structured per-abstract records** (title, authors,
affiliations, full abstract body) and adds data-driven topic modelling, author/geography
networks, and a CoSyNe×CNS contrast.

> **Status.** Corpus **and** analysis layer complete. **5,394 abstracts, 2007–2025, 19
> years**, 0% missing titles/bodies, 98.4% with parsed authors. Findings (keyword trends,
> 38 BERTopic topics, author/geography networks, title-vs-abstract robustness, CoSyNe×CNS
> contrast) are in [`docs/RESULTS.md`](docs/RESULTS.md). Publishing layer (Plan 3) is next.

---

## The corpus at a glance

| | |
|---|---|
| **Abstracts** | 5,394 |
| **Years** | 2007–2025 (19 annual meetings; CNS\*2026 not yet published) |
| **Per type** | 4,943 posters · 400 orals · 51 keynotes |
| **Coverage** | every year populated; 0% missing titles or bodies; 98.4% with ≥1 author; ~90% with affiliations |
| **Record** | title · authors · affiliations · structured body · references · DOI · era · license · provenance |

Full per-year composition and the data dictionary are in [`docs/CORPUS.md`](docs/CORPUS.md);
acquisition methodology and the data-availability findings are in
[`docs/METHODS.md`](docs/METHODS.md).

## Why this is non-trivial: three publication eras

CNS abstracts are open but published in three structurally different ways, each needing a
different parser — plus two paywall/PMC-gap workarounds:

| Era | Years | Source | Structure |
|-----|-------|--------|-----------|
| **A** | 2007, 2010–2015 | BMC Neuroscience | one PMC article (JATS) **per abstract** |
| **A′** | 2008, 2009 | BMC Neuroscience | not in PMC → scraped from open-access **article HTML** |
| **B** | 2016–2020 | BMC Neuroscience | **bundled** "Part 1/2/3" articles (`<sec>` per abstract) |
| **C** | 2021 | J. Computational Neuroscience | single PMC article, **flat `<p>` stream** |
| **C′** | 2022–2025 | J. Computational Neuroscience | Springer-paywalled → parsed from user-supplied **PDFs** |

A single canonical schema (`AbstractRecord`) normalises all five paths.

## Quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q                                   # offline unit tests (fixtures, no network)

# Build the freely-available corpus (2007-2021). NCBI_API_KEY optional (faster).
python -m cns_scientometrics build --years 2007-2021 --out data/corpus

# To include 2022-2025 you must supply the paywalled JCN supplement PDFs yourself
# (see docs/notes/pdf-dropbox-instructions.md), then:
python -m cns_scientometrics build --years 2007-2025 --out data/corpus
```

Outputs: `data/corpus/corpus.parquet`, `corpus.jsonl`, and `qa_report.md`.

## Repository layout

```
src/cns_scientometrics/
  schema.py        canonical AbstractRecord (pydantic)
  http_cache.py    disk-cached HTTP + deterministic cache keys
  ncbi.py          NCBI E-utilities (esearch/efetch)
  sources.py       per-year era/venue routing table
  parse_jats.py    Era A single + Era B/C bundle parsers (JATS)
  bmc_html.py      Era A′ fallback (BMC article HTML, 2008/09)
  parse_pdf.py     Era C′ JCN PDF parser (2022-2025)
  normalize.py     ROR affiliation → institution/country
  acquire.py       era-aware orchestrator
  corpus.py        dedupe → Parquet + JSONL + QA report
  __main__.py      `build` CLI
docs/
  specs/           design spec
  plans/           implementation plans
  METHODS.md       acquisition + parsing methodology
  CORPUS.md        composition, data dictionary, provenance, caveats
  notes/           build logs
tests/             pytest suite (fixture-based, offline)
```

## Roadmap

- **Plan 1 — corpus foundation** ✅ — 5,394 abstracts, 2007–2025 ([`docs/CORPUS.md`](docs/CORPUS.md))
- **Plan 2 — analysis** ✅ — keyword trends (A), BERTopic dynamic topics (B), author/geography
  networks (C), title-vs-abstract robustness (D), CoSyNe×CNS contrast (E). Run via
  `scripts/run_{keyword_trends,topics,networks,contrast}.py`. Findings in
  [`docs/RESULTS.md`](docs/RESULTS.md).
- **Plan 3 — publishing**: polished interactive charts (Datawrapper) + a public write-up.

Install analysis extras with `pip install -e ".[analysis,topics]"` (topics pulls the
sentence-transformers/BERTopic stack).

## Data ethics & licensing

The **code** is MIT-licensed. The **corpus is not redistributed**: everything under
`data/` (caches, the assembled corpus, the paywalled PDFs and their extracted text) is
gitignored and never committed. 2007–2020 abstracts are CC-BY; 2021–2025 are *free-to-read
but not open-access*, so their bodies are reconstructed locally from the original sources,
not shipped here. See [`LICENSE`](LICENSE).
