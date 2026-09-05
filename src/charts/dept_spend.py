"""Department spend vs budget over time — Plotly grouped bar + budget line,
clicking a department bar drives the selection loop on the 'department' dim."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import theme as T
from src.data import metrics as M
from src.state import Selection, set_selection

DEPT_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#4a3aa7", "#e34948"]


def render(cube_f: pd.DataFrame, budget_f: pd.DataFrame, selection: Selection, mode: str, tile_key: str):
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

    for dept in depts:
        sub = df[df["department"] == dept].set_index("month").reindex(months, fill_value=0)
        is_selected = selection.dim == "department" and dept in selection.values
        highlighting = mode == "Highlight" and selection.active and selection.dim == "department"
        opacity = 1.0 if (not highlighting or is_selected) else 0.25
        fig.add_trace(go.Bar(
            x=months, y=sub["amount"], name=dept,
            marker=dict(color=dept_color[dept], opacity=opacity),
            hovertemplate=f"<b>{dept}</b><br>%{{x}}<br>$%{{y:,.0f}}<extra></extra>",
            customdata=[dept] * len(months),
        ))
    fig.add_trace(go.Scatter(
        x=months, y=budget_total, name="Total Budget", mode="lines",
        line=dict(color=T.INK, width=2, dash="dot"),
        hovertemplate="Budget<br>%{x}<br>$%{y:,.0f}<extra></extra>",
    ))
    layout = {**T.PLOTLY_LAYOUT, "yaxis": {**T.PLOTLY_LAYOUT["yaxis"], "tickformat": "$,.0s"}}
    fig.update_layout(**layout, barmode="stack", height=280)

    event = st.plotly_chart(fig, width='stretch', key=tile_key, on_select="rerun", selection_mode="points")
    if event and event.get("selection", {}).get("points"):
        vals = {p.get("customdata") for p in event["selection"]["points"] if p.get("customdata")}
        if vals:
            set_selection("department", sorted(vals), tile_key)
