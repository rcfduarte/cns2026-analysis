import pandas as pd

from cns_scientometrics.analyze.robustness import keyword_tier_deltas


def test_keyword_tier_deltas_columns_and_values():
    df = pd.DataFrame(
        [
            {"year": 2019, "title": "spiking network", "body": {"full": "spiking network detail"}},
            {"year": 2020, "title": "deep learning", "body": {"full": "deep learning model"}},
        ]
    )
    kd = keyword_tier_deltas(df)
    assert set(kd.columns) == {
        "keyword",
        "title_mean_per10k",
        "full_mean_per10k",
        "trajectory_corr",
    }
    # 'spiking' appears in 2019 only; title tier should register it
    row = kd[kd["keyword"] == "spiking"].iloc[0]
    assert row["title_mean_per10k"] > 0
