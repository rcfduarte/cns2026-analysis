"""Plan 3 — publication figures with a cohesive house style.

Regenerates every headline figure + aggregate result table into a committed `results/`
directory (figures are aggregate statistics; no raw abstract text is written here).
Reuses the Module A–E analysis functions.
"""

from pathlib import Path

import pandas as pd

from .contrast import contrast_table, load_cns, load_cosyne
from .keyword_trends import frequencies_dataframe
from .keywords_taxonomy import CATEGORIES
from .networks import coauthorship_graph, country_timeseries, internationalization, top_countries
from .robustness import keyword_tier_deltas

# ---- house style ---------------------------------------------------------------------

PALETTE = [
    "#2e86ab", "#d1495b", "#e8a33d", "#3c896d", "#6a4c93",
    "#1b998b", "#c1666b", "#8d99ae", "#587291", "#b56576",
]
ACCENT = "#2e86ab"
CONTRA = "#d1495b"


def _style():
    import matplotlib as mpl

    mpl.use("Agg")
    mpl.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#444444",
            "axes.linewidth": 0.8,
            "axes.grid": True,
            "grid.color": "#e6e6e6",
            "grid.linewidth": 0.7,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "font.family": "sans-serif",
            "font.size": 11,
            "axes.titlesize": 13,
            "axes.titleweight": "bold",
            "axes.prop_cycle": mpl.cycler(color=PALETTE),
            "legend.frameon": False,
            "figure.dpi": 140,
        }
    )


def _smooth(s: pd.Series, w: int = 3) -> pd.Series:
    return s.rolling(w, center=True, min_periods=1).mean()


def _save(fig, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    fig.savefig(path.with_suffix(".svg"), bbox_inches="tight")
    import matplotlib.pyplot as plt

    plt.close(fig)


# ---- figures -------------------------------------------------------------------------


def fig_aiml_rise(freqs: pd.DataFrame, out: Path):
    import matplotlib.pyplot as plt

    piv = freqs[freqs["category"] == "AI/ML Methods"].pivot_table(
        index="keyword", columns="year", values="per10k"
    )
    fig, ax = plt.subplots(figsize=(11, 6.2))
    for i, kw in enumerate(piv.index):
        ax.plot(piv.columns, _smooth(piv.loc[kw]), label=kw, lw=2, color=PALETTE[i % len(PALETTE)])
    ax.set(xlabel="year", ylabel="mentions per 10k words", title="The AI/ML wave at CNS (2007–2025)")
    ax.legend(ncol=2, fontsize=8)
    ax.annotate("LLMs appear\n(2023→)", xy=(2024, piv.loc["LLM", 2024]), xytext=(2019.5, piv.values.max() * 0.8),
                fontsize=9, color=CONTRA, arrowprops=dict(arrowstyle="->", color=CONTRA))
    _save(fig, out / "fig1_aiml_rise.png")


def fig_theme_heatmap(freqs: pd.DataFrame, out: Path):
    import matplotlib.pyplot as plt

    piv = freqs.pivot_table(index="keyword", columns="year", values="per10k")
    norm = piv.div(piv.max(axis=1), axis=0).fillna(0)
    com = norm.apply(lambda r: (r * r.index).sum() / max(r.sum(), 1e-9), axis=1)
    norm = norm.loc[com.sort_values().index]
    fig, ax = plt.subplots(figsize=(11, 14))
    im = ax.imshow(norm.values, aspect="auto", cmap="magma")
    ax.set_yticks(range(len(norm.index)))
    ax.set_yticklabels(norm.index, fontsize=8)
    ax.set_xticks(range(len(norm.columns)))
    ax.set_xticklabels(norm.columns, rotation=90, fontsize=8)
    ax.set_title("CNS keyword intensity (row-normalised to peak), sorted by era")
    fig.colorbar(im, ax=ax, shrink=0.4, label="relative intensity")
    _save(fig, out / "fig2_theme_heatmap.png")


def fig_contrast_divergence(tbl: pd.DataFrame, out: Path):
    import matplotlib.pyplot as plt

    top = pd.concat([tbl.head(12), tbl.tail(12)]).sort_values("gap_cns_minus_cosyne")
    colors = [CONTRA if v < 0 else ACCENT for v in top["gap_cns_minus_cosyne"]]
    fig, ax = plt.subplots(figsize=(9.5, 9))
    ax.barh(top.index, top["gap_cns_minus_cosyne"], color=colors)
    ax.axvline(0, color="#333", lw=0.8)
    ax.set(xlabel="Δ mentions per 10k words  (CNS − CoSyNe)",
           title="Two communities, two vocabularies")
    ax.text(0.98, 0.04, "more CNS →", transform=ax.transAxes, ha="right", color=ACCENT, fontsize=10)
    ax.text(0.02, 0.96, "← more CoSyNe", transform=ax.transAxes, ha="left", color=CONTRA, fontsize=10)
    _save(fig, out / "fig3_cosyne_cns_divergence.png")


def fig_aiml_uptake(cosyne: pd.DataFrame, cns: pd.DataFrame, years: range, out: Path):
    import matplotlib.pyplot as plt

    aiml = set(CATEGORIES["AI/ML Methods"])
    fig, ax = plt.subplots(figsize=(10.5, 6))
    for conf, df, col in [("CoSyNe", cosyne, CONTRA), ("CNS", cns, ACCENT)]:
        d = df[df["keyword"].isin(aiml) & df["year"].isin(years)]
        s = d.groupby("year")["per10k"].sum()
        ax.plot(s.index, _smooth(s), label=conf, lw=2.6, color=col)
    ax.set(xlabel="year", ylabel="Σ AI/ML mentions per 10k words",
           title="AI/ML uptake: CoSyNe adopts harder than CNS")
    ax.legend()
    _save(fig, out / "fig4_aiml_uptake.png")


def fig_topics_over_time(doc_topics_csv: Path, info_csv: Path, corpus: pd.DataFrame, out: Path):
    """Topic share of abstracts per year, computed from per-document (year, topic)."""
    import matplotlib.pyplot as plt

    if not doc_topics_csv.exists():
        return
    dt = pd.read_csv(doc_topics_csv)
    info = pd.read_csv(info_csv)
    per_year = dt.groupby("year").size()
    counts = dt[dt["topic"] != -1].groupby(["year", "topic"]).size().reset_index(name="n")
    counts["share"] = counts.apply(lambda r: r["n"] / per_year[r["year"]], axis=1)
    label = {r["Topic"]: r["Name"] for _, r in info.iterrows()}
    top_ids = [t for t in info["Topic"].tolist() if t != -1][:10]
    fig, ax = plt.subplots(figsize=(12, 6.8))
    for i, t in enumerate(top_ids):
        d = counts[counts["topic"] == t].set_index("year")["share"].reindex(
            sorted(per_year.index), fill_value=0
        )
        ax.plot(d.index, _smooth(d), label=label.get(t, str(t)).split("_", 1)[-1][:26],
                lw=1.9, color=PALETTE[i % len(PALETTE)])
    ax.set(xlabel="year", ylabel="share of abstracts (smoothed)",
           title="Data-driven topics over time (BERTopic, volume-normalised)")
    ax.legend(ncol=2, fontsize=8)
    _save(fig, out / "fig5_topics_over_time.png")


def fig_internationalization(corpus: pd.DataFrame, out: Path):
    import matplotlib.pyplot as plt

    intl = internationalization(corpus)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5.5))
    a1.plot(intl["year"], intl["distinct_countries"], marker="o", color=ACCENT, lw=2)
    a1.set(xlabel="year", ylabel="distinct countries", title="Countries represented per meeting")
    a2.plot(intl["year"], intl["country_entropy"], marker="s", color="#6a4c93", lw=2)
    a2.set(xlabel="year", ylabel="country diversity (bits)", title="Geographic diversity (Shannon entropy)")
    _save(fig, out / "fig6_internationalization.png")

    top = top_countries(corpus, 10).index.tolist()
    cts = country_timeseries(corpus)
    piv = cts[cts["country"].isin(top)].pivot_table(index="year", columns="country", values="abstracts", fill_value=0)
    fig, ax = plt.subplots(figsize=(11, 6))
    for i, c in enumerate(top):
        if c in piv.columns:
            ax.plot(piv.index, _smooth(piv[c]), label=c, lw=1.8, color=PALETTE[i % len(PALETTE)])
    ax.set(xlabel="year", ylabel="abstracts with ≥1 author in country",
           title="Author affiliations by country (top 10)")
    ax.legend(ncol=5, fontsize=8)
    _save(fig, out / "fig7_countries.png")


def fig_robustness(corpus: pd.DataFrame, out: Path):
    import matplotlib.pyplot as plt

    kd = keyword_tier_deltas(corpus).dropna(subset=["trajectory_corr"])
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.hist(kd["trajectory_corr"], bins=20, color=ACCENT, alpha=0.85)
    med = kd["trajectory_corr"].median()
    ax.axvline(med, color=CONTRA, lw=2, label=f"median = {med:.2f}")
    ax.set(xlabel="title-only vs full-abstract trajectory correlation", ylabel="# keywords",
           title="Titles are a lossy proxy for abstracts")
    ax.legend()
    _save(fig, out / "fig8_robustness.png")


# ---- orchestrator --------------------------------------------------------------------


def generate_all(corpus_path: Path, cosyne_json: Path, out: Path,
                 topics_csv: Path | None = None, info_csv: Path | None = None,
                 years: range = range(2007, 2026)) -> Path:
    _style()
    out = Path(out)
    figs, tables = out / "figures", out / "tables"
    figs.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)
    corpus = pd.read_parquet(corpus_path)

    freqs = frequencies_dataframe(corpus, tier="full")
    freqs.to_csv(tables / "keyword_frequencies.csv", index=False)
    fig_aiml_rise(freqs, figs)
    fig_theme_heatmap(freqs, figs)
    fig_internationalization(corpus, figs)
    fig_robustness(corpus, figs)

    cosyne, cns = load_cosyne(cosyne_json), load_cns(tables / "keyword_frequencies.csv")
    tbl = contrast_table(cosyne, cns, years)
    tbl.to_csv(tables / "cosyne_cns_contrast.csv")
    fig_contrast_divergence(tbl, figs)
    fig_aiml_uptake(cosyne, cns, years, figs)

    if topics_csv and Path(topics_csv).exists():
        fig_topics_over_time(Path(topics_csv), Path(info_csv), corpus, figs)  # topics_csv = doc_topics.csv

    g = coauthorship_graph(corpus)
    pd.Series(
        {"n_authors": g.number_of_nodes(), "n_collaborations": g.number_of_edges(),
         "n_abstracts": len(corpus)}
    ).to_csv(tables / "network_summary.csv")
    return out
