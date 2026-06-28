"""Generate the CoSyNe x CNS contrast (Module E)."""

import argparse
from pathlib import Path

from cns_scientometrics.analyze.contrast import write_contrast_outputs

_COSYNE = "/home/neuro/Desktop/Assets/claude/outputs/cosyne-analysis/figures_v2/keyword_data_full.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cosyne", default=_COSYNE)
    ap.add_argument("--cns", default="outputs/keyword_trends/keyword_frequencies.csv")
    ap.add_argument("--out", default="outputs/contrast")
    ap.add_argument("--from-year", type=int, default=2007)
    ap.add_argument("--to-year", type=int, default=2025)
    args = ap.parse_args()
    out = write_contrast_outputs(
        Path(args.cosyne), Path(args.cns), Path(args.out), range(args.from_year, args.to_year + 1)
    )
    print(f"wrote {out}/cosyne_cns_contrast.csv and {out}/figures/*.png")


if __name__ == "__main__":
    main()
