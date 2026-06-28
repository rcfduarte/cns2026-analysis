"""Parse JCN supplement PDFs (Era C, 2022–2025) into per-abstract records.

These supplements are Springer-paywalled (user-supplied PDFs). pdftotext (default
flow mode) reads the two-column layout in reading order. Each abstract is a flat
line block: ``<CODE> <title…>`` → author line(s) → affiliation markers+text →
``Email:`` / ``Abstract`` → body → ``References``. Page running-headers and bare
page numbers are interleaved and stripped.
"""

import re
import subprocess
from pathlib import Path

from .parse_jats import _clean_authors
from .schema import AbstractRecord

_HEADER = re.compile(r"^([A-Z]{1,2})(\d+)\s+(.+)")
# valid abstract code prefixes (keynote/oral/featured/poster/workshop/tutorial/invited/lecture)
_PREFIX_KIND = {"K": "keynote", "L": "keynote", "BK": "keynote"}
_ORAL_PREFIXES = {"O", "F", "FO", "I", "T", "W", "R"}
_AUTHORISH = re.compile(r"[A-Za-z]\d|\*")
_RUNNING_HEADER = re.compile(r"^Journal of Computational Neuroscience|^\d+ \(Suppl")
_PAGE_NUM = re.compile(r"^S?\d{1,4}$")
# Springer cover/footer artifacts on the first page of each article PDF.
_SPRINGER = re.compile(r"^Vol[.:]|0123456789|^Content courtesy of|^13$|^1 3$")
_EMAIL = re.compile(r"^\*?Email:", re.IGNORECASE)


def pdf_to_text(pdf_path: Path, out_dir: Path) -> str:
    """Run pdftotext (default flow mode), caching the .txt next to the source."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    txt = out_dir / (Path(pdf_path).stem + ".txt")
    if not txt.exists():
        subprocess.run(["pdftotext", str(pdf_path), str(txt)], check=True)
    return txt.read_text(encoding="utf-8", errors="replace")


def _kind_for(code: str) -> str:
    if code[:2] in _PREFIX_KIND:
        return _PREFIX_KIND[code[:2]]
    if code[0] in _PREFIX_KIND:
        return _PREFIX_KIND[code[0]]
    if code[0] in _ORAL_PREFIXES:
        return "oral"
    return "poster"


def _is_noise(line: str) -> bool:
    s = line.strip()
    return bool(_RUNNING_HEADER.match(s) or _PAGE_NUM.match(s) or _SPRINGER.search(s))


def _dehyphenate(lines: list[str]) -> str:
    out = ""
    for ln in lines:
        ln = ln.replace("\xad", "")
        if out and out.endswith("-") and re.search(r"[a-z]-$", out):
            out = out[:-1] + ln.lstrip()
        else:
            out = (out + " " + ln).strip() if out else ln
    return re.sub(r"\s+", " ", out).strip()


def _parse_block(code: str, first_title: str, lines: list[str], year: int, meeting_no: int) -> AbstractRecord:
    # locate the body delimiter: a literal "Abstract" line (2025) or the Email line (2022-24)
    body_start = None
    for i, ln in enumerate(lines):
        if ln.strip() == "Abstract":
            body_start = i + 1
            break
    if body_start is None:
        for i, ln in enumerate(lines):
            if _EMAIL.match(ln.strip()):
                body_start = i + 1
                break

    # title = header remainder + continuation lines until the first author-ish line
    title_parts = [first_title]
    author_idx = None
    for i, ln in enumerate(lines):
        s = ln.strip()
        if not s:
            continue
        if _AUTHORISH.search(s):
            author_idx = i
            break
        title_parts.append(s)
    title = re.sub(r"\s+", " ", " ".join(title_parts)).strip()

    # authors: consecutive author-ish lines from author_idx (until a bare marker / Email / Abstract)
    authors = []
    if author_idx is not None:
        byline = []
        for ln in lines[author_idx:]:
            s = ln.strip()
            if not s or s.isdigit() or s == "*" or _EMAIL.match(s) or s == "Abstract":
                break
            byline.append(s)
            if "," not in s and not s.endswith(","):
                break
        authors = _clean_authors(" ".join(byline))

    # affiliations: text lines between authors and the body delimiter, skipping markers
    affs = []
    aff_region = lines[(author_idx + 1) if author_idx is not None else 0 : body_start or 0]
    for ln in aff_region:
        s = ln.strip()
        if not s or s.isdigit() or s == "*" or _EMAIL.match(s) or s == "Abstract":
            continue
        if re.search(r"[A-Za-z]", s) and len(s) > 3:
            affs.append(s)

    # body: from delimiter (or after affiliations) until "References"
    start = body_start if body_start is not None else (author_idx or 0) + 1
    body_lines = []
    for ln in lines[start:]:
        if ln.strip() == "References":
            break
        if not _is_noise(ln) and ln.strip():
            body_lines.append(ln.strip())
    full = _dehyphenate(body_lines) or title

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
        references=[],
        figure_caption=None,
        doi=None,
        pmcid=None,
        era="C",
        license="free-to-read",
        source_url="",
    )


def parse_pdf(text: str, year: int, meeting_no: int) -> list[AbstractRecord]:
    raw = [ln for ln in text.splitlines() if not _is_noise(ln)]
    blocks: list[tuple[str, str, list[str]]] = []
    cur: list[str] | None = None
    for ln in raw:
        m = _HEADER.match(ln)
        if m and (m.group(1)[0] in _PREFIX_KIND or m.group(1) in _ORAL_PREFIXES or m.group(1)[0] in _ORAL_PREFIXES or m.group(1) == "P"):
            blocks.append((f"{m.group(1)}{m.group(2)}", m.group(3).strip(), []))
            cur = blocks[-1][2]
        elif cur is not None:
            cur.append(ln)
    return [_parse_block(code, title, body, year, meeting_no) for code, title, body in blocks]
