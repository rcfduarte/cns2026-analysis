"""Publication figure suite for the Substack write-up.

Editorial / popular-science house style. Reads ONLY from committed aggregate
tables in results/tables/ (keyword_frequencies.csv, cosyne_cns_contrast.csv, and
the recovered_*.csv produced by scripts/recover_tables_from_figures.py) — no raw
corpus required. Colours use the validated categorical/diverging palette.

Run:  python scripts/build_article_figures.py
Out:  results/figures/*.png (+ .svg)
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

# ---- palette (validated: CVD worst adjacent ΔE 24.2, light surface) ------------------
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#8a8a86"
GRID = "#e7e7e4"
BLUE = "#2a78d6"    # CNS / rising / primary
AQUA = "#1baf7a"
YELLOW = "#c98500"  # darker yellow for line legibility on white
GREEN = "#008300"
VIOLET = "#4a3aa7"
RED = "#e34948"     # CoSyNe / falling
MAGENTA = "#d55181"
ORANGE = "#eb6834"


def style():
    mpl.rcParams.update({
        "figure.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "axes.edgecolor": "#c9c9c5",
        "axes.linewidth": 1.0,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": GRID,
        "grid.linewidth": 1.0,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "font.family": "DejaVu Sans",
        "font.size": 12,
        "text.color": INK,
        "axes.labelcolor": INK2,
        "xtick.color": INK2,
        "ytick.color": INK2,
        "xtick.labelsize": 11,
        "ytick.labelsize": 11,
        "legend.frameon": False,
        "figure.dpi": 150,
    })


def titlebox(fig, title, subtitle, x=0.045, y=0.965):
    fig.text(x, y, title, ha="left", va="top", fontsize=17, fontweight="bold", color=INK)
    fig.text(x, y - 0.052, subtitle, ha="left", va="top", fontsize=12, color=INK2)


def source(fig, text, x=0.045, y=0.015):
    fig.text(x, y, text, ha="left", va="bottom", fontsize=9, color=MUTED)


def smooth(a, w=3):
    s = pd.Series(a)
    return s.rolling(w, center=True, min_periods=1).mean().to_numpy()


def spread(values, min_gap):
    """Nudge label y-positions apart (upward) so text doesn't overlap, order kept."""
    vals = np.array(values, float)
    order = np.argsort(vals)
    s = vals[order].copy()
    for i in range(1, len(s)):
        if s[i] - s[i - 1] < min_gap:
            s[i] = s[i - 1] + min_gap
    out = np.empty_like(s)
    out[order] = s
    return out


def save(fig, name):
    fig.savefig(FG / f"{name}.png", bbox_inches="tight")
    fig.savefig(FG / f"{name}.svg", bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


# ======================================================================================
def load_freqs():
    return pd.read_csv(TB / "keyword_frequencies.csv")


# --- Fig 1: the AI/ML wave ------------------------------------------------------------
def fig_aiml_wave(freqs):
    piv = freqs[freqs.category == "AI/ML Methods"].pivot_table(
        index="keyword", columns="year", values="per10k")
    years = piv.columns.to_numpy()
    total = piv.sum(axis=0)

    fig, ax = plt.subplots(figsize=(10.5, 6.4))
    fig.subplots_adjust(top=0.80, bottom=0.12, left=0.09, right=0.83)

    ax.fill_between(years, smooth(total.to_numpy()), color=BLUE, alpha=0.13, zorder=1)
    ax.plot(years, smooth(total.to_numpy()), color=BLUE, lw=3.0, zorder=3, label="All AI/ML terms")
    total_s = smooth(total.to_numpy())

    highlight = [("all AI/ML terms", BLUE, total_s), ]
    for kw, c in [("deep learning", GREEN), ("RNN", ORANGE), ("LLM", RED)]:
        if kw in piv.index:
            y = smooth(piv.loc[kw].to_numpy())
            ax.plot(years, y, color=c, lw=2.0, zorder=2)
            highlight.append((kw, c, y))
    # de-collide the right-edge direct labels
    lab_y = spread([h[2][-1] for h in highlight], min_gap=0.62)
    for (kw, c, _y), ly in zip(highlight, lab_y, strict=False):
        txt = "all AI/ML\nterms" if kw == "all AI/ML terms" else kw
        bold = "bold" if kw == "all AI/ML terms" else "normal"
        ax.text(years[-1] + 0.25, ly, txt, color=c, fontsize=11, va="center", fontweight=bold)

    ax.axvline(2023, color=MUTED, lw=1.0, ls=(0, (3, 3)), zorder=0)
    ax.annotate("LLMs enter\nthe abstracts", xy=(2023, 1.1), xytext=(2018.4, 6.2),
                fontsize=10.5, color=RED, ha="center",
                arrowprops=dict(arrowstyle="->", color=RED, lw=1.3))
    ax.set_xlim(2007, 2027.5)
    ax.set_ylim(bottom=0)
    ax.set_ylabel("mentions per 10,000 words")
    ax.set_xticks(range(2007, 2026, 3))
    titlebox(fig, "The AI/ML wave breaks over computational neuroscience",
             "Machine-learning vocabulary in CNS meeting abstracts, 2007–2025 (3-yr smoothed)")
    source(fig, "Source: CNS/OCNS abstracts 2007–2025 (n=5,394) · keyword frequency, CoSyNe taxonomy")
    save(fig, "fig1_aiml_wave")


# --- Fig 2: rising vs fading vocabulary ----------------------------------------------
def fig_rising_fading(freqs):
    piv = freqs.pivot_table(index="keyword", columns="year", values="per10k")
    early = piv.loc[:, 2007:2011].mean(axis=1)
    recent = piv.loc[:, 2021:2025].mean(axis=1)
    delta = (recent - early).sort_values()
    fade = delta.head(12)
    rise = delta.tail(12)
    sel = pd.concat([fade, rise])

    fig, ax = plt.subplots(figsize=(9.6, 9.2))
    fig.subplots_adjust(top=0.83, bottom=0.09, left=0.24, right=0.94)
    colors = [RED if v < 0 else BLUE for v in sel.values]
    ax.barh(range(len(sel)), sel.values, color=colors, height=0.72, zorder=3)
    ax.set_yticks(range(len(sel)))
    ax.set_yticklabels(sel.index, fontsize=11)
    ax.axvline(0, color=INK, lw=1.1)
    ax.set_xlabel("change in mentions per 10,000 words   (2021–25 average − 2007–11 average)")
    for i, v in enumerate(sel.values):
        ax.text(v + (0.12 if v >= 0 else -0.12), i, f"{v:+.1f}",
                va="center", ha="left" if v >= 0 else "right", fontsize=9, color=INK2)
    ax.margins(x=0.14)
    ax.text(0.985, 1.008, "RISING", transform=ax.transAxes, ha="right", color=BLUE,
            fontsize=11, fontweight="bold")
    ax.text(0.015, 1.008, "FADING", transform=ax.transAxes, ha="left", color=RED,
            fontsize=11, fontweight="bold")
    titlebox(fig, "What computational neuroscience talks about now — and what it dropped",
             "Biggest gains and losses in keyword intensity across CNS abstracts, early-2010s vs 2020s")
    source(fig, "Source: CNS/OCNS abstracts 2007–2025 (n=5,394)")
    save(fig, "fig2_rising_fading")


# --- Fig 3: two communities ----------------------------------------------------------
def fig_two_communities():
    tbl = pd.read_csv(TB / "cosyne_cns_contrast.csv")
    tbl = tbl.rename(columns={tbl.columns[0]: "keyword"})
    tbl = tbl.sort_values("gap_cns_minus_cosyne")
    sel = pd.concat([tbl.head(12), tbl.tail(12)])
    fig, ax = plt.subplots(figsize=(9.6, 9.2))
    fig.subplots_adjust(top=0.83, bottom=0.09, left=0.22, right=0.94)
    colors = [RED if v < 0 else BLUE for v in sel["gap_cns_minus_cosyne"]]
    ax.barh(range(len(sel)), sel["gap_cns_minus_cosyne"], color=colors, height=0.72, zorder=3)
    ax.set_yticks(range(len(sel)))
    ax.set_yticklabels(sel["keyword"], fontsize=11)
    ax.axvline(0, color=INK, lw=1.1)
    ax.set_xlabel("Δ mentions per 10,000 words   (CNS − CoSyNe)")
    ax.margins(x=0.05)
    ax.text(0.985, 1.008, "more CNS →", transform=ax.transAxes, ha="right", color=BLUE,
            fontsize=11, fontweight="bold")
    ax.text(0.015, 1.008, "← more CoSyNe", transform=ax.transAxes, ha="left", color=RED,
            fontsize=11, fontweight="bold")
    titlebox(fig, "Two communities, two vocabularies",
             "Where the CNS and CoSyNe communities emphasise different language (shared keyword axis)")
    source(fig, "Source: CNS abstracts 2007–2025 vs CoSyNe keyword study · mean per-10k-word frequency")
    save(fig, "fig3_two_communities")


# --- Fig 4: AI/ML uptake, CoSyNe vs CNS ----------------------------------------------
def fig_aiml_uptake():
    d = pd.read_csv(TB / "recovered_aiml_uptake.csv")
    fig, ax = plt.subplots(figsize=(10.2, 6.2))
    fig.subplots_adjust(top=0.80, bottom=0.12, left=0.09, right=0.84)
    cmap = {"CoSyNe": RED, "CNS": BLUE}
    for conf, sub in d.groupby("conference"):
        sub = sub.sort_values("year")
        ax.plot(sub.year, sub.aiml_per10k_smoothed, color=cmap[conf], lw=3.0)
        ax.text(sub.year.iloc[-1] + 0.2, sub.aiml_per10k_smoothed.iloc[-1], conf,
                color=cmap[conf], fontsize=12, fontweight="bold", va="center")
    ax.set_xlim(2007, 2027)
    ax.set_ylim(bottom=0)
    ax.set_ylabel("Σ AI/ML mentions per 10,000 words")
    ax.set_xticks(range(2007, 2026, 3))
    ax.annotate("the gap widens\nafter ~2018", xy=(2023, 16.5), xytext=(2013.5, 17.5),
                fontsize=10.5, color=INK2, ha="center",
                arrowprops=dict(arrowstyle="->", color=MUTED, lw=1.2))
    titlebox(fig, "Both fields turned to machine learning — CoSyNe turned harder",
             "Total AI/ML keyword intensity per meeting, CoSyNe vs CNS (3-yr smoothed)")
    source(fig, "Source: CoSyNe keyword study & CNS abstracts 2007–2025 · identical taxonomy")
    save(fig, "fig4_aiml_uptake")


# --- Fig 5: globalization ------------------------------------------------------------
def fig_globalization():
    d = pd.read_csv(TB / "recovered_internationalization.csv")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.4, 5.6))
    fig.subplots_adjust(top=0.74, bottom=0.14, left=0.07, right=0.97, wspace=0.22)
    yr = d.year.to_numpy()
    a1.bar(yr, d.distinct_countries, color=BLUE, width=0.66, zorder=3, alpha=0.85)
    m1, b1 = np.polyfit(yr, d.distinct_countries, 1)
    a1.plot(yr, m1 * yr + b1, color=INK2, lw=1.8, ls=(0, (4, 3)), zorder=4)
    a1.set_title("Countries represented per meeting", fontsize=13, color=INK, pad=8, loc="left")
    a1.set_ylabel("distinct countries")
    a1.set_xticks(range(2007, 2026, 3))
    a2.plot(yr, d.country_entropy_bits, color=VIOLET, lw=2.4, marker="o", ms=5, zorder=3)
    m2, b2 = np.polyfit(yr, d.country_entropy_bits, 1)
    a2.plot(yr, m2 * yr + b2, color=INK2, lw=1.8, ls=(0, (4, 3)), zorder=4)
    a2.set_title("Geographic diversity (Shannon entropy)", fontsize=13, color=INK, pad=8, loc="left")
    a2.set_ylabel("country diversity (bits)")
    a2.set_xticks(range(2007, 2026, 3))
    a2.text(0.03, 0.94, "dashed = linear trend", transform=a2.transAxes, fontsize=9.5,
            color=INK2, va="top")
    for a in (a1, a2):
        a.margins(x=0.02)
    titlebox(fig, "A steadily more international meeting",
             "Author-affiliation geography across CNS meetings, 2007–2025", y=0.97)
    source(fig, "Source: CNS abstracts 2007–2025 · countries parsed from author affiliations (~90% coverage)")
    save(fig, "fig5_globalization")


# --- Fig 6: geography over time ------------------------------------------------------
def fig_geography():
    d = pd.read_csv(TB / "recovered_countries_over_time.csv")
    order = d.groupby("country").abstracts_smoothed.sum().sort_values(ascending=False)
    show = order.index.tolist()[:6]
    cmap = dict(zip(show, [BLUE, ORANGE, GREEN, VIOLET, AQUA, RED], strict=False))
    fig, ax = plt.subplots(figsize=(10.6, 6.2))
    fig.subplots_adjust(top=0.80, bottom=0.12, left=0.08, right=0.80)
    ends = {c: d[d.country == c].sort_values("year").abstracts_smoothed.iloc[-1] for c in show}
    lab_y = dict(zip(show, spread([ends[c] for c in show], min_gap=6.5), strict=False))
    for c in show:
        sub = d[d.country == c].sort_values("year")
        ax.plot(sub.year, sub.abstracts_smoothed, color=cmap[c], lw=2.6 if c == show[0] else 1.8)
        ax.text(sub.year.iloc[-1] + 0.25, lab_y[c], c, color=cmap[c], fontsize=10.5, va="center",
                fontweight="bold" if c == show[0] else "normal")
    ax.set_xlim(2007, 2029.5)
    ax.set_ylim(bottom=0)
    ax.set_ylabel("abstracts with ≥1 author in country")
    ax.set_xticks(range(2007, 2026, 3))
    titlebox(fig, "Where the work comes from: the US leads, Europe close behind",
             "Abstracts per meeting with ≥1 author in each country (top 6, 3-yr smoothed). Spikes track the host city.")
    source(fig, "Source: CNS abstracts 2007–2025 · author-affiliation country parse")
    save(fig, "fig6_geography")


# --- Fig 7: titles are lossy (methods) -----------------------------------------------
def fig_titles_lossy():
    d = pd.read_csv(TB / "recovered_robustness_hist.csv")
    w = d.corr_bin_center.diff().median()
    fig, ax = plt.subplots(figsize=(9.4, 5.8))
    fig.subplots_adjust(top=0.79, bottom=0.14, left=0.09, right=0.95)
    ax.bar(d.corr_bin_center, d.n_keywords, width=w * 0.92, color=BLUE, alpha=0.85, zorder=3)
    ax.axvline(0.648, color=RED, lw=2.2, zorder=4)
    ax.text(0.648 - 0.02, ax.get_ylim()[1] * 0.92, "median = 0.65", color=RED,
            ha="right", fontsize=11, fontweight="bold")
    ax.set_xlabel("correlation between title-only and full-abstract yearly trajectory")
    ax.set_ylabel("number of keywords")
    titlebox(fig, "Why the full abstract matters: titles are a lossy proxy",
             "Per-keyword agreement between what titles say and what full abstracts say (1.0 = identical trend)")
    source(fig, "Source: CNS abstracts 2007–2025 · 55 keywords · median trajectory correlation 0.65")
    save(fig, "fig7_titles_lossy")


# --- Supplementary: full vocabulary map ----------------------------------------------
def fig_vocab_map(freqs):
    piv = freqs.pivot_table(index="keyword", columns="year", values="per10k")
    norm = piv.div(piv.max(axis=1), axis=0).fillna(0)
    com = norm.apply(lambda r: (r * r.index).sum() / max(r.sum(), 1e-9), axis=1)
    norm = norm.loc[com.sort_values().index]
    fig, ax = plt.subplots(figsize=(11, 13.5))
    fig.subplots_adjust(top=0.90, bottom=0.05, left=0.20, right=0.98)
    im = ax.imshow(norm.values, aspect="auto", cmap="mako" if "mako" in plt.colormaps() else "viridis")
    ax.set_yticks(range(len(norm.index)))
    ax.set_yticklabels(norm.index, fontsize=8.5)
    ax.set_xticks(range(0, len(norm.columns), 2))
    ax.set_xticklabels(norm.columns[::2], fontsize=9)
    cb = fig.colorbar(im, ax=ax, shrink=0.35, pad=0.02)
    cb.set_label("relative intensity (row-normalised to each term's peak)", fontsize=10)
    titlebox(fig, "The vocabulary map, sorted from fading to emerging",
             "Every tracked keyword × year; each row scaled to its own peak. Bright late = a rising term.",
             y=0.975)
    save(fig, "figS1_vocabulary_map")


def main():
    style()
    FG.mkdir(parents=True, exist_ok=True)
    freqs = load_freqs()
    fig_aiml_wave(freqs)
    fig_rising_fading(freqs)
    fig_two_communities()
    fig_aiml_uptake()
    fig_globalization()
    fig_geography()
    fig_titles_lossy()
    fig_vocab_map(freqs)


if __name__ == "__main__":
    main()
