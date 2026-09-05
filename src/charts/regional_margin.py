"""Regional gross margin — Altair horizontal bar, click-to-filter/highlight
region. Uses Altair's native selection param (on_select) rather than
Plotly's, to genuinely exercise both native selection mechanisms."""

import altair as alt
import pandas as pd
import streamlit as st

from src import theme as T
from src.data import metrics as M
from src.state import Selection, set_selection


def render(cube_f: pd.DataFrame, selection: Selection, mode: str, tile_key: str):
    df = M.regional_margin(cube_f)
    if df.empty:
        st.info("No data in the current filter.")
        return
    df = df.sort_values("revenue", ascending=True)

    is_highlighting = mode == "Highlight" and selection.active and selection.dim == "region"
    df["opacity"] = 1.0
    if is_highlighting:
        df["opacity"] = df["region"].apply(lambda r: 1.0 if r in selection.values else 0.3)

    click = alt.selection_point(fields=["region"], name="region_click")

    bars = (
        alt.Chart(df)
        .mark_bar(cornerRadiusEnd=4, height=16)
        .encode(
            y=alt.Y("region:N", sort=None, title=None),
            x=alt.X("revenue:Q", title="Revenue", axis=alt.Axis(format="$,.2s")),
            color=alt.Color("region:N", scale=alt.Scale(domain=T.REGION_ORDER, range=list(T.REGION_SERIES.values())), legend=None),
            opacity=alt.Opacity("opacity:Q", legend=None, scale=alt.Scale(domain=[0, 1], range=[0.3, 1.0])) if is_highlighting else alt.value(1.0),
            tooltip=[
                alt.Tooltip("region:N", title="Region"),
                alt.Tooltip("revenue:Q", title="Revenue", format="$,.0f"),
                alt.Tooltip("gross_margin:Q", title="Gross Margin", format=".1%"),
            ],
        )
        .add_params(click)
        .properties(height=210)
    )
    labels = bars.mark_text(align="left", dx=4, font=T.FONT_MONO, fontSize=10, color=T.INK_SECONDARY).encode(
        text=alt.Text("gross_margin:Q", format=".1%")
    )

    chart = (bars + labels).properties(**{})
    event = st.altair_chart(chart, width='stretch', key=tile_key, on_select="rerun")
    sel = (event or {}).get("selection", {}).get("region_click")
    regions = []
    if isinstance(sel, dict):
        regions = sel.get("region", [])
    elif isinstance(sel, list):
        regions = [p["region"] for p in sel if "region" in p]
    if regions:
        set_selection("region", list(regions), tile_key)
