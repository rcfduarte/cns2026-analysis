"""Generate keyword-trend tables + figures from the corpus (Module A)."""

import argparse
from pathlib import Path

import pandas as pd

from cns_scientometrics.analyze.keyword_trends import write_keyword_outputs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="data/corpus/corpus.parquet")
    ap.add_argument("--out", default="outputs/keyword_trends")
    ap.add_argument("--tier", default="full", choices=["title", "full"])
    args = ap.parse_args()
    df = pd.read_parquet(args.corpus)
    out = write_keyword_outputs(df, Path(args.out), tier=args.tier)
    print(f"wrote {out}/keyword_frequencies.csv and {out}/figures/*.png ({len(df)} abstracts)")


if __name__ == "__main__":
    main()
