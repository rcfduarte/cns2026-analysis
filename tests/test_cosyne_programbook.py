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


# A pre-2021 book: poster ids run through Roman sessions I/II/III, one talk abstract is
# wrapped at ~100 chars (below the 120-char "long line" cue used for poster prose), and an
# alphabetical author index follows the last abstract.
_PROSE = (
    "We record from populations of neurons while animals perform the task and we then fit "
    "a latent dynamical model to the resulting spike trains to characterise the geometry."
)
_NARROW = "\n".join(
    [
        "Neural populations encode many task variables at once, and this talk shows how a",
        "single recurrent circuit can multiplex them without interference between them, by",
        "relying on low-dimensional subspaces that are rotated across successive epochs of",
        "the behaviour, which we establish with recordings and with a matched network model.",
    ]
)
_BOOK_2016 = f"""I-1. Session one poster
Ann One

ANN @ MIT . EDU

Massachusetts Institute of Technology
{_PROSE}

II-1. Session two poster
Bo Two

BO @ UCL . AC . UK

University College London
{_PROSE}

III-12. Session three poster
Cy Three

CY @ EPFL . CH

EPFL
{_PROSE}

T-2. A narrow-wrapped invited talk
Di Four

DI @ GOOGLE . COM

Google
{_NARROW}

COSYNE 2016

Author Index
Ambrose A., 12, 40
Baker B., 18
Chen C., 22, 90
Dube D., 31
Evans E., 44, 101
Fox F., 57
"""


def test_roman_session_ii_iii_ids_start_their_own_records(tmp_path):
    f = tmp_path / "cosyne_2016.txt"
    f.write_text(_BOOK_2016)
    recs = parse_programbook(f)
    # I-1, II-1, III-12 and the talk are four distinct records (not merged into one block)
    assert len(recs) == 4
    firsts = [r["text"].splitlines()[0] for r in recs]
    assert firsts[1].startswith("II-1.")
    assert firsts[2].startswith("III-12.")
    assert record_countries_by_institution(recs[1]["affiliations"]) == ["GB"]
    assert record_countries_by_institution(recs[2]["affiliations"]) == ["CH"]


def test_narrow_wrapped_abstract_is_kept(tmp_path):
    f = tmp_path / "cosyne_2016.txt"
    f.write_text(_BOOK_2016)
    recs = parse_programbook(f)
    talk = [r for r in recs if r["text"].startswith("T-2.")]
    assert len(talk) == 1  # every prose line < 120 chars, but 4 lines >= 80


def test_author_index_is_not_absorbed_into_last_record(tmp_path):
    f = tmp_path / "cosyne_2016.txt"
    f.write_text(_BOOK_2016)
    last = parse_programbook(f)[-1]["text"]
    assert "Ambrose A." not in last
    assert "multiplex" in last  # the abstract itself is intact
