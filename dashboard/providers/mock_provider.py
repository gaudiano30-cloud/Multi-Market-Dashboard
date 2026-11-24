"""Synthetic provider: geometric Brownian motion. Satisfies the 'at least two
providers' requirement and lets the app be demoed with no internet access.
"""
import numpy as np
import pandas as pd

from .base import DataProvider


class MockProvider(DataProvider):
    name = "mock"

    def __init__(self, seed: int = 42, annual_vol: float = 0.25, drift: float = 0.05):
        self._seed = seed
        self._annual_vol = annual_vol
        self._drift = drift

    def get_prices(self, ticker: str, start: str, end: str) -> pd.DataFrame:
        # Seed derived from the ticker: same instrument, same series, always.
        rng = np.random.default_rng(self._seed + abs(hash(ticker)) % 10_000)
        dates = pd.bdate_range(start=start, end=end, name="date")
        steps = len(dates)

        daily_vol = self._annual_vol / np.sqrt(252)
        daily_drift = self._drift / 252
        shocks = rng.normal(daily_drift, daily_vol, steps)
        close = 100 * np.exp(np.cumsum(shocks))

        return pd.DataFrame(
            {
                "open": close * (1 + rng.normal(0, 0.002, steps)),
                "high": close * (1 + abs(rng.normal(0, 0.004, steps))),
                "low": close * (1 - abs(rng.normal(0, 0.004, steps))),
                "close": close,
                "volume": rng.integers(1e5, 5e6, steps),
                "adj_close": close,
            },
            index=dates,
        )

    def get_dividends(self, ticker: str, start: str, end: str) -> pd.DataFrame:
        dates = pd.date_range(start=start, end=end, freq="2QE")
        return pd.DataFrame({"date": dates, "amount": [0.35] * len(dates)})

    def get_fundamentals(self, ticker: str) -> dict:
        rng = np.random.default_rng(abs(hash(ticker)) % 10_000)
        return {
            "market_cap": float(rng.integers(1e9, 9e10)),
            "pe_ratio": round(float(rng.uniform(8, 28)), 2),
            "eps": round(float(rng.uniform(0.5, 6)), 2),
            "pb_ratio": round(float(rng.uniform(0.6, 4)), 2),
            "dividend_yield": round(float(rng.uniform(0, 0.06)), 4),
        }