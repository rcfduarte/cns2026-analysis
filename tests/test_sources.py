from cns_scientometrics.sources import YEARS


def test_year_table_covers_all_eras():
    assert YEARS[2015].era == "A" and YEARS[2015].license == "cc-by"
    assert YEARS[2018].era == "B"
    assert YEARS[2021].era == "C" and YEARS[2021].license == "free-to-read"
    assert YEARS[2015].meeting_no == 24
    assert set(range(2007, 2025)).issubset(set(YEARS))
