# Corpus — composition & data dictionary

Snapshot of the assembled corpus (build of 2026-06-28). The corpus itself is not committed
(`data/` is gitignored); rebuild it with `python -m cns_scientometrics build`.

## Headline

**5,394 abstracts · 19 annual meetings (2007–2025) · 4,943 posters / 400 orals / 51 keynotes.**
0% missing titles or bodies; 98.4% with ≥1 parsed author; ~90% with ≥1 affiliation.

## Per-year composition

| Year | Meeting | Era | Abstracts | with authors |
|------|---------|-----|-----------|--------------|
| 2007 | 16th | A | 234 | 234 |
| 2008 | 17th | A′ (HTML) | 179 | 175 |
| 2009 | 18th | A′ (HTML) | 399 | 395 |
| 2010 | 19th | A | 218 | 213 |
| 2011 | 20th | A | 409 | 404 |
| 2012 | 21st | A | 212 | 205 |
| 2013 | 22nd | A | 460 | 453 |
| 2014 | 23rd | A | 241 | 241 |
| 2015 | 24th | A | 323 | 323 |
| 2016 | 25th | B | 214 | 214 |
| 2017 | 26th | B | 342 | 342 |
| 2018 | 27th | B | 310 | 310 |
| 2019 | 28th | B | 383 | 383 |
| 2020 | 29th | B | 247 | 247 |
| 2021 | 30th | C | 237 | 237 |
| 2022 | 31st | C′ (PDF) | 147 | 139 |
| 2023 | 32nd | C′ (PDF) | 303 | 274 |
| 2024 | 33rd | C′ (PDF) | 161 | 152 |
| 2025 | 34th | C′ (PDF) | 375 | 364 |
| **Total** | | | **5,394** | **5,305** |

By era: A = 2,675 · B = 1,496 · C = 1,223.

## Data dictionary (`AbstractRecord`)

| Field | Type | Notes |
|-------|------|-------|
| `abstract_id` | str | stable id `"<year>-<CODE>"`, e.g. `2017-P1` |
| `year` | int | meeting year |
| `meeting_no` | int | ordinal (year − 1991) |
| `type` | enum | `oral` · `poster` · `keynote` · `frontmatter` |
| `title` | str | |
| `authors[]` | Author | `{raw_name, given, family, openalex_id?}` |
| `affiliations[]` | str | raw affiliation strings |
| `institutions[]` | str | ROR-resolved (best-effort) |
| `countries[]` | str | ISO codes (best-effort) |
| `body{background,methods,results,full}` | dict | structured where available; `full` always populated |
| `references[]` | str | when present in source |
| `doi`, `pmcid` | str? | provenance |
| `era` | enum | `A` · `B` · `C` |
| `license` | enum | `cc-by` (2007–2020) · `free-to-read` (2021–2025) |
| `source_url` | str | |

## Caveats

- **Affiliation resolution is best-effort** (ROR); ~90% of records carry ≥1 affiliation,
  and PDF-era affiliations occasionally wrap across lines into two strings.
- **~1.3% short bodies**, concentrated in keynotes whose figures interrupt PDF text flow.
- **Type granularity** depends on the source's code scheme; featured/invited talks are
  folded into `oral`.
- **Licensing:** 2021–2025 bodies are free-to-read but not CC-BY — see `LICENSE`.

## Provenance

Each record carries its `doi`/`pmcid` and `source_url`. Detailed per-era acquisition and the
data-availability findings (the 2008/09 PMC gap, the 2022–25 paywall) are in
[`METHODS.md`](METHODS.md) and [`notes/build-log-2026-06-27.md`](notes/build-log-2026-06-27.md).
