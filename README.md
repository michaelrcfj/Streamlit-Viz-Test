# Global FinCorp — Streamlit BI Feasibility Prototype

A Streamlit replica of the reference dark BI dashboard screenshot, redesigned
into a cohesive light "financial ledger" theme, built to answer a specific
question: **can Streamlit replace these Tableau dashboards?**

Two pages:
- **Dashboard** — the replica, with sidebar filters, a Filter/Highlight/Drill
  interaction-mode toggle, URL-shareable state, CSV/PNG/PDF export, and a
  perf panel.
- **Limitations Scorecard** — the actual findings: what worked, what needed a
  workaround, and an honest verdict against Tableau for each requirement.

## Setup

```bash
pip install -r requirements.txt
python scripts/generate_data.py            # ~100k rows, required
python scripts/generate_data.py --stress   # ~1M rows, optional (for the stress toggle)
streamlit run app.py
```

## Project layout

```
app.py                    entrypoint: page config, theme CSS, navigation
pages/dashboard.py         the dashboard grid
pages/scorecard.py         the findings page
.streamlit/config.toml     native Streamlit theme tokens
src/theme.py                single source of truth for the palette/fonts
src/style.css               CSS layer for grid geometry + tile chrome
src/state.py                 filters + chart selection + URL sync
src/data/load.py              cached Parquet loaders
src/data/metrics.py           filtering, the aggregation cube, KPI derivation
src/charts/*.py                one module per tile
src/components/tile.py          tile chrome helper
src/components/echarts/          hand-rolled ECharts custom component (no build step)
src/export.py                    CSV / PNG / PDF export
scripts/generate_data.py          synthetic data generator (seeded, reproducible)
```

## Data

All data is synthetic (`numpy.random.default_rng(42)`, reproducible) and all
headline KPIs are derived from the transaction rows — never hardcoded — so
the KPI strip, waterfall, and monthly bars always reconcile, unlike the
source screenshot.

## Known gaps

See the in-app Limitations Scorecard page for the full write-up. Headline
items: whole-dashboard PDF export is a server-side re-render (misses the
ECharts tiles and CSS chrome); free tile placement is column/row-based, not a
true grid; no auth/multi-user/live-refresh was tested.
