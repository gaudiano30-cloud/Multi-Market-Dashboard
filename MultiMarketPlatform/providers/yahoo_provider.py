"""
Yahoo Finance Data Provider Module.

This module implements a financial data provider that
retrieves real market data from Yahoo Finance through
direct HTTP requests.

Its main responsibilities include:
    - Retrieving historical OHLCV market data.
    - Retrieving adjusted closing prices.
    - Retrieving historical dividend payments.
    - Retrieving financial fundamentals.
    - Converting dates into Unix timestamps.
    - Processing JSON responses from external endpoints.
    - Standardizing financial data into Pandas DataFrames.
    - Handling request failures through retry mechanisms.

The YahooFinanceProvider class implements the DataProvider
interface, allowing the platform to retrieve real financial
data independently of its analytical and presentation
components.
"""

import time
from datetime import datetime, timezone

import pandas as pd
import requests  # libreria Python esterna che permette di effettuare richieste HTTP

from .base import DataProvider

# indirizzo per recuperare le serie storiche finanziarie
CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"

# indirizzo per recuperare informazioni sintetiche e fondamentali degli strumenti finanziari
QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"

# software cliente che effettua la richiesta
HEADERS = {"User-Agent": "Mozilla/5.0"}

MAX_RETRIES = 3  # numero max di tentativi
RETRY_WAIT = 2  # secondi di pausa dopo un tentativo fallito


def _to_unix(date_string: str) -> int:
    """'Questa funzione converte una data rappresentata come stringa in un Unix timestamp.
    Questa conversione è necessaria perché il nostro codice invia le date all'endpoint Yahoo Finance sotto forma di timestamp.
    L'underscore iniziale indica che la funzione è destinata principalmente all'utilizzo interno del modulo."""
    return int(datetime.strptime(date_string, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


class YahooFinanceProvider(DataProvider):
    name = "yahoo"

    def _fetch_chart(self, ticker: str, start: str, end: str) -> dict | None:
        """Single API call with retries. Returns the 'result' payload."""
        # dizionario contenente i parametri che accompagneranno la richiesta HTTP
        params = {
            "period1": _to_unix(start),
            "period2": _to_unix(end),
            "interval": "1d",  # frequenza delle osservazioni (qui giornaliere)
            "events": "div,splits",  # eventi finanziari richiesti (dividendi e stock split)
        }
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get(
                    CHART_URL.format(ticker=ticker),
                    params=params,
                    headers=HEADERS,
                    timeout=30,
                )  # istruzione che effettua concretamente la richiesta al server esterno
                response.raise_for_status()  # controllo dello status HTTP
                chart = response.json()["chart"]  # converte il contenuto JSON della risposta in oggetti Python
                if chart.get("error"):
                    raise ValueError(chart["error"])
                results = chart.get("result")
                if not results:
                    raise ValueError("Nessun dato disponibile")
                return results[0]
            except Exception as error:
                print(f"[yahoo] attempt number {attempt + 1}/{MAX_RETRIES} " f"failed for {ticker}: {error}")
                time.sleep(RETRY_WAIT)
        print(
            f"[yahoo] ATTENTION: impossible downloading for {ticker}"
        )  # nessuno dei tre tentativi ha avuto successo
        return None

    def get_prices(self, ticker: str, start: str, end: str) -> pd.DataFrame | None:
        payload = self._fetch_chart(ticker, start, end)  # contenuto informativo ricevuto
        if payload is None:
            return None

        indicators = payload["indicators"]
        quote = indicators["quote"][0]  # dizionario relativo a prezzi e volumi
        adjclose = indicators.get("adjclose")

        # trasformare i timestamp restituiti da Yahoo Finance in un indice temporale Pandas
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
        frame.index.name = "date"  # assegniamo il nome date all'indice del dataframe
        return frame.dropna(
            subset=["close"]
        )  # eliminiamo le righe che contengono valori mancanti nella colonna close

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
        """Si occupa di recuperare i fondamentali finanziari attraverso un endpoint differente da quello utilizzato per i prezzi.
        Snapshot metrics. Yahoo throttles this endpoint, so failures are
        tolerated: the ETL stores whatever comes back."""
        try:
            # Effettuiamo una richiesta HTTP passando come parametro solamente il ticker.
            # Non specifichiamo un intervallo temporale perché vogliamo recuperare uno snapshot delle informazioni fondamentali disponibili.
            response = requests.get(
                QUOTE_URL,
                params={"symbols": ticker},
                headers=HEADERS,
                timeout=30,
            )
            response.raise_for_status()
            # Convertiamo il JSON in oggetti Python e accediamo ai risultati
            rows = response.json()["quoteResponse"]["result"]
            # Se non sono disponibili informazioni, restituiamo un dizionario vuoto.
            # Altrimenti recuperiamo il primo risultato.
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
            print(f"[yahoo] fundamentals not available for {ticker}: {error}")
            return {}
