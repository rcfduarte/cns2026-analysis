"""JATS XML → canonical AbstractRecord parsers (Era A single, Era B/C bundled)."""

import re

from lxml import etree

from .schema import AbstractRecord, Author

_SEC_KEYS = ("background", "methods", "results")


def _text(el) -> str:
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip() if el is not None else ""


def _classify(doi: str | None) -> tuple[str, str]:
    """Return (type, code) from a DOI suffix like ...-16-S1-P173 / -O5 / -A1."""
    m = re.search(r"-([OPA])(\d+)$", doi or "")
    if not m:
        return "poster", "P0"
    kind = {"O": "oral", "P": "poster", "A": "frontmatter"}[m.group(1)]
    return kind, f"{m.group(1)}{m.group(2)}"


def _authors(scope) -> list[Author]:
    out = []
    for c in scope.findall('.//contrib[@contrib-type="author"]'):
        sur, giv = _text(c.find(".//surname")), _text(c.find(".//given-names"))
        if sur or giv:
            out.append(
                Author(raw_name=f"{giv} {sur}".strip(), given=giv or None, family=sur or None)
            )
    return out


def parse_era_a_article(xml: bytes, year: int, meeting_no: int) -> AbstractRecord:
    root = etree.fromstring(xml) if isinstance(xml, bytes) else etree.fromstring(xml.encode())
    art = root.find(".//article")
    if art is None:
        art = root
    doi = _text(art.find('.//article-id[@pub-id-type="doi"]')) or None
    pmcid = _text(art.find('.//article-id[@pub-id-type="pmcid"]')) or None
    if pmcid and not pmcid.startswith("PMC"):
        pmcid = f"PMC{pmcid}"
    title = _text(art.find(".//title-group/article-title"))
    affs = [_text(a) for a in art.findall(".//aff") if _text(a)]
    body = {"background": None, "methods": None, "results": None, "full": None}
    for sec in art.findall(".//body//sec") + art.findall(".//abstract//sec"):
        head = _text(sec.find("./title")).lower()
        for key in _SEC_KEYS:
            if key in head:
                body[key] = _text(sec)
    full = " ".join(v for v in (body["background"], body["methods"], body["results"]) if v)
    if not full:
        full = _text(art.find(".//abstract")) or _text(art.find(".//body"))
    body["full"] = full or title
    kind, code = _classify(doi)
    refs = [_text(r) for r in art.findall(".//ref-list//ref")]
    fig = art.find(".//fig//caption")
    return AbstractRecord(
        abstract_id=f"{year}-{code}",
        year=year,
        meeting_no=meeting_no,
        type=kind,
        title=title,
        authors=_authors(art),
        affiliations=affs,
        institutions=[],
        countries=[],
        body=body,
        references=refs,
        figure_caption=_text(fig) or None,
        doi=doi,
        pmcid=pmcid,
        era="A",
        license="cc-by",
        source_url=f"https://doi.org/{doi}" if doi else "",
    )


def _abstract_sections(art):
    body = art.find(".//body")
    if body is None:
        return []
    return [s for s in body.findall("./sec") if s.find("./title") is not None and s.findall(".//p")]


def split_bundle(
    xml: bytes,
    year: int,
    meeting_no: int,
    era: str,
    license: str,
    source_url: str,
) -> list[AbstractRecord]:
    root = etree.fromstring(xml) if isinstance(xml, bytes) else etree.fromstring(xml.encode())
    art = root.find(".//article")
    if art is None:
        art = root
    out = []
    for i, sec in enumerate(_abstract_sections(art), start=1):
        title = _text(sec.find("./title"))
        m = re.search(r"\b([OP])\s?-?(\d+)\b", title)
        if m:
            kind = {"O": "oral", "P": "poster"}[m.group(1)]
            code = f"{m.group(1)}{m.group(2)}"
        else:
            kind, code = "poster", f"B{i:04d}"
        affs = [_text(a) for a in sec.findall(".//aff") if _text(a)]
        out.append(
            AbstractRecord(
                abstract_id=f"{year}-{code}",
                year=year,
                meeting_no=meeting_no,
                type=kind,
                title=title,
                authors=_authors(sec),
                affiliations=affs,
                institutions=[],
                countries=[],
                body={"background": None, "methods": None, "results": None, "full": _text(sec)},
                references=[],
                figure_caption=None,
                doi=None,
                pmcid=None,
                era=era,
                license=license,
                source_url=source_url,
            )
        )
    return out
