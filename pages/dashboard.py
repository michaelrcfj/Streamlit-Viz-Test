"""The Global FinCorp dashboard grid.

Layout: a fixed 4-column grid. Every row sums to 4 "slots", so a row can hold
four even tiles, two double-width ones, or a mix (row 2 runs 1-1-2, giving
the Top Customers table the width its sparkline and progress columns want).

Every tile below is its own @st.fragment, keyed and listed in
S.DEPENDENT_FRAGMENTS. A click-to-filter chart, a sidebar filter, or one of
the two clear/reset buttons all end up calling one of the S.apply_*
callbacks, which commits the change and calls
`st.rerun(scope=S.DEPENDENT_FRAGMENTS)` -- a TARGETED rerun of exactly the
tiles whose content depends on filters/selection, not a full-page one.
Nothing outside that list is ever torn down, so there's no "whole dashboard
blanks out for a second" flash: only the fragments that actually need new
data disappear and reappear, and only while their own new content is on the
way.

Because a targeted rerun re-invokes each fragment's stored closure directly
without re-running the rest of this script, every fragment below reads
filters/selection fresh from session_state (via cube_for() or
S.get_filters()/S.get_selection() directly) rather than closing over the
`filters`/`selection` this script computed on its last full run -- that
closure would otherwise go stale the moment a targeted rerun (rather than a
full one) is what updated the underlying state. facts_full/cube_full are the
exception: they're `@st.cache_data`-backed and never change for the session,
so a stale reference to them is byte-for-byte identical to a fresh one and
closing over them is fine.
"""

import time

import streamlit as st

from src import state as S
from src import theme as T
from src.charts import cashflow, dept_spend, expense_bullet, kpi as kpi_chart
from src.charts import market_share, regional_margin, top_customers, treemap, trend, waterfall
from src.components.tile import tile
from src.data import metrics as M
from src.data.load import data_ready, load_facts

S.bootstrap()

# ---- Data readiness ---------------------------------------------------------
if not data_ready():
    st.error(
        "No data found. Run `python scripts/generate_data.py` from the project "
        "root to generate the dataset, then reload."
    )
    st.stop()

facts_full = load_facts()
cube_full = M.build_cube(facts_full)


def cube_for(tile_key: str | None):
    """Every tile's data in one call: the cube carries actual and budget as
    columns, so there is no second frame to filter alongside this one."""
    filters = S.get_filters()
    selection = S.get_selection()
    return M.filter_cube(cube_full, filters, selection.dim, selection.values, selection.source, current_tile=tile_key)


# ---- Sidebar: global filters -------------------------------------------------
# A fragment like every other filter/selection-dependent piece of UI: a
# filter widget's own value change already updates its own display
# optimistically client-side, but "Clear all filters" changes these same
# widgets' values from a DIFFERENT callback -- without this in
# S.DEPENDENT_FRAGMENTS, that change would commit server-side (as the URL
# sync would show) while the widgets kept displaying their old values.
@st.fragment(key="sidebar_filters")
def sidebar_filters():
    st.markdown("### Filters")
    st.caption("Applied to every tile on the dashboard.")

    all_regions = list(T.REGION_ORDER)
    all_products = list(T.SERIES_ORDER)
    all_depts = sorted(facts_full["department"].cat.categories.tolist())
    all_periods = ["All"] + sorted(facts_full["quarter"].unique().tolist())

    st.multiselect("Region", all_regions, key="f_region", on_change=S.apply_filters_changed)
    st.multiselect("Product", all_products, key="f_product", on_change=S.apply_filters_changed)
    st.multiselect("Department", all_depts, key="f_department", on_change=S.apply_filters_changed)
    st.selectbox("Fiscal Period", all_periods, key="f_period", on_change=S.apply_filters_changed)
    st.radio("Compare To", ["Target", "Previous Year"], key="f_compare", horizontal=True,
             on_change=S.apply_filters_changed)

    st.divider()
    st.button("Clear all filters", width='stretch', on_click=S.apply_clear_all_filters)


with st.sidebar:
    sidebar_filters()


# ---- Header + active filter chips --------------------------------------------
@st.fragment(key="chips")
def header_and_chips():
    st.markdown('<div class="gfc-header">', unsafe_allow_html=True)
    h1, h2 = st.columns([4, 1])
    with h1:
        st.markdown("## 📊 Global FinCorp — Financial Performance Dashboard")
        st.caption("Q1–Q3 2023 · Jan 1 – Sep 30 · synthetic data")
    with h2:
        st.write("")
        st.button("✕ Reset selection", width='stretch', disabled=not S.get_selection().active,
                   help="Click a chart to filter every other tile by it (like a Tableau filter action). "
                        "This clears that selection without touching the sidebar filters.",
                   on_click=S.apply_reset_selection)
    st.markdown("</div>", unsafe_allow_html=True)

    chips = S.active_filter_chips()
    if chips:
        chip_html = "".join(
            f'<span class="gfc-chip{" selection" if kind == "selection" else ""}">{label}</span>'
            for label, kind in chips
        )
        st.markdown(f'<div class="gfc-chip-row">{chip_html}</div>', unsafe_allow_html=True)


header_and_chips()


# ---- KPI strip (4 tiles — already a full row) --------------------------------
@st.fragment(key="kpi_strip")
def kpi_strip():
    cube_f = cube_for(None)
    if cube_f.empty:
        st.warning("No data matches the current filters + selection. Try clearing a filter.")
        return
    kpi_chart.render_kpi_strip(cube_f, M.compute_kpis(cube_f))


kpi_strip()

# ---- 4-column tile grid -------------------------------------------------------
GRID_RATIOS = {1: [4], 2: [2, 2], 3: [2, 1, 1], 4: [1, 1, 1, 1]}


def grid_row(n: int, ratios: list[int] | None = None):
    """`ratios` overrides the default split for that tile count — it still has
    to sum to 4 slots so the row lines up with the rest of the grid."""
    return st.columns(ratios or GRID_RATIOS[n])


@st.fragment(key="tile_trend")
def tile_trend():
    with tile("Monthly Revenue Trend (Combo Chart)", "📈"):
        trend.render(cube_for("trend_chart"), tile_key="trend_chart")


@st.fragment(key="tile_regional_margin")
def tile_regional_margin():
    with tile("Regional Gross Margin", "🌍"):
        regional_margin.render(cube_for("regional_margin"), tile_key="regional_margin")


@st.fragment(key="tile_expense_bullet")
def tile_expense_bullet():
    with tile("Expense Breakdown vs Budget", "💰"):
        expense_bullet.render(cube_for("expense_bullet"), tile_key="expense_bullet")


@st.fragment(key="tile_treemap")
def tile_treemap():
    with tile("Revenue by Region & Product", "🌳"):
        treemap.render(cube_for("treemap"), tile_key="treemap")


@st.fragment(key="tile_waterfall")
def tile_waterfall():
    with tile("Profitability Waterfall", "💧"):
        waterfall.render(M.compute_kpis(cube_for(None)), tile_key="waterfall")


@st.fragment(key="tile_dept_spend")
def tile_dept_spend():
    with tile("Dept Spend vs Budget", "🏢"):
        dept_spend.render(cube_for("dept_spend"), tile_key="dept_spend")


@st.fragment(key="tile_top_customers")
def tile_top_customers():
    with tile("Top Customers by Revenue", "🏆"):
        selection = S.get_selection()
        facts_f = M.filter_raw(facts_full, S.get_filters(), selection.dim, selection.values, selection.source, current_tile=None)
        top_customers.render(facts_f, tile_key="top_customers")


@st.fragment(key="tile_market_share")
def tile_market_share():
    with tile("Market Share Analysis", "🥧"):
        market_share.render(S.get_filters(), tile_key="market_share")


@st.fragment(key="tile_cashflow")
def tile_cashflow():
    with tile("Cash Flow Trends", "💵"):
        cashflow.render(cube_for(None), tile_key="cashflow")


# Row 1 (4 tiles)
c1, c2, c3, c4 = grid_row(4)
with c1:
    tile_trend()
with c2:
    tile_regional_margin()
with c3:
    tile_expense_bullet()
with c4:
    tile_treemap()

# Row 2 (3 tiles — Top Customers takes two slots; it's a table with a
# sparkline and a progress column, and it was the tile most starved of width)
c1, c2, c3 = grid_row(3, [1, 1, 2])
with c1:
    tile_waterfall()
with c2:
    tile_dept_spend()
with c3:
    tile_top_customers()

# Row 3 (2 tiles — each takes the width of two grid slots)
c1, c2 = grid_row(2)
with c1:
    tile_market_share()
with c2:
    tile_cashflow()


# ---- Perf footer + export ------------------------------------------------------
@st.fragment(key="perf_and_export")
def perf_and_export():
    t0 = time.perf_counter()
    cube_build_ms = (time.perf_counter() - t0) * 1000  # cube_full above is already a cache hit here

    filters = S.get_filters()
    selection = S.get_selection()
    t0 = time.perf_counter()
    cube_f = M.filter_cube(cube_full, filters, selection.dim, selection.values, selection.source, current_tile=None)
    perf_kpis = M.compute_kpis(cube_f)
    filter_agg_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    facts_f_all = M.filter_raw(facts_full, filters, selection.dim, selection.values, selection.source)
    raw_filter_ms = (time.perf_counter() - t0) * 1000

    with st.expander("⏱ Performance & Export", expanded=False):
        fc1, fc2, fc3, fc4, fc5 = st.columns(5)
        fc1.metric("Raw rows loaded", f"{len(facts_full):,}")
        fc2.metric("Cube rows (post-filter)", f"{len(cube_f):,}")
        fc3.metric("Cube build (cache)", f"{cube_build_ms:.2f} ms")
        fc4.metric("Filter + aggregate", f"{filter_agg_ms:.2f} ms")
        fc5.metric("Raw-row filter (Top Customers)", f"{raw_filter_ms:.2f} ms")
        st.caption(
            "Cube build is cached on the raw table (cache hit after first load, regardless of filter). "
            "Filter+aggregate re-derives KPIs from the ~3-4k row cube on every interaction — this is the "
            "number to watch as you toggle filters. Raw-row filter is the uncached path (Top Customers) — "
            "this is the one place row count actually costs something."
        )

        from src import export as E
        ec1, ec2, ec3 = st.columns(3)
        with ec1:
            st.download_button("Download filtered transactions (CSV)", data=E.csv_bytes(facts_f_all),
                                file_name="gfc_transactions_filtered.csv", mime="text/csv", width='stretch')
        with ec2:
            if st.button("Export dashboard as PDF", width='stretch'):
                with st.spinner("Re-rendering charts server-side for PDF..."):
                    import plotly.graph_objects as go
                    figs = []
                    wf_df = M.waterfall_frame(perf_kpis)
                    fig = go.Figure(go.Waterfall(x=wf_df["stage"], y=wf_df["value"],
                                                  measure=["absolute" if k == "total" else "relative" for k in wf_df["kind"]]))
                    fig.update_layout(**T.PLOTLY_LAYOUT, height=400)
                    figs.append(("Profitability Waterfall", E.plotly_png_bytes(fig)))
                    pdf_bytes = E.build_dashboard_pdf(
                        title="Global FinCorp — Financial Performance",
                        subtitle="Q1-Q3 2023 · exported from Streamlit prototype",
                        kpi_lines=[
                            f"Revenue ${perf_kpis.revenue:,.0f}", f"Gross Profit ${perf_kpis.gross_profit:,.0f}",
                            f"OpEx ${perf_kpis.opex:,.0f}", f"Net Income ${perf_kpis.net_income:,.0f}",
                        ],
                        images=figs,
                    )
                    st.session_state["_pdf_bytes"] = pdf_bytes
            if st.session_state.get("_pdf_bytes"):
                st.download_button("Download PDF", data=st.session_state["_pdf_bytes"],
                                    file_name="gfc_dashboard.pdf", mime="application/pdf", width='stretch')
                st.caption("⚠️ PDF is a server-side re-render: ECharts tiles and CSS chrome are not captured. See the Scorecard page.")
        with ec3:
            st.page_link("pages/scorecard.py", label="Open Limitations Scorecard →", icon="🧪", width='stretch')


perf_and_export()

S.sync_url()
