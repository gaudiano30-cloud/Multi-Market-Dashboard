"""Database schema as Python constants.

Kept here rather than in a .sql file so the schema travels with the package:
PyInstaller bundles modules automatically, data files only with extra
configuration. Each statement is idempotent, so applying the schema twice is
harmless.
"""

PRAGMAS = ("PRAGMA foreign_keys = ON",)

MARKETS = """
CREATE TABLE IF NOT EXISTS markets (
    market_code   TEXT PRIMARY KEY,
    label         TEXT NOT NULL,
    asset_class   TEXT NOT NULL,
    currency      TEXT
)
"""

INSTRUMENTS = """
CREATE TABLE IF NOT EXISTS instruments (
    ticker        TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    market_code   TEXT NOT NULL,
    is_benchmark  INTEGER NOT NULL DEFAULT 0 CHECK (is_benchmark IN (0, 1)),
    FOREIGN KEY (market_code) REFERENCES markets(market_code)
)
"""

PRICES = """
CREATE TABLE IF NOT EXISTS prices (
    ticker     TEXT NOT NULL,
    date       TEXT NOT NULL,
    open       REAL,
    high       REAL,
    low        REAL,
    close      REAL NOT NULL,
    adj_close  REAL,
    volume     INTEGER,
    PRIMARY KEY (ticker, date),
    FOREIGN KEY (ticker) REFERENCES instruments(ticker)
)
"""

DIVIDENDS = """
CREATE TABLE IF NOT EXISTS dividends (
    ticker  TEXT NOT NULL,
    date    TEXT NOT NULL,
    amount  REAL NOT NULL CHECK (amount >= 0),
    PRIMARY KEY (ticker, date),
    FOREIGN KEY (ticker) REFERENCES instruments(ticker)
)
"""

FUNDAMENTALS = """
CREATE TABLE IF NOT EXISTS fundamentals (
    ticker          TEXT PRIMARY KEY,
    market_cap      REAL,
    pe_ratio        REAL,
    eps             REAL,
    pb_ratio        REAL,
    dividend_yield  REAL,
    FOREIGN KEY (ticker) REFERENCES instruments(ticker)
)
"""

# Required by the brief: timestamp, source, update status.
METADATA = """
CREATE TABLE IF NOT EXISTS metadata (
    ticker        TEXT PRIMARY KEY,
    provider      TEXT NOT NULL,
    last_update   TEXT NOT NULL,
    status        TEXT NOT NULL,
    rows_loaded   INTEGER DEFAULT 0,
    message       TEXT,
    FOREIGN KEY (ticker) REFERENCES instruments(ticker)
)
"""

INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_prices_date ON prices(date)",
    "CREATE INDEX IF NOT EXISTS idx_instruments_market ON instruments(market_code)",
)

# Order matters: a child table cannot reference a parent that does not exist.
TABLES = (
    MARKETS,
    INSTRUMENTS,
    PRICES,
    DIVIDENDS,
    FUNDAMENTALS,
    METADATA,
)

ALL_STATEMENTS = PRAGMAS + TABLES + INDEXES