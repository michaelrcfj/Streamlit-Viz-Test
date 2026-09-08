"""Cash Flow Trends — Altair layered area, Operating / Investing / Financing.

Derived from the same fact rows as every other tile (see
metrics.cash_flow_by_month) rather than read from its own table, so this tile
now moves with the filters and the chart selection instead of sitting static."""

import altair as alt
import pandas as pd
import streamlit as st

from src import theme as T
from src.data import metrics as M


def render(cube_f: pd.DataFrame, tile_key: str):
    df = M.cash_flow_by_month(cube_f)
    if df.empty:
        st.info("No data in the current filter.")
        return
    chart = (
        alt.Chart(df)
        .mark_area(opacity=0.55, interpolate="monotone", line=alt.OverlayMarkDef(strokeWidth=2))
        .encode(
            x=alt.X("month:N", title=None),
            y=alt.Y("amount:Q", title=None, axis=alt.Axis(format="$,.2s")),
            color=alt.Color("flow:N", scale=alt.Scale(domain=list(T.CASHFLOW_SERIES.keys()), range=list(T.CASHFLOW_SERIES.values())), title=None),
            tooltip=[alt.Tooltip("month:N", title="Month"), alt.Tooltip("flow:N", title="Flow"),
                     alt.Tooltip("amount:Q", title="Amount", format="$,.0f")],
        )
        .properties(height=T.CHART_HEIGHT)
    )
    st.altair_chart(chart, width='stretch', key=tile_key)
