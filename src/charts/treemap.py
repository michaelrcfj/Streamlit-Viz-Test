"""Revenue by Region & Product — nested treemap. Deliberate redesign from the
source screenshot's rainbow treemap: identity (product) carries hue from the
fixed categorical slots, magnitude (region revenue within a product) carries
a tint of that same hue — one encoding per channel, not color doing both
jobs at once."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import theme as T
from src.data import metrics as M
from src.state import Selection, set_selection


def _tint(hex_color: str, amount: float) -> str:
    """Lighten hex_color toward white by `amount` (0=no change, 1=white)."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    r = int(r + (255 - r) * amount)
    g = int(g + (255 - g) * amount)
    b = int(b + (255 - b) * amount)
    return f"#{r:02x}{g:02x}{b:02x}"


def render(cube_f: pd.DataFrame, selection: Selection, mode: str, tile_key: str):
    df = M.revenue_by_region_product(cube_f)
    if df.empty:
        st.info("No revenue in the current filter.")
        return

    labels, parents, values, colors, ids = [], [], [], [], []
    for product in T.SERIES_ORDER:
        sub = df[df["product"] == product]
        total = sub["amount"].sum()
        if total <= 0:
            continue
        labels.append(product); parents.append(""); values.append(total); ids.append(product)
        colors.append(T.SERIES[product])
        max_region = sub["amount"].max()
        for _, row in sub.sort_values("amount", ascending=False).iterrows():
            tint_amt = 0.15 + 0.45 * (1 - row["amount"] / max_region) if max_region else 0.3
            labels.append(row["region"]); parents.append(product); values.append(row["amount"])
            ids.append(f"{product}/{row['region']}")
            colors.append(_tint(T.SERIES[product], tint_amt))

    fig = go.Figure(go.Treemap(
        labels=labels, parents=parents, values=values, ids=ids,
        marker=dict(colors=colors, line=dict(width=2, color=T.TILE_BG)),
        textfont=dict(family=T.FONT_SANS, size=12, color="white"),
        texttemplate="<b>%{label}</b><br>$%{value:,.0f}",
        hovertemplate="<b>%{label}</b><br>$%{value:,.0f}<extra></extra>",
        pathbar=dict(visible=True, textfont=dict(size=11, color=T.INK_SECONDARY)),
    ))
    fig.update_layout(**{k: v for k, v in T.PLOTLY_LAYOUT.items() if k not in ("xaxis", "yaxis")}, height=300)

    event = st.plotly_chart(fig, width='stretch', key=tile_key, on_select="rerun", selection_mode="points")
    if event and event.get("selection", {}).get("points"):
        pt = event["selection"]["points"][0]
        clicked_id = pt.get("id") or pt.get("label")
        if clicked_id and "/" in str(clicked_id):
            product = clicked_id.split("/")[0]
            set_selection("product", [product], tile_key)
        elif clicked_id in T.SERIES_ORDER:
            set_selection("product", [clicked_id], tile_key)
