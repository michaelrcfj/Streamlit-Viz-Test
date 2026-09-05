"""CSV / PNG / whole-dashboard PDF export.

Honest limitation, stated up front (also on the Limitations Scorecard): the
PDF path re-renders each Plotly/Altair figure server-side via kaleido /
vl-convert and composes them with fpdf2. It is a re-render, not a capture of
the live DOM — the two ECharts tiles (which run entirely client-side in a
component iframe) and all CSS chrome (tile shadows, chip row, fonts) are
NOT reproducible this way and are visibly absent from the PDF.
"""

import io

import pandas as pd
import plotly.graph_objects as go
from fpdf import FPDF

from src import theme as T


def csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def plotly_png_bytes(fig: go.Figure, width=900, height=500, scale=2) -> bytes:
    return fig.to_image(format="png", width=width, height=height, scale=scale)


def altair_png_bytes(chart) -> bytes:
    import vl_convert as vlc
    spec = chart.to_dict()
    return vlc.vegalite_to_png(spec, scale=2)


def build_dashboard_pdf(title: str, subtitle: str, kpi_lines: list[str], images: list[tuple[str, bytes]]) -> bytes:
    """images: list of (tile_title, png_bytes). Renders a simple grid PDF."""
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(26, 26, 23)
    pdf.cell(0, 10, title, ln=1)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(107, 103, 96)
    pdf.cell(0, 6, subtitle, ln=1)
    pdf.ln(2)

    pdf.set_font("Courier", "B", 11)
    pdf.set_text_color(26, 26, 23)
    col_w = (297 - 20) / max(len(kpi_lines), 1)
    for line in kpi_lines:
        pdf.cell(col_w, 8, line, border=0)
    pdf.ln(12)

    x0, y0 = pdf.get_x(), pdf.get_y()
    col = 0
    ncols = 3
    tile_w = (297 - 20) / ncols
    tile_h = 70
    for i, (tile_title, png) in enumerate(images):
        col = i % ncols
        row = i // ncols
        x = 10 + col * tile_w
        y = y0 + row * (tile_h + 8)
        if y + tile_h > 190:
            pdf.add_page()
            y0 = pdf.get_y()
            y = y0 + (row % 1) * (tile_h + 8)
        pdf.set_xy(x, y)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(26, 26, 23)
        pdf.cell(tile_w - 4, 5, tile_title, ln=0)
        img_stream = io.BytesIO(png)
        pdf.image(img_stream, x=x, y=y + 6, w=tile_w - 4)

    return bytes(pdf.output())
