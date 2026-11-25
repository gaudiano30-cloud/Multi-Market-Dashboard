"""Visual identity of the platform. No application logic lives here.

Palette inspired by the MFE / Università Cattolica banner:
deep navy, white and financial blues. Changing the look of the whole
dashboard means editing this file only.
"""

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------

COLORS = {
    "bg": "#001A3E",  # deep navy from the MFE logo
    "bg_panel": "#0A2B50",  # panels and cards
    "bg_panel_alt": "#123B66",  # hover states and alternate surfaces
    "border": "#28547D",
    # Legacy keys retained so main.py does not need to change.
    # Their values now follow the blue-and-white logo palette.
    "gold": "#4DA3FF",  # primary blue accent
    "gold_soft": "#B8D2EA",  # pale blue for labels and highlights
    "text": "#F5F8FC",
    "text_muted": "#A7BCD2",
    "positive": "#35C99A",
    "negative": "#FF6470",
    "accent": "#69B7FF",
}

# Ordered series colours for multi-line financial charts.
SERIES = [
    "#69B7FF",
    "#B8D2EA",
    "#35C99A",
    "#4DA3FF",
    "#8CA9D1",
    "#49D6D6",
    "#FF6470",
    "#D7E5F2",
]

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
    "gap": "28px",
    "width": "100%",
    "boxSizing": "border-box",
    "minHeight": "210px",
    "padding": "22px 48px",
    "background": f"linear-gradient(90deg, {COLORS['bg_panel']} 0%, #06264A 60%, {COLORS['bg']} 100%)",
    "borderBottom": f"3px solid {COLORS['gold']}",
}

# The source logo is square: a fixed size keeps it large without distortion.
LOGO = {
    "height": "160px",
    "width": "160px",
    "objectFit": "contain",
    "flex": "0 0 auto",
}

TITLE = {
    "margin": 0,
    "fontSize": "36px",
    "fontWeight": 600,
    "letterSpacing": "0.5px",
}

SUBTITLE = {
    "margin": 0,
    "fontSize": "12px",
    "color": COLORS["gold_soft"],
    "letterSpacing": "1.8px",
    "textTransform": "uppercase",
}

STATUS_BAR = {
    "marginLeft": "auto",
    "fontFamily": MONO_STACK,
    "fontSize": "11px",
    "color": COLORS["text_muted"],
    "textAlign": "right",
}

CONTAINER = {"maxWidth": "1440px", "margin": "0 auto", "padding": "28px 40px"}

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

TABLE_CELL_LEFT = {"if": {"column_id": "Strumento"}, "textAlign": "left", "fontFamily": FONT_STACK}

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
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0, "title": None, "font": {"size": 11}},
        hoverlabel={"bgcolor": "#0a2039", "font_size": 12, "font_family": MONO_STACK},
        colorway=SERIES,
    )
    figure.update_xaxes(gridcolor=COLORS["border"], zeroline=False, linecolor=COLORS["border"], title=None)
    figure.update_yaxes(gridcolor=COLORS["border"], zeroline=False, linecolor=COLORS["border"], title=None)
    return figure


def style_map(figure, region: str = "all"):
    """Orthographic globe with a region-aware initial viewpoint."""
    rotations = {
        "all": (-20, 12),
        "Europa": (12, 49),
        "Nord America": (-98, 38),
        "Sud America": (-60, -16),
        "Asia": (100, 30),
        "Africa": (18, 0),
        "Oceania": (135, -25),
        "Altro": (-20, 12),
    }
    lon, lat = rotations.get(region, rotations["all"])
    figure.update_layout(
        paper_bgcolor=COLORS["bg_panel"],
        font={"family": FONT_STACK, "color": COLORS["text"]},
        margin={"l": 0, "r": 0, "t": 8, "b": 8},
        height=540,
        showlegend=False,
        geo={
            "scope": "world",
            "projection": {
                "type": "orthographic",
                "rotation": {"lon": lon, "lat": lat},
            },
            "bgcolor": COLORS["bg_panel"],
            "showland": True,
            "landcolor": "#183F68",
            "showocean": True,
            "oceancolor": "#052346",
            "showlakes": True,
            "lakecolor": "#052346",
            "showcoastlines": True,
            "coastlinecolor": "#5F89B2",
            "showcountries": True,
            "countrycolor": "#37638B",
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


# Responsive website-style layout, sidebar and market discovery area.
CSS += f"""
.mfe-website-shell {{
    display: flex;
    align-items: stretch;
    width: 100%;
    max-width: 1800px;
    margin: 0 auto;
    min-height: calc(100vh - 210px);
}}
.mfe-sidebar {{
    flex: 0 0 248px;
    box-sizing: border-box;
    padding: 36px 18px 30px 26px;
    background: #07264A;
    border-right: 1px solid {COLORS['border']};
}}
.mfe-sidebar-eyebrow, .mfe-eyebrow {{
    color: {COLORS['gold_soft']};
    font-size: 10px;
    letter-spacing: 2px;
    font-weight: 600;
}}
.mfe-sidebar-title {{
    margin: 8px 0 26px;
    font-size: 20px;
    font-weight: 600;
}}
.mfe-asset-nav label {{
    display: flex !important;
    align-items: center;
    box-sizing: border-box;
    padding: 14px 12px;
    margin-bottom: 7px;
    font-size: 13px;
    border: 1px solid transparent;
    border-radius: 8px;
    cursor: pointer;
    color: {COLORS['text_muted']};
    transition: background-color .15s ease, border-color .15s ease;
}}
.mfe-asset-nav label:hover {{
    background: {COLORS['bg_panel_alt']};
    color: {COLORS['text']};
}}
.mfe-asset-nav label:has(input:checked) {{
    background: #19456F;
    border-color: {COLORS['gold']};
    color: {COLORS['text']};
    font-weight: 600;
}}
.mfe-asset-nav input {{
    position: absolute;
    opacity: 0;
    pointer-events: none;
}}
.mfe-asset-nav label:has(input:focus-visible) {{
    outline: 2px solid {COLORS['gold']};
    outline-offset: 2px;
}}
.mfe-sidebar-note {{
    margin: 14px 4px 26px;
    font-size: 11px;
    line-height: 1.6;
    color: {COLORS['text_muted']};
}}
.mfe-sidebar-divider {{
    height: 1px;
    background: {COLORS['border']};
    margin: 24px 0;
}}
.mfe-sidebar-back {{
    width: 100%;
    padding: 12px;
    font-family: {FONT_STACK};
    font-size: 12px;
    font-weight: 600;
    border: 1px solid {COLORS['gold']};
    border-radius: 7px;
    background: transparent;
    color: {COLORS['text']};
    cursor: pointer;
}}
.mfe-sidebar-back:hover {{ background: #19456F; }}
.mfe-sidebar-help {{
    margin-top: 22px;
    font-size: 11px;
    line-height: 1.75;
    color: {COLORS['text_muted']};
}}
.mfe-main {{
    flex: 1 1 0;
    min-width: 0;
    padding: 32px 40px 60px;
}}
.mfe-explorer-intro {{ margin: 18px 0 24px; }}
.mfe-explorer-title {{
    margin: 8px 0 8px;
    font-size: 30px;
    font-weight: 600;
    letter-spacing: -.5px;
}}
.mfe-explorer-description {{
    font-size: 13px;
    line-height: 1.6;
    color: {COLORS['text_muted']};
    margin: 0;
}}
.mfe-filter-grid {{
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 18px;
    margin: 0 0 20px;
}}
.mfe-filter-field {{
    min-width: 0;
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    background: {COLORS['bg_panel']};
    padding: 12px 14px;
}}
.mfe-filter-label {{
    display: block;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 1.1px;
    margin-bottom: 9px;
    color: {COLORS['gold_soft']};
}}
.mfe-globe-card {{
    background: {COLORS['bg_panel']};
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
    overflow: hidden;
    padding: 20px 20px 12px;
}}
.mfe-globe-heading {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
}}
.mfe-globe-title {{ font-size: 15px; font-weight: 600; }}
.mfe-globe-hint, .mfe-globe-footer {{
    font-size: 11px;
    color: {COLORS['text_muted']};
}}
.mfe-globe-footer {{ margin: 0 0 8px; }}
.mfe-dropdown .Select-control {{ min-height: 37px; }}
@media (max-width: 940px) {{
    .mfe-website-shell {{ flex-direction: column; }}
    .mfe-sidebar {{
        flex: initial;
        border-right: 0;
        border-bottom: 1px solid {COLORS['border']};
        padding: 20px 24px;
    }}
    .mfe-asset-nav {{ display: flex; flex-wrap: wrap; gap: 6px; }}
    .mfe-asset-nav label {{ margin: 0; padding: 10px; }}
    .mfe-sidebar-note, .mfe-sidebar-help, .mfe-sidebar-divider {{ display: none; }}
    .mfe-sidebar-title {{ margin-bottom: 12px; }}
    .mfe-sidebar-back {{ width: auto; margin-top: 12px; }}
    .mfe-main {{ padding: 22px 24px 45px; }}
}}
@media (max-width: 620px) {{
    .mfe-filter-grid {{ grid-template-columns: 1fr; }}
    .mfe-explorer-title {{ font-size: 24px; }}
    .mfe-globe-card {{ padding: 12px; }}
}}
"""


# Semantic breadcrumb buttons: identical appearance to existing text,
# with a discreet hover / keyboard-focus treatment.
CSS += f"""
.mfe-breadcrumb-link {{
    padding: 0;
    margin: 0;
    border: none;
    border-radius: 2px;
    background: transparent;
    color: {COLORS['text_muted']};
    font: inherit;
    cursor: pointer;
    transition: color 160ms ease;
}}
.mfe-breadcrumb-link:hover {{
    color: {COLORS['accent']};
    text-decoration: underline;
    text-underline-offset: 4px;
}}
.mfe-breadcrumb-link:focus-visible {{
    outline: 2px solid {COLORS['accent']};
    outline-offset: 4px;
}}
.mfe-breadcrumb-separator {{
    margin: 0 11px;
    color: {COLORS['text_muted']};
    opacity: .75;
}}
.mfe-breadcrumb-current {{
    color: {COLORS['text']};
}}
"""



# DatePickerInput (Dash Mantine Components): match the MFE palette while
# retaining the built-in month / year / decade navigation.
CSS += f"""
.mfe-period-picker {{
    width: 310px;
    max-width: 100%;
    font-family: {FONT_STACK};
}}
.mfe-period-picker .mantine-DatePickerInput-input {{
    background-color: {COLORS['bg_panel']} !important;
    color: {COLORS['text']} !important;
    border: 1px solid {COLORS['border']} !important;
    border-radius: 6px;
    cursor: pointer;
}}
.mfe-period-picker .mantine-DatePickerInput-input:hover,
.mfe-period-picker .mantine-DatePickerInput-input:focus {{
    border-color: {COLORS['accent']} !important;
}}
.mfe-period-picker .mantine-DatePickerInput-placeholder {{
    color: {COLORS['text_muted']};
}}
.mfe-period-picker .mantine-DatePickerInput-section {{
    color: {COLORS['accent']};
}}
@media (max-width: 620px) {{
    .mfe-period-picker {{ width: 100%; }}
}}
"""



# ---------------------------------------------------------------------------
# Excel-style frozen navigation WITH NORMAL WINDOW SCROLLING.
# IMPORTANT: The document must keep its natural height. Never apply
# overflow:hidden or height:100vh to html/body/.mfe-viewport/.mfe-main.
# The app.py from the previous freeze already contains the two structural
# wrappers .mfe-market-freeze and .mfe-market-scroll.
# ---------------------------------------------------------------------------
CSS += f"""
:root {{
    --mfe-header-height: 210px;
    --mfe-breadcrumb-height: 46px;
}}
/* Everything uses the main page scrollbar, including Mac trackpad gestures. */
html, body {{
    min-height: 100%;
    height: auto;
    overflow: visible;
}}
.mfe-viewport {{
    width: 100%;
    min-height: 100vh;
    height: auto;
    overflow: visible;
    display: block;
}}
.mfe-website-shell, .mfe-main, #market-page, .mfe-market-layout {{
    height: auto;
    max-height: none;
    min-height: 0;
    overflow: visible;
}}
.mfe-market-layout {{ display: block; }}
.mfe-page-header {{
    position: sticky;
    top: 0;
    z-index: 110;
    background-color: {COLORS['bg']};
}}
/* Sidebar is pinned independently; it does not lock the main page. */
.mfe-sidebar {{
    position: sticky;
    top: var(--mfe-header-height);
    align-self: flex-start;
    max-height: calc(100vh - var(--mfe-header-height));
    overflow-y: auto;
}}
/* Always-visible breadcrumb, stacked immediately below the header. */
.mfe-main > #breadcrumb {{
    position: sticky;
    top: var(--mfe-header-height);
    z-index: 100;
    box-sizing: border-box;
    height: var(--mfe-breadcrumb-height);
    min-height: var(--mfe-breadcrumb-height);
    margin: 0 !important;
    display: flex;
    align-items: center;
    white-space: nowrap;
    overflow-x: auto;
    background-color: {COLORS['bg']};
    border-bottom: 1px solid {COLORS['border']};
}}
/* Filters + tabs stick together below the breadcrumb, while the entire
   chart area stays in the ordinary window scroll flow. */
.mfe-market-freeze {{
    position: sticky;
    top: calc(var(--mfe-header-height) + var(--mfe-breadcrumb-height));
    z-index: 90;
    background-color: {COLORS['bg']};
    padding-top: 12px;
    box-shadow: 0 9px 18px -18px rgba(0,0,0,.9);
}}
.mfe-market-freeze .custom-tabs {{
    background-color: {COLORS['bg']};
}}
.mfe-market-scroll {{
    display: block;
    height: auto;
    max-height: none;
    min-height: 0;
    overflow: visible;
    padding: 20px 0 40px;
}}
/* On short laptop screens the fixed header is compact enough to leave room
   for graphics. Height matches the sticky offsets above. */
@media (max-height: 760px) and (min-width: 941px) {{
    :root {{ --mfe-header-height: 140px; }}
    .mfe-page-header {{
        height: var(--mfe-header-height) !important;
        min-height: 0 !important;
        padding: 10px 30px !important;
    }}
    .mfe-page-header img {{ height: 108px !important; width: 108px !important; }}
    .mfe-page-header h1 {{ font-size: 26px !important; }}
}}
/* On mobile or narrow windows, prioritize comfortable scrolling over fixing
   a large stack of controls in an already small viewport. */
@media (max-width: 940px) {{
    :root {{ --mfe-header-height: 104px; }}
    .mfe-page-header {{
        min-height: 0 !important;
        height: 104px !important;
        padding: 10px 18px !important;
        gap: 12px !important;
    }}
    .mfe-page-header img {{ width: 76px !important; height: 76px !important; }}
    .mfe-page-header h1 {{ font-size: 18px !important; }}
    .mfe-page-header p {{ font-size: 9px !important; letter-spacing: .5px !important; }}
    .mfe-page-header > div:last-child {{ display: none; }}
    .mfe-sidebar {{ position: static; max-height: none; overflow: visible; }}
    .mfe-main > #breadcrumb {{ position: static; height: auto; min-height: 45px; }}
    .mfe-market-freeze {{ position: static; }}
}}
"""

# Link per chiudere la sessione autenticata (il resto del design e invariato).
CSS += f"""
.mfe-logout-link {{
    flex: 0 0 auto;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 10px 16px;
    border: 1px solid {COLORS['accent']};
    border-radius: 6px;
    color: {COLORS['text']};
    text-decoration: none;
    font-size: 12px;
    font-weight: 600;
    background-color: {COLORS['bg_panel']};
    white-space: nowrap;
}}
.mfe-logout-link:hover {{
    background-color: {COLORS['bg_panel_alt']};
    color: {COLORS['accent']};
}}
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
""".replace(
    "__CSS__", CSS
)
