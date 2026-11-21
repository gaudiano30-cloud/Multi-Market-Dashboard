"""Read-only access layer used by the dashboard."""
import pandas as pd

from .connection import get_connection


def list_markets() -> pd.DataFrame:
    query = "SELECT market_code, label, asset_class, currency FROM markets ORDER BY label"
    with get_connection(read_only=True) as connection:
        return pd.read_sql_query(query, connection)


def list_instruments(market_code: str, include_benchmark: bool = False) -> pd.DataFrame:
    query = """
        SELECT ticker, name, is_benchmark
        FROM instruments
        WHERE market_code = ?
          AND (is_benchmark = 0 OR ? = 1)
        ORDER BY name
    """
    with get_connection(read_only=True) as connection:
        return pd.read_sql_query(
            query, connection, params=(market_code, int(include_benchmark))
        )


def get_prices(ticker: str, start: str | None = None, end: str | None = None) -> pd.DataFrame:
    """Price history for one instrument, indexed by date."""
    query = "SELECT date, open, high, low, close, adj_close, volume FROM prices WHERE ticker = ?"
    params: list = [ticker]
    if start:
        query += " AND date >= ?"
        params.append(start)
    if end:
        query += " AND date <= ?"
        params.append(end)
    query += " ORDER BY date"

    with get_connection(read_only=True) as connection:
        frame = pd.read_sql_query(query, connection, params=params,
                                  parse_dates=["date"])
    return frame.set_index("date")


def get_market_closes(market_code: str, start: str | None = None,
                      end: str | None = None) -> pd.DataFrame:
    """Close prices of every instrument in a market: one column per ticker.

    Built with a JOIN so the filtering happens in SQL, not in pandas.
    """
    query = """
        SELECT p.date, i.name, p.adj_close
        FROM prices p
        JOIN instruments i ON i.ticker = p.ticker
        WHERE i.market_code = ? AND i.is_benchmark = 0
    """
    params: list = [market_code]
    if start:
        query += " AND p.date >= ?"
        params.append(start)
    if end:
        query += " AND p.date <= ?"
        params.append(end)

    with get_connection(read_only=True) as connection:
        frame = pd.read_sql_query(query, connection, params=params,
                                  parse_dates=["date"])
    if frame.empty:
        return frame
    return frame.pivot(index="date", columns="name", values="adj_close").sort_index()


def get_dividends(ticker: str) -> pd.DataFrame:
    query = "SELECT date, amount FROM dividends WHERE ticker = ? ORDER BY date"
    with get_connection(read_only=True) as connection:
        return pd.read_sql_query(query, connection, params=(ticker,),
                                 parse_dates=["date"])


def get_fundamentals(ticker: str) -> dict:
    query = "SELECT * FROM fundamentals WHERE ticker = ?"
    with get_connection(read_only=True) as connection:
        row = connection.execute(query, (ticker,)).fetchone()
    return dict(row) if row else {}


def get_metadata() -> pd.DataFrame:
    query = """
        SELECT m.ticker, i.name, m.provider, m.last_update, m.status, m.rows_loaded
        FROM metadata m
        JOIN instruments i ON i.ticker = m.ticker
        ORDER BY m.last_update DESC
    """
    with get_connection(read_only=True) as connection:
        return pd.read_sql_query(query, connection)


def last_update_label() -> str:
    with get_connection(read_only=True) as connection:
        row = connection.execute(
            "SELECT MAX(last_update) AS ts, provider FROM metadata"
        ).fetchone()
    if not row or not row["ts"]:
        return "database vuoto"
    return f"dati aggiornati al {row['ts'][:16].replace('T', ' ')} - fonte: {row['provider']}"