"""
Financial Database Schema Module.

This module defines the relational structure of the
financial database used by MultiMarketPlatform.

Its main responsibilities include:
    - Defining market and financial instrument tables.
    - Defining historical price and dividend tables.
    - Defining financial fundamentals and metadata tables.
    - Establishing primary and foreign key relationships.
    - Defining data integrity constraints.
    - Defining indexes to improve query performance.
    - Supporting backward-compatible schema upgrades.

The module centralizes SQL schema definitions independently
of database connections, data acquisition, analytical
computations and application presentation.
"""

"""Il database finanziario contiene 6 tabelle. 
La tabella centrale è instruments che collega ogni strumento finanziario al rispettivo mercato
e alle sue informazioni finanziarie."""

PRAGMAS = ("PRAGMA foreign_keys = ON",)  # attiva il controllo di Foreign Key per una connessione

# Questa tabella rappresenta il catalogo dei mercati finanziari della nostra piattaforma
MARKETS = """
CREATE TABLE IF NOT EXISTS markets (
    market_code TEXT PRIMARY KEY, 
    label TEXT NOT NULL,
    asset_class TEXT NOT NULL,
    currency TEXT,
    region TEXT,
    city TEXT,
    latitude REAL,
    longitude REAL,
    kind TEXT
)
"""

# Questa tabella contiene gli strumenti finanziari appartenenti ai diversi mercati
INSTRUMENTS = """
CREATE TABLE IF NOT EXISTS instruments (
    ticker TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    market_code TEXT NOT NULL,
    is_benchmark INTEGER NOT NULL DEFAULT 0 CHECK (is_benchmark IN (0, 1)),
    FOREIGN KEY (market_code) REFERENCES markets(market_code)
)
"""
# con la FK colleghiamo la tabella instruments alla tabella markets

# Questa tabella contiene le serie storiche dei prezzi finanziari
PRICES = """
CREATE TABLE IF NOT EXISTS prices (
    ticker TEXT NOT NULL,
    date TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL NOT NULL,
    adj_close REAL,
    volume INTEGER,
    PRIMARY KEY (ticker, date),
    FOREIGN KEY (ticker) REFERENCES instruments(ticker)
)
"""
# chiave primaria composta: ticker+date (perché nella stessa giornata possiamo avere due osservazioni relative allo stesso strumento finanziario)

# Questa tabella contiene i dividendi distribuiti dagli strumenti finanziari
DIVIDENDS = """
CREATE TABLE IF NOT EXISTS dividends (
    ticker TEXT NOT NULL,
    date TEXT NOT NULL,
    amount REAL NOT NULL CHECK (amount >= 0),
    PRIMARY KEY (ticker, date),
    FOREIGN KEY (ticker) REFERENCES instruments(ticker)
)
"""

# Questa tabella contiene gli indicatori fondamentali degli strumenti finanziari
FUNDAMENTALS = """
CREATE TABLE IF NOT EXISTS fundamentals (
    ticker TEXT PRIMARY KEY,
    market_cap REAL,
    pe_ratio REAL,
    eps REAL,
    pb_ratio REAL,
    dividend_yield REAL,
    FOREIGN KEY (ticker) REFERENCES instruments(ticker)
)
"""

# Questa tabella conserva lo stato dell'ultima operazione per ciascuno strumento, non lo storico completo dei caricamenti
METADATA = """
CREATE TABLE IF NOT EXISTS metadata (
    ticker TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    last_update TEXT NOT NULL,
    status TEXT NOT NULL,
    rows_loaded INTEGER DEFAULT 0,
    message TEXT,
    FOREIGN KEY (ticker) REFERENCES instruments(ticker)
)
"""

TABLES = (MARKETS, INSTRUMENTS, PRICES, DIVIDENDS, FUNDAMENTALS, METADATA)


MARKETS_EXTRA_COLUMNS = {
    "region": "TEXT",
    "city": "TEXT",
    "latitude": "REAL",
    "longitude": "REAL",
    "kind": "TEXT",
}

INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_prices_date ON prices(date)",
    "CREATE INDEX IF NOT EXISTS idx_instruments_market ON instruments(market_code)",
    "CREATE INDEX IF NOT EXISTS idx_markets_asset_region ON markets(asset_class, region)",
)
ALL_STATEMENTS = PRAGMAS + TABLES + INDEXES
