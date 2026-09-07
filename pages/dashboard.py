"""The Global FinCorp dashboard grid.

Layout: a fixed 4-column grid. A row of 4 tiles splits evenly; a shorter
final row still fills the full width by giving its tiles wider ratios so
the total always sums to 4 "slots" (e.g. 2 tiles -> 2 slots each)."""

import time

import streamlit as st

from src import state as S
from src import theme as T
from src.charts import cashflow, dept_spend, ebitda, expense_bullet, kpi as kpi_chart
from src.charts import market_share, regional_margin, top_customers, treemap, trend, waterfall
from src.components.tile import tile
from src.data import metrics as M
from src.data.load import data_ready, load_budget, load_cashflow, load_transactions

S.bootstrap()

# ---- Data readiness ---------------------------------------------------------
if not data_ready():
    st.error(
        "No data found. Run `python scripts/generate_data.py` from the project "
        "root to generate the dataset, then reload."
    )
    st.stop()

tx_full = load_transactions()

# ---- Sidebar: global filters -------------------------------------------------
with st.sidebar:
    st.markdown("### Filters")
    st.caption("Applied to every tile on the dashboard.")

    all_regions = list(T.REGION_ORDER)
    all_products = list(T.SERIES_ORDER)
    all_depts = sorted(tx_full["department"].cat.categories.tolist())
    all_periods = ["All"] + sorted(tx_full["quarter"].unique().tolist())

    st.multiselect("Region", all_regions, key="f_region")
    st.multiselect("Product", all_products, key="f_product")
    st.multiselect("Department", all_depts, key="f_department")
    st.selectbox("Fiscal Period", all_periods, key="f_period")
    st.radio("Compare To", ["Target", "Previous Year"], key="f_compare", horizontal=True)

    st.divider()
    if st.button("Clear all filters", width='stretch'):
        for dim in ("f_region", "f_product", "f_department"):
            st.session_state[dim] = []
        st.session_state["f_period"] = "All"
        S.clear_selection()
        st.rerun()

# ---- Header ------------------------------------------------------------------
st.markdown('<div class="gfc-header">', unsafe_allow_html=True)
h1, h2 = st.columns([4, 1])
with h1:
    st.markdown("## 📊 Global FinCorp — Financial Performance Dashboard")
    st.caption("Q1–Q3 2023 · Jan 1 – Sep 30 · synthetic data")
with h2:
    st.write("")
    if st.button("✕ Reset selection", width='stretch', disabled=not S.get_selection().active,
                 help="Click a chart to filter every other tile by it (like a Tableau filter action). "
                      "This clears that selection without touching the sidebar filters."):
        S.clear_selection()
        st.rerun()
st.markdown("</div>", unsafe_allow_html=True)

# ---- Active filter chips ------------------------------------------------------
chips = S.active_filter_chips()
if chips:
    chip_html = "".join(
        f'<span class="gfc-chip{" selection" if kind == "selection" else ""}">{label}</span>'
        for label, kind in chips
    )
    st.markdown(f'<div class="gfc-chip-row">{chip_html}</div>', unsafe_allow_html=True)

filters = S.get_filters()
selection = S.get_selection()

# ---- Core aggregation (this is what the perf footer measures) --------------
perf = {}
t0 = time.perf_counter()
cube_full = M.build_cube(tx_full)
perf["cube_build_ms"] = (time.perf_counter() - t0) * 1000

budget_full = load_budget()
cashflow_df = load_cashflow()

t0 = time.perf_counter()
cube_f = M.filter_cube(cube_full, filters, selection.dim, selection.values, selection.source, current_tile=None)
budget_f = M.filter_budget(budget_full, filters)
kpis = M.compute_kpis(cube_f)
perf["filter_agg_ms"] = (time.perf_counter() - t0) * 1000
perf["cube_rows"] = len(cube_f)
perf["raw_rows"] = len(tx_full)

if cube_f.empty:
    st.warning("No data matches the current filters + selection. Try clearing a filter.")
    st.stop()


def cube_for(tile_key: str):
    return M.filter_cube(cube_full, filters, selection.dim, selection.values, selection.source, current_tile=tile_key)


def budget_for():
    return M.filter_budget(budget_full, filters)


# ---- KPI strip (4 tiles — already a full row) --------------------------------
kpi_chart.render_kpi_strip(cube_f, kpis)

# ---- 4-column tile grid -------------------------------------------------------
# Each tile that owns a widget (a clickable chart, a toggle, ...) is wrapped in
# @st.fragment. A click/toggle inside one tile now reruns only that tile
# instead of the whole script and every other tile with it. Cross-filtering
# still needs every OTHER tile to pick up the new selection, so the handlers
# below still call the bare `st.rerun()` they always did — inside a fragment
# that's documented to trigger a full app rerun, not a fragment-scoped one.
# The win is the click itself: it used to cost a full-script rerun just to
# discover the selection changed (rendering all 9 other tiles with data that
# was about to be replaced) before the real, propagating rerun could fire.
# Now that first pass is fragment-scoped, so it skips the other tiles and the
# cube re-filter entirely.
GRID_RATIOS = {1: [4], 2: [2, 2], 3: [2, 1, 1], 4: [1, 1, 1, 1]}


def grid_row(n: int):
    return st.columns(GRID_RATIOS[n])


@st.fragment
def tile_trend():
    with tile("Monthly Revenue Trend (Combo Chart)", "📈"):
        trend.render(cube_for("trend_chart"), budget_for(), selection, tile_key="trend_chart")


@st.fragment
def tile_regional_margin():
    with tile("Regional Gross Margin", "🌍"):
        regional_margin.render(cube_for("regional_margin"), selection, tile_key="regional_margin")


@st.fragment
def tile_expense_bullet():
    with tile("Expense Breakdown vs Budget", "💰"):
        expense_bullet.render(cube_for("expense_bullet"), budget_for(), selection, tile_key="expense_bullet")


@st.fragment
def tile_treemap():
    with tile("Revenue by Region & Product", "🌳"):
        treemap.render(cube_for("treemap"), selection, tile_key="treemap")


@st.fragment
def tile_dept_spend():
    with tile("Dept Spend vs Budget", "🏢"):
        dept_spend.render(cube_for("dept_spend"), budget_for(), selection, tile_key="dept_spend")


@st.fragment
def tile_market_share():
    with tile("Market Share Analysis", "🥧"):
        market_share.render(filters, tile_key="market_share")


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

# Row 2 (4 tiles)
c1, c2, c3, c4 = grid_row(4)
with c1:
    with tile("Profitability Waterfall", "💧"):
        waterfall.render(kpis, tile_key="waterfall")
with c2:
    tile_dept_spend()
with c3:
    with tile("Top Customers by Revenue", "🏆"):
        t0 = time.perf_counter()
        tx_f = M.filter_raw(tx_full, filters, selection.dim, selection.values, selection.source, current_tile=None)
        perf["raw_filter_ms"] = (time.perf_counter() - t0) * 1000
        top_customers.render(tx_f, tile_key="top_customers")
with c4:
    with tile("Cash Flow Trends", "💵"):
        cashflow.render(cashflow_df, tile_key="cashflow")

# Row 3 (2 tiles — each takes the width of two grid slots)
c1, c2 = grid_row(2)
with c1:
    tile_market_share()
with c2:
    with tile("Quarterly EBITDA Margin", "📐"):
        ebitda.render(cube_for("ebitda"), tile_key="ebitda")


# ---- Perf footer + export ------------------------------------------------------
# Also a fragment: clicking a download/export button here has zero effect on
# filters or selection, so it has no business re-running the cube build and
# all 10 tiles above it either.
@st.fragment
def perf_and_export():
    with st.expander("⏱ Performance & Export", expanded=False):
        fc1, fc2, fc3, fc4, fc5 = st.columns(5)
        fc1.metric("Raw rows loaded", f"{perf['raw_rows']:,}")
        fc2.metric("Cube rows (post-filter)", f"{perf['cube_rows']:,}")
        fc3.metric("Cube build (cache)", f"{perf['cube_build_ms']:.2f} ms")
        fc4.metric("Filter + aggregate", f"{perf['filter_agg_ms']:.2f} ms")
        fc5.metric("Raw-row filter (Top Customers)", f"{perf.get('raw_filter_ms', 0):.2f} ms")
        st.caption(
            "Cube build is cached on the raw table (cache hit after first load, regardless of filter). "
            "Filter+aggregate re-derives KPIs from the ~3-4k row cube on every interaction — this is the "
            "number to watch as you toggle filters. Raw-row filter is the uncached path (Top Customers) — "
            "this is the one place row count actually costs something."
        )

        from src import export as E
        ec1, ec2, ec3 = st.columns(3)
        with ec1:
            st.download_button("Download filtered transactions (CSV)", data=E.csv_bytes(
                M.filter_raw(tx_full, filters, selection.dim, selection.values, selection.source)
            ), file_name="gfc_transactions_filtered.csv", mime="text/csv", width='stretch')
        with ec2:
            if st.button("Export dashboard as PDF", width='stretch'):
                with st.spinner("Re-rendering charts server-side for PDF..."):
                    import plotly.graph_objects as go
                    figs = []
                    wf_df = M.waterfall_frame(kpis)
                    fig = go.Figure(go.Waterfall(x=wf_df["stage"], y=wf_df["value"],
                                                  measure=["absolute" if k == "total" else "relative" for k in wf_df["kind"]]))
                    fig.update_layout(**T.PLOTLY_LAYOUT, height=400)
                    figs.append(("Profitability Waterfall", E.plotly_png_bytes(fig)))
                    pdf_bytes = E.build_dashboard_pdf(
                        title="Global FinCorp — Financial Performance",
                        subtitle="Q1-Q3 2023 · exported from Streamlit prototype",
                        kpi_lines=[
                            f"Revenue ${kpis.revenue:,.0f}", f"Gross Profit ${kpis.gross_profit:,.0f}",
                            f"OpEx ${kpis.opex:,.0f}", f"Net Income ${kpis.net_income:,.0f}",
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
