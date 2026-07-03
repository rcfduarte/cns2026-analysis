"""Countries / regions of origin — CNS (committed data) and the CoSyNe comparison hook.

The CNS side runs from the committed `recovered_countries_over_time.csv` (top-8 origin
countries). The CoSyNe side needs CoSyNe author affiliations, which the project does NOT
have (the CoSyNe data is keyword-frequency only). When a CoSyNe country table is
available (see `--cosyne-countries`), the same regional split is drawn side by side.

Run:  python scripts/geography_comparison.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TB = ROOT / "results" / "tables"
FG = ROOT / "results" / "figures"

SURFACE, INK, INK2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8a86"
EUROPE, NAM, APAC = "#2a78d6", "#eb6834", "#1baf7a"

REGION = {
    # North America
    "United States": "North America", "Canada": "North America", "Mexico": "North America",
    # Europe
    "Germany": "Europe", "United Kingdom": "Europe", "France": "Europe",
    "Spain": "Europe", "Italy": "Europe", "Netherlands": "Europe",
    "Switzerland": "Europe", "Sweden": "Europe", "Austria": "Europe",
    "Portugal": "Europe", "Belgium": "Europe", "Norway": "Europe",
    "Finland": "Europe", "Denmark": "Europe", "Hungary": "Europe",
    "Ireland": "Europe", "Slovenia": "Europe",
    # Asia-Pacific
    "Japan": "Asia-Pacific", "Australia": "Asia-Pacific", "China": "Asia-Pacific",
    "India": "Asia-Pacific", "South Korea": "Asia-Pacific", "Korea, Republic of": "Asia-Pacific",
    "Singapore": "Asia-Pacific", "Hong Kong": "Asia-Pacific",
    # Israel, Brazil, etc. fall through to "Other" (kept identical on both sides)
}
RCOLOR = {"Europe": EUROPE, "North America": NAM, "Asia-Pacific": APAC, "Other": MUTED}


def _style():
    mpl.rcParams.update({
        "figure.facecolor": SURFACE, "savefig.facecolor": SURFACE, "axes.facecolor": SURFACE,
        "axes.edgecolor": "#c9c9c5", "axes.grid": True, "axes.axisbelow": True,
        "grid.color": "#e7e7e4", "axes.spines.top": False, "axes.spines.right": False,
        "font.family": "DejaVu Sans", "font.size": 12, "text.color": INK,
        "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    })


def titlebox(fig, title, subtitle, y=0.965):
    fig.text(0.045, y, title, ha="left", va="top", fontsize=17, fontweight="bold", color=INK)
    fig.text(0.045, y - 0.05, subtitle, ha="left", va="top", fontsize=12, color=INK2)


def source(fig, text):
    fig.text(0.045, 0.012, text, ha="left", va="bottom", fontsize=9, color=MUTED)


def fig_cns_regions():
    d = pd.read_csv(TB / "recovered_countries_over_time.csv")
    d["region"] = d["country"].map(REGION).fillna("Other")
    totals = d.groupby("country").abstracts_smoothed.sum().sort_values()
    reg_tot = d.groupby("region").abstracts_smoothed.sum().sort_values(ascending=False)
    grand = reg_tot.sum()

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13.5, 6.6))
    fig.subplots_adjust(top=0.74, bottom=0.13, left=0.13, right=0.97, wspace=0.28)

    # Panel A — countries as bars, coloured by region
    cregion = {c: REGION.get(c, "Other") for c in totals.index}
    a1.barh(range(len(totals)), totals.values,
            color=[RCOLOR[cregion[c]] for c in totals.index], height=0.7, zorder=3)
    a1.set_yticks(range(len(totals)))
    a1.set_yticklabels(totals.index, fontsize=11)
    a1.set_xlabel("abstracts with ≥1 author in country (2007–2025 total)")
    a1.set_title("The US is the largest single country…", fontsize=13, color=INK, loc="left", pad=8)
    for i, v in enumerate(totals.values):
        a1.text(v + 12, i, f"{v:,.0f}", va="center", fontsize=9, color=INK2)
    a1.margins(x=0.14)

    # Panel B — region shares over time (among the top-8 origin countries)
    piv = d.pivot_table(index="year", columns="region", values="abstracts_smoothed", aggfunc="sum",
                        fill_value=0)
    share = piv.div(piv.sum(axis=1), axis=0) * 100
    order = ["Europe", "North America", "Asia-Pacific"]
    for r in order:
        if r in share.columns:
            s = share[r].rolling(3, center=True, min_periods=1).mean()
            a2.plot(share.index, s, color=RCOLOR[r], lw=2.6, zorder=3)
            a2.text(share.index[-1] + 0.2, s.iloc[-1], r, color=RCOLOR[r], fontsize=10.5,
                    va="center", fontweight="bold" if r == "Europe" else "normal")
    a2.set_xlim(2007, 2029.5)
    a2.set_ylabel("share of the leading origin countries (%)")
    a2.set_xlabel("year")
    a2.set_title("…but Europe leads as a bloc, throughout", fontsize=13, color=INK, loc="left", pad=8)
    a2.set_xticks(range(2007, 2026, 3))

    eu, na = reg_tot.get("Europe", 0), reg_tot.get("North America", 0)
    box = (f"Origin mix (top-8 countries)\n"
           f"Europe:        {eu / grand * 100:.0f}%\n"
           f"North America: {na / grand * 100:.0f}%\n"
           f"Asia-Pacific:  {reg_tot.get('Asia-Pacific', 0) / grand * 100:.0f}%\n"
           f"Europe / US ratio:  {eu / max(na, 1):.2f}×")
    a2.text(0.03, 0.05, box, transform=a2.transAxes, fontsize=9.5, color=INK2, va="bottom",
            bbox=dict(boxstyle="round,pad=0.5", fc="#f3f3f1", ec="#dddddd"))

    titlebox(fig, "CNS is a European-anchored meeting",
             "Countries of origin in CNS abstracts, 2007–2025. Europe as a bloc supplies more work "
             "than the US, even though the US is the single largest country.")
    source(fig, "Source: CNS abstracts 2007–2025 · author-affiliation country parse · top-8 origin "
                "countries (smaller countries not shown; would add mostly to Europe)")
    fig.savefig(FG / "fig14_cns_origin_regions.png", bbox_inches="tight")
    fig.savefig(FG / "fig14_cns_origin_regions.svg", bbox_inches="tight")
    plt.close(fig)
    print("wrote fig14_cns_origin_regions")
    print(f"  Europe {eu:.0f} ({eu/grand*100:.0f}%) · US/NA {na:.0f} ({na/grand*100:.0f}%) · "
          f"Europe/US {eu/max(na,1):.2f}x")


def _regional_shares(country_abstracts: pd.Series) -> pd.Series:
    reg = country_abstracts.groupby(country_abstracts.index.map(lambda c: REGION.get(c, "Other"))).sum()
    return (reg / reg.sum() * 100).reindex(["North America", "Europe", "Asia-Pacific", "Other"]).fillna(0)


def _cns_country_series() -> tuple[pd.Series, str]:
    """CNS country counts. Prefer the full-corpus institution parse (all countries,
    directly comparable to the CoSyNe institution resolution); fall back to the
    recovered top-8 origin countries if the full table is absent."""
    full = TB / "country_year_totals.csv"
    if full.exists():
        import pycountry

        def _name(iso):
            c = pycountry.countries.get(alpha_2=iso)
            return c.name if c else iso

        s = pd.read_csv(full).groupby("country").abstracts.sum()
        s.index = [_name(i) for i in s.index]
        return s, "full corpus, all countries, 2007–2025"
    s = pd.read_csv(TB / "recovered_countries_over_time.csv").groupby("country").abstracts_smoothed.sum()
    return s, "top-8 origin countries, 2007–2025"


def fig_region_comparison(cosyne_csv: Path):
    """Paired CNS-vs-CoSyNe regional composition. cosyne_csv: columns country, abstracts."""
    cns, cns_note = _cns_country_series()
    cos = pd.read_csv(cosyne_csv)
    ccol = "abstracts" if "abstracts" in cos.columns else cos.columns[1]
    cos = cos.set_index(cos.columns[0])[ccol]
    scns, scos = _regional_shares(cns), _regional_shares(cos)
    regions = ["North America", "Europe", "Asia-Pacific", "Other"]
    x = np.arange(len(regions))
    fig, ax = plt.subplots(figsize=(10.5, 6.2))
    fig.subplots_adjust(top=0.80, bottom=0.12, left=0.09, right=0.97)
    ax.bar(x - 0.2, [scns[r] for r in regions], width=0.38, color="#2a78d6", label="CNS", zorder=3)
    ax.bar(x + 0.2, [scos[r] for r in regions], width=0.38, color="#e34948", label="CoSyNe", zorder=3)
    ax.set_xticks(x)
    ax.set_xticklabels(regions)
    ax.set_ylabel("share of author-affiliation countries (%)")
    ax.legend()
    for xi, r in zip(x, regions, strict=False):
        ax.text(xi - 0.2, scns[r] + 1, f"{scns[r]:.0f}", ha="center", fontsize=9, color=INK2)
        ax.text(xi + 0.2, scos[r] + 1, f"{scos[r]:.0f}", ha="center", fontsize=9, color=INK2)
    na_gap = scos["North America"] - scns["North America"]
    titlebox(fig, "CoSyNe leans North-American; CNS leans European",
             f"Regional composition of author affiliations. CoSyNe is {scos['North America']:.0f}% "
             f"North America vs CNS's {scns['North America']:.0f}% (+{na_gap:.0f} pts); "
             f"CNS is {scns['Europe']:.0f}% Europe vs CoSyNe's {scos['Europe']:.0f}%.")
    source(fig, f"Source: CNS ({cns_note}) vs CoSyNe (program books 2014–2026, "
                "institution→country resolution) · country counted once per abstract")
    fig.savefig(FG / "fig15_cns_cosyne_geography.png", bbox_inches="tight")
    fig.savefig(FG / "fig15_cns_cosyne_geography.svg", bbox_inches="tight")
    plt.close(fig)
    print("wrote fig15_cns_cosyne_geography")


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cosyne-countries", type=Path,
                    help="CSV of CoSyNe country counts (columns: country, abstracts) for the comparison")
    args, _ = ap.parse_known_args()
    _style()
    FG.mkdir(parents=True, exist_ok=True)
    fig_cns_regions()
    if args.cosyne_countries and args.cosyne_countries.exists():
        fig_region_comparison(args.cosyne_countries)


if __name__ == "__main__":
    main()
