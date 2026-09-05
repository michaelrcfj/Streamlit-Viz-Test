"""App shell: page config, native theme (config.toml) + CSS layer, and
st.navigation between the dashboard and the Limitations Scorecard."""

from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="Global FinCorp — Financial Performance",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

_CSS_PATH = Path(__file__).parent / "src" / "style.css"
st.html(f"<style>{_CSS_PATH.read_text()}</style>")

pages = {
    "Dashboard": [
        st.Page("pages/dashboard.py", title="Financial Performance", icon="📊", default=True),
    ],
    "Evaluation": [
        st.Page("pages/scorecard.py", title="Limitations Scorecard", icon="🧪"),
    ],
}
nav = st.navigation(pages)
nav.run()
