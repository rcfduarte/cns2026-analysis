"""Adapter: turn a CoSyNe abstracts dataset (from your other repo) into the two
tables the CNS pipeline needs, so the CoSyNe side drops straight in.

Emits:
  results/tables/cosyne_countries.csv       -> geography_comparison.py --cosyne-countries
  results/tables/keyword_incidence_cosyne.csv -> keyword_networks.py --cosyne-incidence

Both are NON-SENSITIVE aggregates (country counts; per-abstract 0/1 keyword flags —
no abstract text), so they can be committed and shared.

Input: a parquet or JSONL of CoSyNe abstracts. You point at the columns holding the
abstract text and the affiliation list; sensible defaults are auto-detected. The
keyword incidence uses the SAME taxonomy as CNS (cns_scientometrics), so the two
co-occurrence networks are directly comparable.

Examples:
  python scripts/adapt_cosyne.py --abstracts /path/cosyne.parquet
  python scripts/adapt_cosyne.py --abstracts /path/cosyne.jsonl \
      --text-col abstract --affil-col affiliations --year-col year
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from cns_scientometrics.analyze.keyword_trends import count_keyword
from cns_scientometrics.analyze.keywords_taxonomy import KEYWORDS
from cns_scientometrics.analyze.networks import country_of, record_countries

ROOT = Path(__file__).resolve().parents[1]
TB = ROOT / "results" / "tables"

_TEXT_CANDIDATES = ["body_full", "abstract", "text", "body", "full_text", "abstract_text"]
_AFFIL_CANDIDATES = ["affiliations", "affiliation", "affils", "author_affiliations"]
_YEAR_CANDIDATES = ["year", "meeting_year", "date_year"]


def _load(path: Path) -> pd.DataFrame:
    if path.suffix in (".parquet", ".pq"):
        return pd.read_parquet(path)
    if path.suffix in (".jsonl", ".ndjson"):
        return pd.DataFrame(json.loads(line) for line in path.read_text().splitlines() if line.strip())
    if path.suffix == ".json":
        obj = json.loads(path.read_text())
        return pd.DataFrame(obj if isinstance(obj, list) else obj.get("abstracts", obj))
    if path.suffix == ".csv":
        return pd.read_csv(path)
    raise SystemExit(f"unsupported input format: {path.suffix}")


def _pick(df: pd.DataFrame, override: str | None, candidates: list[str], what: str,
          required: bool = True) -> str | None:
    if override:
        if override not in df.columns:
            raise SystemExit(f"--{what}-col {override!r} not in {list(df.columns)}")
        return override
    for c in candidates:
        if c in df.columns:
            return c
    if required:
        raise SystemExit(f"could not auto-detect the {what} column; pass --{what}-col. "
                         f"columns present: {list(df.columns)}")
    return None


def _is_seq(v) -> bool:
    # list/tuple/ndarray/pandas array — anything iterable that isn't a str/bytes/dict
    return hasattr(v, "__iter__") and not isinstance(v, (str, bytes, dict))


def _as_text(v) -> str:
    if isinstance(v, dict):  # e.g. {"full": "..."} like the CNS corpus body
        return str(v.get("full") or v.get("text") or " ".join(map(str, v.values())))
    if _is_seq(v):
        return " ".join(map(str, v))
    return str(v or "")


def _as_affils(v) -> list[str]:
    if _is_seq(v):
        return [str(x) for x in v]
    if isinstance(v, str):
        return [s for s in v.split(";") if s.strip()] or [v]
    return []


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--abstracts", required=True, type=Path)
    ap.add_argument("--text-col", dest="text_col")
    ap.add_argument("--affil-col", dest="affil_col")
    ap.add_argument("--year-col", dest="year_col")
    args = ap.parse_args()

    df = _load(args.abstracts)
    tcol = _pick(df, args.text_col, _TEXT_CANDIDATES, "text")
    acol = _pick(df, args.affil_col, _AFFIL_CANDIDATES, "affil", required=False)
    ycol = _pick(df, args.year_col, _YEAR_CANDIDATES, "year", required=False)
    print(f"columns -> text={tcol!r} affil={acol!r} year={ycol!r}  (n={len(df)})")

    TB.mkdir(parents=True, exist_ok=True)

    # 1) keyword incidence (per-abstract 0/1), same taxonomy as CNS
    inc_rows = []
    for _, r in df.iterrows():
        text = _as_text(r[tcol]).lower()
        row = {kw: int(count_keyword(text, syns) > 0) for kw, syns in KEYWORDS.items()}
        inc_rows.append(row)
    inc = pd.DataFrame(inc_rows)
    if ycol:
        inc.insert(0, "year", df[ycol].to_numpy())
    inc.to_csv(TB / "keyword_incidence_cosyne.csv", index=False)
    print(f"wrote keyword_incidence_cosyne.csv  ({inc.shape[0]} abstracts x {len(KEYWORDS)} keywords)")

    # 2) country counts (abstract-level; a country counts once per abstract)
    if acol:
        counts: dict[str, int] = {}
        for _, r in df.iterrows():
            for c in record_countries(_as_affils(r[acol])):
                counts[c] = counts.get(c, 0) + 1
        # map ISO alpha-2 -> readable names used by geography_comparison REGION map
        import pycountry
        name = {}
        for iso, n in counts.items():
            try:
                name[pycountry.countries.get(alpha_2=iso).name] = n
            except Exception:
                name[iso] = n
        cc = pd.Series(name).sort_values(ascending=False).rename("abstracts")
        cc.index.name = "country"
        cc.to_csv(TB / "cosyne_countries.csv")
        print(f"wrote cosyne_countries.csv  ({len(cc)} countries; top: "
              f"{', '.join(cc.head(3).index)})")
    else:
        print("no affiliation column found -> skipped cosyne_countries.csv "
              "(pass --affil-col if affiliations exist)")

    _ = country_of  # affiliations parsed via record_countries above


if __name__ == "__main__":
    main()
