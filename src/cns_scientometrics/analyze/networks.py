"""Module C — author & geography networks over the corpus.

Country is parsed from raw affiliation strings (the corpus is built --no-enrich, so
ROR `countries` are empty but `affiliations` are populated). Co-authorship graph and
internationalization metrics come from the populated `authors`/`affiliations` fields.
"""

import math
import re
from collections import Counter
from itertools import combinations
from pathlib import Path

import networkx as nx
import pandas as pd
import pycountry

# Common surface forms → ISO alpha-2.
_ALIASES = {
    "usa": "US",
    "united states": "US",
    "united states of america": "US",
    "u.s.a.": "US",
    "uk": "GB",
    "united kingdom": "GB",
    "u.k.": "GB",
    "england": "GB",
    "scotland": "GB",
    "wales": "GB",
    "korea": "KR",
    "south korea": "KR",
    "republic of korea": "KR",
    "russia": "RU",
    "iran": "IR",
    "czech republic": "CZ",
    "the netherlands": "NL",
    "netherlands": "NL",
    "p.r. china": "CN",
    "pr china": "CN",
    "china": "CN",
}
_BY_NAME = {c.name.lower(): c.alpha_2 for c in pycountry.countries}


def country_of(affiliation: str) -> str | None:
    """Best-effort ISO alpha-2 country from an affiliation's trailing segments."""
    segs = [s.strip().rstrip(".").lower() for s in re.split(r"[,;]", affiliation) if s.strip()]
    for seg in reversed(segs[-3:]):  # country is usually the last meaningful segment
        seg = re.sub(r"\b[a-z]{1,2}\d[\da-z ]*$", "", seg).strip()  # drop trailing postal codes
        if seg in _ALIASES:
            return _ALIASES[seg]
        if seg in _BY_NAME:
            return _BY_NAME[seg]
    return None


def record_countries(affiliations: list[str]) -> list[str]:
    out = []
    for a in affiliations:
        c = country_of(a)
        if c and c not in out:
            out.append(c)
    return out


def coauthorship_graph(df: pd.DataFrame) -> nx.Graph:
    g = nx.Graph()
    for authors in df["authors"]:
        names = [a["raw_name"] for a in authors if a.get("raw_name")]
        for n in names:
            g.add_node(n)
            g.nodes[n]["abstracts"] = g.nodes[n].get("abstracts", 0) + 1
        for a, b in combinations(sorted(set(names)), 2):
            if g.has_edge(a, b):
                g[a][b]["weight"] += 1
            else:
                g.add_edge(a, b, weight=1)
    return g


def country_timeseries(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in df.iterrows():
        for c in record_countries(list(r["affiliations"])):
            rows.append({"year": r["year"], "country": c})
    return pd.DataFrame(rows).value_counts(["year", "country"]).reset_index(name="abstracts")


def internationalization(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for year, group in df.groupby("year"):
        per_abstract = [len(record_countries(list(a))) for a in group["affiliations"]]
        ctys = Counter()
        for _, r in group.iterrows():
            for c in record_countries(list(r["affiliations"])):
                ctys[c] += 1
        total = sum(ctys.values()) or 1
        entropy = -sum((n / total) * math.log2(n / total) for n in ctys.values())
        rows.append(
            {
                "year": year,
                "n_abstracts": len(group),
                "distinct_countries": len(ctys),
                "country_entropy": round(entropy, 3),
                "mean_countries_per_abstract": round(
                    sum(per_abstract) / max(len(per_abstract), 1), 3
                ),
            }
        )
    return pd.DataFrame(rows)


def top_countries(df: pd.DataFrame, n: int = 20) -> pd.Series:
    c = Counter()
    for affs in df["affiliations"]:
        for cc in record_countries(list(affs)):
            c[cc] += 1
    return pd.Series(dict(c.most_common(n)))


def write_network_outputs(df: pd.DataFrame, out_dir: Path) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_dir = Path(out_dir)
    (out_dir / "figures").mkdir(parents=True, exist_ok=True)

    intl = internationalization(df)
    intl.to_csv(out_dir / "internationalization.csv", index=False)
    cts = country_timeseries(df)
    cts.to_csv(out_dir / "country_timeseries.csv", index=False)

    g = coauthorship_graph(df)
    deg = sorted(dict(g.degree()).items(), key=lambda x: -x[1])[:30]
    pd.DataFrame(deg, columns=["author", "n_collaborators"]).to_csv(
        out_dir / "top_collaborators.csv", index=False
    )

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(intl["year"], intl["distinct_countries"], marker="o", label="distinct countries")
    ax2 = ax.twinx()
    ax2.plot(intl["year"], intl["country_entropy"], color="tab:orange", marker="s", label="entropy")
    ax.set_xlabel("year")
    ax.set_ylabel("distinct countries")
    ax2.set_ylabel("country diversity (Shannon entropy, bits)")
    ax.set_title("CNS internationalization over time")
    fig.tight_layout()
    fig.savefig(out_dir / "figures" / "internationalization.png", dpi=130)
    plt.close(fig)

    top = top_countries(df, 12).index.tolist()
    piv = cts[cts["country"].isin(top)].pivot_table(
        index="year", columns="country", values="abstracts", fill_value=0
    )
    fig, ax = plt.subplots(figsize=(11, 6))
    for c in top:
        if c in piv.columns:
            ax.plot(piv.index, piv[c], label=c, linewidth=1.5)
    ax.set_title("Author-affiliations by country over time (top 12)")
    ax.set_xlabel("year")
    ax.set_ylabel("abstracts with ≥1 author in country")
    ax.legend(fontsize=7, ncol=3)
    fig.tight_layout()
    fig.savefig(out_dir / "figures" / "countries_over_time.png", dpi=130)
    plt.close(fig)
    return out_dir
