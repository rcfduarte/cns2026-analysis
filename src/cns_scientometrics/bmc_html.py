"""Fallback fetcher/parser for BMC supplement abstracts not deposited in PMC.

Used for CNS*2008 (vol 9 S1) and CNS*2009 (vol 10 S1), whose individual abstracts
live only as open-access BMC HTML articles. Title + authors + affiliations come from
the page's JSON-LD; the abstract body from the `c-article-body` container.
"""

import json
import re

from lxml import html as LH

from .http_cache import cached_get, stable_key
from .parse_jats import _classify, is_supplement_abstract
from .schema import AbstractRecord, Author

_DOI_RE = re.compile(r"10\.1186/1471-2202-\d+-S\d+-[A-Z]+\d+")
_LD_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
# BMC/Springer blocks non-browser User-Agents with 403.
_BROWSER_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"


def supplement_dois(supp_url: str, cache_dir, max_pages: int = 30) -> list[str]:
    """Distinct CNS abstract DOIs across all pages of a BMC supplement landing page.

    The listing paginates at 50 articles/page; iterate until a page adds nothing new.
    """
    seen, out = set(), []
    for page in range(1, max_pages + 1):
        html = cached_get(
            supp_url, {"page": str(page)}, f"bmcsupp_{stable_key(supp_url)}_{page}", cache_dir, _BROWSER_UA
        )
        new = []
        for d in _DOI_RE.findall(html):  # each DOI appears >once per listing page
            if d not in seen:
                seen.add(d)
                new.append(d)
        if not new:
            break
        out.extend(new)
    return out


def _ld_main_entity(html: str) -> dict:
    m = _LD_RE.search(html)
    if not m:
        return {}
    try:
        return json.loads(m.group(1)).get("mainEntity", {}) or {}
    except Exception:
        return {}


def parse_bmc_html(html: str, doi: str, year: int, meeting_no: int) -> AbstractRecord:
    me = _ld_main_entity(html)
    doc = LH.fromstring(html)
    title = me.get("headline") or (doc.xpath("//h1/text()") or [""])[0]
    title = re.sub(r"\s+", " ", title).strip()

    authors: list[Author] = []
    affs: list[str] = []
    for a in me.get("author", []) or []:
        name = (a.get("name") or "").strip()
        if name:
            authors.append(Author(raw_name=name))
        for org in a.get("affiliation", []) or []:
            addr = (org.get("address", {}) or {}).get("name") or org.get("name")
            if addr and addr not in affs:
                affs.append(addr)

    body_els = doc.xpath('//div[contains(@class,"c-article-body")]')
    full = re.sub(r"\s+", " ", body_els[0].text_content()).strip() if body_els else title

    kind, code = _classify(doi)
    return AbstractRecord(
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
        references=[],
        figure_caption=None,
        doi=doi,
        pmcid=None,
        era="A",
        license="cc-by",
        source_url=f"https://doi.org/{doi}",
    )


def acquire_bmc_supplement(supp_url: str, year: int, meeting_no: int, cache_dir) -> list[AbstractRecord]:
    base = "https://bmcneurosci.biomedcentral.com/articles/"
    out = []
    for doi in supplement_dois(supp_url, cache_dir):
        if not is_supplement_abstract(doi):
            continue
        html = cached_get(base + doi, None, f"bmcart_{stable_key(doi)}", cache_dir, _BROWSER_UA)
        try:
            rec = parse_bmc_html(html, doi, year, meeting_no)
        except Exception:
            continue
        if rec.type != "frontmatter" and rec.title:
            out.append(rec)
    return out
