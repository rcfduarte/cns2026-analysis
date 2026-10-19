# Four-Meeting Generalization Plan (CoSyNe · CNS · Bernstein · CCN)

**Goal:** Extend the CNS×CoSyNe community analysis to the four main computational-neuroscience
meetings — CoSyNe, CNS*, the Bernstein Conference, and CCN — and produce a complete,
comprehensive, publication-ready analysis and write-up. The destination (a journal/outlet vs.
Substack) is deliberately undecided and does not shape the analysis.

**Status:** Phase 0 (data audit) is **partly done**: CoSyNe audited on real data (and a parser
defect fixed); CCN, Bernstein and CNS\*2026 still blocked on network access (§5). Findings:
[`../notes/data-audit-2026-10-19.md`](../notes/data-audit-2026-10-19.md).
Prepared 2026-10-13, revised after the maintainer's decisions (§6). Evidence labels:
**[confirmed]** = stated by an official/primary page seen in search results *or* inspected
locally; **[inferred]** = derived by counting from confirmed facts; **[unverified]** = not
checked, do not publish without checking.

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
| **CNS** | 2007–2025: BMC Neurosci. / J. Comput. Neurosci. supplements. **2026: Zenodo record 22639749** ("Proceedings of the 35th CNS*2026", dated 7 Sep 2026; PDF + index CSV; per-item DOIs) | 2007–2025 **in repo** (5,394); 2026 **found, not yet ingested** | 3 publication eras already parsed. The Zenodo record lists **165 items** (abstracts + keynotes) — check it against the PDF. Licence on Zenodo not yet read [unverified]. 2022–25 counts in `meeting_sizes.csv` (147/161 for 2022/24) are documented in `CORPUS.md` and are in the same range as CNS\*2026's 165 — probably genuine (smaller hybrid meetings), verify against the official indices | Not found [unverified] |
| **CoSyNe** | `rcfduarte/cosyne-keywords` → `data/cosyne_YYYY.txt` (pdftotext of program books) | **2004–2026 in hand** (23 books, 0.4–1.9 MB each). Per-abstract records only **2014–2026** | 2014+ books are structured (id, title, authors, e-mail, affiliation footnotes, prose) and parsed by `analyze/cosyne_programbook.py` — **audited 2026-10-19: after a parser fix, 96–100% of accepted ids are recovered** (it was 26–31% for 2014–20; see audit note). **2004–2013 are unstructured OCR** → keyword-frequency only, no per-abstract/affiliation analyses. Accepted counts 2014–26: 342→716 | Not in repo; not found online [unverified] |
| **Bernstein** | G-Node Conference Abstract Server (`abstracts.g-node.org/conference/BCyy`); Frontiers for early years | G-Node **BC16, BC17, BC19, BC21–BC26 [confirmed present]**; BC13 on the older portal and Frontiers 2010 + 2012 (265 abstracts) [confirmed present]; **BC14, BC15, BC18, BC20 [unverified]**; **2005–2009 and 2011: no archive found** | Posters + invited/contributed talks, DOIs per abstract, session-grouped. BC26 is listed but submissions only just closed — check whether 2026 abstracts are published | **Not found** [unverified] |
| **CCN** | **2-page extended abstracts only (scope decision, §6).** OpenReview (2025–2026); per-year sites `YYYY.ccneuro.org` (2022–2024 seen; 2017–2021 archived) | 2017–2026 exist (no 2020 meeting, see §1); machine-readable only from ~2025 | 8-page CCN-P proceedings (new 2025) are **excluded**. 2-pagers have no DOI. Format/hosting changed across years; 2017–2021 hosting is the biggest unknown | **2025: 508 extended-abstract + 103 proceedings submissions** [confirmed]. 2-pagers "generally accepted" up to an 800-poster cap. 2023/24: no stats found [unverified] |

### Comparable windows (what the data can actually support)
- **Per-abstract analyses** (geography, institutions, co-occurrence, author overlap, embeddings):
  CoSyNe **2014–2026**; CNS **2007–2026**; CCN **2017–2026** if 2017–2021 are recoverable, else
  2022–2026; Bernstein **G-Node era (2016–2026)** at minimum, back to 2010 if Frontiers parses.
  → The **four-way overlap window is 2017–2026** (CCN's lifespan). This is the headline window.
- **Keyword-frequency trends** (word-level, no segmentation needed): CoSyNe from **2004**,
  CNS from 2007, plus whatever Bernstein/CCN years exist. Longer series are two-meeting only.
- Be explicit in the piece about which claims span which years; never splice windows silently.

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
- [ ] **Bernstein early-years hunt (explicit decision, §6):** try, in order, Frontiers
      (2009/2010/2012 and any other `conf.fncom.YYYY` volumes), the G-Node pages for BC14/15/18/20,
      Wayback Machine copies of the 2005–2011 programmes/abstract books, and Bernstein Network
      PDFs. A year counts as "reliable" only if it yields per-abstract title + authors +
      affiliations + body for a stable majority of the programme. **Fallback:** if nothing
      reliable exists before the G-Node era, fix the window at the G-Node era and say so.
- [ ] CCN 2017–2021 recovery: locate each year's 2-page abstract hosting (site PDFs, OpenReview,
      Wayback) and test parseability; otherwise the CCN window starts at 2022.
- [ ] Decide per-meeting year windows from the matrix. **Go/no-go:** a meeting enters the main
      analysis only if it has ≥ ~8 usable years with affiliations (needed for geography/networks).
- [ ] Collect any published submission counts (CCN 2025 already in hand) into `data/submissions.csv`.

**Phase 1 — Ingestion adapters.** `gnode.py` (Bernstein), `frontiers.py` (early Bernstein),
`openreview.py` (CCN 2-pagers), `zenodo.py` (CNS 2026: index CSV + per-item records), CoSyNe
import from the cosyne-keywords program books (reuse `cosyne_programbook.py`; extend it to also
yield title + author names, which the author-overlap analysis needs). One test fixture per
adapter (offline, as in `tests/fixtures/`).

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

**Phase 4 — Write.** Single complete long-form piece, written to stand on its own (no
outlet-specific constraints); reuse the house figure style (`titlebox()`, `source()`,
`spread()` in `scripts/build_article_figures.py`). Methods box states the selection-regime
caveat and the per-claim year windows up front. Interactive chart versions as for the CNS piece.

**Phase 5 — Finalise.** Validation pass (extend `docs/VALIDATION.md` to the new meetings),
README/RESULTS updated, everything regenerable from committed aggregates. Choice of venue is
made after the piece exists.

## 5. Blockers & next steps for the maintainer

- **Network access.** In the environment settings (cloud environment menu in the session
  title bar → *Edit*), either choose a broader access level or add these under *Allowed
  domains* (leave the *Allow package managers* box ticked):
  `ccneuro.org` and each `YYYY.ccneuro.org` (2017–2026) if wildcards are not accepted,
  `openreview.net`, `api2.openreview.net`, `api.openreview.net`,
  `abstracts.g-node.org`, `portal.g-node.org`, `www.g-node.org`,
  `www.frontiersin.org`, `zenodo.org`, `doi.org`, `web.archive.org` (needed for the Bernstein
  early-years hunt), `bernstein-network.de`, `www.bernstein-conference.de`, `www.cnsorg.org`.
  Steps: https://code.claude.com/docs/en/cloud-environments#network-access
  Alternative: run the Phase 0 probe on a local clone.
- ~~CoSyNe data~~ — **resolved:** `rcfduarte/cosyne-keywords` is readable and holds 2004–2026.
- ~~CNS 2026 abstracts~~ — **resolved:** published on Zenodo (record 22639749); ingest once
  `zenodo.org` is reachable. The JCN-PDF route is no longer needed for 2026.

## 6. Decisions (maintainer, 2026-10-13) and remaining questions
**Decided**
1. No target outlet is assumed; build the most complete and comprehensive analysis possible.
2. **CCN = 2-page extended abstracts only**, for comparability. 8-page proceedings excluded.
3. **Bernstein: chase the early years** (Phase 0 hunt). If none is reliable, fix the G-Node era.
4. CoSyNe data source = `rcfduarte/cosyne-keywords`; CNS 2026 = Zenodo.

**Still open**
- Headline framing: "four meetings, one field" (overlap/bridges) vs "the field's centre of
  gravity" (AI/ML shift across meetings) — decide after Phase 3 shows which result is stronger.
- Whether the CNS 2022/24 counts (147/161) are real — settled
  in Phase 2 by comparing against the official indices.
