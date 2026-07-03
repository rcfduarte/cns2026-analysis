# Methodology validation & publishing-layer review

Review of the CNS-scientometrics pipeline ahead of the public write-up: what was
verified, what was corrected, and what was added. Companion to
[`METHODS.md`](METHODS.md) (acquisition) and [`RESULTS.md`](RESULTS.md) (findings).

## 1. What was verified

- **Test suite green.** All 34 offline (fixture-based) tests pass
  (`pytest -m 'not network'`). Parsers for all five publication eras (BMC-JATS,
  BMC-HTML, bundled `<sec>`, JCN flat-`<p>`, JCN-PDF) are exercised against committed
  fixtures, and the CoSyNe program-book parser + institution→country resolver against a
  synthetic program-book excerpt (`test_cosyne_programbook.py`).
- **Keyword engine is CoSyNe-faithful.** `analyze/keyword_trends.py` implements the
  per-10k-words frequency with the exact matching rule of the reference CoSyNe study
  (word-boundary regex for synonyms ≤4 chars, substring otherwise, on lowercased
  text). The taxonomy in `keywords_taxonomy.py` is copied verbatim, so the CNS×CoSyNe
  contrast is genuinely apples-to-apples.
- **Numbers reproduce.** The committed aggregate tables were cross-checked internally:
  the AI/ML uptake CNS line recomputed from `keyword_frequencies.csv` matches the
  committed figure to the digit; recovered per-country totals reproduce the
  `RESULTS.md` headline counts (US 1,673, DE 929, GB 600, FR 415, JP 289) to within
  <1%; recovered internationalization endpoints match (entropy 3.18→4.17, 24–41
  countries). See §4.

## 2. Methodological caveats confirmed (and how the article handles them)

1. **Overlapping-synonym inflation.** For synonyms >4 chars the counter uses substring
   matching (`text.count`), so an umbrella term is also counted inside its own
   compounds — e.g. `oscillation` is counted again inside *gamma oscillation*, and
   `cortex` inside *neocortex*. This is **intentional** (it mirrors the CoSyNe recipe,
   preserving comparability) but it means broad terms carry inflated absolute
   magnitudes. *Handled:* the article presents keyword magnitudes as **indices for
   comparison across years and meetings**, never as literal counts, and says so in the
   method note.
2. **Denominator dilution.** Frequencies are per-10k-words over full abstract text;
   longer bodies dilute per-10k rates relative to title-dense text. This is quantified,
   not hand-waved — see the title-vs-abstract robustness check (Module D / Fig 7).
3. **Host-city confound in geography.** Author-country counts spike in years the meeting
   is hosted in that country (US peaks in 2010/2012/2018 = US-hosted meetings).
   *Handled:* the geography figure is retitled to a descriptive claim and the confound
   is stated; the *trend* claim rests on the host-invariant diversity/entropy measure,
   shown with an explicit linear fit so the modest signal isn't oversold.
4. **CoSyNe comparison now spans three axes.** Earlier the contrast was keyword-only,
   because CoSyNe was ingested as keyword frequencies. CoSyNe's program books
   (`cosyne-keywords` repo) were parsed into per-abstract records (§4c), so the
   comparison now also covers **per-abstract keyword co-occurrence** and
   **institution-resolved geography**. Two honest limits remain, stated in the article:
   per-abstract structure is only recoverable for **2014–2026** (older program books are
   unstructured OCR), and CoSyNe affiliations are bare institution names, so country
   comes from a curated institution→country map (97% of abstracts resolved; the
   unresolved tail of bare department names is left uncounted, not guessed).

## 3. Corrections made

- **`analyze/figures.py::fig_aiml_rise`** hard-coded `piv.loc["LLM", 2024]` for its
  annotation, which raises `KeyError` on any corpus missing that exact cell (e.g. a
  free-tier 2007–2021 build, where 2024 is absent). Replaced with a guarded lookup of
  the LLM row's last non-null year. This is the one latent crash found in the analysis
  layer.

## 4. Extensions added (this review)

The publishing layer previously required the **raw corpus** (gitignored, and partly
paywalled for 2022–2025) to regenerate any figure. That makes the published figures
effectively non-reproducible for anyone without the private data. Two additions fix
this and add the article-quality figure suite:

- **`scripts/recover_tables_from_figures.py`** — recovers the aggregate series behind
  the corpus-only figures (AI/ML uptake, internationalization, per-country time series,
  robustness histogram) directly from the committed SVGs, by inverting each plot's
  pixel↔data calibration (matplotlib stores tick labels as HTML comments beside
  tick-mark `<use>` elements; data are coloured `<path>` polylines / rectangles). The
  recovered values are the *exact plotted values* and are cross-validated against
  `keyword_frequencies.csv` and `RESULTS.md` (agreement <1%, see §1). Outputs the
  committed `results/tables/recovered_*.csv`. Original figures are archived under
  `results/figures/_source_v1/` as provenance.
- **`scripts/build_article_figures.py`** — regenerates the entire publication figure
  suite in an editorial / popular-science house style, reading **only** from
  `results/tables/` (committed aggregates + recovered series). No raw corpus required.
  Colours use a CVD-validated categorical/diverging palette (worst adjacent ΔE 24.2 on
  the light surface); every figure carries a title, one-line subtitle, direct labels,
  and a source line.
  - New analytical figure: **rising-vs-fading keyword change** (2021–25 mean − 2007–11
    mean) as a diverging bar chart — a cleaner headline than the raw heatmap for "how
    the field's attention rotated." The full heatmap is kept as a supplementary
    "vocabulary map."

Net effect: `results/` is now **self-contained and reproducible** — anyone can
regenerate every published figure from the committed tables with
`python scripts/build_article_figures.py`, with no access to the private corpus.

### 4b. Community structure (CoSyNe vs CNS) — run on the real corpus

- **`scripts/keyword_networks.py`** (committed data): keyword **co-trajectory network**
  with greedy-modularity communities (`fig8`); **two-vocabularies map** (`fig9`);
  **scale-normalized specialization + overlap** (`fig10`). Overlap of the two
  communities on scale-free vocabulary shares: cosine 0.90, shared mass 78%, top-15
  Jaccard 0.43, 18/55 shared-core terms. Community membership in
  `results/tables/cotrajectory_communities.csv`. The **corpus** path now produces the true
  per-abstract co-occurrence networks (`fig_cooccurrence_cns`, `fig_cooccurrence_cosyne`):
  CNS = 38 nodes / 49 edges, CoSyNe = 48 / 86 (CoSyNe's concepts co-occur more densely).
  **Partition co-membership Jaccard = 0.21** on the 36 shared keywords — the two fields
  cluster even their shared vocabulary differently.
- **`scripts/affiliation_analysis.py`** (corpus): institution parsing, top institutions
  (`fig11`), collaboration network + communities (`fig12`), scale-normalized country
  shares (`fig13`). Fixed a parse bug where leading affiliation-footnote digits were not
  stripped, fragmenting institutions (e.g. "Bernstein Center…" split across
  "2Bernstein…"/"3Bernstein…"); `_strip_footnote` now merges them. `--export` writes the
  committable aggregates (`institution_stats`, `institution_edges`, `country_year_totals`,
  `keyword_incidence_cns`).
- **`scripts/geography_comparison.py`**: `fig15` now runs — CNS (full corpus, all
  countries, 2007–2025) vs CoSyNe (program books, 2014–2026): CoSyNe **58% North America /
  34% Europe** (US alone 54%), CNS **28% / 55%**. `REGION` extended to cover every country
  CoSyNe surfaces.
- **`scripts/meeting_sizes.py`** (new): accepted-abstract counts per year, CNS vs CoSyNe
  (`fig16`, `meeting_sizes.csv`). CoSyNe runs ~1.5× larger over 2014–2025 and is pulling
  away.

### 4c. CoSyNe program-book adapter

- **`src/cns_scientometrics/analyze/cosyne_programbook.py`** (new): parses `cosyne_YYYY.txt`
  program books into per-abstract records (id-header segmentation; keeps blocks with an
  e-mail block + prose), extracts institution footnotes, and resolves them to countries
  with a curated, country-diagnostic rule set (first-match-wins, specific→general). 96.7%
  per-abstract country coverage on the real data; the unresolved tail is department
  fragments, left uncounted. Also counts accepted abstracts across both poster-numbering
  schemes (Roman pre-2021, Arabic 2021+). Covered by `tests/test_cosyne_programbook.py`.
- **`scripts/adapt_cosyne.py`**: takes a directory of program books (or a structured
  parquet/JSONL/CSV) and emits the two committable aggregates the CNS pipeline consumes —
  `keyword_incidence_cosyne.csv` (per-abstract 0/1 flags, same taxonomy) and
  `cosyne_countries.csv` (institution-resolved country counts). No abstract text is
  written.

All corpus paths above were run against the real CNS corpus (5,394 abstracts, 2007–2025)
and the real CoSyNe program books (3,143 segmentable abstracts, 2014–2026). A menu of
further analyses is in [`ANALYSIS_IDEAS.md`](ANALYSIS_IDEAS.md).

## 5. Reproduce

```bash
pip install -e ".[dev,analysis]"
pytest -q                                     # 34 pass, 1 network-deselected
python scripts/recover_tables_from_figures.py # committed; recovers series from _source_v1 SVGs
python scripts/build_article_figures.py       # -> results/figures/*.png (+ .svg)

# corpus-dependent (needs the private CNS corpus + the CoSyNe program books):
python scripts/affiliation_analysis.py --corpus data/corpus/corpus.parquet --export
python scripts/adapt_cosyne.py --abstracts ~/repos/cosyne-keywords/data
python scripts/geography_comparison.py --cosyne-countries results/tables/cosyne_countries.csv
python scripts/keyword_networks.py --incidence results/tables/keyword_incidence_cns.csv \
    --cosyne-incidence results/tables/keyword_incidence_cosyne.csv   # prints partition Jaccard
python scripts/meeting_sizes.py --corpus data/corpus/corpus.parquet \
    --cosyne-dir ~/repos/cosyne-keywords/data
```

The narrative write-up embedding these figures is in [`ARTICLE.md`](ARTICLE.md).
