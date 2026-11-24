"""Yahoo Finance provider: your original download routine, wrapped in the
DataProvider interface. Uses the public chart endpoint directly, so there is
no third-party client library to break.
"""
import time
from datetime import datetime, timezone

import pandas as pd
import requests

from .base import DataProvider

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"
HEADERS = {"User-Agent": "Mozilla/5.0"}
MAX_RETRIES = 3
RETRY_WAIT = 2


def _to_unix(date_string: str) -> int:
    """'2015-01-01' -> Unix timestamp in seconds, UTC."""
    return int(
        datetime.strptime(date_string, "%Y-%m-%d")
        .replace(tzinfo=timezone.utc)
        .timestamp()
    )


class YahooFinanceProvider(DataProvider):
    name = "yahoo"

    def _fetch_chart(self, ticker: str, start: str, end: str) -> dict | None:
        """Single API call with retries. Returns the 'result' payload."""
        params = {
            "period1": _to_unix(start),
            "period2": _to_unix(end),
            "interval": "1d",
            "events": "div,splits",
        }
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get(
                    CHART_URL.format(ticker=ticker),
                    params=params,
                    headers=HEADERS,
                    timeout=30,
                )
                response.raise_for_status()
                chart = response.json()["chart"]
                if chart.get("error"):
                    raise ValueError(chart["error"])
                results = chart.get("result")
                if not results:
                    raise ValueError("Nessun dato disponibile")
                return results[0]
            except Exception as error:
                print(f"[yahoo] tentativo {attempt + 1}/{MAX_RETRIES} "
                      f"fallito per {ticker}: {error}")
                time.sleep(RETRY_WAIT)
        print(f"[yahoo] ATTENZIONE: impossibile scaricare {ticker}")
        return None

    def get_prices(self, ticker: str, start: str, end: str) -> pd.DataFrame | None:
        payload = self._fetch_chart(ticker, start, end)
        if payload is None:
            return None

        indicators = payload["indicators"]
        quote = indicators["quote"][0]
        adjclose = indicators.get("adjclose")

        dates = (
            pd.to_datetime(payload["timestamp"], unit="s", utc=True)
            .tz_convert("Europe/Rome")
            .tz_localize(None)
            .normalize()
        )

        frame = pd.DataFrame(
            {
                "open": quote.get("open"),
                "high": quote.get("high"),
                "low": quote.get("low"),
                "close": quote.get("close"),
                "volume": quote.get("volume"),
                "adj_close": (
                    adjclose[0]["adjclose"]
                    if adjclose and adjclose[0].get("adjclose") is not None
                    else quote.get("close")
                ),
            },
            index=dates,
        )
        frame.index.name = "date"
        return frame.dropna(subset=["close"])

    def get_dividends(self, ticker: str, start: str, end: str) -> pd.DataFrame:
        payload = self._fetch_chart(ticker, start, end)
        empty = pd.DataFrame(columns=["date", "amount"])
        if payload is None:
            return empty

        events = payload.get("events", {}).get("dividends", {})
        if not events:
            return empty

        records = [
            {
                "date": pd.to_datetime(item["date"], unit="s").normalize(),
                "amount": item["amount"],
            }
            for item in events.values()
        ]
        return pd.DataFrame(records).sort_values("date").reset_index(drop=True)

    def get_fundamentals(self, ticker: str) -> dict:
        """Snapshot metrics. Yahoo throttles this endpoint, so failures are
        tolerated: the ETL stores whatever comes back."""
        try:
            response = requests.get(
                QUOTE_URL,
                params={"symbols": ticker},
                headers=HEADERS,
                timeout=30,
            )
            response.raise_for_status()
            rows = response.json()["quoteResponse"]["result"]
            if not rows:
                return {}
            row = rows[0]
            return {
                "market_cap": row.get("marketCap"),
                "pe_ratio": row.get("trailingPE"),
                "eps": row.get("epsTrailingTwelveMonths"),
                "pb_ratio": row.get("priceToBook"),
                "dividend_yield": row.get("trailingAnnualDividendYield"),
            }
        except Exception as error:
            print(f"[yahoo] fondamentali non disponibili per {ticker}: {error}")
            return {}