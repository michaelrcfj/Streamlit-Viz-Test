"""Tile chrome helper: consistent header + CSS marker used by style.css to
target the enclosing bordered container."""

from contextlib import contextmanager

import streamlit as st


@contextmanager
def tile(title: str, icon: str = "", height: int | None = None, key: str | None = None):
    """Wraps content in a bordered container with a consistent tile header.
    The invisible marker div lets style.css select the *enclosing*
    st.container(border=True) via :has() without touching every bordered
    container app-wide (sidebar widgets, dialogs, etc. stay unaffected)."""
    with st.container(border=True, height=height or "content", key=key):
        st.markdown(
            f'<div class="gfc-tile-marker" style="display:none"></div>'
            f'<div class="gfc-tile-title"><span class="gfc-icon">{icon}</span>{title}</div>',
            unsafe_allow_html=True,
        )
        yield
