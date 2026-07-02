# Runbook — regenerate everything locally (incl. the CoSyNe side)

This is the full local workflow for Claude Code (or you) on a clone that has the private
data. Nothing here needs network access; all outputs land in `results/`.

## 0. Setup
```bash
git fetch origin claude/community-analysis-substack-ljnve7
git checkout claude/community-analysis-substack-ljnve7
pip install -e ".[dev,analysis]"      # add ,topics for BERTopic
pytest -q                              # 29 pass, 1 network-deselected
```

## 1. Committed-data figures — no corpus needed (verify the toolchain)
```bash
python scripts/recover_tables_from_figures.py   # recovered_*.csv from archived SVGs
python scripts/build_article_figures.py         # fig1–7 + figS1
python scripts/keyword_networks.py              # fig8 (network), fig9 (map), fig10 (overlap)
python scripts/geography_comparison.py          # fig14 (CNS origins by region)
```

## 2. CNS corpus analyses — need the CNS corpus parquet
```bash
CNS=/path/to/cns_corpus.parquet     # the parquet analyze/networks.py expects

# institutions + collaboration network + scale-normalized country shares,
# and export shareable aggregates (no abstract text) so they can be committed:
python scripts/affiliation_analysis.py --corpus "$CNS" --export
#   -> fig11 (top institutions), fig12 (institution network), fig13 (country shares)
#   -> results/tables/{institution_stats,institution_edges,country_year_totals,
#                      keyword_incidence_cns}.csv

# true per-abstract keyword co-occurrence network (CNS):
python scripts/keyword_networks.py --incidence results/tables/keyword_incidence_cns.csv
#   -> fig_cooccurrence_cns
```

## 3. CoSyNe side — from your *other* repo's CoSyNe abstracts
The CoSyNe data in THIS repo is keyword-frequencies only (no affiliations). Point the
adapter at the other repo's abstracts (parquet / jsonl / json / csv). It auto-detects the
text / affiliation / year columns (override with `--text-col` / `--affil-col` /
`--year-col`) and writes the two tables the pipeline consumes — **non-sensitive
aggregates** (country counts + per-abstract 0/1 keyword flags, no text):
```bash
COS=/path/to/other-repo/cosyne_abstracts.parquet
python scripts/adapt_cosyne.py --abstracts "$COS"
#   -> results/tables/cosyne_countries.csv
#   -> results/tables/keyword_incidence_cosyne.csv   (SAME taxonomy as CNS -> comparable)

# (a) geography: paired CNS vs CoSyNe regional composition
python scripts/geography_comparison.py --cosyne-countries results/tables/cosyne_countries.csv
#   -> fig15_cns_cosyne_geography   (tests "CoSyNe = US, CNS = EU" head-to-head)

# (b) community structure: co-occurrence networks for BOTH + partition overlap
python scripts/keyword_networks.py \
    --incidence results/tables/keyword_incidence_cns.csv \
    --cosyne-incidence results/tables/keyword_incidence_cosyne.csv
#   -> fig_cooccurrence_cns, fig_cooccurrence_cosyne
#   -> prints partition co-membership Jaccard (how differently the two fields cluster
#      the shared keyword set)
```

## 4. Commit the shareable aggregates (optional)
The `results/tables/*.csv` above carry no abstract text and are safe to commit, which
makes every figure regenerable anywhere (as the CNS figures already are):
```bash
git add results/tables/*.csv results/figures/*.png results/figures/*.svg
git commit -m "data: institution + co-occurrence + CoSyNe aggregates" && git push
```
Push those and the remote session can finish/iterate on the figures without your raw data.

## Where things are
- Narrative: `docs/ARTICLE.md` · methods review: `docs/VALIDATION.md`
- Further ideas: `docs/ANALYSIS_IDEAS.md` · figure/table index: `results/README.md`
- If a CoSyNe corpus column layout is unusual, `scripts/adapt_cosyne.py` prints the
  columns it sees — pass the right `--*-col` flags, or have local Claude Code adjust it.
