"""Expense Breakdown vs Budget — ECharts bullet chart (replaces the source
screenshot's three radial gauges; see treemap.py-style rationale in the
project plan). A gauge-variant toggle is offered so the original chart type
is still demonstrable via the same JS bridge."""

import pandas as pd
import streamlit as st

from src.components.echarts import echarts_bullet, echarts_gauges
from src.data import metrics as M
from src.state import Selection, set_selection


def render(cube_f: pd.DataFrame, budget_f: pd.DataFrame, selection: Selection, tile_key: str):
    df = M.expense_breakdown(cube_f, budget_f)
    if df.empty:
        st.info("No data in the current filter.")
        return
    df = df.head(6).sort_values("actual")

    show_gauge = st.toggle("Gauge variant", value=False, key=f"{tile_key}_gauge_toggle",
                            help="Swap to the source screenshot's radial-gauge style, rendered through the same ECharts bridge.")

    if show_gauge:
        top3 = df.sort_values("actual", ascending=False).head(3)
        gauges = [
            {"name": row["department"], "value": round(min(row["pct_of_budget"], 150), 1),
             "color": "#d03b3b" if row["pct_of_budget"] > 100 else "#18794e"}
            for _, row in top3.iterrows()
        ]
        echarts_gauges(gauges, key=f"{tile_key}_gauge")
        return

    clicked = echarts_bullet(
        categories=df["department"].tolist(),
        actual=df["actual"].round(0).tolist(),
        budget=df["budget"].round(0).tolist(),
        over_budget=(df["pct_of_budget"] > 100).tolist(),
        key=tile_key,
    )
    if clicked and clicked.get("name"):
        set_selection("department", [clicked["name"]], tile_key)
