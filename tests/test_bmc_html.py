from pathlib import Path

from cns_scientometrics.bmc_html import parse_bmc_html, supplement_dois

FIXTURE = Path(__file__).parent / "fixtures" / "bmc_article_2009_P1.html"


def test_parse_bmc_html_extracts_title_authors_body():
    html = FIXTURE.read_text(encoding="utf-8")
    rec = parse_bmc_html(html, "10.1186/1471-2202-10-S1-P1", year=2009, meeting_no=18)
    assert rec.abstract_id == "2009-P1"
    assert rec.type == "poster"
    assert "HoneyBee Standard Brain" in rec.title
    assert len(rec.authors) >= 2
    assert any("Rybak" in a.raw_name for a in rec.authors)
    assert rec.affiliations  # from JSON-LD author affiliations
    assert len(rec.body["full"]) > 500
    assert rec.era == "A" and rec.license == "cc-by"


def test_supplement_dois_extracts_distinct(tmp_path, monkeypatch):
    import cns_scientometrics.bmc_html as m

    page = (
        '<a href="/articles/10.1186/1471-2202-10-S1-P1">x</a>'
        '<a href="/articles/10.1186/1471-2202-10-S1-P1">dup</a>'
        '<a href="/articles/10.1186/1471-2202-10-S1-O3">y</a>'
    )
    monkeypatch.setattr(m, "cached_get", lambda url, params, key, cache, ua=None: page)
    dois = supplement_dois("http://supp", tmp_path)
    assert dois == ["10.1186/1471-2202-10-S1-P1", "10.1186/1471-2202-10-S1-O3"]
