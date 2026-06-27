"""Canonical per-abstract record schema (spec §5 Layer 2)."""

from typing import Literal

from pydantic import BaseModel


class Author(BaseModel):
    raw_name: str
    given: str | None = None
    family: str | None = None
    openalex_id: str | None = None


class AbstractRecord(BaseModel):
    abstract_id: str
    year: int
    meeting_no: int
    type: Literal["oral", "poster", "keynote", "frontmatter"]
    title: str
    authors: list[Author] = []
    affiliations: list[str] = []
    institutions: list[str] = []
    countries: list[str] = []
    body: dict[str, str | None]
    references: list[str] = []
    figure_caption: str | None = None
    doi: str | None = None
    pmcid: str | None = None
    era: Literal["A", "B", "C"]
    license: Literal["cc-by", "free-to-read"]
    source_url: str
