# Handoff — finish the CNS × CoSyNe community analysis (local)

**You are Claude Code running on the maintainer's laptop, which has the private data this
remote session could not reach.** A prior session built the full analysis + article from
committed aggregates and wrote all the code for the remaining data-dependent tasks. Your
job is to run those against the real data, verify the outputs, fold the real numbers into
the write-up, and push.

Work on branch **`claude/community-analysis-substack-ljnve7`**. Keep commits scoped; keep
`ruff` clean and `pytest -q` green; push to the same branch.

## First, orient (read these — don't reinvent)
- `docs/RUNBOOK.md` — exact commands for every step below.
- `docs/ARTICLE.md` — the Substack draft you'll update with real results.
- `docs/VALIDATION.md` — methods review + what's already verified.
- `docs/ANALYSIS_IDEAS.md` — optional follow-ups (§ "Recommended next three").
- `results/README.md` — figure/table index.
- Reuse the existing house style: the `titlebox()`, `source()`, `spread()` helpers and the
  validated palette in `scripts/build_article_figures.py` / `scripts/keyword_networks.py`.
  New figures must match it (same fonts, colours, title/subtitle/source layout).

## Setup
```bash
git fetch origin claude/community-analysis-substack-ljnve7
git checkout claude/community-analysis-substack-ljnve7
pip install -e ".[dev,analysis]"     # add ,topics only if you do Task F
pytest -q                            # expect 29 passed, 1 deselected
```

## Data you need from the maintainer (ask if paths unknown)
1. **CNS corpus parquet** — the one `src/cns_scientometrics/analyze/networks.py` reads
   (columns: `year`, `title`, `authors[{raw_name}]`, `affiliations[list[str]]`,
   `body{full}`). Likely under the gitignored `data/`.
2. **CoSyNe abstracts** from the *other repo* — path + format (parquet/jsonl/json/csv).
   Confirm whether records include **author affiliations** (needed for geography) and
   **full abstract text** (needed for co-occurrence). If CoSyNe is only keyword
   frequencies with no abstracts, geography/co-occurrence for CoSyNe is not possible —
   report that and stop at Task D.

Before writing anything, **inspect the CoSyNe schema** (print columns + one row) and state
exactly what's computable.

---

## Tasks (in order)

### A. CNS institutions & collaboration — needs CNS corpus
```bash
python scripts/affiliation_analysis.py --corpus "$CNS" --export
```
Produces `fig11_top_institutions`, `fig12_institution_network`, `fig13_country_shares`
and exports `results/tables/{institution_stats,institution_edges,country_year_totals,
keyword_incidence_cns}.csv`.
- **Verify visually**: open each PNG; fix label collisions / empty-graph thresholds
  (`institution_of()` is heuristic — sanity-check the top-20 institution names and merge
  obvious duplicates/aliases if needed, e.g. "MIT" vs "Massachusetts Institute of
  Technology"; extend the alias handling in `affiliation_analysis.py` if the parse is
  noisy).

### B. True CNS keyword co-occurrence network — needs the export from A
```bash
python scripts/keyword_networks.py --incidence results/tables/keyword_incidence_cns.csv
```
Produces `fig_cooccurrence_cns`. If the graph is too dense/sparse, tune `min_count` /
`npmi_thresh` in `cooccurrence_network()`.

### C. Bring in CoSyNe — needs the other repo's abstracts
```bash
python scripts/adapt_cosyne.py --abstracts "$COS"      # add --text-col/--affil-col/--year-col if needed
```
Produces `results/tables/cosyne_countries.csv` and `keyword_incidence_cosyne.csv` (same
taxonomy as CNS → directly comparable). The script prints the columns it detected; if the
CoSyNe layout is unusual, pass the right `--*-col` flags or adjust the loader in
`adapt_cosyne.py` (you can see both repos — do what's correct for the real schema).

### D. CoSyNe vs CNS geography — the hypothesis test
```bash
python scripts/geography_comparison.py --cosyne-countries results/tables/cosyne_countries.csv
```
Produces `fig15_cns_cosyne_geography` (paired regional bars). This settles "CoSyNe = US,
CNS = EU." **Extend `REGION` in `geography_comparison.py`** if CoSyNe surfaces countries
not yet mapped (add them to Europe/North America/Asia-Pacific). Report the CoSyNe US share
and Europe share.

### E. CoSyNe vs CNS community structure — needs B + C
```bash
python scripts/keyword_networks.py \
    --incidence results/tables/keyword_incidence_cns.csv \
    --cosyne-incidence results/tables/keyword_incidence_cosyne.csv
```
Produces `fig_cooccurrence_cns`, `fig_cooccurrence_cosyne`, and prints the **partition
co-membership Jaccard** (how differently the two fields cluster the shared keyword set).
Capture that number.

### F. (Optional) Topics — needs `.[topics]` + CNS corpus
The original BERTopic pipeline (`scripts/run_topics.py`) is intact but its figure was
dropped from the new suite. If you want a topics figure, regenerate `topic_catalogue.csv`
+ `doc_topics.csv` and build a clean, house-style "topics over time" figure to replace the
archived `_source_v1/fig5_topics_over_time`. Optional.

---

## Then: fold real results into the write-up
Currently the article/docs describe the CoSyNe geography + co-occurrence as *pending*. Once
D and E produce real numbers:
- **`docs/ARTICLE.md`**: in the geography section replace the "coded and waiting (`fig15`)"
  paragraph with the real CNS-vs-CoSyNe result + embed `fig15`. In the community-structure
  section, add the co-occurrence finding + the partition-Jaccard number (does CoSyNe
  cluster concepts the same way CNS does?). Add the institution figures where relevant.
- **`docs/VALIDATION.md`** and **`results/README.md`**: add the new figures/tables and drop
  the "await the private corpus" caveats that no longer apply.
- Keep every new figure in the same editorial style; **open each PNG and eyeball it**
  (label collisions, overflow) before committing.

## Definition of done
- [ ] figs 11, 12, 13, 15, `fig_cooccurrence_cns`, `fig_cooccurrence_cosyne` generated and
      visually clean (PNG **and** SVG).
- [ ] CoSyNe US/Europe shares and the CNS-vs-CoSyNe partition Jaccard reported in the article.
- [ ] `docs/ARTICLE.md` updated so no section still says a result is "pending/coded and
      waiting"; all embedded image paths resolve.
- [ ] Only **non-sensitive aggregates** committed under `results/tables/` (country counts,
      institution stats/edges, per-abstract 0/1 keyword incidence — **never** abstract
      text). `data/` stays gitignored.
- [ ] `ruff check src scripts` clean; `pytest -q` green.
- [ ] Commit the aggregates + figures + doc updates and `git push -u origin
      claude/community-analysis-substack-ljnve7`.

## Guardrails
- Don't commit raw abstract text or the corpus. If unsure whether an output is shareable,
  it must be an aggregate (counts / flags), not text.
- Prefer editing the existing scripts over new ones; match the established style.
- If a CoSyNe field is missing (no affiliations or no text), don't fake it — report the
  gap and complete the half that's possible.
- Ask the maintainer only for data paths / schema; everything else is decided in-repo.
