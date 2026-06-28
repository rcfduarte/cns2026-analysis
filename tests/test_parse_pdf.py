from cns_scientometrics.parse_pdf import parse_pdf

# Two abstracts: P1 (Email-delimited, 2022-style) and K1 (Abstract-delimited, 2025-style).
SAMPLE = """Journal of Computational Neuroscience (2023) 51 (Suppl 1):S3
P1 A poster about spiking networks
Jane Doe*1, John Roe2
1

University of Coimbra, Coimbra, Portugal
2

MIT, Cambridge, USA

Email: jane@uc.pt
We studied spiking networks in detail and found interesting dynamics
across many regimes of the model parameters.
References
1. Someone et al. 2020
K1 A keynote on neural manifolds
Konrad Example1
1

Stanford University, Stanford, USA
*Email: k@stanford.edu
Abstract
Neural manifolds capture low dimensional structure in population activity
and explain much of the variance.
"""


def test_parse_pdf_handles_email_and_abstract_delimiters():
    recs = parse_pdf(SAMPLE, year=2022, meeting_no=31)
    by = {r.abstract_id: r for r in recs}
    assert set(by) == {"2022-P1", "2022-K1"}

    p1 = by["2022-P1"]
    assert p1.type == "poster"
    assert p1.title == "A poster about spiking networks"
    assert {a.raw_name for a in p1.authors} == {"Jane Doe", "John Roe"}
    assert "spiking networks in detail" in p1.body["full"]
    assert "References" not in p1.body["full"]

    k1 = by["2022-K1"]
    assert k1.type == "keynote"
    assert k1.title == "A keynote on neural manifolds"
    assert any("Konrad" in a.raw_name for a in k1.authors)
    assert "Neural manifolds capture" in k1.body["full"]
