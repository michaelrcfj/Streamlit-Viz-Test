"""Zero-build ECharts custom component — python side. Declares the component
against the local index.html (loads ECharts from a CDN, speaks the Streamlit
postMessage protocol by hand; see index.html's docstring)."""

from pathlib import Path

import streamlit.components.v1 as components

from src import theme as T

_COMPONENT_DIR = Path(__file__).resolve().parent

_echarts_component = components.declare_component("gfc_echarts", path=str(_COMPONENT_DIR))

_THEME_PROPS = {
    "fontSans": T.FONT_SANS,
    "fontMono": T.FONT_MONO,
    "ink": T.INK,
    "inkSecondary": T.INK_SECONDARY,
    "inkMuted": T.INK_MUTED,
    "line": T.LINE,
    "lineStrong": T.LINE_STRONG,
    "tileBg": T.TILE_BG,
    "accent": T.ACCENT,
    "critical": T.CRITICAL,
}


def echarts_donut(data: list[dict], colors: list[str], series_name: str = "Share",
                   clickable: bool = True, key: str | None = None, height: int = 260):
    """data: [{"name": str, "value": float}, ...]"""
    return _echarts_component(
        kind="donut", data=data, colors=colors, seriesName=series_name, height=height,
        clickable=clickable, theme=_THEME_PROPS, key=key, default=None,
    )


def echarts_bullet(categories: list[str], actual: list[float], budget: list[float],
                    over_budget: list[bool], clickable: bool = True,
                    key: str | None = None, height: int = 260):
    return _echarts_component(
        kind="bullet", categories=categories, actual=actual, budget=budget, height=height,
        overBudget=over_budget, clickable=clickable, theme=_THEME_PROPS, key=key, default=None,
    )


def echarts_gauges(gauges: list[dict], key: str | None = None, height: int = 200):
    """gauges: [{"name": str, "value": float, "color": str}, ...]"""
    return _echarts_component(
        kind="gauge", gauges=gauges, height=height, clickable=False, theme=_THEME_PROPS, key=key, default=None,
    )
