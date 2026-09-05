"""Limitations Scorecard — the actual point of this project. Scores each of
the five requirements plus the gaps identified up front, with the workaround
used, what was actually observed, and an honest verdict against Tableau."""

import streamlit as st

st.markdown("## 🧪 Limitations Scorecard — Streamlit vs Tableau")
st.caption(
    "Findings from building the Global FinCorp replica. Verdicts are qualitative "
    "judgment calls made while building this prototype, not a benchmark suite — "
    "re-run the perf panel on the dashboard page yourself for your own numbers."
)

VERDICT_COLOR = {"Strong": "🟢", "Workable": "🟡", "Weak": "🔴"}


def row(title, verdict, workaround, finding, tableau_comparison):
    with st.container(border=True):
        c1, c2 = st.columns([4, 1])
        with c1:
            st.markdown(f"#### {title}")
        with c2:
            st.markdown(f"### {VERDICT_COLOR[verdict]} {verdict}")
        st.markdown(f"**Workaround used:** {workaround}")
        st.markdown(f"**What we found:** {finding}")
        st.markdown(f"**vs Tableau:** {tableau_comparison}")


st.markdown("### The 5 requirements")

row(
    "1. Generate the visuals",
    "Strong",
    "Plotly for cross-filtering charts (combo trend, treemap, waterfall, dept spend), "
    "Altair for lighter declarative tiles (regional margin, cash flow, EBITDA), a hand-rolled "
    "ECharts component for the bullet/gauge and donut tiles.",
    "Every chart type in the source screenshot has a real equivalent. The treemap and waterfall "
    "took no more code than the bar charts — Plotly's chart-type breadth is the pleasant surprise here. "
    "The redesign (bullet instead of gauges, single-hue nested treemap instead of rainbow) was a "
    "deliberate improvement, not a limitation.",
    "Tableau's chart gallery is still broader out of the box (no-code gauges, bullet graphs, box "
    "plots), but Plotly + Altair cover this dashboard's real chart types without a gap.",
)

row(
    "2. Interactive cross-filtering (filter / highlight / drill)",
    "Workable",
    "A single `Selection` object in session_state, written by whichever tile's `on_select` fired, "
    "consumed differently per mode: Filter re-filters the shared data cube (excluding the source "
    "tile), Highlight leaves data intact and drops trace/mark opacity, Drill opens an `st.dialog` "
    "scoped to the clicked entity.",
    "All three modes work and are genuinely useful. The rough edges: Plotly and Altair each have "
    "their own selection-event shape (`points` list vs a dict of field arrays), so the selection "
    "handler is duplicated per chart type rather than one shared function. There's also no equivalent "
    "of Tableau's automatic 'this action only affects these sheets' scoping — it's hand-wired per tile "
    "via the `current_tile` exclusion parameter threaded through every render call.",
    "Tableau's dashboard actions (filter/highlight/URL/parameter) are a declarative UI over the same "
    "idea with no code. This is more code and more moving parts for the same outcome — but it is also "
    "far more flexible per-tile (e.g. the market-share donut deliberately opts out of cross-filtering "
    "because competitor identity isn't a real dimension, which a Tableau action can't express as cleanly).",
)

row(
    "3. Global filters + shareable state",
    "Strong",
    "Sidebar filters + the click-selection both live in `st.session_state` and are mirrored "
    "bidirectionally to `st.query_params` (`src/state.py`), rehydrated before any filter widget "
    "is instantiated.",
    "A filtered, selected view is genuinely copy-paste shareable — paste the URL in a new tab and "
    "the exact state reconstructs. The gotcha: `st.query_params` writes have to happen in a specific "
    "order relative to widget instantiation, or you get a write-then-reread loop that silently resets "
    "state on rerun. Once solved it's solid, but it is not documented as clearly as it should be.",
    "Equivalent capability to a Tableau published-view URL with filter state, achieved with roughly "
    "20 lines of code instead of zero — but with full control over exactly what's encoded.",
)

row(
    "4. Free tile placement",
    "Weak",
    "`st.columns` for structural rows/ratios, `st.container(border=True)` per tile, and an injected "
    "CSS layer (`src/style.css`) that targets Streamlit's internal `data-testid` attributes for tile "
    "chrome, sticky header, and fixed heights.",
    "This gets close to the screenshot's grid, but it is fundamentally a stack of rows, not a true "
    "grid — a tile cannot span two rows, and matching row heights across columns of differing content "
    "requires manually fixing `height=` on every `st.container`, which then clips or wastes space "
    "when content doesn't match. The CSS selectors that make tile chrome look intentional "
    "(`div[data-testid=\"stVerticalBlockBorderWrapper\"]`) are pinned to Streamlit's internal DOM "
    "structure, which is explicitly not a public API and has changed across versions before.",
    "This is the single biggest gap versus Tableau, where dragging a tile to any pixel position or "
    "spanning it across a grid is native. Streamlit's layout primitives are column-and-row only; "
    "a real drag-and-drop canvas would require a third-party grid component (evaluated, not built, "
    "for this prototype — see the note below).",
)

row(
    "5. Bring your own JS chart library",
    "Workable",
    "A zero-build custom component (`src/components/echarts/index.html`) that loads ECharts from a "
    "CDN and implements Streamlit's component postMessage protocol by hand — no npm, no build step, "
    "`declare_component(path=...)` pointed straight at a static HTML file.",
    "It works, including bidirectional click events flowing back into the same selection state as "
    "the native charts. The cost: you're reimplementing plumbing (`streamlit:render`, "
    "`streamlit:setComponentValue`, `streamlit:setFrameHeight`) that a proper component build (React "
    "+ `streamlit-component-lib`) gives you for free, and the component reloads its full HTML/JS on "
    "every Streamlit rerun rather than patching state — noticeably less smooth than the native charts "
    "on rapid filter changes.",
    "Tableau has no equivalent extension point at all for a dashboard author without Tableau "
    "Extensions API + a hosted web app. Streamlit's iframe-component model is more open, just rawer.",
)

st.markdown("### Gaps beyond the 5 — from the up-front risk list")

row(
    "Rerun latency & scale (100k rows)",
    "Workable",
    "A cached `build_cube()` groupby (month x quarter x region x product x department x account, "
    "~3-4k rows) computed once from the raw table; every filter/selection interaction re-filters "
    "that small cube, not the 100k-row source. Row-level tiles (Top Customers, drill-through) filter "
    "the raw frame directly.",
    "Cube-based filtering is sub-millisecond even under the 1M-row stress toggle — the architecture "
    "choice matters more than raw row count. The row-level path (uncached, ~1-5ms at 100k, "
    "measurably more at 1M) is where Streamlit's full-script-rerun model actually costs something: "
    "every click reruns the whole page script, so total time is the sum of every tile's render call, "
    "not just the one that changed. `st.fragment` scoping per-tile is the next lever, not yet applied "
    "here uniformly.",
    "Tableau's extract engine is purpose-built for this and doesn't rerun a whole dashboard script on "
    "every click. At 100k rows the gap is invisible; it will show up first at higher concurrency "
    "(multiple users) rather than higher row counts, since Streamlit reruns are single-session CPU work.",
)

row(
    "URL state sync",
    "Strong",
    "See requirement #3 above — same mechanism.",
    "No gap beyond the ordering subtlety already noted.",
    "On par with a Tableau published view URL.",
)

row(
    "Export: CSV / PNG / PDF",
    "Weak",
    "Per-tile CSV via `st.download_button`; PNG via `kaleido` (Plotly) and `vl-convert-python` "
    "(Altair); whole-dashboard PDF via server-side re-render + `fpdf2` composition.",
    "CSV and single-chart PNG are genuinely solid and fast. Whole-dashboard PDF is the honest failure: "
    "it re-renders figures from scratch server-side rather than capturing the live page, so the two "
    "ECharts tiles (client-side only) and all CSS chrome (tile shadows, chip row, fonts, sticky header) "
    "are simply absent from the output. A faithful whole-page PDF would need a headless-browser "
    "screenshot pipeline (e.g. Playwright) outside Streamlit's own APIs entirely.",
    "Tableau's 'Download as PDF/PowerPoint' captures the actual rendered dashboard, including every "
    "chart type and all formatting, in one click. This is a real, un-worked-around gap.",
)

row(
    "Rich tables & tooltips",
    "Strong",
    "`st.column_config` (`ProgressColumn`, `LineChartColumn`, percent-formatted `NumberColumn`) on "
    "Top Customers; custom `hovertemplate` on every Plotly trace; formatted Altair `tooltip` encodings.",
    "This is close to Tableau-grade out of the box — sparkline columns and progress bars in a "
    "dataframe took a few keyword arguments, not custom rendering code.",
    "On par with Tableau's table formatting for this use case; Tableau still wins on ad-hoc "
    "conditional-formatting rules a business user can set without code.",
)

st.markdown("### Other things worth knowing before committing")

st.markdown(
    """
- **No multi-user / auth / row-level security** was tested here — this prototype is single-session.
  Streamlit Community Cloud and Snowflake-hosted Streamlit have auth primitives; a self-hosted
  deployment does not, out of the box.
- **No live/scheduled data refresh** — this dashboard reads static Parquet. `@st.cache_data(ttl=...)`
  is the standard pattern for a live warehouse connection; not exercised here.
- **Responsive/mobile behavior** was not hardened — the CSS layer assumes a desktop-width viewport,
  consistent with how this style of dense BI grid is used in practice, but it was not tested on a
  narrow screen.
- **Native theming in Streamlit 1.58 is more capable than commonly assumed** — `config.toml`'s
  `theme.chartCategoricalColors` / `chartSequentialColors` / `chartDivergingColors` and per-sidebar
  theme overrides did real work here, reducing how much of this app depends on the injected CSS layer
  (which is the fragile part, per requirement #4 above).
    """
)
