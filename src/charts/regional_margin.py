"""Regional gross margin — Altair horizontal bar, click-to-filter region.
Uses Altair's native selection param (on_select) rather than Plotly's, to
genuinely exercise both native selection mechanisms."""

import altair as alt
import pandas as pd
import streamlit as st

from src import state as S
from src import theme as T
from src.data import metrics as M


def render(cube_f: pd.DataFrame, tile_key: str):
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
            # Dims non-selected bars the instant a mark is clicked. This is
            # driven entirely by the `click` param below, which Vega-Lite
            # tracks client-side -- it is never conditioned on backend
            # selection state, so (unlike the Plotly charts, see trend.py)
            # there's no self-restyle-wipes-selection risk to worry about
            # even if this tile ends up owning the selection.
            opacity=alt.condition(click, alt.value(1.0), alt.value(0.35)),
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
    widget_key = S.chart_widget_key(tile_key)

    def _on_select():
        event = st.session_state[widget_key]
        sel = (event or {}).get("selection", {}).get("region_click")
        regions = []
        if isinstance(sel, dict):
            regions = sel.get("region", [])
        elif isinstance(sel, list):
            regions = [p["region"] for p in sel if "region" in p]
        if regions:
            S.apply_selection("region", list(regions), tile_key)
        else:
            S.apply_selection_clear(tile_key)

    st.altair_chart(chart, width='stretch', key=widget_key, on_select=_on_select)
