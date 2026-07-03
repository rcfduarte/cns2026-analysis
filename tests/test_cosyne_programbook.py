"""Tests for the CoSyNe program-book parser + institution->country resolver."""
from cns_scientometrics.analyze.cosyne_programbook import (
    accepted_counts,
    country_of_institution,
    load_cosyne_dir,
    parse_programbook,
    record_countries_by_institution,
)

# A minimal, structurally-faithful CoSyNe program-book excerpt: id header, title,
# authors, e-mail block, numbered affiliation footnotes, then abstract prose. Includes
# both the Roman (pre-2021) and Arabic (2021+) poster-id styles plus a talk id.
_BOOK_2024 = """Program Summary
Poster Session 1

1-001. A consistent map in entorhinal cortex supports spatial memory
Yi Gu

YI . GU @ NIH . GOV

National Institute of Neurological Disorders and Stroke
The medial entorhinal cortex is hypothesized to function as a cognitive map for memory-guided navigation, and here we image its calcium dynamics across ten days of learning in mice to test that idea directly.

1-002. Duality of Bures and Shape Distances
Sarah Harvey1,2
Alex Williams3

SHARVEY @ FLATIRONINSTITUTE . ORG
ALEX @ NYU. EDU

1 Flatiron Institute
2 Champalimaud Research
3 New York University
How should neuroscientists mathematically evaluate whether two networks have similar neural representations across many recorded units and artificial hidden layers in a large population model of cortex.

T-13. A talk with a European lab
Foo Bar

FOO @ EPFL . CH

EPFL
This is the abstract body prose for the talk, written as one long unwrapped line so that it clears the prose threshold and the block is retained as a real accepted-abstract record with its footnote.
"""


def test_country_of_institution_known_cases():
    assert country_of_institution("Stanford University") == "US"
    assert country_of_institution("Massachusetts Institute of Technology") == "US"
    assert country_of_institution("MIT") == "US"
    assert country_of_institution("University College London") == "GB"
    assert country_of_institution("EPFL") == "CH"
    assert country_of_institution("Champalimaud Research") == "PT"
    assert country_of_institution("Weizmann Institute of Science") == "IL"
    assert country_of_institution("McGill University") == "CA"
    # a bare department fragment is not an institution -> no country (not a wrong guess)
    assert country_of_institution("Neuroscience") is None
    assert country_of_institution("Department of Physics") is None


def test_record_countries_dedupes_by_institution():
    got = record_countries_by_institution(
        ["New York University", "Center for Neural Science", "Flatiron Institute", "Neuroscience"]
    )
    assert got == ["US"]  # all US, deduped; the department fragment drops out


def test_parse_programbook_segments_records(tmp_path):
    f = tmp_path / "cosyne_2024.txt"
    f.write_text(_BOOK_2024)
    recs = parse_programbook(f)
    assert len(recs) == 3
    # affiliation footnote numbers are stripped; institutions captured
    assert "New York University" in recs[1]["affiliations"]
    assert "Champalimaud Research" in recs[1]["affiliations"]
    # per-abstract country resolution over the parsed affiliations
    assert set(record_countries_by_institution(recs[1]["affiliations"])) == {"US", "PT"}


def test_load_cosyne_dir_has_year_and_affils(tmp_path):
    (tmp_path / "cosyne_2024.txt").write_text(_BOOK_2024)
    df = load_cosyne_dir(tmp_path)
    assert len(df) == 3
    assert set(df.columns) == {"year", "text", "affiliations"}
    assert (df["year"] == 2024).all()


def test_accepted_counts_counts_ids(tmp_path):
    (tmp_path / "cosyne_2024.txt").write_text(_BOOK_2024)
    ac = accepted_counts(tmp_path, min_posters=1)
    assert len(ac) == 1
    row = ac.iloc[0]
    assert row["year"] == 2024
    assert row["posters"] == 2  # 1-001, 1-002
    assert row["talks"] == 1  # T-13
    assert row["accepted"] == 3
