"""Department spend vs budget over time — Plotly grouped bar + budget line,
clicking a department bar drives the selection loop on the 'department' dim."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import theme as T
from src.data import metrics as M
from src.state import Selection, clear_selection_if_owned_by, consume_once, set_selection_if_changed

DEPT_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#4a3aa7", "#e34948"]


def render(cube_f: pd.DataFrame, budget_f: pd.DataFrame, selection: Selection, tile_key: str):
    df = M.department_spend_vs_budget(cube_f, budget_f)
    if df.empty:
        st.info("No data in the current filter.")
        return
    months = sorted(df["month"].unique())
    depts = sorted(df["department"].unique())
    dept_color = {d: DEPT_COLORS[i % len(DEPT_COLORS)] for i, d in enumerate(depts)}

    fig = go.Figure()
    actual_total = df.groupby("month", observed=True)["amount"].sum().reindex(months, fill_value=0)
    budget_total = df.groupby("month", observed=True)["budget_amount"].sum().reindex(months, fill_value=0)

    # This figure intentionally does not vary with `selection` even for its
    # own selected department — see trend.py for why that causes a
    # selection-erasing feedback loop.
    for dept in depts:
        sub = df[df["department"] == dept].set_index("month").reindex(months, fill_value=0)
        fig.add_trace(go.Bar(
            x=months, y=sub["amount"], name=dept,
            marker=dict(color=dept_color[dept]),
            hovertemplate=f"<b>{dept}</b><br>%{{x}}<br>$%{{y:,.0f}}<extra></extra>",
        ))
    fig.add_trace(go.Scatter(
        x=months, y=budget_total, name="Total Budget", mode="lines",
        line=dict(color=T.INK, width=2, dash="dot"),
        hovertemplate="Budget<br>%{x}<br>$%{y:,.0f}<extra></extra>",
    ))
    layout = {**T.PLOTLY_LAYOUT, "yaxis": {**T.PLOTLY_LAYOUT["yaxis"], "tickformat": "$,.0s"}}
    fig.update_layout(**layout, barmode="stack", height=T.CHART_HEIGHT)

    event = st.plotly_chart(fig, width='stretch', key=tile_key, on_select="rerun", selection_mode="points")
    # Map curve_number -> department (trace order == depts, budget line is last).
    points = (event or {}).get("selection", {}).get("points", [])
    values = sorted({depts[p["curve_number"]] for p in points if p.get("curve_number", -1) < len(depts)})

    if values:
        if consume_once(tile_key, ("select", tuple(values))) and set_selection_if_changed("department", values, tile_key):
            st.rerun()
    else:
        if consume_once(tile_key, ("clear",)) and clear_selection_if_owned_by(tile_key):
            st.rerun()
