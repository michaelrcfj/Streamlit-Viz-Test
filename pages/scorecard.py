"""Limitations Scorecard — the actual point of this project. A traffic-light
summary up top, then a collapsed-by-default detail per item below."""

import streamlit as st

st.markdown("## 🧪 Limitations Scorecard — Streamlit vs Tableau")
st.caption(
    "Findings from building the Global FinCorp replica. Verdicts are judgment calls "
    "made while building this prototype, not a benchmark suite."
)

VERDICT_COLOR = {"Strong": "🟢", "Workable": "🟡", "Weak": "🔴"}

ITEMS = [
    dict(
        group="The 5 requirements", title="1. Generate the visuals", verdict="Strong",
        summary="Plotly + Altair + ECharts cover every chart type in the source screenshot with no gaps.",
        workaround="Plotly for cross-filtering charts, Altair for lighter declarative tiles, a hand-rolled ECharts component for the bullet/gauge and donut.",
        finding="The treemap and waterfall took no more code than a bar chart — Plotly's breadth is the pleasant surprise. The bullet-instead-of-gauges and single-hue treemap redesigns are improvements, not workarounds.",
        tableau="Tableau's gallery is still broader out of the box (no-code gauges, box plots), but nothing here was actually missing.",
    ),
    dict(
        group="The 5 requirements", title="2. Interactive cross-filtering", verdict="Strong",
        summary="Click-to-filter is instant and flicker-free, with the clicked mark visibly highlighted — but getting there took two hard-won bugs and a non-obvious targeted-rerun design.",
        workaround="One `Selection` object in session_state, written by a real `on_select`/`on_change` **callback** (not the old on_select=\"rerun\" + read-every-run pattern) on whichever tile's chart fired; every other tile re-filters by it, excluding the source tile so it keeps its own context. The callback finishes with `st.rerun(scope=DEPENDENT_FRAGMENTS)` — Streamlit 1.63's targeted multi-fragment rerun — which redraws exactly the tiles whose content depends on filters/selection, not the whole page.",
        finding="**Historical bug 1 (sticky selection):** the old on_select=\"rerun\" mode returns a value that stays sticky across every later rerun, so reacting to it needed a `consume_once()` guard to avoid re-firing forever. A genuine `on_change` callback fires exactly once per real value change, so this workaround is gone entirely now. **Historical bug 2 (self-restyle wipes selection):** a chart that restyled its own bars based on the selection it had just emitted changed its own figure enough to make Streamlit remount the widget mid-flow, wiping the very selection it just set. The fix isn't to work around that — it's to never need it: Plotly and Vega-Lite both highlight whatever was just clicked entirely client-side (Plotly by default once `selection_mode` is set, Altair via an `opacity=alt.condition(click, ...)` encoding), so the chart's spec never has to vary with backend selection state at all. That leaves one subtler problem: a tile's own native highlight is purely client-side, so it doesn't know when some *other* tile takes over the active selection and would otherwise keep glowing after it's gone stale. Fixed by busting that one chart's widget key — forcing a fresh, unselected mount — exactly when `selection.source` names a different tile; the currently-active tile keeps a stable key throughout, which is what lets its own just-set highlight survive the rerun.",
        tableau="Tableau's dashboard actions are declarative with no equivalent ordering trap. This is now on par in feel (instant, highlighted, no flicker) but at real engineering cost: the targeted-rerun + native-highlight + key-busting design took real debugging to get right, not a config toggle.",
    ),
    dict(
        group="The 5 requirements", title="3. Global filters + shareable URL", verdict="Strong",
        summary="Sidebar filters and chart selection both sync to the URL — genuinely copy-paste shareable.",
        workaround="Filters + selection live in `st.session_state`, mirrored to `st.query_params`, rehydrated before widgets are instantiated.",
        finding="Solid once built, but `st.query_params` writes must happen in a specific order relative to widget creation or you get a silent reset loop — not well documented.",
        tableau="On par with a Tableau published-view URL, at the cost of ~20 lines of code instead of zero.",
    ),
    dict(
        group="The 5 requirements", title="4. Free tile placement", verdict="Weak",
        summary="Row/column layout only — no true grid, no spanning, and the chrome CSS is pinned to unstable internals.",
        workaround="`st.columns` for structure, `st.container(border=True)` per tile, an injected CSS layer for chrome and fixed heights.",
        finding="Close to the screenshot visually, but a tile can't span rows, and the CSS selectors that make tile chrome look intentional target Streamlit's internal DOM, which isn't a public API.",
        tableau="The single biggest gap — Tableau's drag-to-any-pixel canvas has no real equivalent here short of a third-party grid component.",
    ),
    dict(
        group="The 5 requirements", title="5. Bring your own JS chart library", verdict="Workable",
        summary="A hand-rolled ECharts component works end-to-end, including clicks flowing into the same selection state as native charts.",
        workaround="Zero-build custom component (`src/components/echarts/index.html`) loading ECharts from a CDN, speaking Streamlit's postMessage protocol by hand.",
        finding="Works, but reimplements plumbing a proper React + `streamlit-component-lib` build gives for free, and reloads its full HTML/JS on every rerun rather than patching state.",
        tableau="Tableau has no real equivalent extension point for a dashboard author without its separate Extensions API.",
    ),
    dict(
        group="Gaps beyond the 5", title="Rerun latency & scale (100k rows)", verdict="Strong",
        summary="A small pre-aggregated cube keeps filtering sub-millisecond even at 1M rows, and every filter/selection-dependent piece of UI is its own `@st.fragment` — a click or filter change now redraws only what actually needs to change, nothing else even blinks.",
        workaround="A cached `build_cube()` groupby (~3-4k rows) computed once; every interaction re-filters that small cube. Every tile, the KPI strip, the header/chip row, and even the sidebar filters themselves are `@st.fragment`-wrapped and keyed; every state-mutating callback ends by calling `st.rerun(scope=DEPENDENT_FRAGMENTS)` (Streamlit 1.63's targeted multi-fragment rerun) instead of a bare `st.rerun()`.",
        finding="Cube filtering was sub-ms even in a 1M-row ad hoc test — the real cost was always that every click reran the *whole* page script, tearing down and reloading all 10 tiles (visible as a gray-skeleton flash on every one) before repainting. Targeted multi-fragment reruns eliminate that outright: nothing outside the named fragments is ever torn down, so there's nothing to reload. The catch is that a fragment invoked this way is NOT the result of the enclosing script re-running — Streamlit re-invokes each fragment's stored closure directly — so any fragment that read filters/selection from a variable computed earlier in the script would silently render stale data the first time a *different* fragment's click was what triggered the rerun. Every fragment here reads `S.get_filters()`/`S.get_selection()` fresh instead. The other trap: the sidebar's own filter widgets live outside any fragment, so `st.session_state` mutated from a DIFFERENT callback (e.g. \"Clear all filters\") committed correctly server-side (the URL updated) while the widgets kept showing their old values, until the sidebar itself was made a fragment and added to the same rerun scope.",
        tableau="Tableau's extract engine doesn't rerun a whole dashboard per click; targeted fragment reruns now close that gap in user-visible behavior, though it took materially more design work here than Tableau's declarative dashboard actions to get every dependent piece of UI correctly listed and self-contained.",
    ),
    dict(
        group="Gaps beyond the 5", title="URL state sync", verdict="Strong",
        summary="Same mechanism as requirement #3 — no additional gap.",
        workaround="See requirement #3.",
        finding="No gap beyond the ordering subtlety already noted there.",
        tableau="On par with a Tableau published view URL.",
    ),
    dict(
        group="Gaps beyond the 5", title="Export: CSV / PNG / PDF", verdict="Weak",
        summary="CSV and chart PNG are solid; whole-dashboard PDF is an honest failure that misses the ECharts tiles and all CSS chrome.",
        workaround="Per-tile CSV; PNG via `kaleido`/`vl-convert`; whole-dashboard PDF via server-side re-render + `fpdf2`.",
        finding="The PDF path re-renders figures from scratch rather than capturing the live page — a faithful version would need a headless-browser screenshot pipeline outside Streamlit entirely.",
        tableau="Tableau's one-click PDF/PowerPoint export captures everything. This is a real, un-worked-around gap.",
    ),
    dict(
        group="Gaps beyond the 5", title="Rich tables & tooltips", verdict="Strong",
        summary="`column_config` gets sparklines and progress bars for a few keyword arguments — close to Tableau-grade for free.",
        workaround="`st.column_config` (`ProgressColumn`, `LineChartColumn`) plus custom Plotly/Altair tooltips.",
        finding="No real gap for this use case.",
        tableau="On par; Tableau still wins on ad-hoc conditional formatting a business user can set without code.",
    ),
]

# ---- Summary: traffic lights -------------------------------------------------
counts = {"Strong": 0, "Workable": 0, "Weak": 0}
for it in ITEMS:
    counts[it["verdict"]] += 1
st.markdown(
    f"**{counts['Strong']} 🟢 Strong · {counts['Workable']} 🟡 Workable · {counts['Weak']} 🔴 Weak** "
    "— expand any row under Detail below for the full write-up."
)

cols = st.columns(3)
for i, it in enumerate(ITEMS):
    with cols[i % 3]:
        with st.container(border=True):
            st.markdown(f"{VERDICT_COLOR[it['verdict']]} **{it['title']}**")
            st.caption(it["summary"])

st.divider()

# ---- Detail, collapsed by default --------------------------------------------
st.markdown("### Detail")
current_group = None
for it in ITEMS:
    if it["group"] != current_group:
        current_group = it["group"]
        st.markdown(f"**{current_group}**")
    with st.expander(f"{VERDICT_COLOR[it['verdict']]} {it['title']}"):
        st.markdown(f"**Workaround:** {it['workaround']}")
        st.markdown(f"**Finding:** {it['finding']}")
        st.markdown(f"**vs Tableau:** {it['tableau']}")

st.markdown("### Other things worth knowing before committing")
st.markdown(
    """
- **No multi-user / auth / row-level security** tested — this is single-session.
- **No live/scheduled data refresh** — reads static Parquet; `@st.cache_data(ttl=...)` is the standard pattern for a live warehouse, not exercised here.
- **Responsive/mobile** not hardened — the CSS assumes a desktop-width dense BI grid.
- **Streamlit's native theming is more capable than commonly assumed** — `config.toml`'s categorical/sequential/diverging chart colors and per-sidebar overrides did real work, reducing reliance on the injected CSS layer (the fragile part, per #4 above).
- **Running Streamlit 1.63.** Upgraded from 1.58 specifically for `st.rerun(scope=[...])`'s targeted multi-fragment reruns (see "Rerun latency & scale" above) — that one capability drove most of the interaction-layer rewrite.
"""
)
