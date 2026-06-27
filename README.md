# cns-scientometrics

Scientometric analysis of CNS/OCNS (Organization for Computational Neuroscience) annual
meeting abstracts, 2007–2024/25. Builds a clean canonical per-abstract corpus and runs
data-driven topic modeling, author/geography networks, and a contrast against the CoSyNe
conference — a deliberately deeper companion to the prior CoSyNe keyword-frequency study.

See `docs/specs/2026-06-27-cns-scientometrics-design.md` for the design and
`docs/plans/` for implementation plans.

## Quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q                       # offline unit tests
python -m cns_scientometrics build --years 2007-2024 --out data/corpus
```

Set `NCBI_API_KEY` for faster acquisition (10 req/s vs 3).

## Data eras & licensing

- 2007–2015 — BMC Neuroscience, one article per abstract, **CC-BY**.
- 2016–2020 — BMC Neuroscience, bundled "Part 1/2/3" articles, CC-BY.
- 2021–2025 — J. Computational Neuroscience, one article per meeting, **free-to-read** (not CC-BY; do not redistribute raw body text).
