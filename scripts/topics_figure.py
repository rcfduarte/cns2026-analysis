"""Task F — data-driven topics over time (BERTopic), house-style + interactive.

Reads the BERTopic outputs produced by `scripts/run_topics.py`
(`outputs/topics/{topics_over_time.csv,topic_catalogue.csv}`) and builds:

  * `results/figures/fig5_topics_over_time.png` / `.svg` — static, house style,
    replacing the archived `_source_v1/fig5_topics_over_time`.
  * `results/tables/topics_over_time_shares.csv` and `topic_catalogue_public.csv` —
    committable aggregates (per-year topic shares; topic id/label/keywords/count).
    **No abstract text** — the `Representative_Docs` column is dropped.

The interactive (Datawrapper) version is built by `scripts/export_datawrapper.py`, which
turns these aggregates into upload-ready wide CSVs.

Run:  python scripts/topics_figure.py            # uses outputs/topics/
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TB = ROOT / "results" / "tables"
FG = ROOT / "results" / "figures"

SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8a86", "#e7e7e4"
# qualitative palette (house categorical set, CVD-aware)
PAL = ["#2a78d6", "#e34948", "#1baf7a", "#eb6834", "#4a3aa7",
       "#c98500", "#d55181", "#008300", "#7a7a76", "#2bb8c4"]


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


def _spread(values, min_gap):
    """Nudge label y-positions apart so end-labels don't overlap (order-preserving)."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = list(values)
    for k in range(1, len(order)):
        lo, hi = order[k - 1], order[k]
        if out[hi] - out[lo] < min_gap:
            out[hi] = out[lo] + min_gap
    return out


def _short(name: str, n: int = 3) -> str:
    """"0_visual_v1_model_orientation" -> "visual · v1 · model"."""
    parts = name.split("_")[1:] if name and name[0].isdigit() else name.split("_")
    return " · ".join(parts[:n])


def prepare(topics_dir: Path, top: int = 9):
    tot = pd.read_csv(topics_dir / "topics_over_time.csv")
    cat = pd.read_csv(topics_dir / "topic_catalogue.csv")
    tot["year"] = tot["Timestamp"].round().astype(int)
    yr_tot = tot.groupby("year")["Frequency"].sum()  # all docs (incl. outliers) per year
    keep = (
        tot[tot["Topic"] != -1].groupby("Topic")["Frequency"].sum()
        .sort_values(ascending=False).head(top).index.tolist()
    )
    names = cat.set_index("Topic")["Name"].to_dict()
    piv = (
        tot[tot["Topic"].isin(keep)]
        .pivot_table(index="year", columns="Topic", values="Frequency", fill_value=0)
        .reindex(sorted(yr_tot.index))
    )
    share = piv.div(yr_tot, axis=0) * 100.0  # % of that year's abstracts
    share = share.reindex(columns=keep)
    labels = {t: _short(names.get(t, str(t))) for t in keep}
    return share, labels, names, cat


def fig_static(share: pd.DataFrame, labels: dict):
    sm = share.rolling(3, center=True, min_periods=1).mean()
    fig, ax = plt.subplots(figsize=(11.2, 7.0))
    fig.subplots_adjust(top=0.83, bottom=0.10, left=0.08, right=0.74)
    ends = []
    for i, t in enumerate(share.columns):
        ax.plot(sm.index, sm[t], color=PAL[i % len(PAL)], lw=2.2, zorder=3)
        ends.append(sm[t].iloc[-1])
    ys = _spread(ends, (max(ends) - min(ends) + 1) * 0.055)
    for i, (t, y) in enumerate(zip(share.columns, ys, strict=False)):
        ax.text(sm.index[-1] + 0.25, y, labels[t], color=PAL[i % len(PAL)],
                fontsize=9.5, va="center")
    ax.set_xlim(share.index.min(), share.index.max() + 0.2)
    ax.set_ylabel("share of the year's abstracts (%)")
    ax.set_xlabel("year")
    ax.set_xticks(range(int(share.index.min()), int(share.index.max()) + 1, 3))
    titlebox(fig, "Data-driven topics over time",
             "BERTopic themes over sentence embeddings of every abstract (top themes; 3-yr "
             "smoothed). The classic visual-cortex theme recedes as functional-connectivity rises.")
    source(fig, "Source: CNS abstracts 2007–2024 · BERTopic (all-MiniLM-L6-v2) · share of each "
                "year's abstracts assigned to the theme")
    FG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FG / "fig5_topics_over_time.png", bbox_inches="tight")
    fig.savefig(FG / "fig5_topics_over_time.svg", bbox_inches="tight")
    plt.close(fig)
    print("wrote fig5_topics_over_time (png + svg)")


def write_aggregates(share: pd.DataFrame, labels: dict, cat: pd.DataFrame):
    TB.mkdir(parents=True, exist_ok=True)
    long = share.reset_index().melt(id_vars="year", var_name="topic", value_name="share_pct")
    long["label"] = long["topic"].map(labels)
    long.to_csv(TB / "topics_over_time_shares.csv", index=False)
    # public catalogue: drop the free-text Representative_Docs (contains abstract text)
    pub = cat.drop(columns=[c for c in ("Representative_Docs",) if c in cat.columns])
    pub.to_csv(TB / "topic_catalogue_public.csv", index=False)
    print("wrote topics_over_time_shares.csv + topic_catalogue_public.csv")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--topics-dir", type=Path, default=ROOT / "outputs" / "topics")
    ap.add_argument("--top", type=int, default=9)
    args = ap.parse_args()
    _style()
    share, labels, _names, cat = prepare(args.topics_dir, top=args.top)
    fig_static(share, labels)
    write_aggregates(share, labels, cat)


if __name__ == "__main__":
    main()
