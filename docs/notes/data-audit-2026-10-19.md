# Data audit — four-meeting generalization (Phase 0)

Run 2026-10-19 from the cloud session. Plan: [`../plans/2026-10-13-four-meeting-generalization.md`](../plans/2026-10-13-four-meeting-generalization.md).
Evidence labels: **[verified]** = measured on data in hand · **[search]** = from search-result
text only, nothing downloaded · **[unverified]** = not checked.

## 1. Network status — still blocked

All 16 hosts probed returned **HTTP 403 on CONNECT** (proxy policy), i.e. the allowlist change
has not reached this session: `{2017,2022,2025,2026}.ccneuro.org`, `openreview.net`,
`api2.openreview.net`, `abstracts.g-node.org`, `portal.g-node.org`, `www.frontiersin.org`,
`zenodo.org`, `doi.org`, `web.archive.org`, `bernstein-network.de`, `www.bernstein-conference.de`,
`www.cnsorg.org`, `www.cosyne.org`. PyPI and GitHub remain reachable. Consequently **no CCN,
Bernstein or CNS\*2026 record has been downloaded or parsed**; only the CoSyNe books (already
in the `cosyne-keywords` repo) could be audited on real data.

## 2. CoSyNe — audited on real data [verified]

Source: `rcfduarte/cosyne-keywords` `data/cosyne_YYYY.txt`, 23 books (2004–2026).
Reproduce: `python scripts/audit_cosyne_coverage.py <data dir>`.

| Window | Status |
|---|---|
| **2004–2013** | Unstructured OCR. 0–4 recoverable ids per book → **word-level keyword frequencies only**; no per-abstract, affiliation or author analyses. |
| **2014–2026** | Structured. Per-abstract records for **96–100%** of distinct accepted ids (after the fix below), 0 duplicate ids, 95.6–98.5% with a resolved country. |

| Year | ids | records | % of ids | with country % | Year | ids | records | % of ids | with country % |
|---|---|---|---|---|---|---|---|---|---|
| 2014 | 342 | 330 | 96.5 | 97.0 | 2021 | 390 | 390 | 100.0 | 98.5 |
| 2015 | 358 | 357 | 99.7 | 95.8 | 2022 | 472 | 460 | 97.5 | 95.9 |
| 2016 | 358 | 358 | 100.0 | 96.6 | 2023 | 464 | 460 | 99.1 | 97.4 |
| 2017 | 382 | 369 | 96.6 | 95.9 | 2024 | 574 | 562 | 97.9 | 96.3 |
| 2018 | 408 | 408 | 100.0 | 96.8 | 2025 | 461 | 458 | 99.3 | 97.2 |
| 2019 | 386 | 372 | 96.4 | 96.8 | 2026 | 716 | 704 | 98.3 | 95.6 |
| 2020 | 415 | 415 | 100.0 | 96.6 | | | | | |

### Defect found and fixed in `analyze/cosyne_programbook.py`
Three bugs in `parse_programbook` (commit `94a56cb`, regression tests added):
1. **Roman sessions II/III were not block starts.** `_ID_HDR` matched `I-<n>` but not
   `II-<n>`/`III-<n>`, so in the pre-2021 books those posters were swallowed into the preceding
   block. **2014–2020 recovered only 26–31% of accepted abstracts** (95–121 of 342–415).
2. **Narrow-wrapped abstracts were dropped** (prose test required a ≥120-char line; invited-talk
   abstracts wrap at ~110). Cost ~25% of 2021–2026.
3. **The last record of every book absorbed the author index** (1,000–9,500 lines).

**Impact on already-committed results** (`results/tables/cosyne_countries.csv`,
`keyword_incidence_cosyne.csv`, fig15, `fig_cooccurrence_cosyne`, and the matching article text
were produced with the buggy parser and are **not regenerated**):
- Geography conclusion is **robust**: US share of CoSyNe abstracts 73.2% → 74.8% (2014–20) and
  65.4% → 66.1% (2021–26); UK 12.4 → 12.3 and 13.5 → 13.6; Germany 7.9 → 7.5 and 10.9 → 10.5.
- Keyword incidence / co-occurrence were **not** re-measured; regenerate before quoting the
  CoSyNe partition Jaccard. `meeting_sizes.csv` is unaffected (it counts ids, not records).

## 3. CNS [partly verified]
- 2007–2025: in the committed aggregates; the raw corpus (`data/`, gitignored) is not in this
  checkout, so it could not be re-audited here.
- Per-year counts of 147 (2022) and 161 (2024) are documented in `CORPUS.md` without a flag and
  sit in the same range as CNS\*2026's 165 items; they may be genuine (smaller hybrid meetings)
  — **[unverified]** until compared against the official indices.
- **CNS\*2026:** Zenodo record 22639749 (Sep 2026; PDF + index CSV; 165 items; per-item DOIs)
  **[search]**. Licence and parseability unchecked.

## 4. Bernstein — hosting map [search]

| Years | Host | Evidence | Notes |
|---|---|---|---|
| 2005–2008 | none found | — | Network symposia pre-dating the open conference; no abstract archive located. |
| 2009 (BCCN 2009, Frankfurt) | Frontiers (call says so) | call text only | No listing or DOI pattern seen. |
| **2010** (Berlin) | Frontiers `conf.fncom.2010.51.*` | listing seen, **140 abstracts** | |
| **2011** (Freiburg, 4–6 Oct) | Frontiers `conf.fncom.2011.53.*` | listing seen | |
| **2012** | Frontiers `conf.fncom.2012.55.*` | listing seen, **265 abstracts** | |
| 2013 | G-Node older portal `portal.g-node.org/abstracts/bc13` | page indexed, content not seen | |
| 2014 (Göttingen, 3–5 Sep), 2015 (Heidelberg, 15–17 Sep) | calls say "published online with DOI" | call text only | No G-Node page found for BC14/BC15. |
| 2016, 2017, 2019, 2021–2026 | `abstracts.g-node.org/conference/BCyy` | pages indexed | BC26: submissions closed; 2026 abstracts may not be published yet. |
| 2018 (Berlin, 26–28 Sep), 2020 | no G-Node page found | — | |

**Assessment:** a **2010–2026 window looks reachable** (Frontiers 2010–12 → G-Node 2013+), with
2009 and 2014/15/18/20 to be located. 2005–2008 look unrecoverable. No submission counts were
found for any year.

## 5. CCN (2-page abstracts) [search]

| Year | Dates / place | Site | Status |
|---|---|---|---|
| 2017 | 6–8 Sep, Columbia (NYC) | `2017.ccneuro.org` | site not surfaced by search |
| 2018 | 5–8 Sep, Philadelphia | `2018.ccneuro.org` | has an "Accepted Papers" section; list not seen |
| 2019 | 13–16 Sep, Berlin | `2019.ccneuro.org` | has an "Accepted Papers" section; list not seen |
| 2020 | — | — | no numbered meeting (inferred from official 7th = 2024) |
| 2021 | online, 7 Sep–1 Oct | `2021.ccneuro.org` | GACs / keynotes / Algonauts format — **may have no 2-page abstract set** |
| 2022–2024 | SF / Oxford / MIT | `YYYY.ccneuro.org` | 2-page author kit seen (2023); lists not seen |
| 2025–2026 | Amsterdam / NYU | OpenReview | 2-pagers on OpenReview; 508 extended-abstract submissions in 2025 |

**Assessment:** 2-page sets are probably recoverable for 2018–2019 and 2022–2026 (site lists /
OpenReview); **2017 and 2021 are the risks**. A realistic CCN window is **2018–2026 minus 2020
(8 meetings)**, pending the probes below.

## 6. Next steps once the network is open (in order)
1. Re-run the 16-host probe; then `zenodo.org/api/records/22639749` → count the index CSV, read licence.
2. CCN: fetch each `YYYY.ccneuro.org` accepted-papers page (2017–2024) and the OpenReview venues
   (2025, 2026); record counts, fields (title/authors/affiliations/abstract), PDF-only or HTML.
3. Bernstein: Frontiers event pages 2009–2013, G-Node `BC14, BC15, BC18, BC20`; Wayback for gaps.
4. Fill this note's matrix with measured counts and decide the final per-meeting windows.
