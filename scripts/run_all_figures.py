"""Plan 3 — regenerate every publication figure + aggregate table into results/."""

import argparse
from pathlib import Path

from cns_scientometrics.analyze.figures import generate_all

_COSYNE = "/home/neuro/Desktop/Assets/claude/outputs/cosyne-analysis/figures_v2/keyword_data_full.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="data/corpus/corpus.parquet")
    ap.add_argument("--cosyne", default=_COSYNE)
    ap.add_argument("--out", default="results")
    ap.add_argument("--topics-csv", default="outputs/topics/doc_topics.csv")
    ap.add_argument("--topic-info", default="outputs/topics/topic_catalogue.csv")
    args = ap.parse_args()
    out = generate_all(
        Path(args.corpus),
        Path(args.cosyne),
        Path(args.out),
        topics_csv=Path(args.topics_csv),
        info_csv=Path(args.topic_info),
    )
    print(f"wrote figures + tables to {out}/")


if __name__ == "__main__":
    main()
