"""Institutions & affiliations analysis (needs the raw corpus).

Runs on the local clone's corpus parquet (the one `analyze/networks.py` uses:
columns year, title, authors[{raw_name}], affiliations[list[str]]). Produces
institution-level statistics, an institution collaboration network with
communities, and *scale-normalized* geography (shares, not raw counts, so the
meeting-size and host-city effects don't dominate).

It also exports small, **non-sensitive aggregates** (no abstract text) so they can
be committed and the figures regenerated anywhere — see `--export`.

Usage:
  python scripts/affiliation_analysis.py --corpus /path/to/corpus.parquet
  python scripts/affiliation_analysis.py --corpus /path/to/corpus.parquet --export
"""
from __future__ import annotations

import argparse
import re
from collections import Counter
from itertools import combinations
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from networkx.algorithms.community import greedy_modularity_communities

from cns_scientometrics.analyze.networks import country_of  # reuse the country parser

ROOT = Path(__file__).resolve().parents[1]
TB = ROOT / "results" / "tables"
FG = ROOT / "results" / "figures"

SURFACE, INK, INK2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8a86"
BLUE, VIOLET = "#2a78d6", "#4a3aa7"
COMM = ["#2a78d6", "#e34948", "#1baf7a", "#eb6834", "#4a3aa7", "#c98500", "#d55181", "#008300"]

_INST_HINTS = re.compile(
    r"\b(univ|universit|institut|college|hospital|laborator|laboratoire|"
    r"center|centre|school|academy|cnrs|mpi|max planck|inserm|riken|ecole|politecnic)\b",
    re.I,
)
_DROP = re.compile(r"\b(department|dept|division|faculty|school of|lab of|group|unit)\b", re.I)


def _strip_footnote(seg: str) -> str:
    """Drop a leading affiliation-footnote number glued to the name ("2Bernstein")."""
    return re.sub(r"^\d{1,3}\s*", "", seg).strip()


def institution_of(affiliation: str) -> str | None:
    """Best-effort canonical institution name from an affiliation string."""
    segs = [_strip_footnote(s.strip()) for s in re.split(r"[,;]", affiliation) if s.strip()]
    cand = [s for s in segs if _INST_HINTS.search(s) and not _DROP.match(s)]
    if not cand:
        return None
    # prefer the shortest institution-bearing segment (usually the bare name)
    name = min(cand, key=len)
    name = re.sub(r"\s+", " ", name).strip(" .")
    return name if len(name) > 3 else None


def record_institutions(affiliations: list[str]) -> list[tuple[str, str | None]]:
    seen, out = set(), []
    for a in affiliations:
        inst = institution_of(a)
        if inst and inst.lower() not in seen:
            seen.add(inst.lower())
            out.append((inst, country_of(a)))
    return out


# ---- aggregates ----------------------------------------------------------------------
def institution_stats(corpus: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in corpus.iterrows():
        for inst, cc in record_institutions(list(r["affiliations"])):
            rows.append({"institution": inst, "country": cc, "year": r["year"]})
    df = pd.DataFrame(rows)
    g = df.groupby("institution")
    stats = pd.DataFrame({
        "n_abstracts": g.size(),
        "country": g["country"].agg(lambda s: s.dropna().mode().iloc[0] if s.notna().any() else None),
        "first_year": g["year"].min(),
        "last_year": g["year"].max(),
    }).sort_values("n_abstracts", ascending=False)
    return stats.reset_index()


def institution_edges(corpus: pd.DataFrame, min_weight: int = 2) -> pd.DataFrame:
    w: Counter = Counter()
    for _, r in corpus.iterrows():
        insts = sorted({i for i, _ in record_institutions(list(r["affiliations"]))})
        for a, b in combinations(insts, 2):
            w[(a, b)] += 1
    rows = [{"a": a, "b": b, "weight": n} for (a, b), n in w.items() if n >= min_weight]
    return pd.DataFrame(rows)


def country_year_totals(corpus: pd.DataFrame) -> pd.DataFrame:
    """Per-year: total abstracts + per-country abstract counts (for scale-normalized shares)."""
    rows = []
    for _, r in corpus.iterrows():
        ccs = {c for _, c in record_institutions(list(r["affiliations"])) if c}
        for c in ccs:
            rows.append({"year": r["year"], "country": c})
    per = pd.DataFrame(rows).value_counts(["year", "country"]).reset_index(name="abstracts")
    totals = corpus.groupby("year").size().rename("n_abstracts").reset_index()
    return per.merge(totals, on="year")


# ---- figures -------------------------------------------------------------------------
def _titlebox(fig, title, subtitle, y=0.965):
    fig.text(0.045, y, title, ha="left", va="top", fontsize=17, fontweight="bold", color=INK)
    fig.text(0.045, y - 0.05, subtitle, ha="left", va="top", fontsize=12, color=INK2)


def fig_top_institutions(stats: pd.DataFrame, n: int = 20):
    d = stats.head(n).iloc[::-1]
    fig, ax = plt.subplots(figsize=(10.5, 8.6))
    fig.subplots_adjust(top=0.86, bottom=0.08, left=0.42, right=0.95)
    ax.barh(range(len(d)), d["n_abstracts"], color=BLUE, height=0.72, zorder=3)
    ax.set_yticks(range(len(d)))
    ax.set_yticklabels([f"{i}  ·{c or '?'}" for i, c in zip(d["institution"], d["country"], strict=False)],
                       fontsize=9.5)
    for i, v in enumerate(d["n_abstracts"]):
        ax.text(v + 1, i, str(int(v)), va="center", fontsize=9, color=INK2)
    ax.set_xlabel("abstracts with ≥1 author at the institution")
    _titlebox(fig, "Who shows up: the most active institutions",
              f"Top {n} institutions by abstract count across CNS meetings, 2007–2025")
    fig.text(0.045, 0.012, "Source: CNS abstracts · institution parsed from affiliation strings",
             fontsize=9, color=MUTED)
    fig.savefig(FG / "fig11_top_institutions.png", bbox_inches="tight")
    fig.savefig(FG / "fig11_top_institutions.svg", bbox_inches="tight")
    plt.close(fig)
    print("wrote fig11_top_institutions")


def fig_institution_network(edges: pd.DataFrame, stats: pd.DataFrame, top: int = 90):
    keep = set(stats.head(top)["institution"])
    e = edges[edges["a"].isin(keep) & edges["b"].isin(keep)]
    g = nx.Graph()
    for _, r in e.iterrows():
        g.add_edge(r["a"], r["b"], weight=r["weight"])
    g.remove_nodes_from(list(nx.isolates(g)))
    if g.number_of_nodes() == 0:
        print("institution network empty at this threshold; skipping")
        return
    # keep the giant connected component: the scattered dyads otherwise blow up the
    # spring-layout scale and collapse the backbone into an unreadable clump.
    giant = max(nx.connected_components(g), key=len)
    g = g.subgraph(giant).copy()

    comms = sorted(greedy_modularity_communities(g, weight="weight"), key=len, reverse=True)
    cof = {n: ci for ci, m in enumerate(comms) for n in m}
    cnt = {r["institution"]: r["n_abstracts"] for _, r in stats.iterrows()}
    try:
        pos = nx.kamada_kawai_layout(g, weight="weight")  # spreads ~40 nodes cleanly
    except Exception:
        pos = nx.spring_layout(g, weight="weight", seed=11, k=1.3, iterations=400)
    fig, ax = plt.subplots(figsize=(14, 12))
    fig.subplots_adjust(top=0.92, bottom=0.03, left=0.03, right=0.97)
    ax.axis("off")
    for u, v, d in g.edges(data=True):
        ax.plot([pos[u][0], pos[v][0]], [pos[u][1], pos[v][1]], color="#cfcfca",
                lw=0.3 + 0.5 * d["weight"], alpha=0.45, zorder=1)
    sz = np.array([cnt.get(n, 1) for n in g.nodes], float)
    for n, s in zip(g.nodes, 90 + 700 * np.sqrt(sz / sz.max()), strict=False):
        ax.scatter(*pos[n], s=s, color=COMM[cof[n] % len(COMM)], edgecolors="white",
                   linewidths=1.1, zorder=2)
    # label the hubs, offset above the node with a soft halo (matches fig8 style)
    ys = np.array([pos[n][1] for n in g.nodes])
    yoff = (ys.max() - ys.min()) * 0.022
    big = sorted(g.nodes, key=lambda n: -cnt.get(n, 0))[:20]  # label only the hubs
    for n in big:
        ax.annotate(n[:28], (pos[n][0], pos[n][1] + yoff), fontsize=7.8, ha="center",
                    va="bottom", zorder=4, color=INK,
                    bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.65))
    _titlebox(fig, "The collaboration backbone", "Institutions that co-author abstracts (largest "
              "connected component); colour = collaboration community, size = output (top hubs labelled)",
              y=0.975)
    fig.text(0.045, 0.012, "Source: CNS abstracts · institution co-authorship (edge weight ≥ 2)",
             fontsize=9, color=MUTED)
    fig.savefig(FG / "fig12_institution_network.png", bbox_inches="tight")
    fig.savefig(FG / "fig12_institution_network.svg", bbox_inches="tight")
    plt.close(fig)
    print("wrote fig12_institution_network")


def fig_country_shares(cyt: pd.DataFrame, top: int = 6):
    """Scale-normalized: each country's SHARE of abstracts per year (removes meeting-size)."""
    cyt = cyt.copy()
    cyt["share"] = cyt["abstracts"] / cyt["n_abstracts"]
    top_c = cyt.groupby("country")["abstracts"].sum().sort_values(ascending=False).head(top).index
    piv = cyt[cyt["country"].isin(top_c)].pivot_table(index="year", columns="country",
                                                      values="share", fill_value=0)
    piv = piv.rolling(3, center=True, min_periods=1).mean()
    fig, ax = plt.subplots(figsize=(10.6, 6.2))
    fig.subplots_adjust(top=0.82, bottom=0.12, left=0.09, right=0.82)
    for i, c in enumerate(top_c):
        if c in piv.columns:
            ax.plot(piv.index, 100 * piv[c], color=COMM[i % len(COMM)], lw=2.4 if i == 0 else 1.8)
            ax.text(piv.index[-1] + 0.2, 100 * piv[c].iloc[-1], c, color=COMM[i % len(COMM)],
                    fontsize=10.5, va="center")
    ax.set_ylabel("share of the meeting's abstracts (%)")
    ax.set_xlabel("year")
    _titlebox(fig, "The US share is shrinking as the field globalizes",
              "Each country's share of abstracts per meeting (scale-normalized; 3-yr smoothed)")
    fig.text(0.045, 0.012, "Source: CNS abstracts · shares remove meeting-size and host-city scale effects",
             fontsize=9, color=MUTED)
    fig.savefig(FG / "fig13_country_shares.png", bbox_inches="tight")
    fig.savefig(FG / "fig13_country_shares.svg", bbox_inches="tight")
    plt.close(fig)
    print("wrote fig13_country_shares")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True, type=Path, help="path to corpus parquet")
    ap.add_argument("--export", action="store_true",
                    help="also write committable non-sensitive aggregates to results/tables/")
    args = ap.parse_args()

    corpus = pd.read_parquet(args.corpus)
    stats = institution_stats(corpus)
    edges = institution_edges(corpus)
    cyt = country_year_totals(corpus)

    FG.mkdir(parents=True, exist_ok=True)
    fig_top_institutions(stats)
    fig_institution_network(edges, stats)
    fig_country_shares(cyt)

    if args.export:
        TB.mkdir(parents=True, exist_ok=True)
        stats.to_csv(TB / "institution_stats.csv", index=False)
        edges.to_csv(TB / "institution_edges.csv", index=False)
        cyt.to_csv(TB / "country_year_totals.csv", index=False)
        # per-abstract keyword incidence for co-occurrence networks (no text, shareable)
        try:
            from scripts.keyword_networks import keyword_incidence  # `python -m scripts.…`
        except ModuleNotFoundError:
            from keyword_networks import keyword_incidence  # `python scripts/…`
        keyword_incidence(corpus).to_csv(TB / "keyword_incidence_cns.csv", index=False)
        print("exported 4 aggregates to results/tables/: institution_stats.csv, "
              "institution_edges.csv, country_year_totals.csv, keyword_incidence_cns.csv")
        print("-> commit & push these (they contain NO abstract text) and I'll build "
              "the institution + co-occurrence figures here.")


if __name__ == "__main__":
    main()
