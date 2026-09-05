"""Quarterly EBITDA Margin — Actual vs Target line, Altair. EBITDA is
approximated here as Operating Income (Gross Profit - OpEx), which is the
closest derivable proxy given the transaction schema has no separate
D&A account — noted on the Limitations Scorecard as a modeling shortcut,
not hidden."""

import altair as alt
import pandas as pd
import streamlit as st

from src import theme as T


def render(cube_f: pd.DataFrame, tile_key: str):
    q = cube_f.groupby("quarter", observed=True).apply(
        lambda g: pd.Series({
            "revenue": g.loc[g["account"] == "Revenue", "amount"].sum(),
            "cogs": g.loc[g["account"] == "COGS", "amount"].sum(),
            "opex": g.loc[g["account"] == "OpEx", "amount"].sum(),
        }), include_groups=False,
    ).reset_index()
    q["ebitda_margin"] = ((q["revenue"] - q["cogs"] - q["opex"]) / q["revenue"].replace(0, pd.NA) * 100).fillna(0)
    q["target_margin"] = 22.0
    long = q.melt(id_vars="quarter", value_vars=["ebitda_margin", "target_margin"], var_name="series", value_name="value")
    long["series"] = long["series"].map({"ebitda_margin": "Actual", "target_margin": "Target"})

    chart = (
        alt.Chart(long)
        .mark_line(point=alt.OverlayMarkDef(size=45, filled=True), strokeWidth=2.5)
        .encode(
            x=alt.X("quarter:N", title=None),
            y=alt.Y("value:Q", title="EBITDA Margin %", axis=alt.Axis(format=".0f")),
            color=alt.Color("series:N", scale=alt.Scale(domain=["Actual", "Target"], range=[T.ACCENT, T.INK_MUTED]), title=None),
            strokeDash=alt.StrokeDash("series:N", scale=alt.Scale(domain=["Actual", "Target"], range=[[1, 0], [4, 3]]), legend=None),
            tooltip=[alt.Tooltip("quarter:N", title="Quarter"), alt.Tooltip("series:N", title="Series"),
                     alt.Tooltip("value:Q", title="Margin %", format=".1f")],
        )
        .properties(height=230)
    )
    st.altair_chart(chart, width='stretch', key=tile_key)
