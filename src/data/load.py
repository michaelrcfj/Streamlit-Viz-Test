"""Cached Parquet loaders. Every load is @st.cache_data so repeat reruns
(the dominant cost of Streamlit's rerun-on-every-interaction model) are a
cache hit, not a disk read.

The dataset is fixed and committed to the repo (see scripts/generate_data.py
and README.md) rather than generated at runtime — this app is also deployed
on Streamlit Community Cloud, which has no step to run a generator script
before the app starts, so the Parquet files under data/ ship as-is."""

from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "data"


@st.cache_data(show_spinner=False)
def load_transactions() -> pd.DataFrame:
    path = DATA_DIR / "transactions.parquet"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found — run `python scripts/generate_data.py` once "
            "from the project root to generate it."
        )
    return pd.read_parquet(path)


@st.cache_data(show_spinner=False)
def load_budget() -> pd.DataFrame:
    return pd.read_parquet(DATA_DIR / "budget.parquet")


@st.cache_data(show_spinner=False)
def load_market_share() -> pd.DataFrame:
    return pd.read_parquet(DATA_DIR / "market_share.parquet")


@st.cache_data(show_spinner=False)
def load_cashflow() -> pd.DataFrame:
    return pd.read_parquet(DATA_DIR / "cashflow.parquet")


def data_ready() -> bool:
    return (DATA_DIR / "transactions.parquet").exists()
