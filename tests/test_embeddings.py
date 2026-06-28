import numpy as np
import pandas as pd

from cns_scientometrics.analyze.embeddings import doc_texts, embed_corpus


def _df():
    return pd.DataFrame(
        [
            {"abstract_id": "2020-P1", "title": "Spiking nets", "body": {"full": "we model spikes"}},
            {"abstract_id": "2020-P2", "title": "Bayesian brain", "body": {"full": "priors"}},
        ]
    )


def test_doc_texts_tiers():
    assert doc_texts(_df(), "title") == ["Spiking nets", "Bayesian brain"]
    assert doc_texts(_df(), "full")[0].startswith("Spiking nets. we model")


def test_embed_corpus_caches_and_uses_encoder(tmp_path):
    calls = {"n": 0}

    class FakeEncoder:
        def encode(self, texts, **kw):
            calls["n"] += 1
            return np.ones((len(texts), 4), dtype="float32")

    emb = embed_corpus(_df(), "full", "fake-model", tmp_path, encoder=FakeEncoder())
    assert emb.shape == (2, 4)
    # second call hits the .npy cache, encoder not invoked again
    emb2 = embed_corpus(_df(), "full", "fake-model", tmp_path, encoder=FakeEncoder())
    assert np.array_equal(emb, emb2)
    assert calls["n"] == 1
