"""Embed the corpus and fit a BERTopic dynamic topic model (Module B)."""

import argparse
from pathlib import Path

import pandas as pd

from cns_scientometrics.analyze.embeddings import doc_texts, embed_corpus
from cns_scientometrics.analyze.topics import fit_topics, write_topic_outputs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="data/corpus/corpus.parquet")
    ap.add_argument("--out", default="outputs/topics")
    ap.add_argument("--tier", default="full", choices=["title", "full"])
    ap.add_argument("--model", default="all-MiniLM-L6-v2")
    ap.add_argument("--min-topic-size", type=int, default=25)
    args = ap.parse_args()

    df = pd.read_parquet(args.corpus)
    emb = embed_corpus(df, tier=args.tier, model_name=args.model)
    docs = doc_texts(df, tier=args.tier)
    years = df["year"].tolist()
    model = fit_topics(emb, docs, min_topic_size=args.min_topic_size)
    out = write_topic_outputs(model, docs, years, Path(args.out))
    info = model.get_topic_info()
    print(f"topics={len(info[info['Topic'] != -1])} (outliers={int((model.topics_ == -1).sum())})")
    print(f"wrote {out}/topic_catalogue.csv, topics_over_time.csv, figures/")


if __name__ == "__main__":
    main()
