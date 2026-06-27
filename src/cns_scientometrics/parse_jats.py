"""JATS XML → canonical AbstractRecord parsers (Era A single, Era B/C bundled)."""

import re

from lxml import etree

from .schema import AbstractRecord, Author

_SEC_KEYS = ("background", "methods", "results")


def _text(el) -> str:
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip() if el is not None else ""


# A CNS supplement abstract DOI ends in -S<suppl>-<CODE><num>, e.g. -16-S1-P173, -S1-F3, -S1-A1.
_SUPP_RE = re.compile(r"-S\d+-([A-Z]{1,2})(\d+)$")
# Prefix → record type. Keynotes K; orals O/F(featured)/I(invited)/T(tutorial)/W(workshop);
# posters P; front matter A.
_PREFIX_KIND = {"K": "keynote", "O": "oral", "F": "oral", "I": "oral", "T": "oral", "W": "oral"}


def is_supplement_abstract(doi: str | None) -> bool:
    return bool(_SUPP_RE.search(doi or ""))


def _classify(doi: str | None) -> tuple[str, str]:
    """Return (type, code) from a supplement DOI suffix; ('poster','P0') if unrecognized."""
    m = _SUPP_RE.search(doi or "")
    if not m:
        return "poster", "P0"
    prefix, num = m.group(1), m.group(2)
    kind = "frontmatter" if prefix == "A" else _PREFIX_KIND.get(prefix[0], "poster")
    return kind, f"{prefix}{num}"


def _authors(scope) -> list[Author]:
    out = []
    for c in scope.findall('.//contrib[@contrib-type="author"]'):
        sur, giv = _text(c.find(".//surname")), _text(c.find(".//given-names"))
        if sur or giv:
            out.append(
                Author(raw_name=f"{giv} {sur}".strip(), given=giv or None, family=sur or None)
            )
    return out


def _parse_era_a_element(art, year: int, meeting_no: int) -> AbstractRecord:
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


def _root(xml):
    return etree.fromstring(xml) if isinstance(xml, bytes) else etree.fromstring(xml.encode())


def parse_era_a_article(xml: bytes, year: int, meeting_no: int) -> AbstractRecord:
    root = _root(xml)
    art = root.find(".//article")
    return _parse_era_a_element(art if art is not None else root, year, meeting_no)


def parse_era_a_articleset(xml: bytes, year: int, meeting_no: int) -> list[AbstractRecord]:
    """Parse every <article> in a batched PMC articleset into Era A records."""
    root = _root(xml)
    arts = root.findall(".//article")
    if not arts:
        arts = [root]
    out = []
    for art in arts:
        doi = _text(art.find('.//article-id[@pub-id-type="doi"]')) or None
        if not is_supplement_abstract(doi):
            continue  # regular (non-CNS) journal article — exclude
        try:
            out.append(_parse_era_a_element(art, year, meeting_no))
        except Exception:
            continue
    return out


# Abstract header line: "<CODE><num> <title>", e.g. "P1 ...", "K3 ...", "F12 ...".
_HEADER_RE = re.compile(r"^([A-Z]{1,2})(\d+)\b\s*(.*)")
_KIND_BY_PREFIX = {
    "K": "keynote",
    "O": "oral",
    "F": "oral",
    "I": "oral",
    "T": "oral",
    "W": "oral",
    "P": "poster",
}


def _kind_for(code: str) -> str:
    return _KIND_BY_PREFIX.get(code[0], "poster")


def _starts_affiliation(t: str) -> bool:
    return bool(re.match(r"^\d", t.strip()))


def _clean_authors(text: str) -> list[Author]:
    """Parse an author byline, tolerating spaced (Era C) and glued (Era B) sup markers."""
    text = re.sub(r"\d+", " ", text)  # names carry no digits; drop superscript markers
    out = []
    for chunk in re.split(r"[,;]", text):
        name = re.sub(r"\s+", " ", chunk).strip(" .,&")
        if len(name) >= 3 and re.search(r"[A-Za-z]", name) and not name.lower().startswith("email"):
            out.append(Author(raw_name=name))
    return out


def _split_affiliations(line: str) -> list[str]:
    """Split a (possibly glued) affiliation line like '1Inst A, USA2Inst B, UK' into items."""
    out = []
    for part in re.split(r"\d+(?=[A-Z])", line):
        p = re.sub(r"^\d+\s*", "", part).strip(" .,;")
        if len(p) > 3:
            out.append(p)
    return out


def _assemble(
    code: str,
    title: str,
    lines: list[str],
    year: int,
    meeting_no: int,
    era: str,
    license: str,
    source_url: str,
) -> AbstractRecord:
    """Build a record from an abstract's title and its ordered following text lines."""
    authors: list[Author] = []
    affs: list[str] = []
    body_paras: list[str] = []
    refs: list[str] = []
    in_refs = False
    seen_author = False
    for t in lines:
        low = t.lower()
        if low.startswith("references"):
            in_refs = True
            continue
        if in_refs:
            refs.append(t)
            continue
        if low.startswith("email:"):
            continue
        if not seen_author and not _starts_affiliation(t):
            authors = _clean_authors(t)
            seen_author = True
            continue
        if _starts_affiliation(t):
            affs += _split_affiliations(t)
            continue
        body_paras.append(t)
    full = " ".join(body_paras).strip() or title
    return AbstractRecord(
        abstract_id=f"{year}-{code}",
        year=year,
        meeting_no=meeting_no,
        type=_kind_for(code),
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
    (e.g. K1, F1, O5, P173); following paragraphs are author/affiliation/body.
    """
    root = _root(xml)
    art = root.find(".//article")
    if art is None:
        art = root
    body = art.find(".//body")
    if body is None:
        return []

    groups: list[tuple[str, str, list[str]]] = []
    cur: list[str] | None = None
    for p in body.findall("./p"):
        t = _text(p)
        m = _HEADER_RE.match(t)
        if m and m.group(3):
            groups.append((f"{m.group(1)}{m.group(2)}", m.group(3).strip(), []))
            cur = groups[-1][2]
        elif cur is not None:
            cur.append(t)

    return [
        _assemble(code, title, rest, year, meeting_no, era, license, source_url)
        for code, title, rest in groups
    ]


def _abstract_sections(art):
    body = art.find(".//body")
    if body is None:
        return []
    return [s for s in body.findall("./sec") if s.find("./title") is not None]


def _section_lines(sec) -> list[str]:
    """Ordered text lines under an abstract <sec>, excluding its own title.

    Era B stores the byline and affiliations as nested <sec> titles; body as <p>.
    """
    own_title = sec.find("./title")
    lines = []
    for el in sec.iter("title", "p"):
        if el is own_title:
            continue
        t = _text(el)
        if t:
            lines.append(t)
    return lines


def split_bundle(
    xml: bytes,
    year: int,
    meeting_no: int,
    era: str,
    license: str,
    source_url: str,
) -> list[AbstractRecord]:
    """Split a <sec>-structured bundle (BMC / Era B): one top-level <sec> per abstract."""
    root = _root(xml)
    art = root.find(".//article")
    if art is None:
        art = root
    out = []
    for i, sec in enumerate(_abstract_sections(art), start=1):
        title_text = _text(sec.find("./title"))
        m = _HEADER_RE.match(title_text)
        if m and m.group(3):
            code, title = f"{m.group(1)}{m.group(2)}", m.group(3).strip()
        else:
            code, title = f"B{i:04d}", title_text
        out.append(
            _assemble(code, title, _section_lines(sec), year, meeting_no, era, license, source_url)
        )
    return out
