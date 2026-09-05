"""Monthly revenue trend by product — stacked bar + budget line. Plotly, so
it drives the Filter/Highlight/Drill selection loop via on_select."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import theme as T
from src.data import metrics as M
from src.state import Selection


def render(cube_f: pd.DataFrame, budget_f: pd.DataFrame, selection: Selection, mode: str, tile_key: str):
    by_product = M.monthly_revenue_by_product(cube_f)
    months = sorted(by_product["month"].unique())
    budget_monthly = budget_f[budget_f["account"] == "Revenue"].groupby("month", observed=True)["budget_amount"].sum()

    fig = go.Figure()
    for product in T.SERIES_ORDER:
        sub = by_product[by_product["product"] == product].set_index("month").reindex(months, fill_value=0)
        is_selected = selection.dim == "product" and product in selection.values
        highlighting = mode == "Highlight" and selection.active
        opacity = 1.0 if (not highlighting or is_selected or selection.dim != "product") else 0.25
        fig.add_trace(go.Bar(
            x=months, y=sub["amount"], name=product,
            marker=dict(color=T.SERIES[product], opacity=opacity,
                        line=dict(width=1.5 if is_selected else 0, color=T.INK)),
            hovertemplate=f"<b>{product}</b><br>%{{x}}<br>$%{{y:,.0f}}<extra></extra>",
            customdata=[product] * len(months),
        ))
    budget_vals = budget_monthly.reindex(months, fill_value=0)
    fig.add_trace(go.Scatter(
        x=months, y=budget_vals, name="Budget", mode="lines+markers",
        line=dict(color=T.INK, width=2, dash="dot"), marker=dict(size=5),
        hovertemplate="Budget<br>%{x}<br>$%{y:,.0f}<extra></extra>",
    ))
    layout = {**T.PLOTLY_LAYOUT, "yaxis": {**T.PLOTLY_LAYOUT["yaxis"], "tickformat": "$,.0s"}}
    fig.update_layout(**layout, barmode="stack", height=280)

    event = st.plotly_chart(
        fig, width='stretch', key=tile_key, on_select="rerun", selection_mode="points",
    )
    _handle_selection(event, "product", tile_key)


def _handle_selection(event, dim: str, source: str):
    if not event or not event.get("selection"):
        return
    points = event["selection"].get("points", [])
    if not points:
        return
    values = sorted({p.get("customdata") if p.get("customdata") is not None else p.get("legendgroup") for p in points} - {None})
    if not values:
        return
    from src.state import set_selection
    set_selection(dim, values, source)
