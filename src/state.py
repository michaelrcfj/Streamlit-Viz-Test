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


def consume_once(tile_key: str, payload) -> bool:
    """Returns True the first time `payload` is seen for this tile_key, False
    on every subsequent rerun with the same payload.

    Plotly/Altair/component selection state is STICKY — it persists as the
    widget's current value across reruns until the user changes it, so a
    chart's on_select handler runs on *every* script execution, not just the
    one right after a click. Without this guard, reacting to that value
    (calling st.rerun(), opening a dialog) would refire on every unrelated
    rerun, either looping forever or re-opening a dialog the user just
    closed. This makes reacting to a selection idempotent per distinct value.
    """
    marker_key = f"_consumed_{tile_key}"
    key_repr = repr(payload)
    if st.session_state.get(marker_key) == key_repr:
        return False
    st.session_state[marker_key] = key_repr
    return True


def set_selection_if_changed(dim: str, values: list, source: str) -> bool:
    """Updates the selection and returns True only if it actually changed
    vs. the current one — use this + st.rerun() so a click propagates to
    every other tile on the SAME interaction, without looping once the
    state has settled (see consume_once for why that matters)."""
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
