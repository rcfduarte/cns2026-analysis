"""Module D — title-only vs title+abstract robustness.

How much do the scientometric conclusions change when you only have titles vs the full
abstract? Quantified on the keyword axis (always available) and the embedding axis
(how much the body moves each document's representation).
"""

from pathlib import Path

import numpy as np
import pandas as pd

from .keyword_trends import per_year_frequencies


def keyword_tier_deltas(df: pd.DataFrame) -> pd.DataFrame:
    """Per keyword: per-year trajectory correlation between title-only and full tiers."""
    f_title = per_year_frequencies(df, tier="title")
    f_full = per_year_frequencies(df, tier="full")
    rows = []
    for kw in f_full:
        years = sorted(f_full[kw])
        a = np.array([f_title[kw][y] for y in years])
        b = np.array([f_full[kw][y] for y in years])
        corr = float(np.corrcoef(a, b)[0, 1]) if a.std() > 0 and b.std() > 0 else np.nan
        rows.append(
            {
                "keyword": kw,
                "title_mean_per10k": round(a.mean(), 3),
                "full_mean_per10k": round(b.mean(), 3),
                "trajectory_corr": round(corr, 3) if not np.isnan(corr) else None,
            }
        )
    return pd.DataFrame(rows).sort_values("trajectory_corr")


def embedding_tier_shift(df: pd.DataFrame, model_name: str = "all-MiniLM-L6-v2") -> dict:
    """Cosine similarity between each doc's title-only and full embeddings."""
    from .embeddings import embed_corpus

    et = embed_corpus(df, tier="title", model_name=model_name)
    ef = embed_corpus(df, tier="full", model_name=model_name)
    et = et / np.linalg.norm(et, axis=1, keepdims=True)
    ef = ef / np.linalg.norm(ef, axis=1, keepdims=True)
    cos = (et * ef).sum(axis=1)
    return {
        "mean_cosine_title_vs_full": float(cos.mean()),
        "median_cosine": float(np.median(cos)),
        "p10_cosine": float(np.percentile(cos, 10)),
    }


def write_robustness_outputs(df: pd.DataFrame, out_dir: Path, with_embeddings: bool = True) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    kd = keyword_tier_deltas(df)
    kd.to_csv(out_dir / "keyword_tier_deltas.csv", index=False)
    summary = {
        "median_keyword_trajectory_corr": float(kd["trajectory_corr"].median()),
        "n_keywords_corr_below_0.7": int((kd["trajectory_corr"] < 0.7).sum()),
    }
    if with_embeddings:
        summary.update(embedding_tier_shift(df))
    pd.Series(summary).to_csv(out_dir / "robustness_summary.csv")
    return out_dir
