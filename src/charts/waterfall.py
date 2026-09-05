"""Profitability waterfall: Revenue -> COGS -> Gross Profit -> OpEx -> Tax ->
Net Income. Values are pulled straight from KPIs.compute_kpis, so this always
reconciles with the KPI strip and the monthly bars by construction."""

import plotly.graph_objects as go
import streamlit as st

from src import theme as T
from src.data.metrics import KPIs, waterfall_frame


def render(kpi: KPIs, tile_key: str):
    df = waterfall_frame(kpi)
    measure = ["absolute" if k == "total" else "relative" for k in df["kind"]]

    fig = go.Figure(go.Waterfall(
        x=df["stage"], y=df["value"], measure=measure,
        text=[f"${abs(v):,.0f}" for v in df["value"]],
        textposition="outside", textfont=dict(family=T.FONT_MONO, size=10, color=T.INK_SECONDARY),
        increasing=dict(marker=dict(color=T.SEQUENTIAL[4])),
        decreasing=dict(marker=dict(color=T.CRITICAL)),
        totals=dict(marker=dict(color=T.ACCENT)),
        connector=dict(line=dict(color=T.LINE_STRONG, width=1)),
        hovertemplate="<b>%{x}</b><br>$%{y:,.0f}<extra></extra>",
    ))
    layout = {**T.PLOTLY_LAYOUT, "yaxis": {**T.PLOTLY_LAYOUT["yaxis"], "tickformat": "$,.0s"}}
    fig.update_layout(**layout, height=290, showlegend=False)
    st.plotly_chart(fig, width='stretch', key=tile_key)
