"""Dash web interface: sidebar navigation, market explorer and analytics.

Business logic, SQL and quantitative calculations stay in analytics/ and
 database/. The globe and page design live in app.py and style.py only.
"""

from datetime import date

import dash_mantine_components as dmc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import ALL, Dash, Input, Output, State, callback, ctx, dash_table, dcc, html, no_update
from dash import _dash_renderer

import style
from analytics import metrics
from database import repository
from database.connection import database_exists

if not database_exists():
    raise SystemExit("Database non trovato. Lancia prima: python -m database.populate")


# ---------------------------------------------------------------------------
# Navigation metadata (display only; market data still comes from database)
# ---------------------------------------------------------------------------

# Geography is read from the database, not maintained in a second Python list.
# Markets with no physical exchange (e.g. FX OTC and bond categories) have no pin.
DEFAULT_GEOGRAPHY = {
    "exchange": "Mercato", "city": "", "continent": "Globale", "lat": None, "lon": None
}


ASSET_CLASS_LABELS = {
    "equity": "Equity",
    "fixed_income": "Fixed Income",
    "derivative": "Derivatives",
    "commodity": "Commodities",
    "fx": "Foreign Exchange",
}

ASSET_ICONS = {
    "equity": "▥", "fixed_income": "▤", "derivative": "⌁", "commodity": "◇", "fx": "⇄",
}

MARKETS = repository.list_markets()

GEOGRAPHY = {
    row.market_code: {
        "exchange": row.label.split(" - ", 1)[-1],
        "city": row.city or "",
        "continent": row.region or "Globale",
        "lat": None if pd.isna(row.latitude) else float(row.latitude),
        "lon": None if pd.isna(row.longitude) else float(row.longitude),
    }
    for row in MARKETS.itertuples()
}


def geography_of(market_code: str) -> dict:
    return GEOGRAPHY.get(market_code, DEFAULT_GEOGRAPHY)


def markets_of_asset_class(asset_class: str) -> pd.DataFrame:
    if MARKETS.empty or not asset_class:
        return MARKETS.iloc[0:0]
    return MARKETS[MARKETS["asset_class"] == asset_class]


def filtered_markets(asset_class: str, region: str = "all") -> pd.DataFrame:
    frame = markets_of_asset_class(asset_class)
    if region and region != "all" and not frame.empty:
        frame = frame[frame["market_code"].map(lambda code: geography_of(code)["continent"] == region)]
    return frame


# ---------------------------------------------------------------------------
# Application shell
# ---------------------------------------------------------------------------

# dash-mantine-components 2.x uses Mantine/React hooks that require React 18.
# Some Dash 2.x installations still default to React 16; in that case the
# browser crashes with "(0,r.useId) is not a function".
# IMPORTANT: choose React 18 BEFORE instantiating Dash().
_dash_renderer._set_react_version("18.2.0")

app = Dash(
    __name__,
    title="MFE | Multi-Market Financial Data Analysis Platform",
    suppress_callback_exceptions=True,
)
app.index_string = style.INDEX_TEMPLATE
server = app.server


def header() -> html.Div:
    """Preserved MFE header, logo and data freshness label."""
    return html.Div(
        className="mfe-page-header",
        style=style.HEADER,
        children=[
            html.Img(
                src=app.get_asset_url("MFEimage.png"),
                style=style.LOGO,
                alt="Master Financial Engineering - Università Cattolica",
            ),
            html.Div(
                [
                    html.P(
                        "Master in Financial Engineering for Portfolio and Risk Management",
                        style=style.SUBTITLE,
                    ),
                    html.H1("Multi-Market Financial Data Analysis Platform", style=style.TITLE),
                ]
            ),
            html.Div(repository.last_update_label(), style=style.STATUS_BAR),
        ],
    )


def sidebar() -> html.Aside:
    """Navigation is visible on both the globe view and the market page."""
    options = [
        {"label": f"{ASSET_ICONS[key]}  {label}", "value": key}
        for key, label in ASSET_CLASS_LABELS.items()
    ]
    return html.Aside(
        className="mfe-sidebar",
        children=[
            html.Div("NAVIGAZIONE", className="mfe-sidebar-eyebrow"),
            html.H2("Asset classes", className="mfe-sidebar-title"),
            dcc.RadioItems(
                id="asset-class",
                className="mfe-asset-nav",
                options=options,
                value="equity",
                labelStyle={"display": "flex"},
                inputStyle={"marginRight": "12px"},
            ),
            html.Div(id="asset-status", className="mfe-sidebar-note"),
            html.Div(className="mfe-sidebar-divider"),
            html.Button(
                "◉  Esplora sul globo",
                id="back-to-globe",
                n_clicks=0,
                className="mfe-sidebar-back",
            ),
            html.P(
                "Seleziona un'asset class e scegli un mercato dai menu oppure clicca un punto sul globo.",
                className="mfe-sidebar-help",
            ),
        ],
    )


def explorer() -> html.Div:
    """The world globe remains in the layout even when hidden."""
    return html.Div(
        id="nav-panel",
        className="mfe-explorer",
        children=[
            html.Div(
                className="mfe-explorer-intro",
                children=[
                    html.Div("MARKET EXPLORER", className="mfe-eyebrow"),
                    html.H2("Esplora i mercati finanziari", className="mfe-explorer-title"),
                    html.P(
                        "Scegli una regione e una piazza finanziaria, oppure ruota il globo e seleziona un marcatore.",
                        className="mfe-explorer-description",
                    ),
                ],
            ),
            html.Div(
                className="mfe-filter-grid",
                children=[
                    html.Div(
                        className="mfe-filter-field",
                        children=[
                            html.Label("Area geografica", htmlFor="region-dropdown", className="mfe-filter-label"),
                            dcc.Dropdown(
                                id="region-dropdown",
                                options=[{"label": "Tutte le aree", "value": "all"}],
                                value="all",
                                searchable=False,
                                clearable=False,
                                className="mfe-dropdown",
                            ),
                        ],
                    ),
                    html.Div(
                        className="mfe-filter-field",
                        children=[
                            html.Label("Borsa / mercato", htmlFor="market-dropdown", className="mfe-filter-label"),
                            dcc.Dropdown(
                                id="market-dropdown",
                                options=[],
                                value=None,
                                placeholder="Seleziona un mercato...",
                                searchable=True,
                                clearable=True,
                                className="mfe-dropdown",
                            ),
                        ],
                    ),
                ],
            ),
            html.Div(
                className="mfe-globe-card",
                children=[
                    html.Div(
                        className="mfe-globe-heading",
                        children=[
                            html.Div("Mercati nel mondo", className="mfe-globe-title"),
                            html.Span("Trascina per ruotare · Clicca per aprire", className="mfe-globe-hint"),
                        ],
                    ),
                    dcc.Graph(
                        id="world-map",
                        className="mfe-world-map",
                        config={"displayModeBar": False, "scrollZoom": False, "displaylogo": False},
                    ),
                    html.P(id="globe-message", className="mfe-globe-footer"),
                ],
            ),
        ],
    )


# MantineProvider enables the dark-themed date calendar (only UI layer).
app.layout = dmc.MantineProvider(
    children=html.Div(
        className="mfe-viewport",
        style=style.PAGE,
        children=[
            header(),
            dcc.Store(id="selected-market"),
            # The breadcrumb uses this store to communicate navigation to the
            # existing selectors without duplicating their Dash outputs.
            dcc.Store(id="breadcrumb-action"),
            html.Div(
                className="mfe-website-shell",
                children=[
                    sidebar(),
                    html.Main(
                        className="mfe-main",
                        children=[
                            html.Div(id="breadcrumb", style=style.BREADCRUMB),
                            explorer(),
                            html.Div(id="market-page"),
                        ],
                    ),
                ],
            ),
        ],
    ),
    forceColorScheme="dark",
)


# ---------------------------------------------------------------------------
# Sidebar -> region -> market selectors
# ---------------------------------------------------------------------------

@callback(Output("asset-status", "children"), Input("asset-class", "value"))
def asset_status(asset_class):
    count = len(markets_of_asset_class(asset_class))
    if count == 0:
        return "Nessun mercato ancora caricato per questa asset class."
    return f"{count} mercat{'o' if count == 1 else 'i'} disponibil{'e' if count == 1 else 'i'} nel database."


@callback(
    Output("region-dropdown", "options"),
    Output("region-dropdown", "value"),
    Input("asset-class", "value"),
    Input("breadcrumb-action", "data"),
)
def update_regions(asset_class, navigation):
    """Update available regions; breadcrumb navigation can select a region."""
    frame = markets_of_asset_class(asset_class)
    regions = (
        sorted({geography_of(code)["continent"] for code in frame["market_code"]})
        if not frame.empty else []
    )
    options = [{"label": "Tutte le aree", "value": "all"}]
    options += [{"label": region, "value": region} for region in regions]

    if ctx.triggered_id == "breadcrumb-action" and navigation:
        if navigation.get("level") == "region":
            target_region = navigation.get("region")
            if target_region in regions:
                return options, target_region

    # Clicking Dashboard or Equity, or changing asset class, shows all regions.
    return options, "all"


@callback(
    Output("market-dropdown", "options"),
    Output("market-dropdown", "value"),
    Input("asset-class", "value"),
    Input("region-dropdown", "value"),
    Input("back-to-globe", "n_clicks"),
)
def update_market_options(asset_class, region, _back_clicks):
    frame = filtered_markets(asset_class, region)
    options = [
        {"label": geography_of(row.market_code)["exchange"] + " — " + row.label, "value": row.market_code}
        for row in frame.itertuples()
    ]
    # Do not open a market automatically: let the visitor select the market.
    return options, None


# ---------------------------------------------------------------------------
# Interactive spherical globe (Plotly orthographic projection)
# ---------------------------------------------------------------------------

@callback(
    Output("world-map", "figure"),
    Output("globe-message", "children"),
    Input("asset-class", "value"),
    Input("region-dropdown", "value"),
)
def draw_map(asset_class, region):
    frame = filtered_markets(asset_class, region)
    records = []

    for row in frame.itertuples():
        geo = geography_of(row.market_code)
        if geo["lat"] is None or geo["lon"] is None:
            continue
        records.append(
            {
                "market_code": row.market_code,
                "label": row.label,
                "exchange": geo["exchange"],
                "lat": geo["lat"],
                "lon": geo["lon"],
                "strumenti": len(repository.list_instruments(row.market_code, include_benchmark=True)),
            }
        )

    if records:
        points = pd.DataFrame(records)
        figure = go.Figure(
            go.Scattergeo(
                lat=points["lat"],
                lon=points["lon"],
                text=points["exchange"],
                customdata=points[["market_code", "label", "strumenti"]].to_numpy(),
                mode="markers",
                marker={
                    "size": 15,
                    "color": style.COLORS["accent"],
                    "line": {"width": 2.5, "color": style.COLORS["text"]},
                    "opacity": 0.96,
                },
                hovertemplate="<b>%{customdata[1]}</b><br>%{text}<br>%{customdata[2]} strumenti<extra></extra>",
            )
        )
    else:
        figure = go.Figure(go.Scattergeo(lat=[], lon=[]))

    if frame.empty:
        message = "Nessun mercato configurato per questa selezione."
    elif not records:
        message = "Mercati disponibili nel menu, ma manca la posizione geografica per mostrarli sul globo."
    else:
        point_label = "punto" if len(records) == 1 else "punti"
        message = f"{len(records)} {point_label} sul globo · clicca un marcatore per aprire il mercato."

    return style.style_map(figure, region), message


@callback(
    Output("selected-market", "data"),
    Input("market-dropdown", "value"),
    Input("world-map", "clickData"),
    Input("asset-class", "value"),
    Input("region-dropdown", "value"),
    Input("back-to-globe", "n_clicks"),
    Input("breadcrumb-action", "data"),
    prevent_initial_call=True,
)
def select_market(dropdown_market, click_data, asset_class, region, _back_clicks, _breadcrumb_action):
    """Open by dropdown or globe; close when navigating to a parent level."""
    trigger = ctx.triggered_id
    if trigger in ("asset-class", "region-dropdown", "back-to-globe", "breadcrumb-action"):
        return None

    frame = filtered_markets(asset_class, region)
    available = set(frame["market_code"]) if not frame.empty else set()
    if trigger == "market-dropdown":
        return dropdown_market if dropdown_market in available else None

    if trigger == "world-map" and click_data and click_data.get("points"):
        custom = click_data["points"][0].get("customdata")
        market_code = custom[0] if custom else None
        return market_code if market_code in available else None

    return no_update


@callback(
    Output("world-map", "clickData"),
    Input("back-to-globe", "n_clicks"),
    Input("asset-class", "value"),
    Input("region-dropdown", "value"),
    Input("breadcrumb-action", "data"),
    prevent_initial_call=True,
)
def clear_map_selection(_back_clicks, _asset_class, _region, _breadcrumb_action):
    """Allow clicking the same globe marker again after going back."""
    return None


@callback(Output("nav-panel", "style"), Input("selected-market", "data"))
def toggle_navigation(market_code):
    # Hide rather than unmount the globe so its callbacks stay connected.
    return {"display": "none"} if market_code else {"display": "block"}


def breadcrumb_button(label: str, level: str) -> html.Button:
    """Clickable parent of the current page; last breadcrumb is plain text."""
    return html.Button(
        label,
        id={"type": "breadcrumb-link", "level": level},
        n_clicks=0,
        className="mfe-breadcrumb-link",
        title=f"Torna a {label}",
    )


def breadcrumb_separator() -> html.Span:
    return html.Span("/", className="mfe-breadcrumb-separator", **{"aria-hidden": "true"})


@callback(
    Output("breadcrumb", "children"),
    Input("asset-class", "value"),
    Input("region-dropdown", "value"),
    Input("selected-market", "data"),
)
def build_breadcrumb(asset_class, region, market_code):
    """Clickable ancestor levels; the current level is non-clickable."""
    parts = [breadcrumb_button("Dashboard", "dashboard"), breadcrumb_separator()]
    asset_label = ASSET_CLASS_LABELS.get(asset_class, "—")

    if not market_code and region in (None, "all"):
        # Dashboard / Equity (current).
        parts.append(html.Span(asset_label, className="mfe-breadcrumb-current"))
        return parts

    parts.extend([breadcrumb_button(asset_label, "asset"), breadcrumb_separator()])

    if market_code:
        geo = geography_of(market_code)
        # Dashboard / Equity / Europa / Borsa Italiana (current).
        parts.extend([
            breadcrumb_button(geo["continent"], "region"),
            breadcrumb_separator(),
            html.Span(geo["exchange"], className="mfe-breadcrumb-current"),
        ])
    else:
        # Dashboard / Equity / Europa (current).
        parts.append(html.Span(region, className="mfe-breadcrumb-current"))

    return parts


@callback(
    Output("breadcrumb-action", "data"),
    Input({"type": "breadcrumb-link", "level": ALL}, "n_clicks"),
    State("selected-market", "data"),
    State("region-dropdown", "value"),
    prevent_initial_call=True,
)
def handle_breadcrumb_click(_clicks, selected_market, selected_region):
    """Capture the intended parent level before the market page disappears."""
    trigger = ctx.triggered_id
    if not isinstance(trigger, dict) or trigger.get("type") != "breadcrumb-link":
        return no_update
    # Newly mounted buttons initially report zero clicks: ignore those events.
    if not ctx.triggered or not ctx.triggered[0].get("value"):
        return no_update

    level = trigger.get("level")
    if level not in ("dashboard", "asset", "region"):
        return no_update

    region = (
        geography_of(selected_market)["continent"]
        if selected_market else selected_region
    )
    return {"level": level, "region": region}


@callback(
    Output("asset-class", "value"),
    Input("breadcrumb-action", "data"),
    prevent_initial_call=True,
)
def navigate_to_dashboard(navigation):
    """Dashboard always returns to the default Equity landing page."""
    if navigation and navigation.get("level") == "dashboard":
        return "equity"
    return no_update


# ---------------------------------------------------------------------------
# Market page: unchanged analysis panels, filters and tabs
# ---------------------------------------------------------------------------

@callback(Output("market-page", "children"), Input("selected-market", "data"))
def render_market_page(market_code):
    """Securities listed on the selected exchange, plus the analysis area."""
    if not market_code:
        return []

    instruments = repository.list_instruments(market_code, include_benchmark=True)
    if instruments.empty:
        return html.Div(
            "Mercato presente nel catalogo. Non ci sono ancora strumenti disponibili "
            "dal provider configurato; non vengono mostrati dati inventati.",
            style=style.EMPTY_STATE,
        )

    options = [
        {"label": f"{'[Indice] ' if row.is_benchmark else ''}{row.name} ({row.ticker})", "value": row.ticker}
        for row in instruments.itertuples()
    ]
    securities = instruments[instruments["is_benchmark"] == 0]
    default_value = securities.iloc[0]["ticker"] if not securities.empty else instruments.iloc[0]["ticker"]

    # The freeze pane never scrolls: security filters and analysis tabs stay in view.
    # Only the sibling tab-content area scrolls, like Excel Freeze Panes.
    return html.Div(
        className="mfe-market-layout",
        children=[
            html.Div(
                className="mfe-market-freeze",
                children=[
                    html.Div(
                        style=style.PANEL,
                        children=[
                            html.H3("Strumenti quotati", style=style.PANEL_TITLE),
                            html.Div(
                                style=style.TOOLBAR,
                                children=[
                                    html.Div(
                                        [
                                            html.Label("Cerca security", style=style.NAV_CHIP_LABEL),
                                            dcc.Dropdown(
                                                id="instrument", options=options, value=default_value,
                                                clearable=False, searchable=True,
                                                placeholder="Digita il nome o il ticker...",
                                                style={"width": "380px", "maxWidth": "100%"},
                                            ),
                                        ]
                                    ),
                                    html.Div(
                                        [
                                            html.Label("Periodo", style=style.NAV_CHIP_LABEL),
                                            dmc.DatePickerInput(
                                                id="period",
                                                type="range",
                                                value=[date(2020, 1, 1).isoformat(), date.today().isoformat()],
                                                valueFormat="DD/MM/YYYY",
                                                firstDayOfWeek=1,
                                                maxLevel="decade",
                                                numberOfColumns=1,
                                                clearable=False,
                                                placeholder="Seleziona un intervallo...",
                                                className="mfe-period-picker",
                                                popoverProps={
                                                    "position": "bottom-start",
                                                    "withinPortal": True,
                                                    "zIndex": 3000,
                                                },
                                                styles={
                                                    "input": {
                                                        "backgroundColor": style.COLORS["bg_panel"],
                                                        "color": style.COLORS["text"],
                                                        "border": f"1px solid {style.COLORS['border']}",
                                                        "minHeight": "42px",
                                                        "fontFamily": style.FONT_STACK,
                                                    },
                                                    "dropdown": {
                                                        "backgroundColor": style.COLORS["bg_panel"],
                                                        "color": style.COLORS["text"],
                                                        "border": f"1px solid {style.COLORS['border']}",
                                                    },
                                                },
                                            ),
                                        ]
                                    ),
                                    html.Div(
                                        [
                                            html.Label("Frequenza", style=style.NAV_CHIP_LABEL),
                                            dcc.Dropdown(
                                                id="frequency",
                                                options=[
                                                    {"label": "Giornaliera", "value": "D"},
                                                    {"label": "Settimanale", "value": "W"},
                                                    {"label": "Mensile", "value": "ME"},
                                                    {"label": "Annuale", "value": "YE"},
                                                ],
                                                value="D", clearable=False, style={"width": "170px"},
                                            ),
                                        ]
                                    ),
                                ],
                            ),
                        ],
                    ),
                    dcc.Tabs(
                        id="tabs", value="prices", parent_className="custom-tabs", className="custom-tabs",
                        children=[
                            dcc.Tab(label="Prezzi", value="prices", className="custom-tab", selected_className="custom-tab--selected"),
                            dcc.Tab(label="Rendimenti", value="returns", className="custom-tab", selected_className="custom-tab--selected"),
                            dcc.Tab(label="Rischio", value="risk", className="custom-tab", selected_className="custom-tab--selected"),
                            dcc.Tab(label="Statistiche di mercato", value="market", className="custom-tab", selected_className="custom-tab--selected"),
                        ],
                    ),
                ],
            ),
            html.Div(id="tab-content", className="mfe-market-scroll"),
        ],
    )


# ---------------------------------------------------------------------------
# Presentation helpers
# ---------------------------------------------------------------------------


def _format_metric(key: str, value) -> str:
    if value is None or (isinstance(value, float) and value != value):
        return "n/d"
    if key == "Osservazioni" or key == "Numero strumenti":
        return f"{value:,.0f}".replace(",", ".")
    if any(word in key for word in ("Sharpe", "Sortino", "Beta")):
        return f"{value:.2f}"
    if "(%)" in key:
        return f"{value:.2f}%"
    return f"{value:.2%}"


def _tiles(values: dict) -> html.Div:
    return html.Div(
        style=style.TILE_ROW,
        children=[
            html.Div(
                style=style.TILE,
                children=[
                    html.Div(key, style=style.TILE_LABEL),
                    html.Div(_format_metric(key, value), style=style.TILE_VALUE),
                ],
            )
            for key, value in values.items()
        ],
    )


def _table(frame: pd.DataFrame) -> dash_table.DataTable:
    return dash_table.DataTable(
        data=frame.round(2).to_dict("records"),
        columns=[{"name": c, "id": c} for c in frame.columns],
        style_cell=style.TABLE_CELL,
        style_header=style.TABLE_HEADER,
        style_cell_conditional=[style.TABLE_CELL_LEFT],
        style_as_list_view=True,
        sort_action="native",
        page_size=15,
    )


def _panel(title: str, *children) -> html.Div:
    return html.Div(style=style.PANEL, children=[html.H3(title, style=style.PANEL_TITLE), *children])


def _graph(figure) -> dcc.Graph:
    return dcc.Graph(figure=figure, config={"displaylogo": False})


# ---------------------------------------------------------------------------
# Analysis tabs
# ---------------------------------------------------------------------------


@callback(
    Output("tab-content", "children"),
    Input("tabs", "value"),
    Input("instrument", "value"),
    Input("period", "value"),
    Input("frequency", "value"),
    State("selected-market", "data"),
)
def render_tab(tab, ticker, period, frequency, market_code):
    if not market_code:
        return []

    # Mantine's range value is a pair of YYYY-MM-DD strings. While the user
    # is choosing the second date, avoid querying SQLite with an incomplete range.
    if not isinstance(period, (list, tuple)) or len(period) != 2 or not all(period):
        return html.Div(
            "Seleziona sia la data iniziale sia quella finale.",
            style=style.EMPTY_STATE,
        )
    start, end = period
    if start > end:
        return html.Div("La data finale precede quella iniziale.", style=style.EMPTY_STATE)

    if tab == "market":
        closes = repository.get_market_closes(market_code, start, end)
        if closes.empty:
            return html.Div("Nessun dato nel periodo selezionato.", style=style.EMPTY_STATE)

        rebased = closes.apply(lambda column: column / column.dropna().iloc[0] * 100)
        comparison = style.style_figure(px.line(rebased), height=400)
        heatmap = style.style_figure(
            px.imshow(
                metrics.correlation_matrix(closes),
                text_auto=".2f",
                color_continuous_scale="RdBu_r",
                zmin=-1,
                zmax=1,
                aspect="auto",
            ),
            height=400,
            show_legend=False,
        )

        return html.Div(
            [
                _panel("Indicatori aggregati di mercato", _tiles(metrics.market_aggregates(closes))),
                _panel("Performance comparata (base 100)", _graph(comparison)),
                _panel("Statistiche cross-section", _table(metrics.market_statistics(closes))),
                _panel("Matrice di correlazione", _graph(heatmap)),
            ]
        )

    if not ticker:
        return html.Div("Seleziona uno strumento.", style=style.EMPTY_STATE)

    prices = repository.get_prices(ticker, start, end)
    if prices.empty:
        return html.Div("Nessun dato nel periodo selezionato.", style=style.EMPTY_STATE)

    close = prices["adj_close"].fillna(prices["close"])

    if tab == "prices":
        blocks = [
            _panel("Serie storica", _graph(style.style_figure(px.line(close), show_legend=False))),
            _panel(
                "Performance cumulata (base 100)",
                _graph(style.style_figure(px.area(metrics.cumulative_return(close)), show_legend=False)),
            ),
        ]
        fundamentals = repository.get_fundamentals(ticker)
        clean = {
            key.replace("_", " ").title(): value
            for key, value in fundamentals.items()
            if key != "ticker" and value is not None
        }
        if clean:
            blocks.append(
                _panel(
                    "Fondamentali",
                    html.Div(
                        style=style.TILE_ROW,
                        children=[
                            html.Div(
                                style=style.TILE,
                                children=[
                                    html.Div(key, style=style.TILE_LABEL),
                                    html.Div(f"{value:,.2f}".replace(",", "."), style=style.TILE_VALUE),
                                ],
                            )
                            for key, value in clean.items()
                        ],
                    ),
                )
            )
        dividends = repository.get_dividends(ticker)
        if not dividends.empty:
            bars = px.bar(dividends, x="date", y="amount")
            bars.update_traces(marker_color=style.COLORS["gold"])
            blocks.append(_panel("Dividendi", _graph(style.style_figure(bars, height=280, show_legend=False))))
        return html.Div(blocks)

    if tab == "returns":
        returns = metrics.resample_returns(close, frequency)
        bars = px.bar(returns * 100)
        bars.update_traces(marker_color=style.COLORS["accent"])
        histogram = px.histogram(returns * 100, nbins=60)
        histogram.update_traces(marker_color=style.COLORS["gold"])
        return html.Div(
            [
                _panel("Rendimenti logaritmici (%)", _graph(style.style_figure(bars, show_legend=False))),
                _panel(
                    "Distribuzione dei rendimenti",
                    _graph(style.style_figure(histogram, height=320, show_legend=False)),
                ),
            ]
        )

    # tab == "risk"
    benchmark = pd.Series(dtype=float)
    catalogue = repository.list_instruments(market_code, include_benchmark=True)
    benchmarks = catalogue[catalogue["is_benchmark"] == 1]
    if not benchmarks.empty:
        benchmark_prices = repository.get_prices(benchmarks.iloc[0]["ticker"], start, end)
        if not benchmark_prices.empty:
            benchmark = benchmark_prices["adj_close"].fillna(benchmark_prices["close"])

    drawdown = px.area(metrics.drawdown_series(close) * 100)
    drawdown.update_traces(line_color=style.COLORS["negative"], fillcolor="rgba(255,90,95,0.18)")
    rolling = px.line(metrics.rolling_volatility(close) * 100)

    return html.Div(
        [
            _panel("Indicatori di rischio", _tiles(metrics.summary(close, benchmark))),
            _panel("Drawdown (%)", _graph(style.style_figure(drawdown, show_legend=False))),
            _panel(
                "Volatilità annualizzata su finestra mobile 60 giorni (%)",
                _graph(style.style_figure(rolling, height=300, show_legend=False)),
            ),
        ]
    )


if __name__ == "__main__":
    app.run(debug=True)
