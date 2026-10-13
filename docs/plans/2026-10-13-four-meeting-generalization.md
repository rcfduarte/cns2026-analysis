# Four-Meeting Generalization Plan (CoSyNe · CNS · Bernstein · CCN)

**Goal:** Extend the CNS×CoSyNe community analysis to the four main computational-neuroscience
meetings — CoSyNe, CNS*, the Bernstein Conference, and CCN — write the full piece, offer it
to Emily, and fall back to Substack if it is declined.

**Status:** Planning. Phase 0 (data audit) is blocked on network access, see below.
Prepared 2026-10-13. Evidence labels: **[confirmed]** = stated by an official/primary page seen
in search results; **[inferred]** = derived by counting from confirmed facts; **[unverified]** =
not checked, do not publish without checking.

---

## 1. Editions — what is 2026?

| Meeting | First held | 2026 edition | 2026 venue / dates | Evidence |
|---|---|---|---|---|
| **CNS\*** (OCNS) | 1992 | **35th** | Halifax, Canada · 11–15 Jul 2026 | [confirmed] "35th Annual Computational Neuroscience Meeting" |
| **CoSyNe** | 2004 | **23rd** | Lisbon + Cascais · 12–17 Mar 2026 | [inferred] founded 2004, annual since (2021 virtual); site does not print the ordinal |
| **Bernstein Conference** | 2005 (as network symposia) | **~22nd** | Frankfurt · 28 Sep–1 Oct 2026 | [inferred] 2009 = "5th year", 2010 = "6th year" in organiser calls → 2005 = 1st. **No official ordinal found.** [unverified] |
| **CCN** | 2017 | **9th** | NYU, New York · 3–6 Aug 2026 | [confirmed] 2024 = 7th, 2025 = 8th, 2026 = 9th |

Notes:
- **CCN is 10 calendar years but 9 editions.** Official numbering (7th in 2024) implies one year
  had no numbered meeting; 2020 is the likely gap (2020 existed as a Generative Adversarial
  Collaboration series, 2021 was online-only, 7 Sep–1 Oct). [inferred; 2020's exact status
  not confirmed — check before printing "9th".]
- Bernstein's "~22nd" depends on whether the 2005–2008 symposia count (the 2009 meeting is
  described as the point where it "opened as an international conference"). **Do not print an
  ordinal for Bernstein until the network confirms it** — otherwise say "since 2005".
- Next venues seen: Bernstein 2027 Lausanne (15–18 Sep); CCN 2027 Edinburgh (secondary source).
- Pandemic years are non-comparable formats: CoSyNe 2021, CCN 2020/21, Bernstein 2020/21, CNS 2020/21.

## 2. Data availability

"Accepted abstracts" and "submissions" are different datasets. Accepted items are public for all
four; submission counts are patchy.

| Meeting | Abstract text — where | Years | Format / quirks | Submissions & acceptance |
|---|---|---|---|---|
| **CNS** | BMC Neurosci. / J. Comput. Neurosci. supplements | 2007–2025 **in repo** (5,394) | 3 publication eras, already parsed. **2026 supplement not yet ingested**; whether it is published is unverified. 2022+ are paywalled → user-supplied PDFs | Not found [unverified] |
| **CoSyNe** | Program books on cosyne.org | 2004–2025 in the user's other repo; **2026 book new** | Selective, double-blind review. | Not found for 2026; earlier years may be in organiser posts [unverified] |
| **Bernstein** | G-Node Conference Abstract Server (`abstracts.g-node.org/conference/BCyy`); Frontiers for early years | BC17, BC21–BC26 [confirmed present]; BC13 (older G-Node portal) and Frontiers 2010/2012 (2012: 265 abstracts) [confirmed present]; **BC14–16, BC18–20 [unverified]**; 2005–2009, 2011 unknown | Posters + invited/contributed talks, DOIs per abstract, grouped by session. BC26 page says submissions are closed → 2026 text may only exist after the meeting | **Not found** [unverified] |
| **CCN** | OpenReview (2-pagers + 8-page proceedings, 2025–2026); per-year sites `YYYY.ccneuro.org` (2022–2024 seen, 2017–2021 archived) | 2017–2026 exist; machine-readable only from ~2025 | **Two tiers:** 2-page "extended abstracts" and (new in 2025) 8-page CCN-P proceedings with DOIs. 2-pagers have no DOI. Format changed across years | **2025: 508 extended-abstract + 103 proceedings submissions** [confirmed]. Proceedings: top ~25% accepted. 2-pagers "generally accepted" up to 800 posters. 2023/24: no stats found [unverified] |

### Why "submissions" is a methodological hazard
The four meetings have **different selection regimes**: CoSyNe is highly selective; CNS and
Bernstein accept most; CCN accepts almost everything in scope up to a capacity cap. Acceptance
rate is therefore **not comparable** across meetings, and "submission counts" should be shown as
context (growth/demand), never as a quality ranking. The primary dataset must be *accepted*
abstracts; submissions are an optional second panel where the organisers published them.

### What I could not verify
The cloud sandbox's network policy returned **403 on CONNECT** for every conference host tested
(`ccneuro.org`, `abstracts.g-node.org`, `cosyne.org`, `cnsorg.org`, `bernstein-network.de`) while
PyPI worked, and WebFetch cannot resolve them. Everything above comes from search-result text.
**No record was actually downloaded or parsed**, so "analysable" is *not yet established* —
that is Phase 0.

## 3. Design decisions to fix early

1. **One schema.** Extend `AbstractRecord` with `conference`, `track` (poster / oral / keynote /
   proceedings), `edition_no`, `virtual: bool`. Keep the existing provenance/licence fields.
2. **Text-length normalisation.** CCN 2-pagers and 8-page papers are 5–30× longer than CoSyNe/CNS
   abstracts. The CoSyNe-style per-10k-word keyword rate partly corrects this, but run all text
   analyses on a **title + first-N-words (or Abstract section) tier** as the primary, full text as
   robustness — mirroring the existing title-vs-abstract check.
3. **Shared taxonomy.** Reuse the existing CoSyNe keyword taxonomy verbatim so every pair of
   meetings is directly comparable.
4. **Host-city / geography.** Bernstein is Frankfurt 2024–26 and CCN is US/EU/UK rotating — keep
   the host-adjusted geography approach from `ANALYSIS_IDEAS.md` #5.
5. **Licence/ethics.** Same rule as today: raw text is never committed; only aggregates under
   `results/tables/`. Check OpenReview / G-Node / Frontiers licences before any redistribution.

## 4. Phases

**Phase 0 — Data audit (gate; ~1 session).** Needs network access (see §5).
- [ ] Probe script: for each meeting × year, record reachable? · record count · fields present
      (title, authors, affiliations, body) · licence. Output a coverage matrix.
- [ ] Decide per-meeting year windows from the matrix. **Go/no-go:** a meeting enters the main
      analysis only if it has ≥ ~8 usable years with affiliations (needed for geography/networks).
- [ ] Collect any published submission counts (CCN 2025 already in hand) into `data/submissions.csv`.

**Phase 1 — Ingestion adapters.** `gnode.py` (Bernstein), `frontiers.py` (early Bernstein),
`openreview.py` (CCN, 2-pager + proceedings), CoSyNe import from the other repo, CNS 2026 PDF via
the existing `parse_pdf.py`. One test fixture per adapter (offline, as in `tests/fixtures/`).

**Phase 2 — Harmonise + QA.** Unified corpus parquet; per-meeting QA report in the existing
`qa_report.md` style; affiliation→country via current `normalize.py`; author-name hygiene.

**Phase 3 — Analyses (reuse existing modules, add cross-meeting layer).**
- Keyword trends + AI/ML-uptake across all four (extends `fig1`, `fig4`).
- Pairwise vocabulary overlap / specialisation (extends `fig9`, `fig10`) → a 4×4 matrix.
- **Embedding separability** (ANALYSIS_IDEAS #11): can a classifier tell the four meetings apart
  from text alone? Headline AUC per pair. Strongest "are these really communities" test.
- **Author overlap across meetings** (new): how many people appear in more than one meeting, and
  which meeting is the bridge. Needs conservative name matching; report as a range, not a point.
- Geography / internationalisation (extends `fig13–15`) and meeting sizes (`fig16`).
- Topic model on the pooled corpus; topic × meeting heatmap.
- Optional panel: submissions vs accepted where published.

**Phase 4 — Write.** Single long-form piece; reuse the house figure style
(`titlebox()`, `source()`, `spread()` in `scripts/build_article_figures.py`). Methods box states
the selection-regime caveat up front.

**Phase 5 — Outreach.** Send draft to Emily with a short ask: publish, or OK to self-publish.
Fallback: Substack. (Open question below: who/where is Emily — it affects length and format.)

## 5. Blockers & next steps for the maintainer

- **Network access.** In the environment settings (cloud environment menu in the session
  title bar → *Edit*), widen Network access or add under *Allowed domains*:
  `ccneuro.org` (+ `*.ccneuro.org`), `openreview.net` / `api2.openreview.net`,
  `abstracts.g-node.org`, `www.frontiersin.org`, `www.cosyne.org`, `www.cnsorg.org`,
  `bernstein-network.de`, `link.springer.com`. Steps:
  https://code.claude.com/docs/en/cloud-environments#network-access
  Alternative: run the Phase 0 probe on a local clone.
- **CoSyNe data.** Needs the other repo's path/format and a decision on whether 2026 is included
  (the 2026 program book is not in the existing analysis).
- **CNS 2026 abstracts.** Supply the JCN supplement PDF if published (same dropbox flow as 2022–25).

## 6. Open questions
1. Who/what is Emily (editor of which outlet)? Length, tone, and figure format depend on it.
2. Should CCN's 8-page proceedings be in scope, or only 2-page abstracts for like-for-like?
3. Headline framing: "four meetings, one field" (overlap/bridges) vs "the field's centre of
   gravity" (AI/ML shift across meetings)?
4. Do we want pre-2013 Bernstein, where data is thinnest, or start at the G-Node era?
