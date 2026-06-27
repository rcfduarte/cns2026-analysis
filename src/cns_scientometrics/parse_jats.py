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


_HEADER_RE = re.compile(r"^([A-Z]{1,2})(\d+)\s+\S")
_KIND_BY_PREFIX = {"K": "keynote", "O": "oral", "F": "oral", "T": "oral", "W": "oral", "P": "poster"}


def _ptext(p) -> str:
    return _text(p)


def _is_affiliation(t: str) -> bool:
    return bool(re.match(r"^\d+\s", t))


def _parse_author_line(t: str) -> list[Author]:
    # e.g. "Andreas Baumbach 1 , Agnes Korcsak-Gorzo 2 , Michael G. Müller 3"
    out = []
    for chunk in re.split(r"\s*,\s*", t):
        name = re.sub(r"[\d\s,]+$", "", chunk).strip()  # drop trailing sup markers
        name = re.sub(r"\s+\d+(\s*,\s*\d+)*$", "", name).strip()
        if name and not _is_affiliation(name) and not name.lower().startswith("email"):
            out.append(Author(raw_name=name))
    return out


def split_flat_paragraphs(
    xml: bytes,
    year: int,
    meeting_no: int,
    era: str,
    license: str,
    source_url: str,
) -> list[AbstractRecord]:
    """Segment a flat <body><p>... stream (JCN / Era C) into per-abstract records.

    A new abstract starts at every header paragraph matching '<CODE><num> <title>'
    (e.g. K1, F1, O5, P173). Following paragraphs are classified as author line,
    affiliation, Email, References, or body until the next header.
    """
    root = etree.fromstring(xml) if isinstance(xml, bytes) else etree.fromstring(xml.encode())
    art = root.find(".//article")
    if art is None:
        art = root
    body = art.find(".//body")
    if body is None:
        return []
    paras = [(_ptext(p)) for p in body.findall("./p")]

    groups: list[tuple[str, str, list[str]]] = []  # (code_letter+num, title, body_paras)
    cur: list[str] | None = None
    for t in paras:
        m = _HEADER_RE.match(t)
        if m:
            code = f"{m.group(1)}{m.group(2)}"
            title = t[m.end() - 1 :].strip()
            groups.append((code, title, []))
            cur = groups[-1][2]
        elif cur is not None:
            cur.append(t)

    out = []
    for code, title, rest in groups:
        prefix = re.match(r"^[A-Z]{1,2}", code).group(0)
        kind = _KIND_BY_PREFIX.get(prefix[0], "poster")
        authors: list[Author] = []
        affs: list[str] = []
        body_paras: list[str] = []
        refs: list[str] = []
        in_refs = False
        seen_author = False
        for t in rest:
            low = t.lower()
            if low.startswith("references"):
                in_refs = True
                continue
            if in_refs:
                refs.append(t)
                continue
            if low.startswith("email:"):
                continue
            if _is_affiliation(t):
                affs.append(t)
                continue
            if not seen_author:
                authors = _parse_author_line(t)
                seen_author = True
                continue
            body_paras.append(t)
        full = " ".join(body_paras).strip() or title
        out.append(
            AbstractRecord(
                abstract_id=f"{year}-{code}",
                year=year,
                meeting_no=meeting_no,
                type=kind,
                title=title,
                authors=authors,
                affiliations=affs,
                institutions=[],
                countries=[],
                body={"background": None, "methods": None, "results": None, "full": full},
                references=refs,
                figure_caption=None,
                doi=None,
                pmcid=None,
                era=era,
                license=license,
                source_url=source_url,
            )
        )
    return out


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
