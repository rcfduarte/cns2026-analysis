from pathlib import Path

from cns_scientometrics.parse_jats import parse_era_a_article

FIXTURE = Path(__file__).parent / "fixtures" / "era_a_P173.xml"


def test_parse_era_a_extracts_core_fields():
    xml = FIXTURE.read_bytes()
    rec = parse_era_a_article(xml, year=2015, meeting_no=24)
    assert rec.type == "poster"
    assert rec.abstract_id == "2015-P173"
    assert rec.title
    assert len(rec.authors) >= 1
    assert rec.body["full"]
    assert rec.era == "A" and rec.license == "cc-by"
    assert rec.doi == "10.1186/1471-2202-16-S1-P173"
