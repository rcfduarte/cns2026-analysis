from cns_scientometrics import normalize
from cns_scientometrics.schema import AbstractRecord


def _rec(affs):
    return AbstractRecord(
        abstract_id="2015-P1",
        year=2015,
        meeting_no=24,
        type="poster",
        title="t",
        authors=[],
        affiliations=affs,
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


def test_enrich_fills_institutions(monkeypatch, tmp_path):
    monkeypatch.setattr(
        normalize, "resolve_affiliation", lambda aff, c: ("University of Coimbra", "PT")
    )
    out = normalize.enrich_record(_rec(["Univ Coimbra, Portugal"]), tmp_path)
    assert out.institutions == ["University of Coimbra"]
    assert out.countries == ["PT"]


def test_enrich_dedupes_and_tolerates_misses(monkeypatch, tmp_path):
    monkeypatch.setattr(
        normalize, "resolve_affiliation", lambda aff, c: ("Univ X", "US") if "X" in aff else (None, None)
    )
    out = normalize.enrich_record(_rec(["Dept, Univ X", "Univ X again", "Unknown place"]), tmp_path)
    assert out.institutions == ["Univ X"]
    assert out.countries == ["US"]
