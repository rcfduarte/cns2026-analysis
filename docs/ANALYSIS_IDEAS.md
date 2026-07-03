# Additional analyses & representations — a menu

Proposals to deepen the CNS × CoSyNe community analysis, grouped by theme. Each is
tagged by data readiness:

- **[now]** computable from the committed aggregates (`results/tables/`) — no corpus.
- **[corpus]** needs the raw corpus parquet (and/or a CoSyNe corpus); code is written
  and runs on the local clone (`scripts/affiliation_analysis.py`,
  `scripts/keyword_networks.py --incidence …`). Export the small non-sensitive
  aggregates with `--export` and the figures regenerate anywhere.
- **[stretch]** needs new data (citations, full author disambiguation, external corpora).

## Already delivered this round
- **[now]** Keyword co-trajectory network + communities (`fig8`).
- **[now]** CoSyNe-vs-CNS vocabulary map, log-log with signatures (`fig9`).
- **[now]** Scale-normalized specialization + overlap metrics — cosine 0.90, shared
  mass 78%, top-15 Jaccard 0.43, 18/55 shared-core terms (`fig10`).
- **[corpus]** Top institutions, institution collaboration network, and
  scale-normalized country shares (`fig11–13`, code ready in
  `scripts/affiliation_analysis.py`).
- **[corpus]** True per-abstract keyword co-occurrence networks for CNS and CoSyNe,
  with a partition-overlap metric (`scripts/keyword_networks.py --incidence`).

## A. Community structure & overlap
1. **Co-occurrence community comparison, side by side [corpus].** Build the NPMI
   co-occurrence graph for each meeting, detect communities, and quantify how
   differently they cluster the *shared* keyword set (co-membership Jaccard / NMI /
   variation-of-information). Answers "do the two fields organise the same concepts
   into the same clusters?" — a deeper notion of "community" than vocabulary overlap.
2. **Bridge vs signature terms [now].** Rank keywords by betweenness centrality in the
   co-trajectory graph (bridges that connect otherwise separate clusters, e.g.
   `dimensionality` linking geometry to ML) vs terms that sit deep inside one cluster.
3. **Temporal community evolution [now].** Recompute co-trajectory communities on
   rolling windows (2007–2013, 2013–2019, 2019–2025) and draw an alluvial/Sankey of how
   terms migrate between clusters — when did the "NeuroAI" cluster crystallise?

## B. Scale & normalization (directly requested)
4. **Rank-based comparison [now].** Beyond share normalization, compare within-community
   *ranks* (Spearman footrule / rank-biased overlap) so a handful of huge umbrella terms
   can't dominate. Robust to the CoSyNe-convention synonym inflation.
5. **Per-year size normalization for geography [corpus].** `fig13` already converts
   country counts to shares of each meeting; extend to institutions and to a
   host-city-adjusted model (regress out a "meeting is in country X" indicator) to
   isolate the genuine internationalization trend from the home-team bump.
6. **Efferson/among-abstract concentration [corpus].** Gini/HHI of institutions and
   countries per year — is the field's output concentrating in a few mega-labs or
   democratizing? Normalize by number of abstracts so trend ≠ meeting size.

## C. Institutions, people, geography
7. **Institution collaboration backbone [corpus].** Done as `fig12`; add k-core
   decomposition and highlight international vs domestic edges (share of cross-border
   collaborations over time — a second, author-level internationalization signal).
8. **Rising vs established institutions [corpus].** Compare each institution's early
   vs recent output share (same early-vs-recent lens as `fig2`) to surface newcomers.
9. **Author career/turnover [corpus].** From the co-authorship graph: newcomer rate per
   year, retention (fraction of authors reappearing), and the growth of team size
   (mean authors per abstract) — a proxy for the field's "big science" shift.
10. **Topic × geography [corpus].** Which countries/institutions specialise in which
    BERTopic themes (e.g. is connectomics US-led, oscillations Europe-led?). A
    country × topic heatmap, row-normalized.
10b. **CoSyNe geography, to close the US-vs-EU comparison [stretch].** CNS origins are
    done (`fig14`: Europe bloc ~52% vs US ~36%, and the "CoSyNe is US / CNS is EU"
    hypothesis holds for the CNS half). The CoSyNe half needs author affiliations, which
    the project lacks (CoSyNe was ingested as keyword frequencies only). Acquire them by
    parsing the CoSyNe abstract/program books (PDFs on cosyne.org, ~2004–present), then
    feed a `country,abstracts` table to `geography_comparison.py --cosyne-countries` to
    render the paired `fig15`. Structural prior: CoSyNe's main meeting is US-hosted almost
    every year vs CNS's global rotation.

## D. Content & semantics
11. **Embedding map of the two corpora [corpus].** Project CNS and CoSyNe abstracts into
    a shared sentence-embedding space (UMAP), colour by meeting — do they occupy
    overlapping or separable regions? Quantify with a simple classifier's AUC
    ("how separable are the two communities by abstract text alone?").
12. **Novelty / recombination [corpus].** Per year, measure the average pairwise distance
    of an abstract's keywords in embedding space (atypical combinations = novelty), à la
    Uzzi et al. — is the field getting more or less interdisciplinary?
13. **Method-vs-question framing [now/corpus].** Split the taxonomy into *methods* (RNN,
    optogenetics, Neuropixels) vs *questions* (decision, navigation, memory) and track
    the methods-to-questions ratio per community — is CoSyNe more method-driven?

## E. Representations to add
14. **Small-multiple trajectory grid [now].** One tiny sparkline per keyword, faceted by
    community — the whole vocabulary at a glance, sorted by trend.
15. **Streamgraph of category share over time [now].** Stacked, volume-normalized share
    of the six taxonomy categories — the field's changing "diet" in one ribbon.
16. **Interactive versions [now].** Port `fig8/9` to an HTML/Plotly or D3 widget for the
    Substack (hover for a keyword's trajectory + its CoSyNe/CNS split).
17. **Bump chart of top-10 terms' ranks over time [now].** Rank churn at the top of the
    field's attention — who overtook whom, and when.

## Recommended next three
Given impact per unit effort:
- **#11 embedding separability** — the single most rigorous "are these really two
  communities?" test, with a headline AUC number.
- **#3 temporal community evolution** — an alluvial of the NeuroAI cluster forming is a
  strong, shareable narrative visual.
- **#7 + #5 international collaboration** — the host-adjusted internationalization trend
  plus cross-border collaboration share is the honest version of the globalization story.
