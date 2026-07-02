"""Recover the aggregate series that back figures 4-8 out of the committed SVGs,
so the whole publication figure suite is regenerable from `results/` alone — no
raw corpus required.

The committed matplotlib SVGs store, per axes, tick labels as HTML comments next
to tick-mark <use x= y=/> elements (a linear pixel<->data calibration) and data
as coloured <path> polylines / histogram rectangles. We invert that transform.
Recovered values are exactly the plotted values (several are 3-year smoothed, as
noted per column); cross-checked against `results/tables/keyword_frequencies.csv`
and `docs/RESULTS.md` (fig4 CNS line and fig7 country totals reproduce to <1%).
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FIGS = ROOT / "results" / "figures" / "_source_v1"
TABLES = ROOT / "results" / "tables"
YEARS = list(range(2007, 2026))


def _axes_blocks(svg: str):
    starts = [(m.start(), m.group(1)) for m in re.finditer(r'<g id="(axes_\d+)">', svg)]
    starts.append((len(svg), None))
    for i in range(len(starts) - 1):
        yield starts[i][1], svg[starts[i][0]:starts[i + 1][0]]


def _ticks(block: str, axis: str):
    out = []
    for tm in re.finditer(rf'<g id="{axis}tick_\d+">(.*?)(?=<g id="{axis}tick_|\Z)', block, re.S):
        b = tm.group(1)
        use = re.search(r'<use[^>]*x="([\d.]+)"[^>]*y="([\d.]+)"', b)
        com = re.search(r"<!--\s*([-\d.]+)\s*-->", b)
        if not (use and com):
            continue
        try:
            val = float(com.group(1))
        except ValueError:
            continue
        pix = float(use.group(1) if axis == "x" else use.group(2))
        out.append((pix, val))
    seen, uniq = set(), []
    for p, v in out:
        if round(p, 1) not in seen:
            seen.add(round(p, 1))
            uniq.append((p, v))
    return uniq


def _fit(ticks):
    p = np.array([t[0] for t in ticks])
    v = np.array([t[1] for t in ticks])
    a, b = np.polyfit(p, v, 1)
    return lambda px: a * px + b


def _polylines(block: str):
    block = re.sub(r'<g id="legend_\d+">.*?(?=<g id="patch_\d+">|\Z)', "", block, flags=re.S)
    out = []
    for m in re.finditer(r'<g id="line2d_\d+">\s*<path d="([^"]+)"[^>]*style="([^"]*)"', block):
        col = re.search(r"stroke:\s*(#[0-9a-fA-F]{6})", m.group(2))
        pts = re.findall(r"[ML]\s+([\d.]+)\s+([\d.]+)", m.group(1))
        if col and len(pts) >= 5:
            out.append((col.group(1).lower(), pts))
    return out


def _one_axes(fig: str):
    svg = (FIGS / fig).read_text()
    return next(iter(_axes_blocks(svg)))[1]


# ---- fig4: AI/ML uptake, CoSyNe vs CNS -----------------------------------------------
def recover_aiml_uptake():
    block = _one_axes("fig4_aiml_uptake.svg")
    fy = _fit(_ticks(block, "y"))
    rows = []
    colmap = {"#d1495b": "CoSyNe", "#2e86ab": "CNS"}
    for col, pts in _polylines(block):
        if col not in colmap:
            continue
        ys = [fy(float(py)) for _, py in pts]
        for y, val in zip(YEARS, ys, strict=False):
            rows.append({"year": y, "conference": colmap[col], "aiml_per10k_smoothed": round(val, 3)})
    return pd.DataFrame(rows)


# ---- fig6: internationalization ------------------------------------------------------
def recover_internationalization():
    svg = (FIGS / "fig6_internationalization.svg").read_text()
    cols = {}
    for name, block in _axes_blocks(svg):
        if len(_ticks(block, "y")) < 2:
            continue
        fy = _fit(_ticks(block, "y"))
        pl = _polylines(block)
        if not pl:
            continue
        ys = [fy(float(py)) for _, py in pl[0][1]]
        cols[name] = ys
    a1, a2 = cols["axes_1"], cols["axes_2"]
    return pd.DataFrame({
        "year": YEARS,
        "distinct_countries": [round(v) for v in a1],
        "country_entropy_bits": [round(v, 3) for v in a2],
    })


# ---- fig7: top countries over time ---------------------------------------------------
def recover_countries():
    block = _one_axes("fig7_countries.svg")
    fy = _fit(_ticks(block, "y"))
    palette = ["#2e86ab", "#d1495b", "#e8a33d", "#3c896d", "#6a4c93",
               "#1b998b", "#c1666b", "#8d99ae", "#587291", "#b56576"]
    # PALETTE order == top_countries(descending). Ranks 1-8 verified vs docs/RESULTS.md
    # (line-sums reproduce US 1673, DE 929, GB 600, FR 415, JP 289, ES/AU/IT). Ranks
    # 9-10 not identifiable from committed data -> omitted from the labelled table.
    names = ["United States", "Germany", "United Kingdom", "France", "Japan",
             "Spain", "Australia", "Italy"]
    by = {c: pts for c, pts in _polylines(block)}
    rows = []
    for col, name in zip(palette, names, strict=False):
        if col not in by:
            continue
        ys = [fy(float(py)) for _, py in by[col]]
        for y, val in zip(YEARS, ys, strict=False):
            rows.append({"year": y, "country": name, "abstracts_smoothed": round(val, 2)})
    return pd.DataFrame(rows)


# ---- fig8: robustness histogram ------------------------------------------------------
def recover_robustness_hist():
    svg = (FIGS / "fig8_robustness.svg").read_text()
    block = next(iter(_axes_blocks(svg)))[1]
    fx, fy = _fit(_ticks(block, "x")), _fit(_ticks(block, "y"))
    rows = []
    for m in re.finditer(r'<path d="(M [^"]+?z)\s*"[^>]*style="([^"]*)"', block):
        if "fill: #2e86ab" not in m.group(2):
            continue
        nums = re.findall(r"([\d.]+)\s+([\d.]+)", m.group(1))
        xs = [float(a) for a, _ in nums]
        ys = [float(b) for _, b in nums]
        center = fx((min(xs) + max(xs)) / 2)
        count = fy(min(ys))  # top edge (smallest pixel y) -> bar height
        rows.append({"corr_bin_center": round(center, 3), "n_keywords": round(count)})
    return pd.DataFrame(rows)


def main():
    TABLES.mkdir(parents=True, exist_ok=True)
    out = {
        "recovered_aiml_uptake.csv": recover_aiml_uptake(),
        "recovered_internationalization.csv": recover_internationalization(),
        "recovered_countries_over_time.csv": recover_countries(),
        "recovered_robustness_hist.csv": recover_robustness_hist(),
    }
    for fname, df in out.items():
        df.to_csv(TABLES / fname, index=False)
        print(f"wrote {fname}: {len(df)} rows")


if __name__ == "__main__":
    main()
