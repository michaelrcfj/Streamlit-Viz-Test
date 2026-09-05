"""Top Customers — rich st.dataframe using column_config: a progress bar for
revenue share, a sparkline column for the monthly trend, mono-formatted YoY
with conditional coloring via a Styler. Row selection opens the drill-through
dialog (this tile is deliberately drill-only — clicking a customer row is a
transaction-level action, not a global filter)."""

import pandas as pd
import streamlit as st

from src.data import metrics as M


def render(tx_filtered: pd.DataFrame, tile_key: str):
    df = M.top_customers(tx_filtered, n=8)
    if df.empty:
        st.info("No revenue in the current filter.")
        return

    display = df[["customer", "revenue", "trend", "yoy", "share_of_max"]].copy()

    event = st.dataframe(
        display,
        width='stretch',
        hide_index=True,
        height=290,
        key=tile_key,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "customer": st.column_config.TextColumn("Customer", width="medium"),
            "revenue": st.column_config.NumberColumn("Revenue", format="$%,.0f"),
            "trend": st.column_config.LineChartColumn("Trend", width="small"),
            "yoy": st.column_config.NumberColumn("YoY Growth", format="percent"),
            "share_of_max": st.column_config.ProgressColumn("Share", format="", min_value=0, max_value=1),
        },
    )
    sel_rows = (event or {}).get("selection", {}).get("rows", [])
    if sel_rows:
        customer = df.iloc[sel_rows[0]]["customer"]
        st.session_state["drill_customer"] = customer
        st.session_state["drill_open"] = True
