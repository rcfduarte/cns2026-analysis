"""Generate author/geography network outputs from the corpus (Module C)."""

import argparse
from pathlib import Path

import pandas as pd

from cns_scientometrics.analyze.networks import (
    coauthorship_graph,
    top_countries,
    write_network_outputs,
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="data/corpus/corpus.parquet")
    ap.add_argument("--out", default="outputs/networks")
    args = ap.parse_args()
    df = pd.read_parquet(args.corpus)
    out = write_network_outputs(df, Path(args.out))
    g = coauthorship_graph(df)
    print(f"authors={g.number_of_nodes()} collaborations={g.number_of_edges()}")
    print("top countries:", dict(top_countries(df, 8)))
    print(f"wrote {out}/*.csv and {out}/figures/*.png")


if __name__ == "__main__":
    main()
