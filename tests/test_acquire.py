from pathlib import Path

from cns_scientometrics import acquire

FIXTURE = Path(__file__).parent / "fixtures" / "era_a_P173.xml"
BUNDLE = Path(__file__).parent / "fixtures" / "era_c_bundle_trimmed.xml"


def test_acquire_year_era_a_routes_and_filters(tmp_path, monkeypatch):
    monkeypatch.setattr(acquire, "_era_a_pmcids", lambda y, c: ["PMC1", "PMC2"])
    xml = FIXTURE.read_text()
    monkeypatch.setattr(acquire, "eutils_efetch", lambda db, ids, c: xml)
    recs = acquire.acquire_year(2015, tmp_path)
    assert len(recs) == 2
    assert recs[0].era == "A"


def test_acquire_year_era_c_routes_to_flat(tmp_path, monkeypatch):
    # Era C 2021 has one bundle id; feed the trimmed JCN fixture
    xml = BUNDLE.read_text()
    monkeypatch.setattr(acquire, "eutils_efetch", lambda db, ids, c: xml)
    recs = acquire.acquire_year(2021, tmp_path)
    assert len(recs) >= 4
    assert all(r.era == "C" for r in recs)
