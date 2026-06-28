"""Keyword-frequency trends over years — replicates the CoSyNe method exactly.

Frequency = (Σ keyword synonym counts in year) / (Σ words in year) × 10000.
Matching: word-boundary regex for synonyms ≤4 chars, substring otherwise, on lowercased text.
Two text tiers: 'title' (title only) and 'full' (title + abstract body).
"""

import re
from pathlib import Path

import pandas as pd

from .keywords_taxonomy import CATEGORIES, KEYWORDS


def count_keyword(text: str, synonyms: list[str]) -> int:
    """Count synonym occurrences in already-lowercased text (CoSyNe rule)."""
    total = 0
    for syn in synonyms:
        if len(syn) <= 4:
            total += len(re.findall(r"\b" + re.escape(syn) + r"\b", text))
        else:
            total += text.count(syn.lower())
    return total


def _doc_text(row, tier: str) -> str:
    title = str(row.get("title") or "")
    if tier == "title":
        return title.lower()
    body = (row.get("body") or {}).get("full") or ""
    return f"{title} {body}".lower()


def per_year_frequencies(df: pd.DataFrame, tier: str = "full") -> dict:
    """Return {keyword: {year: per-10k-words frequency}} across the corpus."""
    raw: dict[str, dict[int, int]] = {kw: {} for kw in KEYWORDS}
    words: dict[int, int] = {}
    for year, group in df.groupby("year"):
        texts = [_doc_text(r, tier) for _, r in group.iterrows()]
        words[year] = sum(len(t.split()) for t in texts)
        blob = "\n".join(texts)
        for kw, syns in KEYWORDS.items():
            raw[kw][year] = count_keyword(blob, syns)
    freqs: dict[str, dict[int, float]] = {}
    for kw in KEYWORDS:
        freqs[kw] = {
            y: (raw[kw][y] / words[y] * 10000 if words.get(y) else 0.0) for y in sorted(words)
        }
    return freqs


def frequencies_dataframe(df: pd.DataFrame, tier: str = "full") -> pd.DataFrame:
    """Tidy frequencies: columns keyword, category, year, per10k."""
    freqs = per_year_frequencies(df, tier)
    cat_of = {kw: cat for cat, kws in CATEGORIES.items() for kw in kws}
    rows = [
        {"keyword": kw, "category": cat_of.get(kw, "Other"), "year": y, "per10k": v}
        for kw, series in freqs.items()
        for y, v in series.items()
    ]
    return pd.DataFrame(rows)


def _smooth(series: pd.Series, window: int = 3) -> pd.Series:
    return series.rolling(window, center=True, min_periods=1).mean()


def write_keyword_outputs(df: pd.DataFrame, out_dir: Path, tier: str = "full") -> Path:
    """Write keyword_frequencies.csv + per-category trend PNGs + a keyword x year heatmap."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_dir = Path(out_dir)
    (out_dir / "figures").mkdir(parents=True, exist_ok=True)
    tidy = frequencies_dataframe(df, tier)
    tidy.to_csv(out_dir / "keyword_frequencies.csv", index=False)
    piv = tidy.pivot_table(index="keyword", columns="year", values="per10k")

    for cat, kws in CATEGORIES.items():
        present = [k for k in kws if k in piv.index]
        if not present:
            continue
        fig, ax = plt.subplots(figsize=(10, 6))
        for kw in present:
            ax.plot(piv.columns, _smooth(piv.loc[kw]), label=kw, linewidth=1.6)
        ax.set_title(f"CNS abstracts — {cat} (per 10k words)")
        ax.set_xlabel("year")
        ax.set_ylabel("frequency per 10k words")
        ax.legend(fontsize=7, ncol=2)
        fig.tight_layout()
        fig.savefig(out_dir / "figures" / f"trend_{cat.replace('/', '-').replace(' ', '_')}.png", dpi=130)
        plt.close(fig)

    order = piv.div(piv.max(axis=1), axis=0).fillna(0)
    order = order.loc[order.apply(lambda r: (r * r.index).sum() / max(r.sum(), 1e-9), axis=1).sort_values().index]
    fig, ax = plt.subplots(figsize=(11, 14))
    im = ax.imshow(order.values, aspect="auto", cmap="magma")
    ax.set_yticks(range(len(order.index)))
    ax.set_yticklabels(order.index, fontsize=7)
    ax.set_xticks(range(len(order.columns)))
    ax.set_xticklabels(order.columns, rotation=90, fontsize=7)
    ax.set_title("CNS keyword intensity (row-normalized to peak), sorted by center-of-mass year")
    fig.colorbar(im, ax=ax, shrink=0.5)
    fig.tight_layout()
    fig.savefig(out_dir / "figures" / "keyword_heatmap.png", dpi=130)
    plt.close(fig)
    return out_dir
