"""
Synthetic Financial Data Provider Module.

This module implements a mock financial data provider
that generates synthetic market data without requiring
access to external financial data sources.

Its main responsibilities include:
    - Simulating historical price series using a
      geometric Brownian motion-style model.
    - Generating synthetic OHLCV market data.
    - Simulating dividend payments.
    - Generating synthetic financial fundamentals.
    - Supporting offline demonstrations and testing.

The MockProvider class implements the DataProvider
interface, allowing synthetic financial data to be used
as an alternative to real market data for development,
testing and demonstration purposes.
"""

import numpy as np
import pandas as pd

from .base import DataProvider


class MockProvider(DataProvider):
    # classe che eredita da DataProvider; siamo obbligati a implementare gli abstract methods
    name = "mock"  # overrriding dell'attributo della classe madre

    def __init__(self, seed: int = 42, annual_vol: float = 0.25, drift: float = 0.05):
        self._seed = seed  # valore iniziale del generatore pseudocasuale
        self._annual_vol = annual_vol  # volatilità annualizzata del 25%
        self._drift = drift  # parametro di crescita media annuale del 5%
        # ci permette di creare provider caratterizzati da condizioni di mercato differenti

    def get_prices(self, ticker: str, start: str, end: str) -> pd.DataFrame:

        rng = np.random.default_rng(self._seed + abs(hash(ticker)) % 10_000)
        dates = pd.bdate_range(start=start, end=end, name="date")
        steps = len(dates)  # numero osservazioni temporali

        daily_vol = self._annual_vol / np.sqrt(252)  # ocnversione della volatilità
        daily_drift = self._drift / 252  # conversione del drift
        shocks = rng.normal(daily_drift, daily_vol, steps)
        close = 100 * np.exp(
            np.cumsum(shocks)
        )  # prezzi di chiusura (artificiali, generati mediante il modello stocastico)

        return pd.DataFrame(
            {
                "open": close * (1 + rng.normal(0, 0.002, steps)),
                "high": close * (1 + abs(rng.normal(0, 0.004, steps))),
                "low": close * (1 - abs(rng.normal(0, 0.004, steps))),
                "close": close,
                "volume": rng.integers(1e5, 5e6, steps),  # volumid i negoziazione casuali
                "adj_close": close,
            },
            index=dates,
        )

    def get_dividends(self, ticker: str, start: str, end: str) -> pd.DataFrame:
        dates = pd.date_range(start=start, end=end, freq="2QE")
        # tutti gli strumenti finanziari ricevono lo stesso schema sintetico di dividendi
        return pd.DataFrame({"date": dates, "amount": [0.35] * len(dates)})

    def get_fundamentals(self, ticker: str) -> dict:
        # il metodo genera artificialmente alcuni indicatori fondamentali
        rng = np.random.default_rng(abs(hash(ticker)) % 10_000)
        return {
            "market_cap": float(rng.integers(1e9, 9e10)),
            "pe_ratio": round(float(rng.uniform(8, 28)), 2),
            "eps": round(float(rng.uniform(0.5, 6)), 2),
            "pb_ratio": round(float(rng.uniform(0.6, 4)), 2),
            "dividend_yield": round(float(rng.uniform(0, 0.06)), 4),
        }
