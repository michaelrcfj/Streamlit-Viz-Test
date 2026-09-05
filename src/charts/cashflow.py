"""Cash Flow Trends — Altair layered area, Operating / Investing / Financing."""

import altair as alt
import pandas as pd
import streamlit as st

from src import theme as T


def render(cashflow: pd.DataFrame, tile_key: str):
    long = cashflow.melt(id_vars="month", value_vars=["Operating", "Investing", "Financing"],
                          var_name="flow", value_name="amount")
    chart = (
        alt.Chart(long)
        .mark_area(opacity=0.55, interpolate="monotone", line=alt.OverlayMarkDef(strokeWidth=2))
        .encode(
            x=alt.X("month:N", title=None),
            y=alt.Y("amount:Q", title=None, axis=alt.Axis(format="$,.2s")),
            color=alt.Color("flow:N", scale=alt.Scale(domain=list(T.CASHFLOW_SERIES.keys()), range=list(T.CASHFLOW_SERIES.values())), title=None),
            tooltip=[alt.Tooltip("month:N", title="Month"), alt.Tooltip("flow:N", title="Flow"),
                     alt.Tooltip("amount:Q", title="Amount", format="$,.0f")],
        )
        .properties(height=230)
    )
    st.altair_chart(chart, width='stretch', key=tile_key)
