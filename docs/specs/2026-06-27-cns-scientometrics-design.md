# CNS / OCNS Abstract Scientometrics — Design Spec

**Date:** 2026-06-27
**Repo:** `/home/neuro/repos/cns-scientometrics/` (GitHub-hosted)
**Status:** Approved design → implementation planning

---

## 1. Purpose

Build a reproducible, GitHub-hosted Python pipeline that (a) assembles a clean
**per-abstract corpus** of CNS meeting abstracts (the annual meeting of the
Organization for Computational Neuroscience, OCNS) spanning 2007–2024/25, and
(b) runs a scientometric analysis that is deliberately **deeper than the prior
CoSyNe keyword-frequency study**.

The end goal is a public Substack "field notes" piece with polished interactive
Datawrapper charts for a general computational-neuroscience audience. The build
order is **rigor first**: a defensible internal pipeline + reusable corpus is the
foundation, and the article is a thin presentation layer on top once the analysis
settles.

This is **not** a carbon copy of the CoSyNe analysis. The CoSyNe study tracked
~40 hand-curated keywords across 23 years of undifferentiated program-book text.
The CNS data is structured per-abstract (title, authors, affiliations, structured
body), which unlocks data-driven topics and community-structure analyses the
CoSyNe blob could not support.

## 2. Background: the data and its three eras

CNS meeting abstracts are open and machine-accessible, but fall into three
structurally distinct publication eras that require different parsing:

| Era | Years | Venue | Structure | Access |
|-----|-------|-------|-----------|--------|
| A | 2007–2015 | BMC Neuroscience | One article (DOI/PMID/PMCID) **per abstract** | PMC OA, **CC-BY**, cleanest |
| B | 2016–2020 | BMC Neuroscience | Bundled "Part 1/2/3" articles (hundreds of abstracts each, as `<sec>`) | PMC OA, CC-BY |
| C | 2021–2025 | J. Computational Neuroscience | **One article per meeting** (pp. e.g. 3–208) | PMC (free-to-read, `license=none`) / Springer API |

Each record contains: **title, full author list, affiliations, and a short
structured body** (typically Background / Methods / Results, ~150–400 words, with
1–6 references and occasionally one small figure). Category encoded in the DOI
suffix: `O` = oral, `P` = poster, `A` = front matter.

**There is no poster/full-text layer** in these publications — the published
abstract is the deepest available text. Volume ≈ 200–500 abstracts/year;
full corpus on the order of **5,000–8,000 abstracts**.

**CNS\*2026** (35th meeting, Halifax, July 11–15 2026) is **not yet published**;
its supplement will appear ~early 2027. Most recent complete year is **2024**
(2025/Florence may be live by build time — include if available in PMC).

No dedicated published scientometric study of the CNS/OCNS abstract corpus exists
(closest analogue: Lin & Maxim 2007 on SfN abstracts, PMC2324197) — a genuine gap.

## 3. Scope decisions (locked)

1. **Two text tiers, not three.** Title-only vs title+abstract. There is no
   full-text/poster tier in the source. The two-tier comparison is a
   **methodological robustness check** (how much does abstract depth change the
   conclusions?), not the centerpiece.
2. **Three headline dimensions beyond CoSyNe:** (i) semantic data-driven topic
   modeling, (ii) author & geography / collaboration networks, (iii) a
   CoSyNe×CNS cross-conference contrast.
3. **Year span:** 2007 → 2024 (include 2025 if its abstract article is live in
   PMC at build time). Full span, all three eras.
4. **Deliverable:** rigorous internal pipeline + reusable corpus data asset,
   structured so the Substack article (Datawrapper charts) is a thin final layer.

## 4. Core methodological choice: topic-modeling engine

**Decision: BERTopic + science-tuned embeddings + an LLM topic-labeling pass.**

- Embed each abstract with a scientific sentence model (SPECTER2 or
  `all-MiniLM-L6-v2` as a lighter fallback).
- Cluster with UMAP + HDBSCAN (BERTopic default).
- Run **dynamic** (temporal) topic modeling to track topic prevalence over years.
- One cheap LLM pass to assign **human-readable names** to clusters — labeling
  only, *not* clustering, to preserve reproducibility.

Rejected alternatives: classic LDA/NMF (weak on short abstracts, less
interpretable); pure-LLM taxonomy (costly, less reproducible, harder to defend).

## 5. Architecture — four layers

### Layer 1 — Acquisition (era-aware, cached)

Three fetchers, one per era, all writing to a raw on-disk cache so external APIs
are hit once:

- **Era A (2007–2015):** enumerate per year via NCBI E-utilities `esearch`
  (`db=pmc`, `"BMC Neurosci"[Journal] AND <year>[PDAT]`); fetch each abstract's
  JATS via PMC OA `oa.fcgi` (`.tar.gz`) or `efetch db=pmc`.
- **Era B (2016–2020):** `efetch db=pmc` the ~3 "Part 1/2/3" articles per year;
  split into abstracts on `<sec>` boundaries.
- **Era C (2021–2025):** `efetch db=pmc` the single JCN article per year (or
  Springer Nature API JATS / publisher PDF); segment internally into abstracts.
- **Crossref** (`api.crossref.org`) for DOI/title/author enumeration and
  cross-checking (note: Crossref carries **no** abstract body for these records —
  metadata only).

Resilience: respect NCBI rate limits (use an API key, ≤3 req/s without / ≤10
with), exponential backoff, idempotent caching keyed by DOI/PMCID. Hardcode-free
volume table — verify supplement volume numbers against live URLs (known typo:
2014 is vol 15 S1, not 14).

### Layer 2 — Parsing → canonical schema

Normalize every era into one record schema, persisted as **Parquet + JSONL**
(the reusable data asset):

```
abstract_id        # stable id: "<year>-<O|P><num>"
year, meeting_no
type               # oral | poster | keynote | frontmatter(excluded from analysis)
title
authors[]          # {raw_name, given, family, openalex_id?}
affiliations[]     # raw affiliation strings
institutions[]     # ROR-resolved institution names
countries[]        # ISO country codes
body{background, methods, results, full}
references[]
figure_caption?
doi, pmcid?
era                # A | B | C
license            # cc-by | free-to-read
source_url
```

- Institution/country resolution via **ROR** + author resolution via **OpenAlex**
  author IDs. Author/affiliation disambiguation is the known time-sink; target
  ~90% coverage, log unresolved cases rather than chase perfection.
- Provenance + a per-year QA report (counts, missing-field rates, dedup) mirroring
  the spirit of the CoSyNe `data_quality_audit.py`.

### Layer 3 — Analysis (independent modules)

Each module consumes the canonical corpus and is independently runnable/testable.

- **A — Keyword-frequency trends (the CoSyNe bridge).** Reuse CoSyNe's keyword
  taxonomy and per-10k-word normalization *exactly*, so Module E is
  apples-to-apples. Imports the CoSyNe keyword list from
  `Assets/claude/outputs/cosyne-analysis/`.
- **B — Semantic topics.** BERTopic dynamic topic modeling on title+abstract;
  discover topics, track rise/fall, project recent trends.
- **C — Author & geography networks.** Co-authorship graph (centrality,
  components, rising/falling labs); institution & country time series;
  internationalization metrics (country count, diversity entropy).
- **D — Title-vs-abstract robustness.** Re-run A and B on title-only vs
  title+abstract; quantify deltas (term coverage, topic recovery, trend
  correlation). The reflexivity section.
- **E — CoSyNe×CNS contrast.** Shared **keyword axis only**: AI/ML uptake,
  methods-vs-systems balance, topic/keyword overlap. (Topic-model-level contrast
  is out of scope — see §6.)

### Layer 4 — Publishing

matplotlib/Plotly static + interactive figures; reuse CoSyNe's Datawrapper export
+ chart-creation scripts. The Substack draft is authored last, as a thin layer
over settled figures.

## 6. Risks & honest caveats

- **Author/affiliation disambiguation** is the main effort sink; build
  incrementally, accept ~90% coverage, log the rest.
- **Era C licensing:** JCN bundles are free-to-read but **not CC-BY**
  (`license=none`). Fine for derived metrics and trend figures; **do not
  redistribute raw abstract text** for 2021–25. Era A (2007–2015) is CC-BY and
  freely redistributable.
- **CoSyNe×CNS contrast is clean only on the keyword axis.** CoSyNe is an
  undifferentiated text blob (no per-abstract structure); topic-level contrast
  would require segmenting old CoSyNe program books into abstracts — feasible for
  recent years, painful for OCR-era books. **Out of scope** as an explicit
  stretch goal; Module E stays on the keyword axis.
- **Year completeness:** 2025 inclusion is conditional on PMC availability at
  build time; pipeline must degrade gracefully if a year is absent.

## 7. Differences from the CoSyNe analysis (summary)

| Axis | CoSyNe study | This CNS study |
|------|--------------|----------------|
| Corpus unit | Whole program book (text blob) | Per-abstract structured records |
| Topics | Hand-curated 40-keyword taxonomy | Data-driven BERTopic + LLM labels (keywords kept as bridge) |
| Community structure | None | Author/affiliation/geography networks |
| Reflexivity | None | Title-only vs title+abstract robustness |
| Cross-conference | None | CoSyNe×CNS keyword-axis contrast |

## 8. Engineering standards

- Python project under user's standards: `[tool.ruff]` (line-length 100, rules
  `E,W,F,I,B,UP,SIM,RUF`), the secrets-aware `.gitignore` block
  (`.env`, `.mcp.json`, `credentials.json`, `*.key`, `*.pem`, `secrets/`),
  GitHub Actions lint CI.
- Layout: `src/cns_scientometrics/{acquire,parse,analyze,viz}/`, `data/`
  (gitignored caches + corpus), `notebooks/` (marimo), `tests/`, `docs/`.
- Reproducibility: cached raw responses, deterministic seeds where applicable,
  pinned deps.

## 9. Out of scope (YAGNI)

- Poster/full-text retrieval (does not exist in source).
- Linking abstracts to subsequent journal papers for a "full-text" tier
  (dropped in favor of the two-tier design).
- Per-abstract segmentation of CoSyNe program books (contrast stays keyword-axis).
- CNS\*2026 abstracts (unpublished as of build date).
