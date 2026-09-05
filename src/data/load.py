"""Cached Parquet loaders. Every load is @st.cache_data so repeat reruns
(the dominant cost of Streamlit's rerun-on-every-interaction model) are a
cache hit, not a disk read."""

from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "data"


@st.cache_data(show_spinner=False)
def load_transactions(stress: bool = False) -> pd.DataFrame:
    suffix = "_stress" if stress else ""
    path = DATA_DIR / f"transactions{suffix}.parquet"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found — run `python scripts/generate_data.py"
            f"{' --stress' if stress else ''}` first."
        )
    df = pd.read_parquet(path)
    return df


@st.cache_data(show_spinner=False)
def load_budget() -> pd.DataFrame:
    return pd.read_parquet(DATA_DIR / "budget.parquet")


@st.cache_data(show_spinner=False)
def load_market_share() -> pd.DataFrame:
    return pd.read_parquet(DATA_DIR / "market_share.parquet")


@st.cache_data(show_spinner=False)
def load_cashflow() -> pd.DataFrame:
    return pd.read_parquet(DATA_DIR / "cashflow.parquet")


def data_ready(stress: bool = False) -> bool:
    suffix = "_stress" if stress else ""
    return (DATA_DIR / f"transactions{suffix}.parquet").exists()
