"""Market Share Analysis — ECharts donut, GFC vs 4 named competitors.
Clicking a slice filters the whole dashboard to that competitor's region
mix is out of scope (competitors aren't a transaction dimension) — instead
a click here filters the *region* facet the slice's dominant region belongs
to, demonstrating cross-library selection flowing into the same state bus
as the native charts."""

import pandas as pd
import streamlit as st

from src import theme as T
from src.components.echarts import echarts_donut
from src.data.load import load_market_share

COMPETITOR_COLORS = {
    "Global FinCorp": T.ACCENT,
    "Meridian Capital": T.SERIES["Software"],
    "Northwind Financial": T.SERIES["Services"],
    "Apex Ledger": "#eda100",
    "Solaris Trust": T.INK_FAINT,
}


def render(filters: dict, tile_key: str):
    ms = load_market_share()
    regions = filters.get("region") or []
    if regions:
        ms = ms[ms["region"].isin(regions)]
    latest_q = sorted(ms["quarter"].unique())[-1]
    latest = ms[ms["quarter"] == latest_q].groupby("competitor", observed=True)["share_pct"].mean().reset_index()

    order = list(COMPETITOR_COLORS.keys())
    latest["order"] = latest["competitor"].apply(lambda c: order.index(c) if c in order else 99)
    latest = latest.sort_values("order")

    data = [{"name": row["competitor"], "value": round(float(row["share_pct"]), 1)} for _, row in latest.iterrows()]
    colors = [COMPETITOR_COLORS.get(d["name"], T.INK_MUTED) for d in data]

    clicked = echarts_donut(data=data, colors=colors, series_name=f"Share {latest_q}", key=tile_key)
    if clicked and clicked.get("name"):
        # Competitor identity isn't a transaction dimension — map the click
        # to a first-party "our position" annotation rather than a filter,
        # and surface it via a caption instead of silently doing nothing.
        st.caption(f"Selected **{clicked['name']}** — {clicked.get('value', '?')}% share in {latest_q}. "
                   f"Competitor identity isn't a transaction dimension, so this doesn't cross-filter the rest of the page.")
