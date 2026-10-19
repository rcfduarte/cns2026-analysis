"""Audit how much of each CoSyNe program book the per-abstract parser recovers.

For every ``cosyne_YYYY.txt`` it compares the number of segmented records against the number
of distinct accepted-abstract ids found in the book (``accepted_counts``), and reports the
share of records with parsed affiliations / a resolved country. Years whose books are
unstructured OCR (2004--2013) have no ids and show 0 records by design.

Usage:
  python scripts/audit_cosyne_coverage.py ~/repos/cosyne-keywords/data [--out audit.csv]
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

from cns_scientometrics.analyze.cosyne_programbook import (
    accepted_counts,
    parse_programbook,
    record_countries_by_institution,
)


def audit(data_dir: Path) -> pd.DataFrame:
    ids = accepted_counts(data_dir, min_posters=1).set_index("year")["accepted"]
    rows = []
    for f in sorted(data_dir.glob("cosyne_*.txt")):
        year = int(re.search(r"(\d{4})", f.name).group(1))
        recs = parse_programbook(f)
        n, n_ids = len(recs), int(ids.get(year, 0))
        lens = sorted(len(r["text"].splitlines()) for r in recs)
        rows.append(
            {
                "year": year,
                "ids": n_ids,
                "records": n,
                "records_pct_of_ids": round(100 * n / n_ids, 1) if n_ids else None,
                "with_affil_pct": round(100 * sum(bool(r["affiliations"]) for r in recs) / n, 1)
                if n
                else None,
                "with_country_pct": round(
                    100
                    * sum(bool(record_countries_by_institution(r["affiliations"])) for r in recs)
                    / n,
                    1,
                )
                if n
                else None,
                "longest_record_lines": lens[-1] if lens else None,
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("data_dir", type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    df = audit(args.data_dir)
    print(df.to_string(index=False))
    if args.out:
        df.to_csv(args.out, index=False)


if __name__ == "__main__":
    main()
