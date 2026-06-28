# CNS Analysis (Plan 2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Turn the 5,394-abstract corpus into scientometric findings: keyword trends (CoSyNe-comparable), data-driven topics, author/geography networks, a title-vs-abstract robustness check, and a CoSyNe×CNS contrast.

**Architecture:** Independent analysis modules under `src/cns_scientometrics/analyze/`, each consuming `data/corpus/corpus.parquet` and writing tables/figures to `outputs/`. Module A (keyword bridge) is dependency-light and replicates the CoSyNe method exactly; Modules B/C need ML/graph deps and run on demand.

**Tech Stack:** pandas, numpy, matplotlib (A, all); sentence-transformers + bertopic + umap-learn + hdbscan (B); networkx + pycountry (C).

## Global Constraints

- Reuse the **exact** CoSyNe keyword taxonomy + normalization (per-10k-words, lowercase, `\b` match for synonyms ≤4 chars else substring) so Module E is apples-to-apples. Taxonomy hardcoded in `analyze/keywords_taxonomy.py` (copied verbatim from CoSyNe `analyze_v2.py`).
- Corpus text tiers: **title-only** and **title + body** — every text analysis runs on both for Module D.
- Outputs (figures, tables) → `outputs/` (gitignored); never commit derived Era C body text.
- Determinism: fixed seeds for UMAP/HDBSCAN; cache embeddings to `data/embeddings/`.

---

### Task A1: Keyword taxonomy + frequency engine (CoSyNe-identical)

**Files:** Create `src/cns_scientometrics/analyze/__init__.py`, `keywords_taxonomy.py` (verbatim KEYWORDS+CATEGORIES), `keyword_trends.py`; Test `tests/test_keyword_trends.py`.

**Interfaces:** Produces `count_keyword(text, synonyms) -> int`; `per_year_frequencies(df, tier="full") -> dict` returning `{keyword: {year: per10k}}` using the CoSyNe formula; `tier` ∈ {title, full} where `full` = title + body.

- [ ] **Step 1: failing test** — assert `count_keyword("we used an rnn and deep learning", SYN)` counts `rnn` via word-boundary (not inside "running") and `deep learning` via substring; assert `per_year_frequencies` returns per-10k values matching a hand-computed fixture (2 abstracts, known word counts).
- [ ] **Step 2:** run → fail.
- [ ] **Step 3:** implement: `count_keyword` (≤4 chars → `\b` regex, else `.count()` on lowercased text); `per_year_frequencies` = Σ keyword counts / Σ words ×10000 per year, over `title` or `title+" "+body.full`.
- [ ] **Step 4:** run → pass.
- [ ] **Step 5:** commit `feat: keyword trend engine (CoSyNe-identical)`.

### Task A2: Keyword trend figures + tables

**Files:** Modify `keyword_trends.py` (add `write_keyword_outputs`); Create `scripts/run_keyword_trends.py`.

**Interfaces:** `write_keyword_outputs(df, out_dir)` → per-category line charts (per-10k vs year), a keyword×year heatmap, and `keyword_frequencies.csv`.

- [ ] Step 1: smoke test asserting CSV + ≥1 PNG written for a 3-abstract df. 2: fail. 3: implement (matplotlib, smoothing window=3 for plots only). 4: pass. 5: run on real corpus, eyeball the AI/ML-rise + enduring-themes curves. 6: commit.

### Task B1: Abstract embeddings (cached)

**Files:** Create `analyze/embeddings.py`; Test `tests/test_embeddings.py` (mock model).

**Interfaces:** `embed_corpus(df, tier, model_name, cache_dir) -> np.ndarray` (sentence-transformers; default `all-MiniLM-L6-v2`, optional SPECTER2); cached to `data/embeddings/<tier>_<model>.npy` keyed by row order + abstract_id hash.

- [ ] TDD with a monkeypatched encoder returning fixed vectors; assert shape + cache hit. Then commit. (Real embedding run is a script step, not a unit test.)

### Task B2: BERTopic dynamic topic model

**Files:** Create `analyze/topics.py`, `scripts/run_topics.py`.

**Interfaces:** `fit_topics(embeddings, docs, seed) -> BERTopic`; `topics_over_time(model, docs, years) -> DataFrame`; optional LLM relabel pass (`label_topics`).

- [ ] Build topic model (UMAP+HDBSCAN, fixed seed), produce topic-prevalence-over-time table + figures + a topic catalogue CSV. Validation = inspect topic coherence on the real corpus; commit script + outputs summary.

### Task C1: Author/affiliation networks

**Files:** Create `analyze/networks.py`, `scripts/run_networks.py`; Test `tests/test_networks.py`.

**Interfaces:** `coauthorship_graph(df) -> nx.Graph`; `country_timeseries(df) -> DataFrame`; `internationalization(df) -> DataFrame` (distinct countries/year, diversity entropy); `top_institutions(df, by_year=False)`.

- [ ] TDD the graph builder + country series on a small df; then run on corpus → collaboration metrics, country trends, internationalization figures. Commit.

### Task D1: Title-vs-abstract robustness

**Files:** Create `analyze/robustness.py`, `scripts/run_robustness.py`.

**Interfaces:** `tier_deltas(df) -> DataFrame` comparing Module A keyword trends and Module B topic assignments under `tier="title"` vs `tier="full"` (term coverage, per-year trend correlation, topic-recovery agreement).

- [ ] Compute + report the deltas as the methods-reflexivity section. Commit.

### Task E1: CoSyNe × CNS contrast (keyword axis)

**Files:** Create `analyze/contrast.py`, `scripts/run_contrast.py`.

**Interfaces:** Loads CoSyNe `keyword_data_full.json` + CNS `keyword_frequencies.csv`; `contrast_table()` aligns shared keywords across both conferences; figures for AI/ML uptake, methods-vs-systems balance, and topic overlap on common years.

- [ ] Build aligned contrast tables + figures (shared keyword axis only, per spec §6 — no topic-level contrast). Commit.

## Self-Review

- Spec coverage: Module A→A1/A2, B→B1/B2, C→C1, D→D1, E→E1. Two text tiers threaded via `tier` param (A1) and exercised in D1.
- Dependencies staged: A is stdlib+pandas+matplotlib (build now); B/C need installs (gated on user go-ahead before the heavy embedding run).
- Determinism: seeds + embedding cache noted in Global Constraints.

## Sequencing

A1→A2 first (immediate CoSyNe-comparable results, no ML deps), then E1 (needs A2 output), then B1→B2 (heavy), C1, D1 (needs B). Build A now; check in before the heavy ML install.
