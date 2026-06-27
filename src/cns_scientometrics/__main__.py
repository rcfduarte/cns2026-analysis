"""CLI: build the canonical CNS abstract corpus."""

import argparse
from pathlib import Path

from .acquire import acquire_all
from .corpus import write_corpus
from .normalize import enrich_record


def _parse_years(s: str) -> list[int]:
    if "-" in s:
        a, b = s.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(s)]


def main() -> None:
    ap = argparse.ArgumentParser(prog="cns_scientometrics")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="acquire + assemble the corpus")
    b.add_argument("--years", default="2007-2024")
    b.add_argument("--out", default="data/corpus")
    b.add_argument("--cache", default="data/cache")
    b.add_argument("--no-enrich", action="store_true", help="skip ROR affiliation enrichment")
    args = ap.parse_args()

    cache = Path(args.cache)
    recs = acquire_all(_parse_years(args.years), cache)
    if not args.no_enrich:
        recs = [enrich_record(r, cache) for r in recs]
    summary = write_corpus(recs, Path(args.out))
    print(summary)


if __name__ == "__main__":
    main()
