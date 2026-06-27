"""Corpus assembler: dedupe records, write Parquet + JSONL, emit a QA report."""

import json
from collections import Counter
from pathlib import Path

import pandas as pd

from .schema import AbstractRecord


def write_corpus(records: list[AbstractRecord], out_dir: Path) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    deduped: list[AbstractRecord] = []
    for r in records:
        if r.abstract_id in seen:
            continue
        seen.add(r.abstract_id)
        deduped.append(r)
    rows = [r.model_dump() for r in deduped]
    df = pd.json_normalize(rows, max_level=0)
    df.to_parquet(out_dir / "corpus.parquet", index=False)
    with (out_dir / "corpus.jsonl").open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    n = len(deduped)
    summary = {
        "n_total": n,
        "n_dropped_dupes": len(records) - n,
        "per_year": dict(sorted(Counter(r.year for r in deduped).items())),
        "per_era": dict(sorted(Counter(r.era for r in deduped).items())),
        "per_type": dict(sorted(Counter(r.type for r in deduped).items())),
        "missing_title_rate": round(sum(1 for r in deduped if not r.title) / max(n, 1), 4),
        "missing_body_rate": round(
            sum(1 for r in deduped if not r.body.get("full")) / max(n, 1), 4
        ),
        "country_coverage_rate": round(sum(1 for r in deduped if r.countries) / max(n, 1), 4),
    }
    (out_dir / "qa_report.md").write_text(build_qa_report(summary), encoding="utf-8")
    return summary


def build_qa_report(summary: dict) -> str:
    lines = [
        "# CNS Corpus QA Report",
        "",
        f"- Total abstracts: {summary['n_total']}",
        f"- Dropped duplicates: {summary['n_dropped_dupes']}",
        f"- Missing-title rate: {summary['missing_title_rate']}",
        f"- Missing-body rate: {summary['missing_body_rate']}",
        f"- Country-coverage rate: {summary['country_coverage_rate']}",
        "",
        "## Per year",
        "",
    ]
    lines += [f"- {y}: {n}" for y, n in summary["per_year"].items()]
    lines += ["", "## Per era", ""]
    lines += [f"- Era {e}: {n}" for e, n in summary["per_era"].items()]
    lines += ["", "## Per type", ""]
    lines += [f"- {t}: {n}" for t, n in summary["per_type"].items()]
    return "\n".join(lines) + "\n"
