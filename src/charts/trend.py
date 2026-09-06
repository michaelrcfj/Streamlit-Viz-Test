"""Monthly revenue trend by product — stacked bar + budget line. Plotly, so
it drives the click-to-filter selection loop via on_select."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import theme as T
from src.data import metrics as M
from src.state import Selection, clear_selection_if_owned_by, consume_once, set_selection_if_changed


def render(cube_f: pd.DataFrame, budget_f: pd.DataFrame, selection: Selection, tile_key: str):
    by_product = M.monthly_revenue_by_product(cube_f)
    months = sorted(by_product["month"].unique())
    budget_monthly = budget_f[budget_f["account"] == "Revenue"].groupby("month", observed=True)["budget_amount"].sum()

    # NOTE: this figure must NOT vary based on `selection` even when this
    # tile is the one that owns it — restyling the source chart in reaction
    # to the selection it just emitted changes the figure between reruns,
    # which remounts the Plotly widget and wipes its client-side selection
    # state, which then reports back as "cleared" and erases the very
    # selection that was just set. (Found by tracing an actual click through
    # several reruns — see the Limitations Scorecard.)
    fig = go.Figure()
    for product in T.SERIES_ORDER:
        sub = by_product[by_product["product"] == product].set_index("month").reindex(months, fill_value=0)
        fig.add_trace(go.Bar(
            x=months, y=sub["amount"], name=product,
            marker=dict(color=T.SERIES[product]),
            hovertemplate=f"<b>{product}</b><br>%{{x}}<br>$%{{y:,.0f}}<extra></extra>",
        ))
    budget_vals = budget_monthly.reindex(months, fill_value=0)
    fig.add_trace(go.Scatter(
        x=months, y=budget_vals, name="Budget", mode="lines+markers",
        line=dict(color=T.INK, width=2, dash="dot"), marker=dict(size=5),
        hovertemplate="Budget<br>%{x}<br>$%{y:,.0f}<extra></extra>",
    ))
    layout = {**T.PLOTLY_LAYOUT, "yaxis": {**T.PLOTLY_LAYOUT["yaxis"], "tickformat": "$,.0s"}}
    fig.update_layout(**layout, barmode="stack", height=T.CHART_HEIGHT)

    event = st.plotly_chart(
        fig, width='stretch', key=tile_key, on_select="rerun", selection_mode="points",
    )
    # Map curve_number -> product rather than trusting customdata's exact
    # shape (Plotly's on_select payload shape for scalar customdata isn't
    # consistent across chart types) — the trace order is exactly
    # T.SERIES_ORDER since that's the order they were added above.
    points = (event or {}).get("selection", {}).get("points", [])
    values = sorted({T.SERIES_ORDER[p["curve_number"]] for p in points if p.get("curve_number", -1) < len(T.SERIES_ORDER)})

    if values:
        if consume_once(tile_key, ("select", tuple(values))) and set_selection_if_changed("product", values, tile_key):
            st.rerun()
    else:
        if consume_once(tile_key, ("clear",)) and clear_selection_if_owned_by(tile_key):
            st.rerun()
