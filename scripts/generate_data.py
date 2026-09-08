"""
Generates the fixed synthetic Parquet dataset for the Global FinCorp
dashboard. Run once; the output under data/ is committed to the repo so the
app (including on Streamlit Community Cloud, which has no pre-launch script
step) just reads it off disk rather than regenerating it per run.

Two datasets, not four. Everything internal lives in ONE fact table:

  facts.parquet        ~100k rows. Actuals AND plan at row grain: every row
                       carries both `amount` and `budget_amount`, so a single
                       filter pass serves every actual-vs-budget tile and the
                       aggregation cube carries plan for free. Cash flow is
                       NOT stored — it is derived from these same rows at
                       read time (see metrics.cash_flow_by_month).
  market_share.parquet 60 rows. The one genuinely external entity: competitor
                       is not a transaction dimension, so it cannot be folded
                       into the fact table without inventing a join key.

Design goals:
  - ~100k transaction rows with real seasonality, growth trend, and
    region/product skew so cross-filtering visibly moves every tile.
  - All headline KPIs (revenue, gross profit, opex, net income) are DERIVED
    from these rows downstream (see src/data/metrics.py) — never hardcoded —
    so the KPI strip reconciles with the waterfall by construction, unlike
    the source screenshot.
  - Deterministic: numpy.random.default_rng(42), so re-running this script
    reproduces byte-identical data.

Run:  python scripts/generate_data.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

REGIONS = ["NAM", "EMEA", "APAC", "LATAM"]  # NAM not "NA" -- reads too much like "N/A"
REGION_WEIGHT = [0.42, 0.33, 0.18, 0.07]

PRODUCTS = ["Software", "Services", "Hardware"]
PRODUCT_WEIGHT = [0.52, 0.31, 0.17]

DEPARTMENTS = ["Sales", "Marketing", "Engineering", "R&D", "IT", "HR", "Finance"]
DEPT_WEIGHT = [0.22, 0.16, 0.24, 0.14, 0.12, 0.06, 0.06]

ACCOUNTS = ["Revenue", "COGS", "OpEx", "Tax"]

COMPETITORS = ["Global FinCorp", "Meridian Capital", "Northwind Financial", "Apex Ledger", "Solaris Trust"]

START = pd.Timestamp("2023-01-01")
END = pd.Timestamp("2023-09-30")

COMPANY_PREFIXES = [
    "Atlas", "Vertex", "Nimbus", "Cascade", "Beacon", "Summit", "Orbit", "Harbor",
    "Lattice", "Meridian", "Pioneer", "Quartz", "Redwood", "Sterling", "Talon",
    "Vantage", "Wayfinder", "Zenith", "Anchor", "Bridgeway", "Crestline", "Dovetail",
    "Everline", "Foundry", "Granite", "Hearth", "Ironclad", "Juniper", "Keystone",
    "Longview", "Marlin", "Novara", "Outrigger", "Pinnacle", "Questar", "Ridgeline",
    "Solstice", "Trailmark", "Umbra", "Viridian", "Westgate", "Yardley", "Aldergate",
    "Brightfield", "Coppervale", "Driftwood", "Eastport", "Fallcrest", "Glenbrook",
    "Highmoor", "Inverness", "Jasperton", "Kettlewood", "Larkspur", "Millbrook",
    "Norwich", "Oakhaven", "Palisade", "Rockford", "Silverpine", "Thornbury",
]
COMPANY_SUFFIXES = ["Group", "Holdings", "Industries", "Partners", "Corp", "Systems", "Global", "Ventures"]


def build_customers(rng, n=60):
    prefixes = rng.choice(COMPANY_PREFIXES, size=n, replace=False)
    suffixes = rng.choice(COMPANY_SUFFIXES, size=n, replace=True)
    names = [f"{p} {s}" for p, s in zip(prefixes, suffixes)]
    # Power-law-ish revenue weight so "Top Customers" has real spread.
    weights = rng.pareto(2.0, size=n) + 0.3
    weights = weights / weights.sum()
    return names, weights


def seasonal_factor(dates: pd.DatetimeIndex) -> np.ndarray:
    doy = dates.dayofyear.to_numpy()
    # Mild seasonality: dip in Feb, ramp into Q3 (fiscal push), light summer lull.
    seasonal = 1.0 + 0.10 * np.sin((doy - 60) / 365 * 2 * np.pi)
    # Overall growth trend across the 9 months.
    days_elapsed = (dates - START).days.to_numpy()
    trend = 1.0 + 0.35 * (days_elapsed / (END - START).days)
    return seasonal * trend


def generate_transactions(rng, n_rows: int) -> pd.DataFrame:
    days = (END - START).days + 1
    date_offsets = rng.integers(0, days, size=n_rows)
    dates = START + pd.to_timedelta(date_offsets, unit="D")

    region = rng.choice(REGIONS, size=n_rows, p=REGION_WEIGHT)
    product = rng.choice(PRODUCTS, size=n_rows, p=PRODUCT_WEIGHT)
    department = rng.choice(DEPARTMENTS, size=n_rows, p=DEPT_WEIGHT)

    customer_names, customer_weights = build_customers(rng)
    customer = rng.choice(customer_names, size=n_rows, p=customer_weights)

    # Revenue rows dominate; COGS/OpEx/Tax are cost rows recorded as positive
    # amounts in their own account bucket (netted in metrics.py).
    account = rng.choice(ACCOUNTS, size=n_rows, p=[0.55, 0.24, 0.17, 0.04])

    base_amount = rng.lognormal(mean=8.6, sigma=0.9, size=n_rows)  # ~ $5k median
    factor = seasonal_factor(pd.DatetimeIndex(dates))
    amount = base_amount * factor

    # Account-level scale factors, solved so the aggregate books land on
    # realistic ratios (~42% gross margin, ~24% opex/rev, ~13% net margin)
    # given the account row-count weights above (each account draws from the
    # same base distribution, so its total scales with count x this factor):
    #   COGS/Rev = 0.582  -> scale 1.333
    #   OpEx/Rev = 0.238  -> scale 0.770
    #   Tax (of Rev)= 0.044 -> scale 0.605
    account_scale = np.select(
        [account == "Revenue", account == "COGS", account == "OpEx", account == "Tax"],
        [1.0, 1.333, 0.770, 0.605],
    )
    amount = amount * account_scale

    # Product-level unit economics layered on top of COGS only: hardware
    # carries thinner margin (higher relative cost) than software. Weighted
    # average across the product mix is ~1.0 so it reshapes COGS by product
    # without shifting the aggregate COGS/Revenue ratio solved above.
    cogs_product_mult = np.select(
        [product == "Software", product == "Services", product == "Hardware"],
        [0.68, 1.24, 1.53],
    )
    amount = np.where(account == "COGS", amount * cogs_product_mult, amount)

    df = pd.DataFrame({
        "date": pd.DatetimeIndex(dates).normalize(),
        "region": pd.Categorical(region, categories=REGIONS),
        "product": pd.Categorical(product, categories=PRODUCTS),
        "department": pd.Categorical(department, categories=DEPARTMENTS),
        "customer": customer,
        "account": pd.Categorical(account, categories=ACCOUNTS),
        "amount": np.round(amount, 2),
    })
    df["quarter"] = df["date"].dt.to_period("Q").astype(str)
    df["month"] = df["date"].dt.to_period("M").astype(str)
    df["year"] = df["date"].dt.year
    return df


def add_budget(rng, tx: pd.DataFrame) -> pd.DataFrame:
    """Adds a per-row `budget_amount` so plan travels with actuals in one table.

    The variance is drawn per CELL (month x region x product x department x
    account) and then applied to every row in that cell, not drawn per row.
    That matters: with a per-row draw the noise would average out on the way
    up to the cube, leaving every department sitting at a flat ~3% to budget
    and the variance charts with nothing to show. Drawing per cell means
    summing rows to any grain reproduces exactly the cell-level variance a
    separate budget table would have carried."""
    cell = (
        tx["month"].astype(str) + "|" + tx["region"].astype(str) + "|"
        + tx["product"].astype(str) + "|" + tx["department"].astype(str) + "|"
        + tx["account"].astype(str)
    )
    # Sorted, so a cell's variance depends only on the cell's identity — not
    # on which row of the 100k happened to hit it first.
    cells = pd.Index(sorted(cell.unique()))
    variance = pd.Series(rng.normal(loc=0.0, scale=0.08, size=len(cells)), index=cells)
    # Budgets set slightly conservative on revenue (actual tends to beat budget)
    # and slightly loose on cost accounts (actual tends to beat/undercut too).
    bias = np.where(tx["account"] == "Revenue", -0.04, 0.03)
    tx["budget_amount"] = np.round(tx["amount"] * (1 + bias + cell.map(variance).to_numpy()), 2)
    return tx


def generate_market_share(rng) -> pd.DataFrame:
    quarters = ["2023Q1", "2023Q2", "2023Q3"]
    rows = []
    base = {"Global FinCorp": 27, "Meridian Capital": 24, "Northwind Financial": 19, "Apex Ledger": 16, "Solaris Trust": 14}
    for region in REGIONS:
        for qi, q in enumerate(quarters):
            drift = rng.normal(0, 1.2, size=len(base))
            shares = np.array(list(base.values())) + drift + qi * np.array([1.1, -0.4, -0.3, -0.2, -0.2])
            shares = np.clip(shares, 3, None)
            shares = shares / shares.sum() * 100
            for name, share in zip(base.keys(), shares):
                rows.append({"quarter": q, "region": region, "competitor": name, "share_pct": round(float(share), 2)})
    return pd.DataFrame(rows)


def assert_invariants(tx: pd.DataFrame):
    """KPI reconciliation guardrail: net income computed two ways must match."""
    revenue = tx.loc[tx["account"] == "Revenue", "amount"].sum()
    costs = tx.loc[tx["account"] != "Revenue", "amount"].sum()
    net_income = revenue - costs
    monthly_signed = tx.assign(signed=np.where(tx["account"] == "Revenue", tx["amount"], -tx["amount"]))
    monthly_sum = monthly_signed.groupby("month", observed=True)["signed"].sum().sum()
    assert abs(net_income - monthly_sum) < 1.0, f"Reconciliation failure: {net_income} vs {monthly_sum}"
    assert revenue > 0 and net_income > 0, "Sanity check failed: expect positive revenue and net income"
    print(f"[ok] revenue=${revenue:,.0f}  net_income=${net_income:,.0f}  margin={net_income/revenue:.1%}")


def main():
    n_rows = 100_000
    rng = np.random.default_rng(42)

    DATA_DIR.mkdir(exist_ok=True)

    print(f"Generating {n_rows:,} fact rows...")
    facts = generate_transactions(rng, n_rows)
    assert_invariants(facts)
    facts = add_budget(rng, facts)
    facts.to_parquet(DATA_DIR / "facts.parquet", index=False)

    market_share = generate_market_share(rng)
    market_share.to_parquet(DATA_DIR / "market_share.parquet", index=False)

    print(f"Wrote facts.parquet ({len(facts):,} rows, actual + budget), "
          f"market_share.parquet ({len(market_share)} rows)")


if __name__ == "__main__":
    sys.exit(main())
