"""The Global FinCorp dashboard grid."""

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
        "root to generate the ~100k-row synthetic dataset, then reload."
    )
    st.stop()

# ---- Sidebar: global filters -------------------------------------------------
with st.sidebar:
    st.markdown("### Filters")
    st.caption("Applied to every tile on the dashboard.")

    stress_mode = st.toggle(
        "Stress test: 1M rows", value=st.session_state.get("stress_mode", False),
        key="stress_mode", help="Swap the data source to a 1M-row table to see where the rerun model actually breaks. "
                                  "Run `python scripts/generate_data.py --stress` once first.",
    )
    if stress_mode and not data_ready(stress=True):
        st.warning("Stress dataset not found — run `python scripts/generate_data.py --stress` first. Falling back to 100k rows.")
        stress_mode = False

    tx_full = load_transactions(stress=stress_mode)

    all_regions = list(T.REGION_ORDER)
    all_products = list(T.SERIES_ORDER)
    all_depts = sorted(tx_full["department"].cat.categories.tolist())
    all_periods = ["All"] + sorted(tx_full["quarter"].unique().tolist())

    # Guard against a persisted session_state value that no longer exists in
    # the current option set (e.g. after toggling the stress dataset) —
    # Streamlit's key-bound widgets raise if the bound value isn't in options.
    st.session_state["f_region"] = [r for r in st.session_state.get("f_region", []) if r in all_regions]
    st.session_state["f_product"] = [p for p in st.session_state.get("f_product", []) if p in all_products]
    st.session_state["f_department"] = [d for d in st.session_state.get("f_department", []) if d in all_depts]
    if st.session_state.get("f_period") not in all_periods:
        st.session_state["f_period"] = "All"

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

# ---- Header: title + interaction mode toggle --------------------------------
st.markdown('<div class="gfc-header">', unsafe_allow_html=True)
h1, h2 = st.columns([3, 2])
with h1:
    st.markdown("## 📊 Global FinCorp — Financial Performance Dashboard")
    st.caption("Q1–Q3 2023 · Jan 1 – Sep 30 · synthetic data")
with h2:
    m1, m2 = st.columns([3, 1])
    with m1:
        st.segmented_control(
            "Interaction mode", S.INTERACTION_MODES, key="mode",
            help=(
                "**Filter** — a click re-filters every other tile (like a Tableau filter action). "
                "**Highlight** — totals stay fixed; other tiles dim non-matching marks. "
                "**Drill** — a click opens a transaction-level detail view."
            ),
        )
    with m2:
        st.write("")
        if st.button("✕ Reset", width='stretch', disabled=not S.get_selection().active):
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
mode = S.get_mode()

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

# ---- KPI strip ----------------------------------------------------------------
kpi_chart.render_kpi_strip(cube_f, kpis)

# ---- Row 1: trend | regional margin | expense vs budget ----------------------
r1c1, r1c2, r1c3 = st.columns([2, 1, 1])
with r1c1:
    with tile("Monthly Revenue Trend (Combo Chart)", "📈"):
        cube_local = M.filter_cube(cube_full, filters, selection.dim, selection.values, selection.source, current_tile="trend_chart")
        budget_local = M.filter_budget(budget_full, filters)
        trend.render(cube_local, budget_local, selection, mode, tile_key="trend_chart")
with r1c2:
    with tile("Regional Gross Margin", "🌍"):
        cube_local = M.filter_cube(cube_full, filters, selection.dim, selection.values, selection.source, current_tile="regional_margin")
        regional_margin.render(cube_local, selection, mode, tile_key="regional_margin")
with r1c3:
    with tile("Expense Breakdown vs Budget", "💰"):
        cube_local = M.filter_cube(cube_full, filters, selection.dim, selection.values, selection.source, current_tile="expense_bullet")
        budget_local = M.filter_budget(budget_full, filters)
        expense_bullet.render(cube_local, budget_local, selection, tile_key="expense_bullet")

# ---- Row 2: treemap | waterfall | dept spend ---------------------------------
r2c1, r2c2, r2c3 = st.columns([1, 1, 1])
with r2c1:
    with tile("Revenue by Region & Product", "🌳"):
        cube_local = M.filter_cube(cube_full, filters, selection.dim, selection.values, selection.source, current_tile="treemap")
        treemap.render(cube_local, selection, mode, tile_key="treemap")
with r2c2:
    with tile("Profitability Waterfall", "💧"):
        waterfall.render(kpis, tile_key="waterfall")
with r2c3:
    with tile("Dept Spend vs Budget", "🏢"):
        cube_local = M.filter_cube(cube_full, filters, selection.dim, selection.values, selection.source, current_tile="dept_spend")
        budget_local = M.filter_budget(budget_full, filters)
        dept_spend.render(cube_local, budget_local, selection, mode, tile_key="dept_spend")

# ---- Row 3: top customers | cash flow | market share | ebitda ----------------
r3c1, r3c2, r3c3, r3c4 = st.columns([1.3, 1, 1, 1])
with r3c1:
    with tile("Top Customers by Revenue", "🏆"):
        t0 = time.perf_counter()
        tx_f = M.filter_raw(tx_full, filters, selection.dim, selection.values, selection.source, current_tile=None)
        perf["raw_filter_ms"] = (time.perf_counter() - t0) * 1000
        top_customers.render(tx_f, tile_key="top_customers")
with r3c2:
    with tile("Cash Flow Trends", "💵"):
        cashflow.render(cashflow_df, tile_key="cashflow")
with r3c3:
    with tile("Market Share Analysis", "🥧"):
        market_share.render(filters, tile_key="market_share")
with r3c4:
    with tile("Quarterly EBITDA Margin", "📐"):
        cube_local = M.filter_cube(cube_full, filters, selection.dim, selection.values, selection.source, current_tile="ebitda")
        ebitda.render(cube_local, tile_key="ebitda")

# ---- Drill-through dialog -----------------------------------------------------
if st.session_state.get("drill_open") and st.session_state.get("drill_customer"):
    @st.dialog(f"Drill through — {st.session_state['drill_customer']}", width="large")
    def _drill():
        customer = st.session_state["drill_customer"]
        rows = tx_full[tx_full["customer"] == customer].sort_values("date", ascending=False)
        c1, c2, c3 = st.columns(3)
        rev_rows = rows[rows["account"] == "Revenue"]
        c1.metric("Total Revenue", f"${rev_rows['amount'].sum():,.0f}")
        c2.metric("Transactions", f"{len(rows):,}")
        c3.metric("Regions", rows["region"].nunique())
        st.dataframe(
            rows[["date", "region", "product", "department", "account", "amount"]].head(200),
            width='stretch', hide_index=True,
            column_config={"amount": st.column_config.NumberColumn("Amount", format="$%,.2f")},
        )
        st.download_button(
            "Download full transaction history (CSV)",
            data=rows.to_csv(index=False).encode("utf-8"),
            file_name=f"{customer.replace(' ', '_')}_transactions.csv",
            mime="text/csv",
        )
        if st.button("Close"):
            st.session_state["drill_open"] = False
            st.rerun()
    _drill()

# ---- Perf footer + export ------------------------------------------------------
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
        "number to watch as you toggle filters. Raw-row filter is the uncached path (Top Customers, "
        "drill-through) — this is where row count actually matters; try the 1M stress toggle."
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

S.sync_url()
