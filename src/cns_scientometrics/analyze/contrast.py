"""Module E — CoSyNe x CNS contrast on the shared keyword axis.

Aligns the CoSyNe keyword-frequency study (per-10k-words) with the CNS corpus
frequencies (same taxonomy, same normalization) to show how the two communities
diverge: which topics each emphasizes, and their relative AI/ML uptake.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .keywords_taxonomy import CATEGORIES

_CAT_OF = {kw: cat for cat, kws in CATEGORIES.items() for kw in kws}


def load_cosyne(json_path: Path) -> pd.DataFrame:
    j = json.loads(Path(json_path).read_text())
    rows = [
        {"keyword": kw, "year": int(y), "per10k": v, "conference": "CoSyNe"}
        for kw, series in j["frequencies"].items()
        for y, v in series.items()
    ]
    return pd.DataFrame(rows)


def load_cns(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)[["keyword", "year", "per10k"]].copy()
    df["conference"] = "CNS"
    return df


def contrast_table(cosyne: pd.DataFrame, cns: pd.DataFrame, years: range) -> pd.DataFrame:
    """Per-keyword mean frequency in each conference over `years`, with the gap."""
    def _mean(df):
        d = df[df["year"].isin(years)]
        return d.groupby("keyword")["per10k"].mean()

    cos, cn = _mean(cosyne), _mean(cns)
    out = pd.DataFrame({"cosyne": cos, "cns": cn}).fillna(0.0)
    out["category"] = [_CAT_OF.get(k, "Other") for k in out.index]
    out["gap_cns_minus_cosyne"] = out["cns"] - out["cosyne"]
    out["log2_ratio"] = np.log2((out["cns"] + 0.05) / (out["cosyne"] + 0.05))
    return out.sort_values("gap_cns_minus_cosyne", ascending=False)


def write_contrast_outputs(cosyne_json: Path, cns_csv: Path, out_dir: Path, years: range) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_dir = Path(out_dir)
    (out_dir / "figures").mkdir(parents=True, exist_ok=True)
    cosyne, cns = load_cosyne(cosyne_json), load_cns(cns_csv)
    tbl = contrast_table(cosyne, cns, years)
    tbl.to_csv(out_dir / "cosyne_cns_contrast.csv")

    # 1) most divergent keywords (top emphasized by each community)
    top = pd.concat([tbl.head(12), tbl.tail(12)])
    fig, ax = plt.subplots(figsize=(9, 9))
    colors = ["#d1495b" if v < 0 else "#2e86ab" for v in top["gap_cns_minus_cosyne"]]
    ax.barh(top.index, top["gap_cns_minus_cosyne"], color=colors)
    ax.axvline(0, color="k", lw=0.6)
    ax.set_xlabel("Δ frequency per 10k words  (CNS − CoSyNe)")
    ax.set_title("Where the two communities diverge\n(blue = more CNS, red = more CoSyNe)")
    fig.tight_layout()
    fig.savefig(out_dir / "figures" / "divergence.png", dpi=130)
    plt.close(fig)

    # 2) AI/ML category uptake over time, both conferences
    aiml = set(CATEGORIES["AI/ML Methods"])
    fig, ax = plt.subplots(figsize=(10, 6))
    for conf, df in [("CoSyNe", cosyne), ("CNS", cns)]:
        d = df[df["keyword"].isin(aiml) & df["year"].isin(years)]
        s = d.groupby("year")["per10k"].sum()
        ax.plot(s.index, s.rolling(3, center=True, min_periods=1).mean(), label=conf, linewidth=2)
    ax.set_title("AI/ML methods uptake: CoSyNe vs CNS (Σ AI/ML keywords per 10k words)")
    ax.set_xlabel("year")
    ax.set_ylabel("per 10k words")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_dir / "figures" / "aiml_uptake.png", dpi=130)
    plt.close(fig)
    return out_dir
