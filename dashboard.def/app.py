"""Dash entry point: layout, navigation and callbacks.

Holds no financial logic and no SQL. Every number comes from `analytics`,
every row from `database.repository`, every colour from `style`.

Navigation follows the brief: asset class -> geography -> exchange ->
security -> analysis, with a way back to the main dashboard at each step.
The map and the back button stay mounted at all times and are hidden with
CSS, because a Dash callback never fires while one of its inputs is absent
from the layout.
"""
from datetime import date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import (ALL, Dash, Input, Output, State, callback, ctx, dash_table,
                  dcc, html, no_update)

import style
from analytics import metrics
from database import repository
from database.connection import database_exists

if not database_exists():
    raise SystemExit("Database non trovato. Lancia prima: python -m database.populate")

# ---------------------------------------------------------------------------
# Navigation metadata.
# Presentation-level geography: where each exchange sits on the map. Belongs
# in config.py once the market catalogue is extended; kept here so the rest
# of the package stays untouched.
# ---------------------------------------------------------------------------

GEOGRAPHY = {
    "EQ_IT": {"exchange": "Borsa Italiana", "city": "Milano",
              "continent": "Europa", "lat": 45.46, "lon": 9.19},
    "EQ_EU": {"exchange": "Deutsche Börse / Euronext", "city": "Frankfurt",
              "continent": "Europa", "lat": 50.11, "lon": 8.68},
    "COMM": {"exchange": "NYMEX / COMEX", "city": "New York",
             "continent": "Nord America", "lat": 40.71, "lon": -74.01},
    "FX": {"exchange": "OTC Interbank", "city": "London",
           "continent": "Europa", "lat": 51.51, "lon": -0.13},
}

DEFAULT_GEOGRAPHY = {"exchange": "N/D", "city": "N/D",
                     "continent": "Altro", "lat": 0.0, "lon": 0.0}

# Plotly scope names, keyed by the labels shown on the buttons.
CONTINENT_SCOPE = {
    "Mondo": "world",
    "Europa": "europe",
    "Nord America": "north america",
    "Asia": "asia",
    "Sud America": "south america",
    "Africa": "africa",
}

ASSET_CLASS_LABELS = {
    "equity": "Equity",
    "fixed_income": "Fixed Income",
    "derivative": "Derivatives",
    "commodity": "Commodities",
    "fx": "Foreign Exchange",
}

MARKETS = repository.list_markets()


def geography_of(market_code: str) -> dict:
    return GEOGRAPHY.get(market_code, DEFAULT_GEOGRAPHY)


def markets_of_asset_class(asset_class: str) -> pd.DataFrame:
    if MARKETS.empty or not asset_class:
        return MARKETS.iloc[0:0]
    return MARKETS[MARKETS["asset_class"] == asset_class]


# ---------------------------------------------------------------------------
# Application shell
# ---------------------------------------------------------------------------

app = Dash(__name__, title="MFE | Multi Market Platform",
           suppress_callback_exceptions=True)
app.index_string = style.INDEX_TEMPLATE
server = app.server


def header() -> html.Div:
    """Top bar: logo, identity, data freshness."""
    return html.Div(
        style=style.HEADER,
        children=[
            # Put logo_unicatt.png in the assets/ folder; Dash serves it.
            html.Img(src="/assets/logo_unicatt.png", style=style.LOGO,
                     alt="Università Cattolica del Sacro Cuore"),
            html.Div([
                html.P("Master in Financial Engineering", style=style.SUBTITLE),
                html.H1("Multi Market Analysis Platform", style=style.TITLE),
            ]),
            html.Div(repository.last_update_label(), style=style.STATUS_BAR),
        ],
    )


def asset_class_selector() -> html.Div:
    """The small rectangle at the top left: click, dropdown opens."""
    classes = sorted(MARKETS["asset_class"].unique()) if not MARKETS.empty else []
    return html.Div(
        style={"minWidth": "230px"},
        children=[
            html.Label("Asset class", style=style.NAV_CHIP_LABEL),
            html.Div(
                style=style.NAV_CHIP,
                children=dcc.Dropdown(
                    id="asset-class",
                    options=[{"label": ASSET_CLASS_LABELS.get(c, c.title()),
                              "value": c} for c in classes],
                    value=classes[0] if classes else None,
                    clearable=False,
                    style={"border": "none", "backgroundColor": "transparent"},
                ),
            ),
        ],
    )


app.layout = html.Div(
    style=style.PAGE,
    children=[
        header(),
        dcc.Store(id="selected-market"),
        dcc.Store(id="selected-scope", data="Mondo"),
        html.Div(
            style=style.CONTAINER,
            children=[
                html.Div(style=style.TOOLBAR, children=[
                    asset_class_selector(),
                    html.Div(id="continent-buttons",
                             style={"display": "flex", "alignItems": "flex-end"}),
                    html.Button("← Torna alla mappa", id="back-to-map", n_clicks=0,
                                style={**style.BACK_BUTTON, "display": "none"}),
                ]),
                html.Div(id="breadcrumb", style=style.BREADCRUMB),
                html.Div(id="nav-panel", children=[
                    html.Div(style=style.PANEL, children=[
                        html.H3("Seleziona una piazza finanziaria",
                                style=style.PANEL_TITLE),
                        dcc.Graph(id="world-map",
                                  config={"displayModeBar": False}),
                    ]),
                ]),
                html.Div(id="market-page"),
            ],
        ),
    ],
)


# ---------------------------------------------------------------------------
# Step 1: asset class -> continent buttons
# ---------------------------------------------------------------------------

@callback(
    Output("continent-buttons", "children"),
    Input("asset-class", "value"),
)
def build_continent_buttons(asset_class):
    """Only continents where this asset class is actually traded are listed.

    Rebuilt on asset class change only: rebuilding them on every scope change
    would remount the buttons and retrigger their own click callback.
    """
    frame = markets_of_asset_class(asset_class)
    available = sorted({geography_of(code)["continent"]
                        for code in frame["market_code"]})
    labels = ["Mondo"] + [c for c in available if c in CONTINENT_SCOPE]
    return [
        html.Button(label, id={"type": "continent", "index": label},
                    n_clicks=0, style=style.CONTINENT_BUTTON)
        for label in labels
    ]


@callback(
    Output("selected-scope", "data"),
    Input({"type": "continent", "index": ALL}, "n_clicks"),
    Input("asset-class", "value"),
    prevent_initial_call=True,
)
def pick_scope(_clicks, _asset_class):
    """Store the continent the user asked for. Changing asset class resets it."""
    triggered = ctx.triggered_id
    if triggered == "asset-class":
        return "Mondo"
    if isinstance(triggered, dict) and triggered.get("type") == "continent":
        # Freshly mounted buttons report n_clicks = 0: that is not a click.
        if not ctx.triggered[0]["value"]:
            return no_update
        return triggered["index"]
    return no_update


@callback(
    Output({"type": "continent", "index": ALL}, "style"),
    Input("selected-scope", "data"),
    State({"type": "continent", "index": ALL}, "id"),
)
def highlight_active_continent(scope, button_ids):
    """Gold fill on the active continent. Styles only: no remount."""
    return [
        style.CONTINENT_BUTTON_ACTIVE if button["index"] == scope
        else style.CONTINENT_BUTTON
        for button in button_ids
    ]


# ---------------------------------------------------------------------------
# Step 2: world map
# ---------------------------------------------------------------------------

@callback(
    Output("world-map", "figure"),
    Input("asset-class", "value"),
    Input("selected-scope", "data"),
)
def draw_map(asset_class, scope_label):
    """One marker per exchange of the selected asset class."""
    frame = markets_of_asset_class(asset_class)
    scope = CONTINENT_SCOPE.get(scope_label, "world")

    if frame.empty:
        empty = go.Figure(go.Scattergeo(lat=[], lon=[]))
        return style.style_map(empty, scope)

    records = []
    for row in frame.itertuples():
        geo = geography_of(row.market_code)
        instruments = repository.list_instruments(row.market_code,
                                                  include_benchmark=True)
        records.append({
            "market_code": row.market_code,
            "label": row.label,
            "exchange": geo["exchange"],
            "lat": geo["lat"],
            "lon": geo["lon"],
            "strumenti": len(instruments),
        })
    points = pd.DataFrame(records)

    figure = go.Figure(go.Scattergeo(
        lat=points["lat"],
        lon=points["lon"],
        text=points["exchange"],
        customdata=points[["market_code", "label", "strumenti"]],
        mode="markers+text",
        textposition="top center",
        textfont={"color": style.COLORS["gold_soft"], "size": 11},
        marker={
            "size": 14,
            "color": style.COLORS["gold"],
            "line": {"width": 2, "color": style.COLORS["accent"]},
            "opacity": 0.9,
        },
        hovertemplate="<b>%{customdata[1]}</b><br>%{text}"
                      "<br>%{customdata[2]} strumenti<extra></extra>",
    ))
    return style.style_map(figure, scope)


@callback(
    Output("selected-market", "data"),
    Input("world-map", "clickData"),
    Input("asset-class", "value"),
    Input("back-to-map", "n_clicks"),
    prevent_initial_call=True,
)
def select_market(click_data, _asset_class, _back_clicks):
    """Enter an exchange by clicking its marker; leave it from the back button.
    Switching asset class also returns to the map."""
    triggered = ctx.triggered_id
    if triggered in ("asset-class", "back-to-map"):
        return None
    if click_data:
        return click_data["points"][0]["customdata"][0]
    return None


@callback(
    Output("world-map", "clickData"),
    Input("back-to-map", "n_clicks"),
    Input("asset-class", "value"),
    prevent_initial_call=True,
)
def clear_map_selection(_back_clicks, _asset_class):
    """Reset the stored click so the same marker can be opened twice in a row."""
    return None


@callback(
    Output("nav-panel", "style"),
    Output("back-to-map", "style"),
    Output("continent-buttons", "style"),
    Input("selected-market", "data"),
)
def toggle_navigation(market_code):
    """Hide the map while inside an exchange; never unmount it."""
    hidden = {"display": "none"}
    visible_buttons = {"display": "flex", "alignItems": "flex-end"}
    if market_code:
        return hidden, style.BACK_BUTTON, hidden
    return {}, {**style.BACK_BUTTON, "display": "none"}, visible_buttons


# ---------------------------------------------------------------------------
# Step 3: exchange page - security search and analysis tabs
# ---------------------------------------------------------------------------

@callback(
    Output("breadcrumb", "children"),
    Input("asset-class", "value"),
    Input("selected-market", "data"),
)
def build_breadcrumb(asset_class, market_code):
    parts = ["Dashboard", ASSET_CLASS_LABELS.get(asset_class, "—")]
    if market_code:
        geo = geography_of(market_code)
        parts += [geo["continent"], geo["exchange"]]
    return " / ".join(parts)


@callback(
    Output("market-page", "children"),
    Input("selected-market", "data"),
)
def render_market_page(market_code):
    """Securities listed on the selected exchange, plus the analysis area."""
    if not market_code:
        return []

    instruments = repository.list_instruments(market_code, include_benchmark=True)
    if instruments.empty:
        return html.Div("Nessuno strumento censito per questo mercato.",
                        style=style.EMPTY_STATE)

    options = [
        {"label": f"{'[Indice] ' if row.is_benchmark else ''}{row.name} "
                  f"({row.ticker})",
         "value": row.ticker}
        for row in instruments.itertuples()
    ]
    securities = instruments[instruments["is_benchmark"] == 0]
    default_value = (securities.iloc[0]["ticker"] if not securities.empty
                     else instruments.iloc[0]["ticker"])

    return html.Div([
        html.Div(style=style.PANEL, children=[
            html.H3("Strumenti quotati", style=style.PANEL_TITLE),
            html.Div(style=style.TOOLBAR, children=[
                html.Div([
                    html.Label("Cerca security", style=style.NAV_CHIP_LABEL),
                    dcc.Dropdown(
                        id="instrument",
                        options=options,
                        value=default_value,
                        clearable=False,
                        searchable=True,
                        placeholder="Digita il nome o il ticker...",
                        style={"width": "380px"},
                    ),
                ]),
                html.Div([
                    html.Label("Periodo", style=style.NAV_CHIP_LABEL),
                    dcc.DatePickerRange(
                        id="period",
                        start_date=date(2020, 1, 1),
                        end_date=date.today(),
                        display_format="DD/MM/YYYY",
                    ),
                ]),
                html.Div([
                    html.Label("Frequenza", style=style.NAV_CHIP_LABEL),
                    dcc.Dropdown(
                        id="frequency",
                        options=[{"label": "Giornaliera", "value": "D"},
                                 {"label": "Settimanale", "value": "W"},
                                 {"label": "Mensile", "value": "ME"},
                                 {"label": "Annuale", "value": "YE"}],
                        value="D", clearable=False,
                        style={"width": "170px"},
                    ),
                ]),
            ]),
        ]),

        dcc.Tabs(id="tabs", value="prices",
                 parent_className="custom-tabs",
                 className="custom-tabs",
                 children=[
                     dcc.Tab(label="Prezzi", value="prices",
                             className="custom-tab",
                             selected_className="custom-tab--selected"),
                     dcc.Tab(label="Rendimenti", value="returns",
                             className="custom-tab",
                             selected_className="custom-tab--selected"),
                     dcc.Tab(label="Rischio", value="risk",
                             className="custom-tab",
                             selected_className="custom-tab--selected"),
                     dcc.Tab(label="Statistiche di mercato", value="market",
                             className="custom-tab",
                             selected_className="custom-tab--selected"),
                 ]),
        html.Div(id="tab-content", style={"marginTop": "20px"}),
    ])


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
    return html.Div(style=style.TILE_ROW, children=[
        html.Div(style=style.TILE, children=[
            html.Div(key, style=style.TILE_LABEL),
            html.Div(_format_metric(key, value), style=style.TILE_VALUE),
        ])
        for key, value in values.items()
    ])


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
    return html.Div(style=style.PANEL,
                    children=[html.H3(title, style=style.PANEL_TITLE), *children])


def _graph(figure) -> dcc.Graph:
    return dcc.Graph(figure=figure, config={"displaylogo": False})


# ---------------------------------------------------------------------------
# Analysis tabs
# ---------------------------------------------------------------------------

@callback(
    Output("tab-content", "children"),
    Input("tabs", "value"),
    Input("instrument", "value"),
    Input("period", "start_date"),
    Input("period", "end_date"),
    Input("frequency", "value"),
    State("selected-market", "data"),
)
def render_tab(tab, ticker, start, end, frequency, market_code):
    if not market_code:
        return []

    if tab == "market":
        closes = repository.get_market_closes(market_code, start, end)
        if closes.empty:
            return html.Div("Nessun dato nel periodo selezionato.",
                            style=style.EMPTY_STATE)

        rebased = closes.apply(lambda column: column / column.dropna().iloc[0] * 100)
        comparison = style.style_figure(px.line(rebased), height=400)
        heatmap = style.style_figure(
            px.imshow(metrics.correlation_matrix(closes), text_auto=".2f",
                      color_continuous_scale="RdBu_r", zmin=-1, zmax=1,
                      aspect="auto"),
            height=400, show_legend=False)

        return html.Div([
            _panel("Indicatori aggregati di mercato",
                   _tiles(metrics.market_aggregates(closes))),
            _panel("Performance comparata (base 100)", _graph(comparison)),
            _panel("Statistiche cross-section",
                   _table(metrics.market_statistics(closes))),
            _panel("Matrice di correlazione", _graph(heatmap)),
        ])

    if not ticker:
        return html.Div("Seleziona uno strumento.", style=style.EMPTY_STATE)

    prices = repository.get_prices(ticker, start, end)
    if prices.empty:
        return html.Div("Nessun dato nel periodo selezionato.",
                        style=style.EMPTY_STATE)

    close = prices["adj_close"].fillna(prices["close"])

    if tab == "prices":
        blocks = [
            _panel("Serie storica",
                   _graph(style.style_figure(px.line(close), show_legend=False))),
            _panel("Performance cumulata (base 100)",
                   _graph(style.style_figure(
                       px.area(metrics.cumulative_return(close)),
                       show_legend=False))),
        ]
        fundamentals = repository.get_fundamentals(ticker)
        clean = {key.replace("_", " ").title(): value
                 for key, value in fundamentals.items()
                 if key != "ticker" and value is not None}
        if clean:
            blocks.append(_panel("Fondamentali", html.Div(
                style=style.TILE_ROW,
                children=[html.Div(style=style.TILE, children=[
                    html.Div(key, style=style.TILE_LABEL),
                    html.Div(f"{value:,.2f}".replace(",", "."),
                             style=style.TILE_VALUE),
                ]) for key, value in clean.items()])))
        dividends = repository.get_dividends(ticker)
        if not dividends.empty:
            bars = px.bar(dividends, x="date", y="amount")
            bars.update_traces(marker_color=style.COLORS["gold"])
            blocks.append(_panel("Dividendi", _graph(
                style.style_figure(bars, height=280, show_legend=False))))
        return html.Div(blocks)

    if tab == "returns":
        returns = metrics.resample_returns(close, frequency)
        bars = px.bar(returns * 100)
        bars.update_traces(marker_color=style.COLORS["accent"])
        histogram = px.histogram(returns * 100, nbins=60)
        histogram.update_traces(marker_color=style.COLORS["gold"])
        return html.Div([
            _panel("Rendimenti logaritmici (%)",
                   _graph(style.style_figure(bars, show_legend=False))),
            _panel("Distribuzione dei rendimenti",
                   _graph(style.style_figure(histogram, height=320,
                                             show_legend=False))),
        ])

    # tab == "risk"
    benchmark = pd.Series(dtype=float)
    catalogue = repository.list_instruments(market_code, include_benchmark=True)
    benchmarks = catalogue[catalogue["is_benchmark"] == 1]
    if not benchmarks.empty:
        benchmark_prices = repository.get_prices(
            benchmarks.iloc[0]["ticker"], start, end)
        if not benchmark_prices.empty:
            benchmark = (benchmark_prices["adj_close"]
                         .fillna(benchmark_prices["close"]))

    drawdown = px.area(metrics.drawdown_series(close) * 100)
    drawdown.update_traces(line_color=style.COLORS["negative"],
                           fillcolor="rgba(255,90,95,0.18)")
    rolling = px.line(metrics.rolling_volatility(close) * 100)

    return html.Div([
        _panel("Indicatori di rischio", _tiles(metrics.summary(close, benchmark))),
        _panel("Drawdown (%)",
               _graph(style.style_figure(drawdown, show_legend=False))),
        _panel("Volatilità annualizzata su finestra mobile 60 giorni (%)",
               _graph(style.style_figure(rolling, height=300, show_legend=False))),
    ])


if __name__ == "__main__":
    app.run(debug=True)
