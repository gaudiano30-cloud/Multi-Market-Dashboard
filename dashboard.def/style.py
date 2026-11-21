"""Visual identity of the platform. No application logic lives here.

Palette taken from the MFE / Università Cattolica banner: deep navy base,
gold accents, cold blue for data. Changing the look of the whole dashboard
means editing this file only.
"""

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------

COLORS = {
    "bg": "#07192f",            # page background, navy not black
    "bg_panel": "#0e2745",      # cards and panels
    "bg_panel_alt": "#13304f",  # hover / alternate rows
    "border": "#1d4068",
    "gold": "#c9a227",          # Cattolica gold, used for accents only
    "gold_soft": "#e0bf5a",
    "text": "#e8eef6",
    "text_muted": "#8da5c0",
    "positive": "#2ecc8f",
    "negative": "#ff5a5f",
    "accent": "#4da3ff",
}

# Ordered series colours for multi-line charts.
SERIES = ["#4da3ff", "#c9a227", "#2ecc8f", "#ff8a5a", "#b07cff",
          "#49d6d6", "#ff5a5f", "#9aa7b8"]

FONT_STACK = "'IBM Plex Sans', 'Segoe UI', system-ui, sans-serif"
MONO_STACK = "'IBM Plex Mono', 'Consolas', monospace"


# ---------------------------------------------------------------------------
# Layout blocks
# ---------------------------------------------------------------------------

PAGE = {
    "backgroundColor": COLORS["bg"],
    "color": COLORS["text"],
    "fontFamily": FONT_STACK,
    "minHeight": "100vh",
    "padding": "0 0 48px 0",
}

HEADER = {
    "display": "flex",
    "alignItems": "center",
    "gap": "18px",
    "padding": "16px 32px",
    "background": f"linear-gradient(90deg, {COLORS['bg_panel']} 0%, #081f3a 60%, {COLORS['bg']} 100%)",
    "borderBottom": f"2px solid {COLORS['gold']}",
}

LOGO = {"height": "46px", "width": "auto"}

TITLE = {
    "margin": 0,
    "fontSize": "20px",
    "fontWeight": 600,
    "letterSpacing": "0.5px",
}

SUBTITLE = {
    "margin": 0,
    "fontSize": "11px",
    "color": COLORS["gold_soft"],
    "letterSpacing": "1.6px",
    "textTransform": "uppercase",
}

STATUS_BAR = {
    "marginLeft": "auto",
    "fontFamily": MONO_STACK,
    "fontSize": "11px",
    "color": COLORS["text_muted"],
    "textAlign": "right",
}

CONTAINER = {"maxWidth": "1320px", "margin": "0 auto", "padding": "24px 32px"}

# The small clickable rectangle at the top left.
NAV_CHIP = {
    "minWidth": "230px",
    "border": f"1px solid {COLORS['gold']}",
    "borderRadius": "3px",
    "backgroundColor": COLORS["bg_panel"],
}

NAV_CHIP_LABEL = {
    "fontSize": "10px",
    "letterSpacing": "1.4px",
    "textTransform": "uppercase",
    "color": COLORS["gold_soft"],
    "marginBottom": "6px",
    "display": "block",
}

TOOLBAR = {
    "display": "flex",
    "gap": "20px",
    "flexWrap": "wrap",
    "alignItems": "flex-end",
    "marginBottom": "22px",
}

PANEL = {
    "backgroundColor": COLORS["bg_panel"],
    "border": f"1px solid {COLORS['border']}",
    "borderRadius": "4px",
    "padding": "18px 20px",
    "marginBottom": "20px",
}

PANEL_TITLE = {
    "margin": "0 0 14px 0",
    "fontSize": "12px",
    "letterSpacing": "1.4px",
    "textTransform": "uppercase",
    "color": COLORS["gold_soft"],
    "borderLeft": f"3px solid {COLORS['gold']}",
    "paddingLeft": "10px",
}

BREADCRUMB = {
    "fontFamily": MONO_STACK,
    "fontSize": "12px",
    "color": COLORS["text_muted"],
    "marginBottom": "16px",
}

BACK_BUTTON = {
    "backgroundColor": "transparent",
    "color": COLORS["gold_soft"],
    "border": f"1px solid {COLORS['border']}",
    "borderRadius": "3px",
    "padding": "6px 14px",
    "fontSize": "12px",
    "cursor": "pointer",
    "fontFamily": FONT_STACK,
}

CONTINENT_BUTTON = {
    "backgroundColor": COLORS["bg_panel_alt"],
    "color": COLORS["text"],
    "border": f"1px solid {COLORS['border']}",
    "borderRadius": "3px",
    "padding": "7px 16px",
    "marginRight": "8px",
    "fontSize": "12px",
    "cursor": "pointer",
    "fontFamily": FONT_STACK,
}

CONTINENT_BUTTON_ACTIVE = {
    **CONTINENT_BUTTON,
    "backgroundColor": COLORS["gold"],
    "color": "#0a1b30",
    "fontWeight": 600,
    "border": f"1px solid {COLORS['gold']}",
}

EMPTY_STATE = {
    "color": COLORS["text_muted"],
    "fontSize": "14px",
    "padding": "28px",
    "textAlign": "center",
    "border": f"1px dashed {COLORS['border']}",
    "borderRadius": "4px",
}

# Key-figure tiles.
TILE_ROW = {"display": "flex", "gap": "14px", "flexWrap": "wrap"}

TILE = {
    "flex": "1 1 170px",
    "backgroundColor": COLORS["bg_panel_alt"],
    "border": f"1px solid {COLORS['border']}",
    "borderLeft": f"3px solid {COLORS['gold']}",
    "borderRadius": "3px",
    "padding": "12px 14px",
}

TILE_LABEL = {
    "fontSize": "10px",
    "letterSpacing": "1.1px",
    "textTransform": "uppercase",
    "color": COLORS["text_muted"],
}

TILE_VALUE = {"fontFamily": MONO_STACK, "fontSize": "19px", "marginTop": "4px"}

# Data tables.
TABLE_CELL = {
    "backgroundColor": COLORS["bg_panel"],
    "color": COLORS["text"],
    "border": f"1px solid {COLORS['border']}",
    "fontFamily": MONO_STACK,
    "fontSize": "12px",
    "padding": "8px 10px",
    "textAlign": "right",
}

TABLE_CELL_LEFT = {"if": {"column_id": "Strumento"}, "textAlign": "left",
                   "fontFamily": FONT_STACK}

TABLE_HEADER = {
    "backgroundColor": "#0a2039",
    "color": COLORS["gold_soft"],
    "border": f"1px solid {COLORS['border']}",
    "fontFamily": FONT_STACK,
    "fontSize": "11px",
    "letterSpacing": "0.8px",
    "textTransform": "uppercase",
    "fontWeight": 600,
    "textAlign": "right",
}


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

def style_figure(figure, height: int = 380, show_legend: bool = True):
    """Apply the house style to any Plotly figure. Called on every chart."""
    figure.update_layout(
        template="plotly_dark",
        paper_bgcolor=COLORS["bg_panel"],
        plot_bgcolor=COLORS["bg_panel"],
        font={"family": FONT_STACK, "color": COLORS["text"], "size": 12},
        margin={"l": 54, "r": 24, "t": 28, "b": 40},
        height=height,
        showlegend=show_legend,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02,
                "x": 0, "title": None, "font": {"size": 11}},
        hoverlabel={"bgcolor": "#0a2039", "font_size": 12,
                    "font_family": MONO_STACK},
        colorway=SERIES,
    )
    figure.update_xaxes(gridcolor=COLORS["border"], zeroline=False,
                        linecolor=COLORS["border"], title=None)
    figure.update_yaxes(gridcolor=COLORS["border"], zeroline=False,
                        linecolor=COLORS["border"], title=None)
    return figure


def style_map(figure, scope: str = "world"):
    """Styling specific to the geographic navigation map."""
    figure.update_layout(
        paper_bgcolor=COLORS["bg_panel"],
        font={"family": FONT_STACK, "color": COLORS["text"]},
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        height=420,
        showlegend=False,
        geo={
            "scope": scope,
            "projection_type": "natural earth" if scope == "world" else "mercator",
            "bgcolor": COLORS["bg_panel"],
            "landcolor": "#102c4a",
            "oceancolor": COLORS["bg_panel"],
            "showocean": True,
            "lakecolor": COLORS["bg_panel"],
            "coastlinecolor": COLORS["border"],
            "countrycolor": "#1b3c60",
            "showcountries": True,
            "showframe": False,
        },
    )
    return figure


# ---------------------------------------------------------------------------
# CSS that inline styles cannot reach (dropdown internals, scrollbars)
# ---------------------------------------------------------------------------

CSS = f"""
body {{ margin: 0; background-color: {COLORS['bg']}; }}

/* Dropdown closed state */
.Select-control, .Select--single > .Select-control {{
    background-color: {COLORS['bg_panel']} !important;
    border: 1px solid {COLORS['border']} !important;
    border-radius: 3px !important;
    color: {COLORS['text']} !important;
}}
.Select-value-label, .Select-placeholder, .Select--single > .Select-control
.Select-value .Select-value-label {{
    color: {COLORS['text']} !important;
}}
.Select-input > input {{ color: {COLORS['text']} !important; }}
.Select-arrow {{ border-color: {COLORS['gold']} transparent transparent !important; }}

/* Dropdown open state */
.Select-menu-outer {{
    background-color: {COLORS['bg_panel']} !important;
    border: 1px solid {COLORS['border']} !important;
    color: {COLORS['text']} !important;
}}
.VirtualizedSelectOption, .Select-option {{
    background-color: {COLORS['bg_panel']} !important;
    color: {COLORS['text']} !important;
}}
.VirtualizedSelectFocusedOption, .Select-option.is-focused {{
    background-color: {COLORS['bg_panel_alt']} !important;
    color: {COLORS['gold_soft']} !important;
}}

/* Tabs */
.custom-tabs {{ border-bottom: 1px solid {COLORS['border']} !important; }}
.custom-tab {{
    background-color: transparent !important;
    border: none !important;
    color: {COLORS['text_muted']} !important;
    font-size: 12px !important;
    letter-spacing: 1px !important;
    text-transform: uppercase !important;
    padding: 12px 20px !important;
}}
.custom-tab--selected {{
    color: {COLORS['gold_soft']} !important;
    border-bottom: 2px solid {COLORS['gold']} !important;
}}

/* Date picker */
.DateInput_input, .DateRangePickerInput {{
    background-color: {COLORS['bg_panel']} !important;
    color: {COLORS['text']} !important;
    border-color: {COLORS['border']} !important;
    font-size: 13px !important;
}}
.DateRangePickerInput_arrow_svg {{ fill: {COLORS['gold']} !important; }}

::-webkit-scrollbar {{ width: 10px; height: 10px; }}
::-webkit-scrollbar-track {{ background: {COLORS['bg']}; }}
::-webkit-scrollbar-thumb {{ background: {COLORS['border']}; border-radius: 5px; }}
"""


INDEX_TEMPLATE = """
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
        <style>__CSS__</style>
    </head>
    <body>
        {%app_entry%}
        <footer>{%config%}{%scripts%}{%renderer%}</footer>
    </body>
</html>
""".replace("__CSS__", CSS)
