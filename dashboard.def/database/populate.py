"""ETL: download from a provider and load the database.

Run from the project root:
    python -m database.populate            # Yahoo Finance
    python -m database.populate --mock     # synthetic data, no internet
"""
import argparse
from datetime import date, datetime

from config import BENCHMARKS, HISTORY_START, MARKETS
from providers.base import DataProvider
from providers.mock_provider import MockProvider
from providers.yahoo_provider import YahooFinanceProvider

from .connection import get_connection, initialise_schema


def _load_catalogue(connection) -> None:
    """Markets and instruments come from config.py: the database mirrors it."""
    for code, market in MARKETS.items():
        connection.execute(
            "INSERT OR REPLACE INTO markets VALUES (?, ?, ?, ?)",
            (code, market["label"], market["asset_class"], market["currency"]),
        )
        for ticker, name in market["instruments"].items():
            connection.execute(
                "INSERT OR REPLACE INTO instruments VALUES (?, ?, ?, 0)",
                (ticker, name, code),
            )
        benchmark = market.get("benchmark")
        if benchmark:
            connection.execute(
                "INSERT OR REPLACE INTO instruments VALUES (?, ?, ?, 1)",
                (benchmark, BENCHMARKS.get(benchmark, benchmark), code),
            )
    connection.commit()


def _write_metadata(connection, ticker, provider, status, rows=0, message=None):
    connection.execute(
        "INSERT OR REPLACE INTO metadata VALUES (?, ?, ?, ?, ?, ?)",
        (ticker, provider, datetime.now().isoformat(timespec="seconds"),
         status, rows, message),
    )


def _load_instrument(connection, provider: DataProvider, ticker: str,
                     start: str, end: str) -> None:
    prices = provider.get_prices(ticker, start, end)
    if prices is None or prices.empty:
        _write_metadata(connection, ticker, provider.name, "FAILED",
                        message="nessun dato restituito")
        print(f"  {ticker}: FALLITO")
        return

    rows = [
        (ticker, index.strftime("%Y-%m-%d"),
         row.get("open"), row.get("high"), row.get("low"),
         row["close"], row.get("adj_close"),
         int(row["volume"]) if row.get("volume") == row.get("volume") else None)
        for index, row in prices.iterrows()
    ]
    connection.executemany(
        "INSERT OR REPLACE INTO prices VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows
    )

    dividends = provider.get_dividends(ticker, start, end)
    if not dividends.empty:
        connection.executemany(
            "INSERT OR REPLACE INTO dividends VALUES (?, ?, ?)",
            [(ticker, d.strftime("%Y-%m-%d"), float(a))
             for d, a in zip(dividends["date"], dividends["amount"])],
        )

    snapshot = provider.get_fundamentals(ticker)
    if snapshot:
        connection.execute(
            """INSERT OR REPLACE INTO fundamentals
               VALUES (?, ?, ?, ?, ?, ?)""",
            (ticker, snapshot.get("market_cap"), snapshot.get("pe_ratio"),
             snapshot.get("eps"), snapshot.get("pb_ratio"),
             snapshot.get("dividend_yield")),
        )

    _write_metadata(connection, ticker, provider.name, "OK", len(rows))
    print(f"  {ticker}: {len(rows)} osservazioni")


def run(provider: DataProvider, start: str = HISTORY_START,
        end: str | None = None) -> None:
    end = end or date.today().isoformat()
    initialise_schema()

    with get_connection() as connection:
        _load_catalogue(connection)
        for code, market in MARKETS.items():
            print(f"\n{market['label']}")
            tickers = list(market["instruments"])
            if market.get("benchmark"):
                tickers.append(market["benchmark"])
            for ticker in tickers:
                _load_instrument(connection, provider, ticker, start, end)
            connection.commit()

    print("\nPopolamento completato.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Popola il database di mercato.")
    parser.add_argument("--mock", action="store_true",
                        help="usa il provider simulato invece di Yahoo Finance")
    parser.add_argument("--start", default=HISTORY_START)
    arguments = parser.parse_args()

    selected = MockProvider() if arguments.mock else YahooFinanceProvider()
    print(f"Provider: {selected.name}")
    run(selected, start=arguments.start)