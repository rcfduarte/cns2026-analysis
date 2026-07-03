# Interactive charts (Datawrapper)

Interactive versions of the key charts, for embedding in the Substack article — the same
approach as the CoSyNe piece. Each chart lives on the Datawrapper account; the CSV that
backs it is committed here (regenerated from `../tables/` by
`scripts/create_datawrapper_charts.py`).

To **rebuild the CSVs** only: `python scripts/create_datawrapper_charts.py --csv-only`.
To **create/update + publish** (needs a Datawrapper API token — see the script header):
`python scripts/create_datawrapper_charts.py`. Re-runs update the existing charts in place
(ids are read back from `charts.json`), so they don't create duplicates.

## Charts

| Chart | Static figure | Type | Embed URL |
|-------|---------------|------|-----------|
| Data-driven topics over time | `fig5_topics_over_time` | lines | https://datawrapper.dwcdn.net/hZl6p/ |
| CoSyNe is the larger meeting | `fig16_meeting_sizes` | lines | https://datawrapper.dwcdn.net/HWuVe/ |
| The machine-learning wave (CoSyNe vs CNS) | `fig4_aiml_uptake` | lines | https://datawrapper.dwcdn.net/nUvV8/ |
| Where CNS work comes from | `fig6_geography` | lines | https://datawrapper.dwcdn.net/vTsUW/ |
| CoSyNe vs CNS geography | `fig15_cns_cosyne_geography` | grouped bars | https://datawrapper.dwcdn.net/xnB4g/ |
| What rose and what left the room | `fig2_rising_fading` | bars | https://datawrapper.dwcdn.net/bss8i/ |

`charts.json` holds the chart id + published URL + type for each. (Network figures —
co-occurrence, institution, co-trajectory — stay static; Datawrapper doesn't do graphs.)

## Embedding in Substack

Paste the chart's **responsive embed** (Datawrapper → *Publish & Embed* → "Responsive
iframe") into a Substack "Embed / paste a link" block, or use the raw iframe:

```html
<iframe src="https://datawrapper.dwcdn.net/hZl6p/" scrolling="no" frameborder="0"
        style="width:100%;min-width:100%;border:none" height="540"></iframe>
```

Trailing-slash URLs always serve the latest published version; a `/2/`-style URL pins a
specific version.
