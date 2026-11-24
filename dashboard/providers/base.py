"""Abstract data provider. The rest of the application never imports a
concrete provider: it receives one. Adding a third source (Bloomberg,
Refinitiv, a CSV dump) means subclassing this and nothing else.
"""
from abc import ABC, abstractmethod

import pandas as pd


class DataProvider(ABC):
    """Contract every market data source must satisfy."""

    name: str = "abstract"

    @abstractmethod
    def get_prices(self, ticker: str, start: str, end: str) -> pd.DataFrame | None:
        """Daily OHLCV-style history.

        Returns a DataFrame indexed by date with at least a 'close' column,
        or None if the instrument could not be retrieved.
        """

    @abstractmethod
    def get_dividends(self, ticker: str, start: str, end: str) -> pd.DataFrame:
        """Cash dividends. Columns: ['date', 'amount']. Empty frame if none."""

    @abstractmethod
    def get_fundamentals(self, ticker: str) -> dict:
        """Point-in-time snapshot: market cap, P/E, EPS, P/B. Empty dict if N/A."""

    def health_check(self) -> bool:
        """Cheap probe used by the ETL to pick a working provider."""
        try:
            data = self.get_prices("AAPL", "2024-01-01", "2024-01-31")
            return data is not None and not data.empty
        except Exception:
            return False