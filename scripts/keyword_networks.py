"""Keyword graphs & semantic community structure.

Two views work from the COMMITTED aggregates alone (no raw corpus):
  A. CNS keyword co-trajectory network — keywords linked when their year-by-year
     intensity trajectories move together; communities = greedy modularity.
  B. CoSyNe-vs-CNS vocabulary map — every keyword positioned by how much each
     community uses it, coloured by community lean.

A third view (true per-abstract co-occurrence networks, CoSyNe vs CNS, with
Louvain/modularity communities) needs the raw corpus and is built by
`cooccurrence_network()` / the `--corpus` CLI path — see module docstring at bottom
and docs/VALIDATION.md.

Run (aggregate views):  python scripts/keyword_networks.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from networkx.algorithms.community import greedy_modularity_communities

ROOT = Path(__file__).resolve().parents[1]
TB = ROOT / "results" / "tables"
FG = ROOT / "results" / "figures"

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#8a8a86"
# qualitative community palette (CVD-aware, extends the article palette)
COMM = ["#2a78d6", "#e34948", "#1baf7a", "#eb6834", "#4a3aa7", "#c98500", "#d55181", "#008300"]


def _style():
    mpl.rcParams.update({
        "figure.facecolor": SURFACE, "savefig.facecolor": SURFACE, "axes.facecolor": SURFACE,
        "font.family": "DejaVu Sans", "font.size": 12, "text.color": INK,
    })


def titlebox(fig, title, subtitle, x=0.045, y=0.975):
    fig.text(x, y, title, ha="left", va="top", fontsize=17, fontweight="bold", color=INK)
    fig.text(x, y - 0.043, subtitle, ha="left", va="top", fontsize=12, color=INK2)


def source(fig, text, x=0.045, y=0.012):
    fig.text(x, y, text, ha="left", va="bottom", fontsize=9, color=MUTED)


# ======================================================================================
# A. Co-trajectory network (committed data)
# ======================================================================================
def cotrajectory_graph(freqs: pd.DataFrame, corr_thresh: float = 0.6):
    piv = freqs.pivot_table(index="keyword", columns="year", values="per10k").fillna(0.0)
    # z-score each keyword's trajectory so shape (not magnitude) drives the correlation
    z = piv.sub(piv.mean(axis=1), axis=0)
    sd = z.std(axis=1).replace(0, np.nan)
    z = z.div(sd, axis=0).dropna()
    corr = np.corrcoef(z.values)
    kws = z.index.tolist()
    g = nx.Graph()
    mean_intensity = piv.mean(axis=1)
    for k in kws:
        g.add_node(k, intensity=float(mean_intensity[k]))
    for i in range(len(kws)):
        for j in range(i + 1, len(kws)):
            c = corr[i, j]
            if c >= corr_thresh:
                g.add_edge(kws[i], kws[j], weight=float(c))
    return g


def _community_lean(members, contrast):
    """Mean log2(CNS/CoSyNe) over a community's keywords -> +CNS / -CoSyNe."""
    vals = [contrast.loc[m, "log2_ratio"] for m in members if m in contrast.index]
    return float(np.mean(vals)) if vals else 0.0


def fig_cotrajectory(freqs, contrast):
    g = cotrajectory_graph(freqs, corr_thresh=0.6)
    g.remove_nodes_from(list(nx.isolates(g)))
    comms = list(greedy_modularity_communities(g, weight="weight"))
    comms = sorted(comms, key=len, reverse=True)
    node_comm, comm_lean = {}, {}
    for ci, members in enumerate(comms):
        comm_lean[ci] = _community_lean(members, contrast)
        for m in members:
            node_comm[m] = ci

    try:
        pos = nx.kamada_kawai_layout(g)  # spreads clusters better than spring for ~50 nodes
    except Exception:
        pos = nx.spring_layout(g, weight="weight", seed=7, k=1.4, iterations=400)
    fig, ax = plt.subplots(figsize=(14, 12.5))
    fig.subplots_adjust(top=0.91, bottom=0.04, left=0.03, right=0.97)
    ax.axis("off")

    for u, v, d in g.edges(data=True):
        ax.plot([pos[u][0], pos[v][0]], [pos[u][1], pos[v][1]],
                color="#ccccc8", lw=0.4 + 2.0 * (d["weight"] - 0.6), alpha=0.45, zorder=1)
    sizes = np.array([g.nodes[n]["intensity"] for n in g.nodes])
    node_size = 90 + 620 * np.sqrt(sizes / sizes.max())
    for n, s in zip(g.nodes, node_size, strict=False):
        ax.scatter(pos[n][0], pos[n][1], s=s, color=COMM[node_comm[n] % len(COMM)],
                   edgecolors="white", linewidths=1.3, zorder=2)
    # labels offset above node, with a soft halo so they stay legible over edges/nodes
    ys = np.array([pos[n][1] for n in g.nodes])
    yoff = (ys.max() - ys.min()) * 0.028
    for n in g.nodes:
        ax.annotate(n, (pos[n][0], pos[n][1] + yoff), fontsize=8.3, ha="center", va="bottom",
                    zorder=4, color=INK,
                    bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.6))

    # legend: community -> lean
    handles = []
    for ci, members in enumerate(comms):
        lean = comm_lean[ci]
        tag = "CNS-leaning" if lean > 0.15 else ("CoSyNe-leaning" if lean < -0.15 else "shared")
        handles.append(plt.Line2D([0], [0], marker="o", ls="", ms=11,
                       markerfacecolor=COMM[ci % len(COMM)], markeredgecolor="white",
                       label=f"community {ci + 1} · {len(members)} terms · {tag}"))
    ax.legend(handles=handles, loc="upper left", fontsize=9.5, frameon=True,
              facecolor="white", edgecolor="#dddddd", framealpha=0.9,
              title="communities (greedy modularity)", title_fontsize=10)
    titlebox(fig, "The shape of the field: keywords that rose and fell together",
             "CNS keyword co-trajectory network — edges link terms with correlated 2007–2025 trajectories "
             "(r ≥ 0.6); colour = community; size = mean intensity")
    source(fig, "Source: CNS abstracts 2007–2025 · community detection = greedy modularity · "
                "lean = mean log2(CNS/CoSyNe) intensity")
    fig.savefig(FG / "fig8_keyword_cotrajectory_network.png", bbox_inches="tight")
    fig.savefig(FG / "fig8_keyword_cotrajectory_network.svg", bbox_inches="tight")
    plt.close(fig)
    print("wrote fig8_keyword_cotrajectory_network")
    return {ci: sorted(m) for ci, m in enumerate(comms)}, comm_lean


# ======================================================================================
# B. CoSyNe-vs-CNS vocabulary map (committed data)
# ======================================================================================
def fig_vocab_map(contrast):
    d = contrast.copy()
    x = d["cosyne"].to_numpy() + 0.05
    y = d["cns"].to_numpy() + 0.05
    lean = d["log2_ratio"].to_numpy()
    fig, ax = plt.subplots(figsize=(11, 9.6))
    fig.subplots_adjust(top=0.89, bottom=0.09, left=0.09, right=0.97)
    lim = [0.04, max(x.max(), y.max()) * 1.5]
    ax.plot(lim, lim, color=MUTED, lw=1.0, ls=(0, (4, 3)), zorder=1)
    ax.fill_between(lim, [lim[0] * 2, lim[1] * 2], lim, color="#2a78d6", alpha=0.04, zorder=0)
    ax.fill_between(lim, lim, [lim[0] / 2, lim[1] / 2], color="#e34948", alpha=0.04, zorder=0)
    sizes = 30 + 220 * np.sqrt((d["cosyne"] + d["cns"]).to_numpy() / (d["cosyne"] + d["cns"]).max())
    cmap = mpl.cm.RdBu
    norm = mpl.colors.TwoSlopeNorm(vmin=-2.2, vcenter=0, vmax=2.2)
    ax.scatter(x, y, s=sizes, c=lean, cmap=cmap, norm=norm, edgecolors="white",
               linewidths=0.8, zorder=3)

    # annotate the strongest signatures on each side + biggest shared terms
    d = d.assign(x=x, y=y, total=d["cosyne"] + d["cns"])
    cns_sig = d.sort_values("gap_cns_minus_cosyne", ascending=False).head(7)
    cos_sig = d.sort_values("gap_cns_minus_cosyne").head(7)
    shared = d[(d["log2_ratio"].abs() < 0.25)].sort_values("total", ascending=False).head(6)
    for _, r in pd.concat([cns_sig, cos_sig, shared]).iterrows():
        ax.annotate(r.name, (r.x, r.y), fontsize=8.6, color=INK,
                    xytext=(4, 3), textcoords="offset points")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(lim)
    ax.set_ylim(lim)
    ax.set_xlabel("CoSyNe intensity  (mentions per 10k words, log scale)")
    ax.set_ylabel("CNS intensity  (mentions per 10k words, log scale)")
    ax.text(0.03, 0.97, "more CNS ↑", transform=ax.transAxes, color="#2a78d6",
            fontsize=11, fontweight="bold", va="top")
    ax.text(0.97, 0.03, "more CoSyNe →", transform=ax.transAxes, color="#e34948",
            fontsize=11, fontweight="bold", ha="right")
    ax.grid(True, which="both", color="#ececea", lw=0.7)
    titlebox(fig, "One vocabulary, two dialects", "Every tracked keyword by how intensely each "
             "community uses it. On the diagonal = shared; off-diagonal = a community signature.")
    source(fig, "Source: CNS abstracts 2007–2025 vs CoSyNe keyword study · shared taxonomy")
    fig.savefig(FG / "fig9_two_vocabularies_map.png", bbox_inches="tight")
    fig.savefig(FG / "fig9_two_vocabularies_map.svg", bbox_inches="tight")
    plt.close(fig)
    print("wrote fig9_two_vocabularies_map")


# ======================================================================================
# B2. Scale-normalized specialization & overlap (committed data)
# ======================================================================================
def overlap_metrics(contrast):
    """Vocabulary overlap between the two communities on scale-normalized shares."""
    cos = contrast["cosyne"].clip(lower=0)
    cns = contrast["cns"].clip(lower=0)
    scos, scns = cos / cos.sum(), cns / cns.sum()       # each -> a probability vector
    cosine = float((scos * scns).sum() / (np.sqrt((scos ** 2).sum()) * np.sqrt((scns ** 2).sum())))
    overlap_mass = float(np.minimum(scos, scns).sum())   # shared probability mass
    spec = np.log2((scns + 1e-4) / (scos + 1e-4))        # +CNS / -CoSyNe, scale-free
    shared = int((spec.abs() < 0.5).sum())
    top15 = set(cns.nlargest(15).index) & set(cos.nlargest(15).index)
    jac15 = len(top15) / len(set(cns.nlargest(15).index) | set(cos.nlargest(15).index))
    return {"cosine": cosine, "overlap_mass": overlap_mass, "shared_core": shared,
            "n": len(spec), "jaccard_top15": jac15, "spec": spec.sort_values()}


def fig_specialization(contrast):
    m = overlap_metrics(contrast)
    spec = m["spec"]
    sel = pd.concat([spec.head(12), spec.tail(12)])
    fig, ax = plt.subplots(figsize=(10.4, 9.4))
    fig.subplots_adjust(top=0.80, bottom=0.09, left=0.26, right=0.9)
    colors = ["#e34948" if v < 0 else "#2a78d6" for v in sel.values]
    ax.barh(range(len(sel)), sel.values, color=colors, height=0.72, zorder=3)
    ax.set_yticks(range(len(sel)))
    ax.set_yticklabels(sel.index, fontsize=11)
    ax.axvline(0, color=INK, lw=1.1)
    ax.set_xlabel("specialization  =  log₂( CNS share ÷ CoSyNe share )   ·  scale-normalized")
    ax.margins(x=0.08)
    ax.text(0.985, 1.005, "CNS-specialized →", transform=ax.transAxes, ha="right",
            color="#2a78d6", fontsize=11, fontweight="bold")
    ax.text(0.015, 1.005, "← CoSyNe-specialized", transform=ax.transAxes, ha="left",
            color="#e34948", fontsize=11, fontweight="bold")
    box = (f"Vocabulary overlap (scale-normalized)\n"
           f"cosine similarity of shares:   {m['cosine']:.2f}\n"
           f"shared mass (Σ min share):    {m['overlap_mass']*100:.0f}%\n"
           f"shared-core (|log₂|<0.5):   {m['shared_core']} of {m['n']}\n"
           f"top-15 vocab Jaccard:          {m['jaccard_top15']:.2f}")
    ax.text(0.02, 0.98, box, transform=ax.transAxes, fontsize=9.5, color=INK2, va="top",
            ha="left", family="DejaVu Sans",
            bbox=dict(boxstyle="round,pad=0.5", fc="#f3f3f1", ec="#dddddd"))
    titlebox(fig, "Same field, different priorities — with scale taken out",
             "Which terms each community over-uses *relative to its own size*. Removing scale surfaces "
             "proportional signatures, not just the loudest words.", y=0.90)
    source(fig, "Source: CNS abstracts 2007–2025 vs CoSyNe keyword study · shares within each community")
    fig.savefig(FG / "fig10_specialization_overlap.png", bbox_inches="tight")
    fig.savefig(FG / "fig10_specialization_overlap.svg", bbox_inches="tight")
    plt.close(fig)
    print("wrote fig10_specialization_overlap")
    return m


# ======================================================================================
# C. True co-occurrence network (needs raw corpus) — run on the local clone
# ======================================================================================
def keyword_incidence(corpus: pd.DataFrame, tier: str = "full") -> pd.DataFrame:
    """Per-abstract 0/1 incidence for every keyword (shareable aggregate, no text).

    corpus: parquet with columns year,title,body{full}; matches the CoSyNe taxonomy.
    """
    from cns_scientometrics.analyze.keyword_trends import _doc_text, count_keyword
    from cns_scientometrics.analyze.keywords_taxonomy import KEYWORDS

    rows = []
    for _, r in corpus.iterrows():
        text = _doc_text(r, tier)
        rows.append({kw: int(count_keyword(text, syns) > 0) for kw, syns in KEYWORDS.items()})
    inc = pd.DataFrame(rows)
    inc.insert(0, "year", corpus["year"].to_numpy())
    return inc


def cooccurrence_network(incidence: pd.DataFrame, min_count: int = 8, npmi_thresh: float = 0.20):
    """Keyword co-occurrence graph weighted by NPMI (normalised pointwise MI)."""
    cols = [c for c in incidence.columns if c != "year"]
    M = incidence[cols].to_numpy().astype(float)
    n = len(M)
    p = M.mean(axis=0)
    co = (M.T @ M) / n  # joint prob
    g = nx.Graph()
    for i, k in enumerate(cols):
        g.add_node(k, count=int(M[:, i].sum()))
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            joint = co[i, j]
            if joint * n < min_count or p[i] == 0 or p[j] == 0:
                continue
            pmi = np.log(joint / (p[i] * p[j])) if joint > 0 else 0.0
            npmi = pmi / (-np.log(joint)) if joint > 0 else 0.0
            if npmi >= npmi_thresh:
                g.add_edge(cols[i], cols[j], weight=float(npmi))
    return g


def fig_cooccurrence(incidence: pd.DataFrame, label: str, contrast: pd.DataFrame | None = None):
    """Render a true co-occurrence network with communities for one meeting."""
    g = cooccurrence_network(incidence)
    g.remove_nodes_from(list(nx.isolates(g)))
    if g.number_of_nodes() == 0:
        print(f"[{label}] co-occurrence graph empty at threshold; lower npmi_thresh")
        return None
    comms = sorted(greedy_modularity_communities(g, weight="weight"), key=len, reverse=True)
    cof = {n: ci for ci, m in enumerate(comms) for n in m}
    try:
        pos = nx.kamada_kawai_layout(g)
    except Exception:
        pos = nx.spring_layout(g, weight="weight", seed=7, k=1.3, iterations=400)
    fig, ax = plt.subplots(figsize=(14, 12.5))
    fig.subplots_adjust(top=0.91, bottom=0.04, left=0.03, right=0.97)
    ax.axis("off")
    for u, v, d in g.edges(data=True):
        ax.plot([pos[u][0], pos[v][0]], [pos[u][1], pos[v][1]], color="#ccccc8",
                lw=0.4 + 3.0 * d["weight"], alpha=0.45, zorder=1)
    cnt = np.array([g.nodes[n]["count"] for n in g.nodes], float)
    for n, s in zip(g.nodes, 90 + 620 * np.sqrt(cnt / cnt.max()), strict=False):
        ax.scatter(*pos[n], s=s, color=COMM[cof[n] % len(COMM)], edgecolors="white",
                   linewidths=1.3, zorder=2)
    ys = np.array([pos[n][1] for n in g.nodes])
    yoff = (ys.max() - ys.min()) * 0.028
    for n in g.nodes:
        ax.annotate(n, (pos[n][0], pos[n][1] + yoff), fontsize=8.3, ha="center", va="bottom",
                    zorder=4, bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.6))
    titlebox(fig, f"What co-occurs with what — {label}",
             "Keyword co-occurrence network: edges = terms appearing in the same abstracts more than "
             "chance (NPMI ≥ 0.2); colour = community")
    source(fig, f"Source: {label} abstracts · per-abstract keyword co-occurrence · greedy-modularity communities")
    slug = label.lower().replace(" ", "_")
    fig.savefig(FG / f"fig_cooccurrence_{slug}.png", bbox_inches="tight")
    fig.savefig(FG / f"fig_cooccurrence_{slug}.svg", bbox_inches="tight")
    plt.close(fig)
    print(f"wrote fig_cooccurrence_{slug}")
    return {ci: sorted(m) for ci, m in enumerate(comms)}


def compare_partitions(part_a: dict, part_b: dict, label_a: str, label_b: str):
    """Report how differently the two communities cluster the shared keyword set."""
    def pairs(part):
        s = set()
        for members in part.values():
            for x, y in combinations_local(sorted(members)):
                s.add((x, y))
        return s
    pa, pb = pairs(part_a), pairs(part_b)
    shared_terms = {t for m in part_a.values() for t in m} & {t for m in part_b.values() for t in m}
    pa = {(x, y) for x, y in pa if x in shared_terms and y in shared_terms}
    pb = {(x, y) for x, y in pb if x in shared_terms and y in shared_terms}
    jac = len(pa & pb) / max(len(pa | pb), 1)
    print(f"partition co-membership Jaccard ({label_a} vs {label_b}) on {len(shared_terms)} "
          f"shared terms: {jac:.3f}")
    return jac


def combinations_local(xs):
    for i in range(len(xs)):
        for j in range(i + 1, len(xs)):
            yield xs[i], xs[j]


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--incidence", type=Path, help="per-abstract keyword incidence CSV (CNS)")
    ap.add_argument("--cosyne-incidence", type=Path, help="per-abstract keyword incidence CSV (CoSyNe)")
    args, _ = ap.parse_known_args()

    _style()
    FG.mkdir(parents=True, exist_ok=True)
    contrast_idx = pd.read_csv(TB / "cosyne_cns_contrast.csv").set_index("keyword")

    # co-occurrence networks (raw corpus incidence, if provided)
    if args.incidence and args.incidence.exists():
        pa = fig_cooccurrence(pd.read_csv(args.incidence), "CNS", contrast_idx)
        if args.cosyne_incidence and args.cosyne_incidence.exists():
            pb = fig_cooccurrence(pd.read_csv(args.cosyne_incidence), "CoSyNe", contrast_idx)
            if pa and pb:
                compare_partitions(pa, pb, "CNS", "CoSyNe")
        return

    freqs = pd.read_csv(TB / "keyword_frequencies.csv")
    contrast = pd.read_csv(TB / "cosyne_cns_contrast.csv").set_index("keyword")
    comms, lean = fig_cotrajectory(freqs, contrast)
    fig_vocab_map(contrast)
    fig_specialization(contrast)
    # dump the community membership for the article/appendix
    rows = [{"community": ci + 1, "lean_log2_cns_over_cosyne": round(lean[ci], 3),
             "keywords": ", ".join(members)} for ci, members in comms.items()]
    pd.DataFrame(rows).to_csv(TB / "cotrajectory_communities.csv", index=False)
    print("wrote cotrajectory_communities.csv")


if __name__ == "__main__":
    main()
