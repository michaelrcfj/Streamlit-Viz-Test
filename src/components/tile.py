"""Tile chrome helper: consistent header + CSS marker used by style.css to
target the enclosing bordered container."""

from contextlib import contextmanager

import streamlit as st

from src import theme as T


@contextmanager
def tile(title: str, icon: str = "", height: int | None = None, key: str | None = None):
    """Wraps content in a bordered container with a consistent tile header.
    The invisible marker div lets style.css select the *enclosing*
    st.container(border=True) via :has() without touching every bordered
    container app-wide (sidebar widgets, dialogs, etc. stay unaffected).

    Defaults to T.TILE_HEIGHT so every tile in a grid row lands at the same
    height without having to pass it at every call site — pass an explicit
    height (or 0) only for a tile that deliberately needs to differ."""
    with st.container(border=True, height=height or T.TILE_HEIGHT, key=key):
        st.markdown(
            f'<div class="gfc-tile-marker" style="display:none"></div>'
            f'<div class="gfc-tile-title"><span class="gfc-icon">{icon}</span>{title}</div>',
            unsafe_allow_html=True,
        )
        yield
