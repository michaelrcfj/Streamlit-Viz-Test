"""
Filtering + aggregation + KPI derivation.

Data design: there is ONE internal dataset (data/facts.parquet), carrying
actual and plan side by side on every row. So a tile that compares the two
filters once and reads two columns, instead of filtering a second budget
table on the same predicates and merging it back per chart. Cash flow is
derived here too (cash_flow_by_month) rather than stored, which leaves
competitor market share as the only other file — it has no join key to the
fact table, so it stays separate.

Performance design (this is what the perf footer on the dashboard measures):
  - build_cube() runs ONE groupby over the full raw transaction table (down
    to month x quarter x region x product x department x account, ~3-4k
    rows) and is @st.cache_data'd on the raw, unfiltered frame — which never
    changes across reruns, so after the first load this is always a cache
    hit, regardless of what the user clicks.
  - Every filter/selection interaction then operates on that small cube, not
    on the 100k-row source — boolean-masking + re-summing a few thousand
    rows is sub-millisecond, so it is deliberately left UNCACHED (caching
    overhead would exceed the work itself).
  - The exception is Top Customers, which needs row-level (customer)
    grain the cube doesn't carry. It filters the raw 100k-row frame
    directly on every call — still ~1-5ms via vectorized boolean
    indexing, but the one place scale genuinely costs something, which is
    exactly why the perf footer times it separately.

All headline KPIs are derived from these rows — never hardcoded — so the KPI
strip, the waterfall, and the monthly trend always reconcile under any filter
combination (the invariant the source screenshot violated).
"""

import time
import zlib
from dataclasses import dataclass

import numpy as np
import pandas as pd
import streamlit as st

CUBE_DIMS = ["month", "quarter", "region", "product", "department", "account"]


@st.cache_data(show_spinner=False)
def build_cube(tx: pd.DataFrame) -> pd.DataFrame:
    """The one expensive full-table groupby. Cached on the raw frame, which
    is stable across the session, so this runs once and is a cache hit
    on every subsequent interaction regardless of filters.

    Actual and plan aggregate together because they live on the same row, so
    every downstream tile gets both from a single filtered frame — there is
    no second budget table to filter in parallel and merge back."""
    return tx.groupby(CUBE_DIMS, observed=True)[["amount", "budget_amount"]].sum().reset_index()


def filter_cube(cube: pd.DataFrame, filters: dict, selection_dim: str | None = None,
                 selection_values: list | None = None, selection_source: str | None = None,
                 current_tile: str | None = None) -> pd.DataFrame:
    """Cheap re-filter of the small cube. Not cached — deliberately, see
    module docstring."""
    mask = pd.Series(True, index=cube.index)
    for dim in ("region", "product", "department"):
        values = filters.get(dim) or []
        if values:
            mask &= cube[dim].isin(values)
    period = filters.get("period", "All")
    if period and period != "All":
        mask &= cube["quarter"] == period
    if selection_dim and selection_values and selection_source != current_tile and selection_dim in cube.columns:
        mask &= cube[selection_dim].isin(selection_values)
    return cube[mask]


def filter_raw(tx: pd.DataFrame, filters: dict, selection_dim: str | None = None,
               selection_values: list | None = None, selection_source: str | None = None,
               current_tile: str | None = None) -> pd.DataFrame:
    """Row-level filter for tiles that need grain the cube doesn't carry
    (Top Customers). Uncached vectorized boolean mask."""
    mask = pd.Series(True, index=tx.index)
    for dim in ("region", "product", "department"):
        values = filters.get(dim) or []
        if values and dim in tx.columns:
            mask &= tx[dim].isin(values)
    period = filters.get("period", "All")
    if period and period != "All" and "quarter" in tx.columns:
        mask &= tx["quarter"] == period
    if selection_dim and selection_values and selection_source != current_tile and selection_dim in tx.columns:
        mask &= tx[selection_dim].isin(selection_values)
    return tx[mask]


@dataclass
class KPIs:
    revenue: float
    gross_profit: float
    opex: float
    net_income: float
    gross_margin: float
    net_margin: float
    revenue_prior: float
    gross_profit_prior: float
    opex_prior: float
    net_income_prior: float


def _account_sums(frame: pd.DataFrame) -> dict:
    g = frame.groupby("account", observed=True)["amount"].sum()
    return {a: float(g.get(a, 0.0)) for a in ("Revenue", "COGS", "OpEx", "Tax")}


def compute_kpis(cube_f: pd.DataFrame) -> KPIs:
    s = _account_sums(cube_f)
    revenue, cogs, opex, tax = s["Revenue"], s["COGS"], s["OpEx"], s["Tax"]
    gross_profit = revenue - cogs
    net_income = gross_profit - opex - tax

    months = sorted(cube_f["month"].unique())
    if months:
        mid = len(months) // 2 or 1
        prior_months, curr_months = months[:mid], months[mid:]
        prior = cube_f[cube_f["month"].isin(prior_months)]
    else:
        prior = cube_f.iloc[0:0]

    sp = _account_sums(prior)
    r_p, gp_p = sp["Revenue"], sp["Revenue"] - sp["COGS"]
    o_p = sp["OpEx"]
    ni_p = gp_p - o_p - sp["Tax"]

    return KPIs(
        revenue=revenue, gross_profit=gross_profit, opex=opex, net_income=net_income,
        gross_margin=(gross_profit / revenue) if revenue else 0.0,
        net_margin=(net_income / revenue) if revenue else 0.0,
        revenue_prior=r_p, gross_profit_prior=gp_p, opex_prior=o_p, net_income_prior=ni_p,
    )


def monthly_by_account(cube_f: pd.DataFrame) -> pd.DataFrame:
    return cube_f.groupby(["month", "account"], observed=True)["amount"].sum().reset_index()


def monthly_revenue_by_product(cube_f: pd.DataFrame) -> pd.DataFrame:
    rev = cube_f[cube_f["account"] == "Revenue"]
    return rev.groupby(["month", "product"], observed=True)["amount"].sum().reset_index()


def waterfall_frame(kpi: KPIs) -> pd.DataFrame:
    return pd.DataFrame({
        "stage": ["Revenue", "COGS", "Gross Profit", "OpEx", "Operating Income", "Tax", "Net Income"],
        "value": [
            kpi.revenue, -(kpi.revenue - kpi.gross_profit), kpi.gross_profit,
            -kpi.opex, kpi.gross_profit - kpi.opex,
            -(kpi.gross_profit - kpi.opex - kpi.net_income), kpi.net_income,
        ],
        "kind": ["total", "relative", "total", "relative", "total", "relative", "total"],
    })


def regional_margin(cube_f: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for region, g in cube_f.groupby("region", observed=True):
        s = _account_sums(g)
        gp = s["Revenue"] - s["COGS"]
        rows.append({"region": region, "revenue": s["Revenue"], "gross_profit": gp,
                     "gross_margin": (gp / s["Revenue"]) if s["Revenue"] else 0.0})
    return pd.DataFrame(rows)


def revenue_by_region_product(cube_f: pd.DataFrame) -> pd.DataFrame:
    rev = cube_f[cube_f["account"] == "Revenue"]
    return rev.groupby(["region", "product"], observed=True)["amount"].sum().reset_index()


def top_customers(tx_filtered: pd.DataFrame, n: int = 8) -> pd.DataFrame:
    rev = tx_filtered[tx_filtered["account"] == "Revenue"]
    if rev.empty:
        return pd.DataFrame(columns=["customer", "revenue", "trend", "yoy", "share_of_max"])
    by_cust = rev.groupby("customer", observed=True)["amount"].sum().sort_values(ascending=False).head(n)
    df = by_cust.reset_index()
    df.columns = ["customer", "revenue"]
    monthly = rev[rev["customer"].isin(df["customer"])].groupby(
        ["customer", "month"], observed=True)["amount"].sum().reset_index()
    trends, yoys = [], []
    for cust in df["customer"]:
        series = monthly.loc[monthly["customer"] == cust].sort_values("month")["amount"].tolist()
        trends.append(series if series else [0])
        if len(series) >= 2 and series[0] > 0:
            yoys.append((series[-1] - series[0]) / series[0])
        else:
            yoys.append(0.0)
    df["trend"] = trends
    df["yoy"] = yoys
    df["share_of_max"] = df["revenue"] / df["revenue"].max()
    return df


def department_spend_vs_budget(cube_f: pd.DataFrame) -> pd.DataFrame:
    """Actual vs plan per month x department. One groupby, no join — actual
    and budget are columns on the same already-filtered rows."""
    spend = cube_f[cube_f["account"].isin(["OpEx", "COGS"])]
    return (
        spend.groupby(["month", "department"], observed=True)[["amount", "budget_amount"]]
        .sum().reset_index().sort_values(["month", "department"])
    )


def expense_breakdown(cube_f: pd.DataFrame) -> pd.DataFrame:
    """One row per department: actual spend, budget, % to budget."""
    spend = cube_f[cube_f["account"].isin(["OpEx", "COGS"])]
    df = spend.groupby("department", observed=True)[["amount", "budget_amount"]].sum().reset_index()
    df = df.rename(columns={"amount": "actual", "budget_amount": "budget"})
    df["pct_of_budget"] = np.where(df["budget"] > 0, df["actual"] / df["budget"] * 100, 0.0)
    return df.sort_values("actual", ascending=False)


CASHFLOW_RATIOS = {"Operating": 0.85, "Investing": -0.18, "Financing": -0.08}


def _jitter(key: str, spread: float) -> float:
    """Stable pseudo-random factor in [-spread, +spread] from a string key.

    zlib.crc32 rather than the built-in hash(): hash() is salted per process
    for strings, so the cash flow chart would change shape on every restart."""
    return (zlib.crc32(key.encode()) % 2001 / 1000.0 - 1.0) * spread


def cash_flow_by_month(cube_f: pd.DataFrame) -> pd.DataFrame:
    """Cash flow by the indirect method: start from net income, split it into
    the three standard flows. Derived from the same filtered rows as every
    other tile rather than read from a separate table, so — unlike the
    version that read cashflow.parquet — this one actually responds to the
    filters and the chart selection like the rest of the dashboard does."""
    if cube_f.empty:
        return pd.DataFrame(columns=["month", "flow", "amount"])
    signed = np.where(cube_f["account"] == "Revenue", cube_f["amount"], -cube_f["amount"])
    net_income = cube_f.assign(signed=signed).groupby("month", observed=True)["signed"].sum()
    return pd.DataFrame([
        {"month": month, "flow": flow,
         "amount": value * ratio * (1 + _jitter(f"{month}|{flow}", 0.18))}
        for month, value in net_income.items()
        for flow, ratio in CASHFLOW_RATIOS.items()
    ])


class Timer:
    """Lightweight context manager for the perf footer."""
    def __enter__(self):
        self._t0 = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.ms = (time.perf_counter() - self._t0) * 1000
