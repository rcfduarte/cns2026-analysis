# Results — CNS scientometrics (2007–2025)

Findings from the analysis layer (Plan 2) over the 5,394-abstract corpus. All numbers are
regenerable via the scripts in `scripts/`; figures land in `outputs/` (gitignored).

## A — Keyword trends (CoSyNe-identical method)

Per-10k-word frequency of the curated taxonomy across 2007–2025. Highlights:

- **AI/ML rises steeply from ~2015.** `deep learning` climbs to a ~2020 peak; `RNN` jumps
  after 2019; **`LLM` appears and takes off from 2023**; generative models and
  `backpropagation` rise recently.
- **Top rising terms (2023–25 vs 2011–13, per-10k):** `manifold` (+4.8), `connectomics`
  (+4.0), `mouse` (+4.8), `navigation`, `dimensionality`, `plasticity`.
- **Top falling:** `inhibition` (−6.9), `spiking` (−6.1), `noise`, `recurrence`,
  `naturalistic` — the field is shifting from classic spiking/biophysical framing toward
  population/manifold/ML language.

Outputs: `outputs/keyword_trends/keyword_frequencies.csv` + per-category trend PNGs + heatmap.

## B — Data-driven topics (BERTopic, dynamic)

Sentence-embedded (all-MiniLM-L6-v2) + UMAP + HDBSCAN over title+abstract.

- **38 coherent topics** (+1,850 outlier docs). Recognisable comp-neuro themes:
  visual/V1/orientation, decision/reward/learning, functional connectivity/fMRI,
  gamma synchronization, seizure/epilepsy, calcium/synaptic release, cerebellar/Purkinje,
  STN/DBS/Parkinson's, ion-channel models, criticality/avalanches.
- **Over time:** the functional-connectivity/fMRI topic rises across the period while the
  classic visual/V1 topic declines from its early dominance.

Outputs: `outputs/topics/topic_catalogue.csv`, `topics_over_time.csv`, figure.

## C — Author & geography networks

- **10,194 unique authors**, **33,341 co-authorship edges**.
- **Top countries** (author-affiliations): US (1,673), Germany (929), UK (600), France
  (415), Japan (289), Spain, Australia, Italy.
- **Internationalization rises:** country-diversity (Shannon entropy) grows from ~3.18
  bits (2007) to ~4.17 (2025); distinct countries per meeting 24–41.

Outputs: `outputs/networks/internationalization.csv`, `country_timeseries.csv`,
`top_collaborators.csv`, figures.

## D — Title-only vs title+abstract robustness (the reflexivity check)

Quantifies how much conclusions depend on having the full abstract vs only the title:

- **Keyword axis:** median per-year trajectory correlation between tiers = **0.648**;
  38/55 keywords fall below 0.70. Titles *overweight* dense terms (e.g. `oscillation`
  37 vs 14 per-10k in full text) and miss several trends.
- **Semantic axis:** mean cosine similarity between a document's title-only and
  title+abstract embedding = **0.73** (median 0.74, 10th percentile 0.61).

**Conclusion:** title-only scientometrics is a materially lossy proxy for the full
abstract — both lexically and semantically. Depth matters; analyses run on titles alone
would draw measurably different conclusions.

Outputs: `outputs/robustness/keyword_tier_deltas.csv`, `robustness_summary.csv`.

## E — CoSyNe × CNS contrast (shared keyword axis)

Same taxonomy and normalization as the CoSyNe study, 2007–2025 overlap.

- **CNS is the mechanistic/biophysical community:** `oscillation` (+9.3), `inhibition`
  (+9.1), `plasticity` (+6.2), `dendritic` (+5.1), `spiking` (+4.0) all higher than CoSyNe.
- **CoSyNe is the systems/behaviour community:** `behavior` (+21.4 toward CoSyNe), `cortex`,
  `primate`, `mouse`, `decision`, `population`, `visual`, `Bayesian` all higher.
- **AI/ML uptake:** both ramp from ~2015, but **CoSyNe adopts it harder** and the gap
  widens — consistent with CoSyNe sitting closer to NeuroAI while CNS stays mechanistic.

Outputs: `outputs/contrast/cosyne_cns_contrast.csv`, divergence + AI/ML-uptake figures.

## Caveats

- Frequencies follow the CoSyNe convention (overlapping synonyms counted separately;
  longer body text dilutes per-10k rates vs title-dense text — see Module D).
- Geography is parsed from raw affiliation strings (best-effort; ~90% coverage).
- BERTopic counts are raw per-year; normalising by yearly abstract volume is a Plan-3 polish.
- The CoSyNe×CNS contrast is intentionally keyword-axis only (CoSyNe has no per-abstract
  structure for a topic-level comparison).
