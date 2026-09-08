"""Monthly revenue trend by product — stacked bar + budget line. Plotly, so
it drives the click-to-filter selection loop via on_select."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import state as S
from src import theme as T
from src.data import metrics as M


def render(cube_f: pd.DataFrame, tile_key: str):
    by_product = M.monthly_revenue_by_product(cube_f)
    months = sorted(by_product["month"].unique())
    # Budget rides on the same filtered rows as the bars, so the target line
    # now narrows with a selection instead of staying at whole-book scale
    # while the bars shrank under it.
    revenue = cube_f[cube_f["account"] == "Revenue"]
    budget_monthly = revenue.groupby("month", observed=True)["budget_amount"].sum()

    # NOTE: this figure must NOT vary based on selection state even when this
    # tile is the one that owns it — restyling the source chart in reaction
    # to the selection it just emitted changes the figure between reruns,
    # which remounts the Plotly widget and wipes its client-side selection
    # state, which then reports back as "cleared" and erases the very
    # selection that was just set. (Found by tracing an actual click through
    # several reruns — see the Limitations Scorecard.) The clicked bar still
    # gets visibly highlighted: Plotly's own selection_mode dims every point
    # except the selected one automatically, entirely client-side, as long as
    # the figure itself never changes shape in reaction to it.
    fig = go.Figure()
    for product in T.SERIES_ORDER:
        # Reindex just the amount Series, not the whole (possibly empty, if
        # this product got filtered out of cube_f) frame -- reindexing the
        # frame itself would need a fill value for the "product" column too,
        # and 0 isn't a valid category on that Categorical dtype.
        sub = by_product[by_product["product"] == product].set_index("month")["amount"].reindex(months, fill_value=0)
        fig.add_trace(go.Bar(
            x=months, y=sub, name=product,
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

    widget_key = S.chart_widget_key(tile_key)

    def _on_select():
        # Reads the value st.plotly_chart just committed to session_state for
        # this widget -- on_change/on_select callbacks fire only on a genuine
        # value change, so unlike the old on_select="rerun" + read-every-run
        # pattern, this never needs a consume_once guard.
        event = st.session_state[widget_key]
        # Map curve_number -> product rather than trusting customdata's exact
        # shape (Plotly's on_select payload shape for scalar customdata isn't
        # consistent across chart types) — the trace order is exactly
        # T.SERIES_ORDER since that's the order they were added above.
        points = (event or {}).get("selection", {}).get("points", [])
        values = sorted({T.SERIES_ORDER[p["curve_number"]] for p in points if p.get("curve_number", -1) < len(T.SERIES_ORDER)})
        if values:
            S.apply_selection("product", values, tile_key)
        else:
            S.apply_selection_clear(tile_key)

    st.plotly_chart(
        fig, width='stretch', key=widget_key, on_select=_on_select, selection_mode="points",
    )
