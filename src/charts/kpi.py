"""KPI stat tiles with an Altair sparkline, matching the source screenshot's
top strip but with numbers that reconcile (see src/data/metrics.py)."""

import altair as alt
import pandas as pd
import streamlit as st

from src import theme as T
from src.data import metrics as M


def _delta_html(current: float, prior: float, suffix: str = "", higher_is_better: bool = True) -> str:
    if prior == 0:
        return '<div class="gfc-kpi-delta">—</div>'
    pct = (current - prior) / abs(prior) * 100
    is_good = (pct >= 0) if higher_is_better else (pct <= 0)
    cls = "good" if is_good else "bad"
    arrow = "▲" if pct >= 0 else "▼"
    return f'<div class="gfc-kpi-delta {cls}">{arrow} {abs(pct):.1f}%{suffix}</div>'


def _sparkline(series: pd.Series, color: str) -> alt.Chart:
    df = series.reset_index()
    df.columns = ["month", "value"]
    return (
        alt.Chart(df, height=36, width=110)
        .mark_line(color=color, strokeWidth=2, point=alt.OverlayMarkDef(size=18, filled=True, color=color))
        .encode(
            x=alt.X("month:N", axis=None),
            y=alt.Y("value:Q", axis=None, scale=alt.Scale(zero=False)),
            tooltip=[alt.Tooltip("month:N", title="Month"), alt.Tooltip("value:Q", title="Value", format=",.0f")],
        )
        .configure_view(strokeWidth=0)
    )


def kpi_tile(label: str, value: float, prior: float, sub: str, series: pd.Series, color: str,
             fmt="${:,.0f}", higher_is_better: bool = True):
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(f'<div class="gfc-kpi-eyebrow">{label}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="gfc-kpi-value">{fmt.format(value)}</div>', unsafe_allow_html=True)
        st.markdown(_delta_html(value, prior, " vs prior period", higher_is_better), unsafe_allow_html=True)
        st.markdown(f'<div class="gfc-kpi-sub">{sub}</div>', unsafe_allow_html=True)
    with col2:
        if len(series) >= 2:
            st.altair_chart(_sparkline(series, color), width='content', key=f"spark_{label}")


def render_kpi_strip(cube_f: pd.DataFrame, kpi: M.KPIs):
    monthly = M.monthly_by_account(cube_f)

    def series_for(account):
        s = monthly[monthly["account"] == account].set_index("month")["amount"]
        return s

    revenue_series = series_for("Revenue")
    gp_series = revenue_series - series_for("COGS").reindex(revenue_series.index, fill_value=0)
    opex_series = series_for("OpEx")
    tax_series = series_for("Tax").reindex(revenue_series.index, fill_value=0)
    ni_series = gp_series - opex_series.reindex(revenue_series.index, fill_value=0) - tax_series

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        with st.container(border=True):
            st.markdown('<div class="gfc-tile-marker" style="display:none"></div>', unsafe_allow_html=True)
            kpi_tile("Total Revenue", kpi.revenue, kpi.revenue_prior,
                     f"{kpi.gross_margin:.1%} gross margin", revenue_series, T.ACCOUNT_SERIES["Revenue"])
    with c2:
        with st.container(border=True):
            st.markdown('<div class="gfc-tile-marker" style="display:none"></div>', unsafe_allow_html=True)
            kpi_tile("Gross Profit", kpi.gross_profit, kpi.gross_profit_prior,
                     f"{kpi.gross_margin:.1%} margin", gp_series, T.ACCOUNT_SERIES["Net Income"])
    with c3:
        with st.container(border=True):
            st.markdown('<div class="gfc-tile-marker" style="display:none"></div>', unsafe_allow_html=True)
            kpi_tile("Operating Expense", kpi.opex, kpi.opex_prior,
                     f"{(kpi.opex / kpi.revenue if kpi.revenue else 0):.1%} of revenue", opex_series,
                     T.ACCOUNT_SERIES["OpEx"], higher_is_better=False)
    with c4:
        with st.container(border=True):
            st.markdown('<div class="gfc-tile-marker" style="display:none"></div>', unsafe_allow_html=True)
            kpi_tile("Net Income", kpi.net_income, kpi.net_income_prior,
                     f"{kpi.net_margin:.1%} margin", ni_series, T.ACCENT)
