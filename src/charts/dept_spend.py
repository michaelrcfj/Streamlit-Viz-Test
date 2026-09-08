"""Department spend vs budget over time — Plotly grouped bar + budget line,
clicking a department bar drives the selection loop on the 'department' dim."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import state as S
from src import theme as T
from src.data import metrics as M

DEPT_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#4a3aa7", "#e34948"]


def render(cube_f: pd.DataFrame, tile_key: str):
    df = M.department_spend_vs_budget(cube_f)
    if df.empty:
        st.info("No data in the current filter.")
        return
    months = sorted(df["month"].unique())
    depts = sorted(df["department"].unique())
    dept_color = {d: DEPT_COLORS[i % len(DEPT_COLORS)] for i, d in enumerate(depts)}

    fig = go.Figure()
    budget_total = df.groupby("month", observed=True)["budget_amount"].sum().reindex(months, fill_value=0)

    # This figure intentionally does not vary with selection state even for
    # its own selected department — see trend.py for why that causes a
    # selection-erasing feedback loop. The clicked bar is still highlighted
    # by Plotly's own selection_mode dimming, entirely client-side.
    for dept in depts:
        # Reindex just the amount Series, not the whole frame -- reindexing
        # the frame would need a fill value for the "department" column too,
        # and 0 isn't a valid category on that Categorical dtype (see the
        # identical fix in trend.py, which is where this actually crashes).
        sub = df[df["department"] == dept].set_index("month")["amount"].reindex(months, fill_value=0)
        fig.add_trace(go.Bar(
            x=months, y=sub, name=dept,
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

    widget_key = S.chart_widget_key(tile_key)

    def _on_select():
        event = st.session_state[widget_key]
        # Map curve_number -> department (trace order == depts, budget line is last).
        points = (event or {}).get("selection", {}).get("points", [])
        values = sorted({depts[p["curve_number"]] for p in points if p.get("curve_number", -1) < len(depts)})
        if values:
            S.apply_selection("department", values, tile_key)
        else:
            S.apply_selection_clear(tile_key)

    st.plotly_chart(fig, width='stretch', key=widget_key, on_select=_on_select, selection_mode="points")
