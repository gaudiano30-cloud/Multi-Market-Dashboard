"""
Abstract Financial Data Provider Module.

This module defines the common interface that all financial
data providers must implement within the platform.

Its main responsibilities include:
    - Defining a standardized interface for data acquisition.
    - Establishing common methods for retrieving historical
      prices, dividends and financial fundamentals.
    - Defining the expected structure of the returned data.
    - Providing a common provider health-check mechanism.
    - Supporting interchangeable financial data sources.

The DataProvider abstract class allows the application
to operate independently of specific data providers,
promoting modularity, extensibility, maintainability
and scalability.
"""

from abc import ABC, abstractmethod

# abc = libreria standard di Python
# ABC = Abstract Base Classes (permette di definire una classe base astratta)
# abstractmethod = permette di definire un metodo astratto
import pandas as pd


class DataProvider(ABC):
    """La classe definita rappresenta il modello generale di un provider finanziario.
    Contract every market data source must satisfy."""

    name: str = "abstract"
    # definiamo un attributo di classe chiamato "name" che permette di identificare il provider utilizzato

    """Un decoratore permette di attribuire un particolare comportamento a una funzione o a un metodo.
    In questo caso, @abstractmethod stabilisce che le classi concrete che ereditano da DataProvider 
    devono implementare questo metodo per poter essere istanziate.
    
    base.py stabilisce che il metodo deve esistere, 
    ma lascia alle classi concrete la responsabilità di decidere come ottenere i prezzi.
    """

    @abstractmethod
    def get_prices(self, ticker: str, start: str, end: str) -> pd.DataFrame | None:
        """Daily OHLCV-style history.

        Returns a DataFrame indexed by date with at least a 'close' column,
        or None if the instrument could not be retrieved.
        """

    @abstractmethod
    def get_dividends(self, ticker: str, start: str, end: str) -> pd.DataFrame:
        """Questo metodo definisce il contratto per recuperare i dividendi distribuiti
        da uno strumento finanziario.
        Cash dividends. Columns: ['date', 'amount']. Empty frame if none."""

    @abstractmethod
    def get_fundamentals(self, ticker: str) -> dict:
        """Questo metodo è destinato al recupero degli indicatori fondamentali degli strumenti finanziari.
        A differenza dei prezzi e dei dividendi, qui non passiamo un intervallo temporale,
        perché vogliamo ottenere una fotografia dei fondamentali disponibili al momento della richiesta, ovvero uno snapshot.
        Il metodo restituisce un dizionario Python.
        Point-in-time snapshot: market cap, P/E, EPS, P/B. Empty dict if N/A."""

    def health_check(self) -> bool:
        """Il metodo permette di verificare se il provider sia operativo.
        Cheap probe used by the ETL to pick a working provider."""
        try:
            data = self.get_prices("AAPL", "2024-01-01", "2024-01-31")  # esempio di polimorfismo
            # Effettuiamo una richiesta di prova relativa alle azioni Apple.
            # Utilizziamo un intervallo storico fisso per verificare se il provider riesca a fornire una serie di prezzi.
            return (
                data is not None and not data.empty
            )  # controlliamo che il provider abbai restituito un oggetto e che questo non sia vuoto
        except Exception:
            return False
