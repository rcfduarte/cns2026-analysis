import pandas as pd

from cns_scientometrics.analyze.contrast import contrast_table


def test_contrast_table_computes_gap():
    cosyne = pd.DataFrame(
        [
            {"keyword": "spiking", "year": 2020, "per10k": 10.0, "conference": "CoSyNe"},
            {"keyword": "deep learning", "year": 2020, "per10k": 8.0, "conference": "CoSyNe"},
        ]
    )
    cns = pd.DataFrame(
        [
            {"keyword": "spiking", "year": 2020, "per10k": 6.0, "conference": "CNS"},
            {"keyword": "deep learning", "year": 2020, "per10k": 2.0, "conference": "CNS"},
        ]
    )
    tbl = contrast_table(cosyne, cns, range(2020, 2021))
    assert round(tbl.loc["spiking", "gap_cns_minus_cosyne"], 1) == -4.0
    assert round(tbl.loc["deep learning", "gap_cns_minus_cosyne"], 1) == -6.0
    # spiking is relatively less depressed at CNS than deep learning -> higher gap, sorts first
    assert tbl.index[0] == "spiking"
