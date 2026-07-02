# Methodology validation & publishing-layer review

Review of the CNS-scientometrics pipeline ahead of the public write-up: what was
verified, what was corrected, and what was added. Companion to
[`METHODS.md`](METHODS.md) (acquisition) and [`RESULTS.md`](RESULTS.md) (findings).

## 1. What was verified

- **Test suite green.** All 29 offline (fixture-based) tests pass
  (`pytest -m 'not network'`). Parsers for all five publication eras (BMC-JATS,
  BMC-HTML, bundled `<sec>`, JCN flat-`<p>`, JCN-PDF) are exercised against committed
  fixtures.
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
4. **Contrast is keyword-axis only.** CoSyNe has no per-abstract structure available, so
   the cross-community comparison is deliberately limited to the shared keyword axis
   (no topic-level or network comparison). Stated in the article.

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

### 4b. Community structure (added — CoSyNe vs CNS)

- **`scripts/keyword_networks.py`** (committed data): keyword **co-trajectory network**
  with greedy-modularity communities (`fig8`); **two-vocabularies map** (`fig9`);
  **scale-normalized specialization + overlap** (`fig10`). Overlap of the two
  communities on scale-free vocabulary shares: cosine 0.90, shared mass 78%, top-15
  Jaccard 0.43, 18/55 shared-core terms. Community membership dumped to
  `results/tables/cotrajectory_communities.csv`. Also carries the **corpus** path: true
  per-abstract co-occurrence networks + a partition co-membership Jaccard between CNS and
  CoSyNe (`--incidence`/`--cosyne-incidence`).
- **`scripts/affiliation_analysis.py`** (corpus): institution parsing, top institutions,
  institution collaboration network + communities, and **scale-normalized** geography
  (country *shares* per meeting, removing the meeting-size/host-city confound). `--export`
  writes committable non-sensitive aggregates (`institution_stats`, `institution_edges`,
  `country_year_totals`, `keyword_incidence_cns`) so these figures can be regenerated
  here without shipping raw text. Verified end-to-end on a synthetic corpus.

Both corpus paths are code-complete but await the private corpus (this environment has no
NCBI access and the corpus is gitignored). A menu of further analyses is in
[`ANALYSIS_IDEAS.md`](ANALYSIS_IDEAS.md).

## 5. Reproduce

```bash
pip install -e ".[dev,analysis]"
pytest -q                                     # 29 pass, 1 network-deselected
python scripts/recover_tables_from_figures.py # committed; recovers series from _source_v1 SVGs
python scripts/build_article_figures.py       # -> results/figures/*.png (+ .svg)
```

The narrative write-up embedding these figures is in [`ARTICLE.md`](ARTICLE.md).
