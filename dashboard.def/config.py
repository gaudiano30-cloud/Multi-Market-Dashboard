"""Market catalogue. Adding a market means adding an entry here, nothing else."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database" / "market_data.db"

HISTORY_START = "2015-01-01"

MARKETS = {
    "EQ_IT": {
        "label": "Equity - Borsa Italiana",
        "asset_class": "equity",
        "currency": "EUR",
        "instruments": {
            "ENEL.MI": "Enel",
            "ENI.MI": "Eni",
            "ISP.MI": "Intesa Sanpaolo",
            "STLAM.MI": "Stellantis",
            "G.MI": "Generali",
        },
        "benchmark": "FTSEMIB.MI",
    },
    "EQ_EU": {
        "label": "Equity - Europa (DE/FR)",
        "asset_class": "equity",
        "currency": "EUR",
        "instruments": {
            "BAS.DE": "BASF",
            "VOW3.DE": "Volkswagen",
            "AIR.PA": "Airbus",
            "SAN.PA": "Sanofi",
        },
        "benchmark": "^STOXX50E",
    },
    "COMM": {
        "label": "Commodities (futures front month)",
        "asset_class": "commodity",
        "currency": "USD",
        "instruments": {
            "GC=F": "Gold",
            "CL=F": "WTI Crude Oil",
            "NG=F": "Natural Gas",
            "ZW=F": "Wheat",
        },
        "benchmark": None,
    },
    "FX": {
        "label": "Foreign Exchange",
        "asset_class": "fx",
        "currency": "-",
        "instruments": {
            "EURUSD=X": "EUR/USD",
            "GBPUSD=X": "GBP/USD",
            "USDJPY=X": "USD/JPY",
        },
        "benchmark": None,
    },
}

# Benchmarks are downloaded too, so the comparison page has data.
BENCHMARKS = {
    "FTSEMIB.MI": "FTSE MIB",
    "^STOXX50E": "Euro Stoxx 50",
}

TRADING_DAYS = 252
RISK_FREE_RATE = 0.02  # annual, used for the Sharpe ratio