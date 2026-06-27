import pandas as pd

from cns_scientometrics.corpus import write_corpus
from cns_scientometrics.schema import AbstractRecord


def _rec(i, year=2015):
    return AbstractRecord(
        abstract_id=f"{year}-P{i}",
        year=year,
        meeting_no=24,
        type="poster",
        title=f"Title {i}",
        authors=[],
        affiliations=[],
        institutions=[],
        countries=["PT"],
        body={"background": None, "methods": None, "results": None, "full": f"body {i}"},
        references=[],
        figure_caption=None,
        doi=None,
        pmcid=None,
        era="A",
        license="cc-by",
        source_url="u",
    )


def test_write_corpus_outputs_and_qa(tmp_path):
    recs = [_rec(1), _rec(2), _rec(2)]  # one duplicate id
    summary = write_corpus(recs, tmp_path)
    assert (tmp_path / "corpus.parquet").exists()
    assert (tmp_path / "corpus.jsonl").exists()
    assert (tmp_path / "qa_report.md").exists()
    df = pd.read_parquet(tmp_path / "corpus.parquet")
    assert len(df) == 2  # dedup on abstract_id
    assert summary["per_year"][2015] == 2
    assert summary["n_dropped_dupes"] == 1
    assert summary["country_coverage_rate"] == 1.0
