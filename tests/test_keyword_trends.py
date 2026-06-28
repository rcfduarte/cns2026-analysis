import pandas as pd

from cns_scientometrics.analyze.keyword_trends import (
    count_keyword,
    frequencies_dataframe,
    per_year_frequencies,
)


def test_count_keyword_short_vs_long():
    text = "we trained an rnn while running deep learning experiments".lower()
    # 'rnn' (<=4 chars) matches on word boundary, NOT inside 'running'
    assert count_keyword(text, ["rnn"]) == 1
    # long synonym matches as substring
    assert count_keyword(text, ["deep learning"]) == 1
    assert count_keyword(text, ["transformer"]) == 0


def _df():
    return pd.DataFrame(
        [
            {"year": 2020, "title": "Deep learning model", "body": {"full": "a b c d"}},
            {"year": 2020, "title": "Bayesian inference study", "body": {"full": "e f"}},
        ]
    )


def test_per_year_frequency_formula():
    freqs = per_year_frequencies(_df(), tier="full")
    # 2020 total words: "deep learning model a b c d" (7) + "bayesian inference study e f" (5) = 12
    # "deep learning" appears once -> 1/12*10000
    assert round(freqs["deep learning"][2020], 2) == round(1 / 12 * 10000, 2)
    # CoSyNe counts overlapping synonyms separately: 'bayesian' + 'bayesian inference' = 2
    assert round(freqs["Bayesian"][2020], 2) == round(2 / 12 * 10000, 2)


def test_title_tier_excludes_body():
    freqs_title = per_year_frequencies(_df(), tier="title")
    # body words excluded; title-only word count = 3 + 3 = 6
    assert round(freqs_title["deep learning"][2020], 2) == round(1 / 6 * 10000, 2)


def test_frequencies_dataframe_shape():
    out = frequencies_dataframe(_df(), tier="full")
    assert set(out.columns) == {"keyword", "category", "year", "per10k"}
    assert (out["keyword"] == "deep learning").any()
