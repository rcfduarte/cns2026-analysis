"""Build the interactive (Datawrapper) chart suite for the CNS × CoSyNe article.

Turns the committed aggregate tables into upload-ready wide CSVs (`results/datawrapper/`)
and, if a Datawrapper API token is available, creates → styles → publishes each chart and
records the embed URLs in `results/datawrapper/charts.json`. This mirrors how the CoSyNe
article's interactive charts were made.

Token resolution (first that exists):
  1. env `DATAWRAPPER_API_TOKEN`
  2. JSON file at env `DATAWRAPPER_TOKEN_FILE` (key `api_token`)
  3. ~/.claude/secrets/datawrapper.json  or  ~/Desktop/.claude/secrets/datawrapper.json

Run:
  python scripts/create_datawrapper_charts.py            # build CSVs + publish
  python scripts/create_datawrapper_charts.py --csv-only # just write the CSVs
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TB = ROOT / "results" / "tables"
DW = ROOT / "results" / "datawrapper"
sys.path.insert(0, str(ROOT / "scripts"))

BASE = "https://api.datawrapper.de/v3"
UA = "cns-scientometrics/1.0"
SOURCE = "CNS/OCNS abstracts 2007–2025 · CoSyNe program books 2014–2026"
SOURCE_URL = "https://github.com/rcfduarte/cns2026-analysis"
BYLINE = "Renato Duarte"

# House categorical palette (matches the static figures).
PAL = ["#2a78d6", "#e34948", "#1baf7a", "#eb6834", "#4a3aa7",
       "#c98500", "#d55181", "#008300", "#7a7a76", "#2bb8c4"]


# ---------------------------------------------------------------------------------------
# CSV builders (wide format, first column = x-axis) -> results/datawrapper/*.csv
# ---------------------------------------------------------------------------------------
def _smooth(df: pd.DataFrame, w: int = 3) -> pd.DataFrame:
    return df.rolling(w, center=True, min_periods=1).mean()


def csv_topics(top: int = 6) -> pd.DataFrame:
    long = pd.read_csv(TB / "topics_over_time_shares.csv")
    wide = long.pivot_table(index="year", columns="label", values="share_pct", fill_value=0)
    order = wide.sum().sort_values(ascending=False).index[:top]  # fewer lines -> readable labels
    return _smooth(wide[order]).round(2).reset_index()


def csv_meeting_sizes() -> pd.DataFrame:
    m = pd.read_csv(TB / "meeting_sizes.csv").rename(
        columns={"cns_abstracts": "CNS", "cosyne_abstracts": "CoSyNe"})
    return m[["year", "CNS", "CoSyNe"]]


def csv_aiml() -> pd.DataFrame:
    a = pd.read_csv(TB / "recovered_aiml_uptake.csv")
    wide = a.pivot_table(index="year", columns="conference", values="aiml_per10k_smoothed")
    return wide.round(2).reset_index()


def csv_countries() -> pd.DataFrame:
    c = pd.read_csv(TB / "recovered_countries_over_time.csv")
    wide = c.pivot_table(index="year", columns="country", values="abstracts_smoothed",
                         fill_value=0)
    order = wide.sum().sort_values(ascending=False).index
    return wide[order].round(1).reset_index()


def csv_geography() -> pd.DataFrame:
    from geography_comparison import _cns_country_series, _regional_shares

    cns, _ = _cns_country_series()
    cos = pd.read_csv(TB / "cosyne_countries.csv").set_index("country")["abstracts"]
    scns, scos = _regional_shares(cns), _regional_shares(cos)
    regions = ["North America", "Europe", "Asia-Pacific", "Other"]
    return pd.DataFrame({
        "region": regions,
        "CNS": [round(scns[r], 1) for r in regions],
        "CoSyNe": [round(scos[r], 1) for r in regions],
    })


def csv_rising_fading(n: int = 10) -> pd.DataFrame:
    k = pd.read_csv(TB / "keyword_frequencies.csv")
    early = k[k.year.between(2007, 2011)].groupby("keyword").per10k.mean()
    late = k[k.year.between(2021, 2025)].groupby("keyword").per10k.mean()
    change = (late - early).dropna().sort_values()
    sel = pd.concat([change.head(n), change.tail(n)])
    out = sel.reset_index()
    out.columns = ["keyword", "change_per10k"]
    return out.round(2)


CSVS = {
    "topics_over_time": csv_topics,
    "meeting_sizes": csv_meeting_sizes,
    "aiml_uptake": csv_aiml,
    "countries_over_time": csv_countries,
    "geography": csv_geography,
    "rising_fading": csv_rising_fading,
}


def write_csvs() -> dict[str, Path]:
    DW.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, fn in CSVS.items():
        p = DW / f"{name}.csv"
        fn().to_csv(p, index=False)
        paths[name] = p
        print(f"  wrote {p.relative_to(ROOT)}")
    return paths


# ---------------------------------------------------------------------------------------
# Chart specs: title, Datawrapper type, description, and visualize/annotate metadata
# ---------------------------------------------------------------------------------------
def _line_colors(cols: list[str]) -> dict:
    return {c: PAL[i % len(PAL)] for i, c in enumerate(cols)}


CHARTS = {
    "topics_over_time": dict(
        title="Data-driven topics over time (CNS)", type="d3-lines",
        intro="Share of each year's CNS abstracts assigned to a BERTopic theme (top themes, "
              "3-yr smoothed). The classic visual-cortex theme recedes as functional "
              "connectivity rises.",
        notes="BERTopic over sentence embeddings of every abstract; share of that year's "
              "abstracts. 3-year moving average.",
        visualize={"y-grid": "on"}),
    "meeting_sizes": dict(
        title="CoSyNe is the larger meeting", type="d3-lines",
        intro="Accepted abstracts per year (posters + talks). CoSyNe overtakes CNS in the "
              "mid-2010s and runs ~1.5× larger through the 2020s.",
        notes="CNS = harvested BMC/OCNS corpus (harvest completeness varies by year); "
              "CoSyNe = program-book poster+talk ids (2014– only).",
        visualize={"y-grid": "on", "line-widths": {"CoSyNe": 3, "CNS": 3}}),
    "aiml_uptake": dict(
        title="The machine-learning wave: CoSyNe vs CNS", type="d3-lines",
        intro="AI/ML keyword intensity (mentions per 10k words). CoSyNe turned toward machine "
              "learning harder and earlier than CNS.",
        notes="Sum of AI/ML keyword frequencies per 10k words. 3-year moving average.",
        visualize={"y-grid": "on"}),
    "countries_over_time": dict(
        title="Where CNS work comes from", type="d3-lines",
        intro="Abstracts with ≥1 author in each country over time (top-8 origin countries, "
              "smoothed). Host-city years bring a home-team bump.",
        notes="Author-affiliation country parse; top-8 origin countries. 3-year moving average.",
        visualize={"y-grid": "on"}),
    "geography": dict(
        title="CoSyNe leans North-American; CNS leans European", type="d3-bars-grouped",
        intro="Regional composition of author affiliations (share of country-mentions, one per "
              "abstract). CoSyNe is 58% North America; CNS is 55% Europe.",
        notes="CNS: full corpus, all countries, 2007–2025. CoSyNe: program books 2014–2026, "
              "institution→country resolution.",
        colors={"CNS": "#2a78d6", "CoSyNe": "#e34948"}),
    "rising_fading": dict(
        title="What rose and what left the room (CNS)", type="d3-bars",
        intro="Change in keyword intensity, 2021–25 mean minus 2007–11 mean (per 10k words). "
              "Positive = rising; negative = fading.",
        notes="Keyword frequency per 10k words of abstract text; taxonomy shared with CoSyNe.",
        visualize={}),
}


# ---------------------------------------------------------------------------------------
# Datawrapper API
# ---------------------------------------------------------------------------------------
def _load_token() -> str | None:
    if os.environ.get("DATAWRAPPER_API_TOKEN"):
        return os.environ["DATAWRAPPER_API_TOKEN"]
    candidates = [os.environ.get("DATAWRAPPER_TOKEN_FILE"),
                  Path.home() / ".claude" / "secrets" / "datawrapper.json",
                  Path.home() / "Desktop" / ".claude" / "secrets" / "datawrapper.json"]
    for c in candidates:
        if c and Path(c).exists():
            return json.loads(Path(c).read_text())["api_token"]
    return None


def _api(method: str, path: str, token: str, *, body=None, csv=None):
    url = f"{BASE}{path}"
    headers = {"Authorization": f"Bearer {token}", "User-Agent": UA}
    if csv is not None:
        data, headers["Content-Type"] = csv.encode(), "text/csv"
    elif body is not None:
        data, headers["Content-Type"] = json.dumps(body).encode(), "application/json"
    else:
        data = None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read().decode()
    return json.loads(raw) if raw else {}


def _metadata(spec: dict, series: list[str]) -> dict:
    colors = spec.get("colors") or {s: PAL[i % len(PAL)] for i, s in enumerate(series)}
    visualize = {"custom-colors": colors, **spec.get("visualize", {})}
    return {
        "describe": {"intro": spec["intro"], "source-name": SOURCE,
                     "source-url": SOURCE_URL, "byline": BYLINE},
        "annotate": {"notes": spec.get("notes", "")},
        "visualize": visualize,
        "publish": {"blocks": {"logo": {"enabled": False}, "get-the-data": True,
                               "download-image": True}},
    }


def publish_chart(name: str, csv_path: Path, spec: dict, token: str,
                  existing_id: str | None = None) -> dict:
    csv = csv_path.read_text()
    series = csv.splitlines()[0].split(",")[1:]  # value columns (skip the x-axis column)
    if existing_id:
        cid = existing_id
        _api("PATCH", f"/charts/{cid}", token, body={"title": spec["title"], "type": spec["type"]})
    else:
        cid = _api("POST", "/charts", token,
                   body={"title": spec["title"], "type": spec["type"]})["id"]
    _api("PUT", f"/charts/{cid}/data", token, csv=csv)
    _api("PATCH", f"/charts/{cid}", token, body={"metadata": _metadata(spec, series)})
    pub = _api("POST", f"/charts/{cid}/publish", token)
    url = pub.get("data", {}).get("publicUrl", f"https://datawrapper.dwcdn.net/{cid}/")
    print(f"  {name}: {cid} -> {url}")
    time.sleep(1)
    return {"id": cid, "url": url, "title": spec["title"], "type": spec["type"]}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv-only", action="store_true", help="write CSVs, skip the API")
    ap.add_argument("--only", nargs="*", help="restrict to these chart names")
    args = ap.parse_args()

    print("Building Datawrapper CSVs:")
    paths = write_csvs()

    if args.csv_only:
        print("--csv-only: skipping publish")
        return
    token = _load_token()
    if not token:
        print("No Datawrapper token found (set DATAWRAPPER_API_TOKEN or the secrets file); "
              "CSVs written, skipping publish.")
        return

    # reuse existing chart ids (update in place) so re-runs don't create duplicates
    existing = {}
    if (DW / "charts.json").exists():
        existing = {k: v.get("id") for k, v in json.loads((DW / "charts.json").read_text()).items()}

    names = args.only or list(CHARTS)
    print("\nCreating + publishing charts:")
    results = json.loads((DW / "charts.json").read_text()) if (DW / "charts.json").exists() else {}
    for name in names:
        try:
            results[name] = publish_chart(name, paths[name], CHARTS[name], token,
                                          existing_id=existing.get(name))
        except urllib.error.HTTPError as e:
            print(f"  {name}: HTTP {e.code} {e.read().decode()[:200]}")
    DW.mkdir(parents=True, exist_ok=True)
    (DW / "charts.json").write_text(json.dumps(results, indent=2))
    print(f"\nwrote {(DW / 'charts.json').relative_to(ROOT)}")
    print("\nEmbed URLs for Substack:")
    for name, info in results.items():
        print(f"  {name}: {info['url']}")


if __name__ == "__main__":
    main()
