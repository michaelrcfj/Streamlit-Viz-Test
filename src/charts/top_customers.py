"""Top Customers — rich st.dataframe using column_config: a progress bar for
revenue share, a sparkline column for the monthly trend, mono-formatted YoY.
Plain display, not a filter source — 'customer' isn't a dimension the
aggregation cube carries, so it can't cross-filter the other tiles."""

import pandas as pd
import streamlit as st

from src import theme as T
from src.data import metrics as M


def render(tx_filtered: pd.DataFrame, tile_key: str):
    df = M.top_customers(tx_filtered, n=8)
    if df.empty:
        st.info("No revenue in the current filter.")
        return

    display = df[["customer", "revenue", "trend", "yoy", "share_of_max"]].copy()

    st.dataframe(
        display,
        width='stretch',
        hide_index=True,
        height=T.CHART_HEIGHT,
        key=tile_key,
        column_config={
            "customer": st.column_config.TextColumn("Customer", width="medium"),
            "revenue": st.column_config.NumberColumn("Revenue", format="$%,.0f"),
            "trend": st.column_config.LineChartColumn("Trend", width="small"),
            "yoy": st.column_config.NumberColumn("YoY Growth", format="percent"),
            "share_of_max": st.column_config.ProgressColumn("Share", format="", min_value=0, max_value=1),
        },
    )
