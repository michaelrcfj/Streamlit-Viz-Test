"""
Global filter state, chart-driven selection state, and interaction mode —
all mirrored to st.query_params so a filtered/selected view is copy-paste
shareable, like a Tableau URL.

Ordering matters here (this is the trap requirement #3 runs into):
  1. bootstrap() reads query params into session_state ONCE, before any
     widget with those keys is instantiated.
  2. Widgets are instantiated with those session_state values as defaults.
  3. sync_url() is called at the END of the script run to write the current
     session_state back to query_params — after widgets may have changed it.
This avoids the write-then-immediately-reread loop that fights Streamlit's
widget/session_state binding.
"""

import json
from dataclasses import dataclass, field, asdict
from typing import Optional

import streamlit as st

FILTER_DIMENSIONS = ["region", "product", "department"]

DEFAULTS = {
    "f_region": [],
    "f_product": [],
    "f_department": [],
    "f_period": "All",
    "f_compare": "Target",
    "sel_dim": None,
    "sel_values": [],
    "sel_source": None,
}


def _encode(value):
    if isinstance(value, list):
        return ",".join(value) if value else ""
    return "" if value is None else str(value)


def _decode_list(raw: str):
    return [v for v in raw.split(",") if v] if raw else []


def bootstrap():
    """Read query params into session_state, once per session."""
    if st.session_state.get("_bootstrapped"):
        return
    qp = st.query_params
    st.session_state["f_region"] = _decode_list(qp.get("region", ""))
    st.session_state["f_product"] = _decode_list(qp.get("product", ""))
    st.session_state["f_department"] = _decode_list(qp.get("department", ""))
    st.session_state["f_period"] = qp.get("period", DEFAULTS["f_period"])
    st.session_state["f_compare"] = qp.get("compare", DEFAULTS["f_compare"])
    sel_dim = qp.get("sel_dim", "")
    st.session_state["sel_dim"] = sel_dim or None
    st.session_state["sel_values"] = _decode_list(qp.get("sel_values", ""))
    sel_source = qp.get("sel_source", "")
    st.session_state["sel_source"] = sel_source or None
    st.session_state["_bootstrapped"] = True


def sync_url():
    """Write current session_state back to query_params."""
    qp = st.query_params
    qp["region"] = _encode(st.session_state.get("f_region", []))
    qp["product"] = _encode(st.session_state.get("f_product", []))
    qp["department"] = _encode(st.session_state.get("f_department", []))
    qp["period"] = _encode(st.session_state.get("f_period", "All"))
    qp["compare"] = _encode(st.session_state.get("f_compare", "Target"))
    if st.session_state.get("sel_dim"):
        qp["sel_dim"] = st.session_state["sel_dim"]
        qp["sel_values"] = _encode(st.session_state.get("sel_values", []))
        qp["sel_source"] = st.session_state.get("sel_source", "") or ""
    else:
        for k in ("sel_dim", "sel_values", "sel_source"):
            if k in qp:
                del qp[k]
    # Drop empty keys to keep the URL tidy.
    for k in ("region", "product", "department"):
        if qp.get(k) == "":
            del qp[k]
    if qp.get("period") == "All":
        del qp["period"]


@dataclass
class Selection:
    dim: Optional[str] = None       # "region" | "product" | "department" | "customer"
    values: list = field(default_factory=list)
    source: Optional[str] = None    # tile key that produced this selection

    @property
    def active(self) -> bool:
        return bool(self.dim and self.values)


def get_filters() -> dict:
    return {
        "region": st.session_state.get("f_region", []),
        "product": st.session_state.get("f_product", []),
        "department": st.session_state.get("f_department", []),
        "period": st.session_state.get("f_period", "All"),
        "compare": st.session_state.get("f_compare", "Target"),
    }


def get_selection() -> Selection:
    return Selection(
        dim=st.session_state.get("sel_dim"),
        values=st.session_state.get("sel_values", []),
        source=st.session_state.get("sel_source"),
    )


def set_selection(dim: str, values: list, source: str):
    st.session_state["sel_dim"] = dim
    st.session_state["sel_values"] = values
    st.session_state["sel_source"] = source


def clear_selection():
    st.session_state["sel_dim"] = None
    st.session_state["sel_values"] = []
    st.session_state["sel_source"] = None


def set_selection_if_changed(dim: str, values: list, source: str) -> bool:
    """Updates the selection and returns True only if it actually changed
    vs. the current one."""
    values = sorted(values)
    current = get_selection()
    if current.dim == dim and sorted(current.values) == values and current.source == source:
        return False
    set_selection(dim, values, source)
    return True


def clear_selection_if_owned_by(source: str) -> bool:
    """Clears the selection only if `source` is the tile that owns it, and
    only if there is one to clear. Used when a chart's selection goes empty
    (e.g. the user clicked the already-selected mark to deselect it)."""
    current = get_selection()
    if current.active and current.source == source:
        clear_selection()
        return True
    return False


# ---- Fragment-targeted reruns -------------------------------------------------
#
# Every fragment below is defined in pages/dashboard.py with a `key=` matching
# one of these strings. All of them read filters/selection fresh from
# session_state on every render (never from a stale closure), so a targeted
# `st.rerun(scope=DEPENDENT_FRAGMENTS)` re-renders exactly the tiles whose
# content actually depends on filters/selection -- not the whole page. This is
# what fixes the "whole dashboard disappears for a second" flash a plain
# st.rerun() (full app scope) causes: elements outside the named fragments
# are never torn down in the first place, so there's nothing to reload.
#
# "sidebar_filters" is here even though a filter widget's own value change
# already updates its own display optimistically client-side: a widget's
# value can also change from a DIFFERENT fragment (apply_clear_all_filters
# resets f_region/f_product/f_department/f_period programmatically), and
# without the sidebar in scope that widget's displayed value would stay
# stuck on its old value until some future full-app rerun caught it up.
#
# "tile_cashflow" is in the list now: cash flow used to read its own static
# table and ignore the filters entirely, but it's derived from the same fact
# rows as everything else (metrics.cash_flow_by_month), so it moves with them.
DEPENDENT_FRAGMENTS = [
    "sidebar_filters", "kpi_strip", "chips",
    "tile_trend", "tile_regional_margin", "tile_expense_bullet", "tile_treemap",
    "tile_waterfall", "tile_dept_spend", "tile_top_customers", "tile_market_share", "tile_cashflow",
    "perf_and_export",
]


def _refresh():
    """Every state-mutating callback ends with this: sync the URL to the
    just-changed session_state, then rerun only the fragments that depend on
    it. Must be called from a genuine widget callback (on_change/on_click) --
    st.rerun() with an explicit fragment scope raises outside of one."""
    sync_url()
    st.rerun(scope=DEPENDENT_FRAGMENTS)


def apply_selection(dim: str, values: list, source: str):
    """on_select callback body for a click-to-filter chart: commit the new
    selection and, if it actually changed, refresh every dependent tile."""
    if set_selection_if_changed(dim, values, source):
        _refresh()


def apply_selection_clear(source: str):
    """on_select callback body for a chart's selection going empty (e.g. the
    user clicked the already-selected mark to deselect it)."""
    if clear_selection_if_owned_by(source):
        _refresh()


def apply_reset_selection():
    """on_click callback for the header's "Reset selection" button."""
    clear_selection()
    _refresh()


def apply_filters_changed():
    """on_change callback for every sidebar filter widget. The widget's own
    `key=` binding already updated session_state by the time this runs --
    this just propagates that to the tiles that depend on it."""
    _refresh()


def chart_widget_key(tile_key: str) -> str:
    """The key a click-to-filter chart should register its widget under.

    Native chart libraries (Plotly, Vega-Lite/Altair) highlight whatever the
    user last clicked entirely client-side, and that highlight survives a
    rerun for free as long as the widget keeps the same key -- which is
    exactly what we want while this tile still owns the active selection (or
    nothing is selected yet): it's what makes the click-to-filter feel
    instant.

    But once some OTHER tile takes over the active selection, this tile's
    own chart is never told to clear its stale highlight -- it just keeps
    showing whatever was last clicked here, which now has nothing to do with
    the active filter. Busting the key exactly then forces a fresh mount
    (clearing that stale highlight) without ever touching the tile that IS
    currently selecting, so it can't reintroduce the self-restyle-wipes-
    selection bug that owning tile has to avoid (see trend.py)."""
    source = get_selection().source
    if source in (None, tile_key):
        return tile_key
    return f"{tile_key}__inactive_{source}"


def apply_clear_all_filters():
    """on_click callback for the sidebar's "Clear all filters" button."""
    for dim in ("f_region", "f_product", "f_department"):
        st.session_state[dim] = []
    st.session_state["f_period"] = "All"
    clear_selection()
    _refresh()


def active_filter_chips() -> list[tuple[str, str]]:
    """Returns (label, kind) pairs for the active-filters chip row."""
    chips = []
    f = get_filters()
    for dim in ("region", "product", "department"):
        for v in f[dim]:
            chips.append((f"{dim.title()}: {v}", "filter"))
    if f["period"] != "All":
        chips.append((f"Period: {f['period']}", "filter"))
    sel = get_selection()
    if sel.active:
        chips.append((f"{sel.dim.title()}: {', '.join(sel.values)} (from {sel.source})", "selection"))
    return chips
