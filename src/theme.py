"""
Single source of truth for the "financial ledger" palette and typography.

Values here are mirrored into .streamlit/config.toml (native theming) and
src/style.css (grid geometry / tile chrome). Chart modules import from here
directly so a chart's colors are never hand-typed hex strings.

Palette provenance:
- Chrome (surfaces/ink/lines/accent) from the cream-design-tokens skill.
- Categorical/sequential/diverging/status slots from the dataviz skill's
  validated reference palette (references/palette.md), snapped to the
  light-mode surface used here (#ffffff tile / #faf8f4 page).
"""

# ---- Surfaces -----------------------------------------------------------
PAGE_BG = "#faf8f4"
TILE_BG = "#ffffff"
PANEL_BG = "#fcfbf8"  # recessed panels: table header rows, alt striping

# ---- Ink (text) -----------------------------------------------------------
INK = "#1a1a17"
INK_SECONDARY = "#6b6760"
INK_MUTED = "#8f897e"
INK_FAINT = "#b3ada1"

# ---- Lines ----------------------------------------------------------------
LINE = "#e8e4dc"
LINE_STRONG = "#e3ddd2"
LINE_SOFT = "#f0ece4"

# ---- Accent (brand) ---------------------------------------------------------
ACCENT = "#18794e"
ACCENT_600 = "#3f8c66"
ACCENT_TINT = "#eef4ef"
ACCENT_WASH = "#f3f7f4"

# ---- Categorical series (dataviz validated order, first 3 slots) ----------
# Fixed assignment — never cycled, never re-assigned on filter.
SERIES = {
    "Software": "#2a78d6",   # slot 1: blue
    "Services": "#eb6834",   # slot 2: orange
    "Hardware": "#1baf7a",   # slot 3: aqua
}
SERIES_ORDER = ["Software", "Services", "Hardware"]

REGION_SERIES = {
    "NAM": "#2a78d6",  # not "NA" -- reads too much like "N/A" (missing data)
    "EMEA": "#eb6834",
    "APAC": "#1baf7a",
    "LATAM": "#eda100",
}
REGION_ORDER = ["NAM", "EMEA", "APAC", "LATAM"]

ACCOUNT_SERIES = {
    "Revenue": "#2a78d6",
    "COGS": "#eb6834",
    "OpEx": "#eda100",
    "Tax": "#e34948",
    "Net Income": "#1baf7a",
}

# ---- Shared sizing so every tile in a grid row lands at the same height ----
# TILE_HEIGHT is the outer st.container height (see components/tile.py);
# CHART_HEIGHT is what's left for the plot/table itself after the tile's own
# header row and padding. Tiles with an extra control (e.g. a toggle) size
# their chart to CHART_HEIGHT - CONTROL_ROW_HEIGHT so the total still matches.
TILE_HEIGHT = 430
CHART_HEIGHT = TILE_HEIGHT - 90
CONTROL_ROW_HEIGHT = 40

CASHFLOW_SERIES = {
    "Operating": "#2a78d6",
    "Investing": "#1baf7a",
    "Financing": "#e87ba4",
}

# ---- Sequential ramp (magnitude), single hue blue --------------------------
SEQUENTIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#2a78d6", "#1c5cab", "#104281", "#0d366b"]

# ---- Diverging (variance vs budget/target): blue <-> red -------------------
DIVERGING = ["#0d366b", "#2a78d6", "#9ec5f4", "#f0efec", "#f2b3b2", "#e34948", "#8c1f1e"]
DIVERGING_MIDPOINT = "#f0efec"

# ---- Status (fixed, never themed) ------------------------------------------
GOOD = "#0ca30c"
WARNING = "#fab219"
CRITICAL = "#d03b3b"

# ---- Typography -------------------------------------------------------------
FONT_SANS = "Hanken Grotesk, system-ui, -apple-system, 'Segoe UI', sans-serif"
FONT_MONO = "IBM Plex Mono, ui-monospace, monospace"

# ---- Shape ------------------------------------------------------------------
RADIUS_CARD = 14

# ---- Plotly layout template (applied to every Plotly figure) ---------------
PLOTLY_LAYOUT = dict(
    paper_bgcolor=TILE_BG,
    plot_bgcolor=TILE_BG,
    font=dict(family=FONT_SANS, color=INK_SECONDARY, size=12),
    # No `title` here — an empty Plotly title object (font styling with no
    # `text`) renders a bold "undefined" tspan client-side. Tile titles come
    # from our own HTML header (src/components/tile.py) instead.
    legend=dict(font=dict(size=11, color=INK_SECONDARY), orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    margin=dict(l=8, r=8, t=8, b=8),
    xaxis=dict(gridcolor=LINE, zerolinecolor=LINE_STRONG, tickfont=dict(color=INK_MUTED, size=10)),
    yaxis=dict(gridcolor=LINE, zerolinecolor=LINE_STRONG, tickfont=dict(color=INK_MUTED, size=10)),
    hoverlabel=dict(bgcolor=TILE_BG, bordercolor=LINE_STRONG, font=dict(family=FONT_MONO, color=INK, size=11)),
)

# ---- Altair theme -----------------------------------------------------------
def altair_theme():
    return {
        "config": {
            "background": TILE_BG,
            "font": FONT_SANS,
            "title": {"font": FONT_SANS, "color": INK, "fontSize": 13, "fontWeight": 600},
            "axis": {
                "labelFont": FONT_SANS, "labelColor": INK_MUTED, "labelFontSize": 10,
                "titleFont": FONT_SANS, "titleColor": INK_SECONDARY, "titleFontSize": 11,
                "gridColor": LINE, "domainColor": LINE_STRONG, "tickColor": LINE_STRONG,
            },
            "legend": {
                "labelFont": FONT_SANS, "labelColor": INK_SECONDARY, "labelFontSize": 11,
                "titleFont": FONT_SANS, "titleColor": INK, "orient": "top", "direction": "horizontal",
            },
            "view": {"stroke": "transparent"},
            "range": {"category": list(SERIES.values())},
        }
    }
