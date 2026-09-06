"""Regional gross margin — Altair horizontal bar, click-to-filter region.
Uses Altair's native selection param (on_select) rather than Plotly's, to
genuinely exercise both native selection mechanisms."""

import altair as alt
import pandas as pd
import streamlit as st

from src import theme as T
from src.data import metrics as M
from src.state import Selection, clear_selection_if_owned_by, consume_once, set_selection_if_changed


def render(cube_f: pd.DataFrame, selection: Selection, tile_key: str):
    df = M.regional_margin(cube_f)
    if df.empty:
        st.info("No data in the current filter.")
        return
    df = df.sort_values("revenue", ascending=True)

    click = alt.selection_point(fields=["region"], name="region_click")

    bars = (
        alt.Chart(df)
        .mark_bar(cornerRadiusEnd=4, height=16)
        .encode(
            y=alt.Y("region:N", sort=None, title=None),
            x=alt.X("revenue:Q", title="Revenue", axis=alt.Axis(format="$,.2s")),
            color=alt.Color("region:N", scale=alt.Scale(domain=T.REGION_ORDER, range=list(T.REGION_SERIES.values())), legend=None),
            tooltip=[
                alt.Tooltip("region:N", title="Region"),
                alt.Tooltip("revenue:Q", title="Revenue", format="$,.0f"),
                alt.Tooltip("gross_margin:Q", title="Gross Margin", format=".1%"),
            ],
        )
        .add_params(click)
        .properties(height=T.CHART_HEIGHT)
    )
    labels = bars.mark_text(align="left", dx=4, font=T.FONT_MONO, fontSize=10, color=T.INK_SECONDARY).encode(
        text=alt.Text("gross_margin:Q", format=".1%")
    )

    chart = bars + labels
    event = st.altair_chart(chart, width='stretch', key=tile_key, on_select="rerun")
    sel = (event or {}).get("selection", {}).get("region_click")
    regions = []
    if isinstance(sel, dict):
        regions = sel.get("region", [])
    elif isinstance(sel, list):
        regions = [p["region"] for p in sel if "region" in p]

    if regions:
        if consume_once(tile_key, ("select", tuple(sorted(regions)))) and set_selection_if_changed("region", list(regions), tile_key):
            st.rerun()
    else:
        if consume_once(tile_key, ("clear",)) and clear_selection_if_owned_by(tile_key):
            st.rerun()
