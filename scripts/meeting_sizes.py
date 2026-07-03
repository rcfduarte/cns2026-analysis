"""Meeting size over time — accepted abstracts per year, CNS vs CoSyNe.

Two different-but-comparable counts of "how big is the meeting":
  * CNS      — abstracts in the harvested BMC/OCNS corpus (poster + oral + keynote).
               Harvest completeness varies year to year, so treat as a lower bound.
  * CoSyNe   — distinct poster + talk identifiers counted in the program books
               (`cns_scientometrics.analyze.cosyne_programbook.accepted_counts`).
               Recoverable from 2014 on (earlier program books are unstructured OCR).

Writes the committable aggregate `results/tables/meeting_sizes.csv` and the figure
`fig16_meeting_sizes` (PNG + SVG), in the house style.

Run:
  python scripts/meeting_sizes.py --corpus data/corpus/corpus.parquet \
      --cosyne-dir ~/repos/cosyne-keywords/data
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from cns_scientometrics.analyze.cosyne_programbook import accepted_counts

ROOT = Path(__file__).resolve().parents[1]
TB = ROOT / "results" / "tables"
FG = ROOT / "results" / "figures"

SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8a86", "#e7e7e4"
BLUE, RED = "#2a78d6", "#e34948"  # CNS / CoSyNe (house convention)


def _style():
    mpl.rcParams.update({
        "figure.facecolor": SURFACE, "savefig.facecolor": SURFACE, "axes.facecolor": SURFACE,
        "axes.edgecolor": "#c9c9c5", "axes.grid": True, "axes.axisbelow": True,
        "grid.color": GRID, "axes.spines.top": False, "axes.spines.right": False,
        "font.family": "DejaVu Sans", "font.size": 12, "text.color": INK,
        "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    })


def titlebox(fig, title, subtitle, x=0.045, y=0.965):
    fig.text(x, y, title, ha="left", va="top", fontsize=17, fontweight="bold", color=INK)
    fig.text(x, y - 0.052, subtitle, ha="left", va="top", fontsize=12, color=INK2)


def source(fig, text, x=0.045, y=0.015):
    fig.text(x, y, text, ha="left", va="bottom", fontsize=9, color=MUTED)


def build(corpus: Path, cosyne_dir: Path) -> pd.DataFrame:
    cns = (
        pd.read_parquet(corpus, columns=["year"])
        .value_counts("year").sort_index().rename("cns_abstracts").reset_index()
    )
    cos = accepted_counts(cosyne_dir)[["year", "accepted"]].rename(
        columns={"accepted": "cosyne_abstracts"}
    )
    m = cns.merge(cos, on="year", how="outer").sort_values("year").reset_index(drop=True)
    return m


def fig_meeting_sizes(m: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(10.6, 6.3))
    fig.subplots_adjust(top=0.80, bottom=0.12, left=0.09, right=0.86)

    cns = m.dropna(subset=["cns_abstracts"])
    cos = m.dropna(subset=["cosyne_abstracts"])
    ax.plot(cns["year"], cns["cns_abstracts"], color=BLUE, lw=2.6, marker="o", ms=5, zorder=3)
    ax.plot(cos["year"], cos["cosyne_abstracts"], color=RED, lw=2.6, marker="s", ms=5, zorder=3)
    ax.text(cns["year"].iloc[-1] + 0.15, cns["cns_abstracts"].iloc[-1], "CNS",
            color=BLUE, fontsize=11.5, va="center", fontweight="bold")
    ax.text(cos["year"].iloc[-1] + 0.15, cos["cosyne_abstracts"].iloc[-1], "CoSyNe",
            color=RED, fontsize=11.5, va="center", fontweight="bold")

    ax.set_ylabel("accepted abstracts (posters + talks)")
    ax.set_xlabel("year")
    ax.set_ylim(0, max(m[["cns_abstracts", "cosyne_abstracts"]].max()) * 1.12)
    ax.set_xlim(m["year"].min() - 0.5, m["year"].max() + 1.4)
    ax.set_xticks(range(int(m["year"].min()), int(m["year"].max()) + 1, 2))

    # mean ratio over the overlap (robust to CNS's year-to-year harvest noise)
    ov = m.dropna(subset=["cns_abstracts", "cosyne_abstracts"])
    ratio = ov["cosyne_abstracts"].mean() / ov["cns_abstracts"].mean()
    box = (f"Overlap {int(ov['year'].min())}–{int(ov['year'].max())}\n"
           f"CoSyNe mean:  {ov['cosyne_abstracts'].mean():.0f}/yr\n"
           f"CNS mean:       {ov['cns_abstracts'].mean():.0f}/yr\n"
           f"CoSyNe / CNS:  {ratio:.1f}× (mean)")
    ax.text(0.03, 0.97, box, transform=ax.transAxes, fontsize=9.5, color=INK2, va="top",
            bbox=dict(boxstyle="round,pad=0.5", fc="#f3f3f1", ec="#dddddd"))

    titlebox(fig, "CoSyNe is the larger meeting — and pulling away",
             "Accepted abstracts per year. CoSyNe overtakes CNS in the mid-2010s and runs about "
             "1.5× larger through the 2020s (wider in CoSyNe's peak years).")
    source(fig, "Source: CNS = harvested BMC/OCNS corpus (poster+oral+keynote; harvest varies by "
                "year) · CoSyNe = program-book poster+talk ids (2014– only; older OCR unparseable)")
    fig.savefig(FG / "fig16_meeting_sizes.png", bbox_inches="tight")
    fig.savefig(FG / "fig16_meeting_sizes.svg", bbox_inches="tight")
    plt.close(fig)
    print("wrote fig16_meeting_sizes")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", required=True, type=Path, help="CNS corpus parquet")
    ap.add_argument("--cosyne-dir", required=True, type=Path, help="dir of cosyne_YYYY.txt")
    args = ap.parse_args()

    _style()
    TB.mkdir(parents=True, exist_ok=True)
    FG.mkdir(parents=True, exist_ok=True)
    m = build(args.corpus, args.cosyne_dir)
    m.to_csv(TB / "meeting_sizes.csv", index=False)
    print("wrote meeting_sizes.csv")
    fig_meeting_sizes(m)
    ov = m.dropna(subset=["cns_abstracts", "cosyne_abstracts"])
    print(f"  overlap {int(ov['year'].min())}-{int(ov['year'].max())}: "
          f"CoSyNe mean {ov['cosyne_abstracts'].mean():.0f}/yr vs CNS {ov['cns_abstracts'].mean():.0f}/yr")


if __name__ == "__main__":
    main()
