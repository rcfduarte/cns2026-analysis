"""Module B (part 2) — BERTopic dynamic topic model over the corpus.

Heavy deps (bertopic/umap/hdbscan) are imported lazily. Determinism via fixed seeds.
"""

from pathlib import Path

import numpy as np
import pandas as pd


def fit_topics(embeddings: np.ndarray, docs: list[str], seed: int = 42, min_topic_size: int = 25):
    """Fit BERTopic on precomputed embeddings (UMAP+HDBSCAN, fixed seed)."""
    from bertopic import BERTopic
    from hdbscan import HDBSCAN
    from sklearn.feature_extraction.text import CountVectorizer
    from umap import UMAP

    umap = UMAP(n_neighbors=15, n_components=5, min_dist=0.0, metric="cosine", random_state=seed)
    hdbscan = HDBSCAN(min_cluster_size=min_topic_size, metric="euclidean", prediction_data=True)
    vectorizer = CountVectorizer(stop_words="english", ngram_range=(1, 2), min_df=5)
    model = BERTopic(
        umap_model=umap,
        hdbscan_model=hdbscan,
        vectorizer_model=vectorizer,
        calculate_probabilities=False,
        verbose=True,
    )
    model.fit_transform(docs, embeddings=embeddings)
    return model


def topics_over_time(model, docs: list[str], years: list[int]) -> pd.DataFrame:
    return model.topics_over_time(docs, years, nr_bins=len(set(years)))


def write_topic_outputs(model, docs: list[str], years: list[int], out_dir: Path) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_dir = Path(out_dir)
    (out_dir / "figures").mkdir(parents=True, exist_ok=True)

    info = model.get_topic_info()
    info.to_csv(out_dir / "topic_catalogue.csv", index=False)

    # per-document (year, topic) — the reliable basis for share-over-time
    pd.DataFrame({"year": list(years), "topic": list(model.topics_)}).to_csv(
        out_dir / "doc_topics.csv", index=False
    )

    tot = topics_over_time(model, docs, years)
    tot.to_csv(out_dir / "topics_over_time.csv", index=False)

    # prevalence trend for the 12 largest non-outlier topics
    top_ids = [t for t in info["Topic"].tolist() if t != -1][:12]
    piv = (
        tot[tot["Topic"].isin(top_ids)]
        .pivot_table(index="Timestamp", columns="Topic", values="Frequency", fill_value=0)
    )
    label = {row["Topic"]: row["Name"] for _, row in info.iterrows()}
    fig, ax = plt.subplots(figsize=(12, 7))
    for t in top_ids:
        if t in piv.columns:
            ax.plot(piv.index, piv[t], label=label.get(t, str(t))[:32], linewidth=1.5)
    ax.set_title("CNS data-driven topics over time (BERTopic, top 12)")
    ax.set_xlabel("year")
    ax.set_ylabel("documents per year")
    ax.legend(fontsize=6, ncol=2)
    fig.tight_layout()
    fig.savefig(out_dir / "figures" / "topics_over_time.png", dpi=130)
    plt.close(fig)
    return out_dir
