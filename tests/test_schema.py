import pytest

from cns_scientometrics.schema import AbstractRecord, Author


def test_minimal_record_validates():
    rec = AbstractRecord(
        abstract_id="2015-P173",
        year=2015,
        meeting_no=24,
        type="poster",
        title="A test abstract",
        authors=[Author(raw_name="Jane Doe", family="Doe", given="Jane")],
        affiliations=["Dept X, Univ Y"],
        institutions=[],
        countries=[],
        body={"background": "bg", "methods": "m", "results": "r", "full": "bg m r"},
        references=[],
        figure_caption=None,
        doi="10.1186/x",
        pmcid="PMC4697476",
        era="A",
        license="cc-by",
        source_url="https://example.org",
    )
    assert rec.abstract_id == "2015-P173"
    assert rec.body["full"] == "bg m r"


def test_invalid_type_rejected():
    with pytest.raises(ValueError):
        AbstractRecord(
            abstract_id="x",
            year=2015,
            meeting_no=24,
            type="banana",
            title="t",
            authors=[],
            affiliations=[],
            institutions=[],
            countries=[],
            body={"background": None, "methods": None, "results": None, "full": "t"},
            references=[],
            figure_caption=None,
            doi=None,
            pmcid=None,
            era="A",
            license="cc-by",
            source_url="u",
        )
