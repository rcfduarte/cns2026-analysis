"""Module B (part 1) — sentence embeddings for abstracts, cached to disk.

Heavy deps (sentence-transformers/torch) are imported lazily so the rest of the
package imports without them.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from ..http_cache import stable_key

DEFAULT_MODEL = "all-MiniLM-L6-v2"


def doc_texts(df: pd.DataFrame, tier: str = "full") -> list[str]:
    out = []
    for _, r in df.iterrows():
        title = str(r.get("title") or "")
        if tier == "title":
            out.append(title)
        else:
            body = (r.get("body") or {}).get("full") or ""
            out.append(f"{title}. {body}".strip())
    return out


def embed_corpus(
    df: pd.DataFrame,
    tier: str = "full",
    model_name: str = DEFAULT_MODEL,
    cache_dir: Path = Path("data/embeddings"),
    encoder=None,
) -> np.ndarray:
    """Return (n, d) embeddings for the corpus, cached by (tier, model, row identity)."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    ids_key = stable_key(tier, model_name, *df["abstract_id"].tolist())
    cache = cache_dir / f"emb_{model_name.replace('/', '_')}_{tier}_{ids_key}.npy"
    if cache.exists():
        return np.load(cache)

    texts = doc_texts(df, tier)
    if encoder is None:
        from sentence_transformers import SentenceTransformer

        encoder = SentenceTransformer(model_name)
    emb = np.asarray(encoder.encode(texts, show_progress_bar=True, batch_size=64))
    np.save(cache, emb)
    return emb
