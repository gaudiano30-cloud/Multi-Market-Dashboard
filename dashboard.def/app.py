"""Dash entry point. Layout and callbacks only: every number on screen comes
from analytics, every row of data from the repository.
"""
from datetime import date

import pandas as pd
import plotly.express as px
from dash import Dash, Input, Output, callback, dash_table, dcc, html

from analytics import metrics
from database import repository

app = Dash(__name__, title="Multi Market Platform")
server = app.server  # entry point for gunicorn when deploying

MARKETS = repository.list_markets()

app.layout = html.Div(
    style={"maxWidth": "1200px", "margin": "0 auto",
           "fontFamily": "system-ui, sans-serif", "padding": "24px"},
    children=[
        html.H1("Multi Market Analysis Platform"),
        html.P(repository.last_update_label(),
               style={"color": "#666", "fontSize": "14px"}),

        html.Div(
            style={"display": "flex", "gap": "16px", "flexWrap": "wrap",
                   "marginBottom": "24px"},
            children=[
                html.Div([
                    html.Label("Mercato"),
                    dcc.Dropdown(
                        id="market",
                        options=[{"label": r.label, "value": r.market_code}
                                 for r in MARKETS.itertuples()],
                        value=MARKETS.iloc[0]["market_code"] if not MARKETS.empty else None,
                        clearable=False,
                    ),
                ], style={"minWidth": "280px"}),

                html.Div([
                    html.Label("Strumento"),
                    dcc.Dropdown(id="instrument", clearable=False),
                ], style={"minWidth": "260px"}),

                html.Div([
                    html.Label("Periodo"),
                    dcc.DatePickerRange(
                        id="period",
                        start_date=date(2020, 1, 1),
                        end_date=date.today(),
                        display_format="DD/MM/YYYY",
                    ),
                ]),

                html.Div([
                    html.Label("Frequenza rendimenti"),
                    dcc.Dropdown(
                        id="frequency",
                        options=[
                            {"label": "Giornaliera", "value": "D"},
                            {"label": "Settimanale", "value": "W"},
                            {"label": "Mensile", "value": "ME"},
                            {"label": "Annuale", "value": "YE"},
                        ],
                        value="D", clearable=False,
                    ),
                ], style={"minWidth": "200px"}),
            ],
        ),

        dcc.Tabs(id="tabs", value="prices", children=[
            dcc.Tab(label="Prezzi", value="prices"),
            dcc.Tab(label="Rendimenti", value="returns"),
            dcc.Tab(label="Rischio", value="risk"),
            dcc.Tab(label="Statistiche di mercato", value="market"),
        ]),

        html.Div(id="tab-content", style={"marginTop": "24px"}),
    ],
)


@callback(
    Output("instrument", "options"),
    Output("instrument", "value"),
    Input("market", "value"),
)
def refresh_instruments(market_code):
    """The instrument dropdown depends on the selected market."""
    if not market_code:
        return [], None
    frame = repository.list_instruments(market_code)
    options = [{"label": r.name, "value": r.ticker} for r in frame.itertuples()]
    return options, (options[0]["value"] if options else None)


def _metrics_table(values: dict) -> dash_table.DataTable:
    rows = [
        {"Metrica": key,
         "Valore": f"{value:,.0f}" if key == "Osservazioni"
                   else (f"{value:.2%}" if abs(value) < 10 and "Sharpe" not in key
                         and "Beta" not in key else f"{value:.2f}")}
        for key, value in values.items()
    ]
    return dash_table.DataTable(
        data=rows,
        columns=[{"name": c, "id": c} for c in ("Metrica", "Valore")],
        style_cell={"textAlign": "left", "padding": "8px",
                    "fontFamily": "system-ui"},
        style_header={"fontWeight": "600", "backgroundColor": "#f4f4f4"},
    )


@callback(
    Output("tab-content", "children"),
    Input("tabs", "value"),
    Input("market", "value"),
    Input("instrument", "value"),
    Input("period", "start_date"),
    Input("period", "end_date"),
    Input("frequency", "value"),
)
def render_tab(tab, market_code, ticker, start, end, frequency):
    if not market_code:
        return html.P("Nessun mercato disponibile: lancia prima lo script di popolamento.")

    if tab == "market":
        closes = repository.get_market_closes(market_code, start, end)
        if closes.empty:
            return html.P("Nessun dato per questo mercato nel periodo selezionato.")

        statistics = metrics.market_statistics(closes)
        correlations = metrics.correlation_matrix(closes)
        rebased = closes.apply(lambda column: column / column.dropna().iloc[0] * 100)

        return html.Div([
            html.H3("Confronto strumenti (base 100)"),
            dcc.Graph(figure=px.line(rebased, labels={"value": "Base 100",
                                                      "date": "Data"})),
            html.H3("Statistiche cross-section"),
            dash_table.DataTable(
                data=statistics.round(2).to_dict("records"),
                columns=[{"name": c, "id": c} for c in statistics.columns],
                style_cell={"padding": "8px", "fontFamily": "system-ui"},
                style_header={"fontWeight": "600", "backgroundColor": "#f4f4f4"},
                sort_action="native",
            ),
            html.H3("Matrice di correlazione"),
            dcc.Graph(figure=px.imshow(correlations, text_auto=".2f",
                                       color_continuous_scale="RdBu_r",
                                       zmin=-1, zmax=1, aspect="auto")),
        ])

    if not ticker:
        return html.P("Seleziona uno strumento.")

    prices = repository.get_prices(ticker, start, end)
    if prices.empty:
        return html.P("Nessun dato nel periodo selezionato.")

    close = prices["adj_close"].fillna(prices["close"])

    if tab == "prices":
        dividends = repository.get_dividends(ticker)
        fundamentals = repository.get_fundamentals(ticker)
        children = [
            html.H3("Serie storica"),
            dcc.Graph(figure=px.line(close, labels={"value": "Prezzo", "date": "Data"})),
            html.H3("Performance cumulata (base 100)"),
            dcc.Graph(figure=px.area(metrics.cumulative_return(close),
                                     labels={"value": "Base 100", "date": "Data"})),
        ]
        if fundamentals:
            children += [html.H3("Fondamentali"), _metrics_table(
                {k.replace("_", " ").title(): v
                 for k, v in fundamentals.items() if k != "ticker" and v is not None}
            )]
        if not dividends.empty:
            children += [html.H3("Dividendi"),
                         dcc.Graph(figure=px.bar(dividends, x="date", y="amount"))]
        return html.Div(children)

    if tab == "returns":
        returns = metrics.resample_returns(close, frequency)
        return html.Div([
            html.H3("Rendimenti logaritmici"),
            dcc.Graph(figure=px.bar(returns * 100,
                                    labels={"value": "Rendimento (%)", "date": "Data"})),
            html.H3("Distribuzione"),
            dcc.Graph(figure=px.histogram(returns * 100, nbins=60,
                                          labels={"value": "Rendimento (%)"})),
        ])

    # tab == "risk"
    benchmark_frame = repository.list_instruments(market_code, include_benchmark=True)
    benchmark_rows = benchmark_frame[benchmark_frame["is_benchmark"] == 1]
    benchmark = pd.Series(dtype=float)
    if not benchmark_rows.empty:
        benchmark_prices = repository.get_prices(
            benchmark_rows.iloc[0]["ticker"], start, end)
        if not benchmark_prices.empty:
            benchmark = benchmark_prices["adj_close"].fillna(benchmark_prices["close"])

    drawdown = close / close.cummax() - 1
    return html.Div([
        html.H3("Indicatori di rischio"),
        _metrics_table(metrics.summary(close, benchmark)),
        html.H3("Drawdown"),
        dcc.Graph(figure=px.area(drawdown * 100,
                                 labels={"value": "Drawdown (%)", "date": "Data"})),
    ])


if __name__ == "__main__":
    app.run(debug=True)