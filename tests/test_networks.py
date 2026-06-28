import pandas as pd

from cns_scientometrics.analyze.networks import (
    coauthorship_graph,
    country_of,
    internationalization,
    record_countries,
)


def test_country_of_aliases_and_names():
    assert country_of("Dept, University of Newcastle, Newcastle, Australia") == "AU"
    assert country_of("MIT, Cambridge, USA") == "US"
    assert country_of("UCL, London, UK") == "GB"
    assert country_of("Univ Hertfordshire, Hatfield, Herts, AL10 9AB, UK") == "GB"
    assert country_of("Some lab with no country") is None


def _df():
    return pd.DataFrame(
        [
            {
                "year": 2020,
                "authors": [{"raw_name": "A X"}, {"raw_name": "B Y"}],
                "affiliations": ["Inst, Coimbra, Portugal", "Inst2, Berlin, Germany"],
            },
            {
                "year": 2020,
                "authors": [{"raw_name": "B Y"}, {"raw_name": "C Z"}],
                "affiliations": ["MIT, Cambridge, USA"],
            },
        ]
    )


def test_record_countries_dedupes():
    assert set(record_countries(["X, Coimbra, Portugal", "Y, Lisbon, Portugal"])) == {"PT"}


def test_coauthorship_graph_edges_and_weights():
    g = coauthorship_graph(_df())
    assert g.has_edge("A X", "B Y")
    assert g.nodes["B Y"]["abstracts"] == 2  # appears in both records


def test_internationalization_columns():
    intl = internationalization(_df())
    row = intl[intl["year"] == 2020].iloc[0]
    assert row["distinct_countries"] == 3  # PT, DE, US
    assert row["n_abstracts"] == 2
