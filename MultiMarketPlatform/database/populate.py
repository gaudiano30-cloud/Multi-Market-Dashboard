"""ETL: catalog first, optional price download from a data provider.

Safe commands (run from project root):
    python -m database.populate --catalog-only
    python -m database.populate --new-only --start 2020-01-01
    python -m database.populate --market EQ_US_NASDAQ --start 2020-01-01
    python -m database.populate --mock --new-only --start 2024-01-01

The '--mock' flag generates SYNTHETIC prices, never use it as real data.
"""
import argparse
from datetime import date, datetime

from config import BENCHMARKS, HISTORY_START, MARKETS
from providers.base import DataProvider
from providers.mock_provider import MockProvider
from providers.yahoo_provider import YahooFinanceProvider
from .connection import get_connection, initialise_schema


def _load_catalogue(connection) -> None:
    """Upsert, never REPLACE: existing historical prices stay linked to tickers."""
    for code, market in MARKETS.items():
        connection.execute(
            """INSERT INTO markets
               (market_code, label, asset_class, currency, region, city, latitude, longitude, kind)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(market_code) DO UPDATE SET
                 label=excluded.label, asset_class=excluded.asset_class,
                 currency=excluded.currency, region=excluded.region,
                 city=excluded.city, latitude=excluded.latitude,
                 longitude=excluded.longitude, kind=excluded.kind""",
            (code, market["label"], market["asset_class"], market["currency"],
             market["region"], market["city"], market["latitude"],
             market["longitude"], market["kind"]),
        )
        instruments = dict(market["instruments"])
        if market.get("benchmark"):
            benchmark = market["benchmark"]
            instruments[benchmark] = BENCHMARKS.get(benchmark, benchmark)
        for ticker, name in instruments.items():
            is_benchmark = int(ticker == market.get("benchmark"))
            connection.execute(
                """INSERT INTO instruments (ticker, name, market_code, is_benchmark)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(ticker) DO UPDATE SET
                     name=excluded.name, market_code=excluded.market_code,
                     is_benchmark=excluded.is_benchmark""",
                (ticker, name, code, is_benchmark),
            )


def _write_metadata(connection, ticker, provider, status, rows=0, message=None):
    connection.execute(
        """INSERT INTO metadata
           (ticker, provider, last_update, status, rows_loaded, message)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(ticker) DO UPDATE SET
             provider=excluded.provider, last_update=excluded.last_update,
             status=excluded.status, rows_loaded=excluded.rows_loaded,
             message=excluded.message""",
        (ticker, provider, datetime.now().isoformat(timespec="seconds"),
         status, rows, message),
    )


def _load_instrument(connection, provider: DataProvider, ticker: str,
                     start: str, end: str) -> None:
    try:
        prices = provider.get_prices(ticker, start, end)
        if prices is None or prices.empty:
            _write_metadata(connection, ticker, provider.name, "FAILED",
                            message="nessun dato restituito")
            print(f"  {ticker}: nessun dato")
            return

        rows = [
            (ticker, index.strftime("%Y-%m-%d"), row.get("open"),
             row.get("high"), row.get("low"), row["close"], row.get("adj_close"),
             int(row["volume"]) if row.get("volume") == row.get("volume") else None)
            for index, row in prices.iterrows()
        ]
        connection.executemany(
            "INSERT OR REPLACE INTO prices VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows
        )

        dividends = provider.get_dividends(ticker, start, end)
        if dividends is not None and not dividends.empty:
            connection.executemany(
                "INSERT OR REPLACE INTO dividends VALUES (?, ?, ?)",
                [(ticker, d.strftime("%Y-%m-%d"), float(a))
                 for d, a in zip(dividends["date"], dividends["amount"])],
            )

        snapshot = provider.get_fundamentals(ticker)
        if snapshot:
            connection.execute(
                """INSERT INTO fundamentals
                   (ticker, market_cap, pe_ratio, eps, pb_ratio, dividend_yield)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(ticker) DO UPDATE SET
                     market_cap=excluded.market_cap, pe_ratio=excluded.pe_ratio,
                     eps=excluded.eps, pb_ratio=excluded.pb_ratio,
                     dividend_yield=excluded.dividend_yield""",
                (ticker, snapshot.get("market_cap"), snapshot.get("pe_ratio"),
                 snapshot.get("eps"), snapshot.get("pb_ratio"),
                 snapshot.get("dividend_yield")),
            )
        _write_metadata(connection, ticker, provider.name, "OK", len(rows))
        print(f"  {ticker}: {len(rows)} osservazioni")
    except Exception as error:
        _write_metadata(connection, ticker, provider.name, "FAILED", message=str(error)[:500])
        print(f"  {ticker}: ERRORE {error}")


def run(provider: DataProvider | None = None, start: str = HISTORY_START,
        end: str | None = None, *, catalog_only: bool = False,
        new_only: bool = False, markets: list[str] | None = None) -> None:
    """Update market/instrument catalogue, then optionally download price history."""
    end = end or date.today().isoformat()
    selected = markets or list(MARKETS)
    unknown = sorted(set(selected) - set(MARKETS))
    if unknown:
        raise ValueError(f"Market code sconosciuto: {', '.join(unknown)}")

    initialise_schema()
    with get_connection() as connection:
        _load_catalogue(connection)
        connection.commit()
        count = connection.execute("SELECT COUNT(*) AS n FROM markets").fetchone()["n"]
        print(f"Catalogo aggiornato: {count} mercati. Dati storici preesistenti preservati.")

        if catalog_only:
            return
        if provider is None:
            provider = YahooFinanceProvider()

        for code in selected:
            market = MARKETS[code]
            tickers = list(market["instruments"])
            if market["benchmark"]:
                tickers.append(market["benchmark"])
            if not tickers:
                print(f"\n{market['name']}: nessun ticker affidabile ancora configurato")
                continue
            print(f"\n{market['label']}")
            for ticker in tickers:
                if new_only:
                    row = connection.execute(
                        "SELECT 1 FROM prices WHERE ticker = ? LIMIT 1", (ticker,)
                    ).fetchone()
                    if row:
                        print(f"  {ticker}: storico già presente, salto")
                        continue
                _load_instrument(connection, provider, ticker, start, end)
                connection.commit()
    print("\nPopolamento completato.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Catalogo ed ETL mercati MFE")
    parser.add_argument("--catalog-only", action="store_true", help="Non scarica dati")
    parser.add_argument("--new-only", action="store_true", help="Non riscarica i ticker con uno storico")
    parser.add_argument("--market", action="append", dest="markets", metavar="CODICE",
                        help="Scarica una sola voce del catalogo; ripetibile")
    parser.add_argument("--mock", action="store_true", help="SOLO dati fittizi di prova")
    parser.add_argument("--start", default=HISTORY_START)
    args = parser.parse_args()
    provider = None if args.catalog_only else (MockProvider() if args.mock else YahooFinanceProvider())
    print(f"Provider: {'solo catalogo' if args.catalog_only else provider.name}")
    run(provider, start=args.start, catalog_only=args.catalog_only,
        new_only=args.new_only, markets=args.markets)
