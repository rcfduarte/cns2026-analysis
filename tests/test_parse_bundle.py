from pathlib import Path

from cns_scientometrics.parse_jats import split_bundle, split_flat_paragraphs

FIXTURE = Path(__file__).parent / "fixtures" / "era_c_bundle_trimmed.xml"
ERA_B = Path(__file__).parent / "fixtures" / "era_b_bundle_trimmed.xml"


def test_split_flat_paragraphs_yields_multiple_records():
    xml = FIXTURE.read_bytes()
    recs = split_flat_paragraphs(
        xml,
        year=2021,
        meeting_no=30,
        era="C",
        license="free-to-read",
        source_url="https://doi.org/10.1007/s10827-021-00801-9",
    )
    assert len(recs) >= 4  # fixture covers K1-K4 (+ F1)
    assert all(r.era == "C" and r.license == "free-to-read" for r in recs)
    assert all(r.body["full"] for r in recs)
    assert all(r.year == 2021 for r in recs)


def test_split_flat_paragraphs_classifies_and_extracts():
    recs = split_flat_paragraphs(
        FIXTURE.read_bytes(), 2021, 30, "C", "free-to-read", "u"
    )
    by_id = {r.abstract_id: r for r in recs}
    k1 = by_id["2021-K1"]
    assert k1.type == "keynote"
    assert "cerebral cortex" in k1.title.lower()
    assert any("Singer" in a.raw_name for a in k1.authors)
    assert k1.affiliations  # at least one affiliation captured
    assert "cortex" in k1.body["full"].lower()


def test_split_bundle_era_b_extracts_authors_and_affiliations():
    recs = split_bundle(
        ERA_B.read_bytes(), year=2017, meeting_no=26, era="B", license="cc-by", source_url="u"
    )
    assert len(recs) == 3
    p1 = recs[0]
    assert p1.abstract_id == "2017-P1"
    assert p1.type == "poster"
    assert any("Rubchinsky" in a.raw_name for a in p1.authors)
    assert p1.affiliations  # nested-sec affiliation lines parsed
    assert len(p1.body["full"]) > 500
    assert all(r.era == "B" and r.license == "cc-by" for r in recs)
