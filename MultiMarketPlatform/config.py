"""Catalogo dei mercati della piattaforma MFE.

Il catalogo contiene borse, mercati OTC e categorie del progetto.
Ogni strumento deve comparire in un solo mercato: lo schema attuale usa
il ticker come chiave primaria nella tabella instruments.

ATTENZIONE: ETF obbligazionari = proxy negoziati, non bond governativi
individuali. Futures Yahoo (=F) = serie generiche del provider, non
storici certificati di una specifica scadenza; opzioni/LME/Eurex
richiedono provider più specializzati.
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database" / "market_data.db"
HISTORY_START = "2015-01-01"


ASSET_LABELS = {
    "equity": "Equity",
    "fixed_income": "Fixed Income",
    "derivative": "Derivatives",
    "commodity": "Commodities",
    "fx": "Foreign Exchange",
}


def market(name, asset_class, currency, region, *, city=None, latitude=None,
           longitude=None, kind="exchange", instruments=None, benchmark=None):
    """Standardizza i metadati di ogni mercato (nessun accesso al DB)."""
    return {
        "name": name,
        "label": f"{ASSET_LABELS[asset_class]} - {name}",
        "asset_class": asset_class,
        "currency": currency,
        "region": region,
        "city": city,
        "latitude": latitude,
        "longitude": longitude,
        "kind": kind,
        "instruments": instruments or {},
        "benchmark": benchmark,
    }


MARKETS = {
    # EQUITY — United States
    "EQ_US_NYSE": market("NYSE", "equity", "USD", "Nord America", city="New York",
        latitude=40.7069, longitude=-74.0113,
        instruments={"JPM": "JPMorgan Chase", "KO": "Coca-Cola"}),
    "EQ_US_AMERICAN": market("NYSE American", "equity", "USD", "Nord America", city="New York",
        latitude=40.7069, longitude=-74.0113,
        instruments={"BTG": "B2Gold"}),
    "EQ_US_ARCA": market("NYSE Arca", "equity", "USD", "Nord America", city="New York",
        latitude=40.7069, longitude=-74.0113,
        instruments={"SPY": "SPDR S&P 500 ETF Trust (ETF)"}),
    "EQ_US_NASDAQ": market("NASDAQ", "equity", "USD", "Nord America", city="New York",
        latitude=40.7581, longitude=-73.9855,
        instruments={"AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "NVIDIA"}),
    "EQ_US_BZX": market("Cboe BZX Exchange", "equity", "USD", "Nord America", city="Chicago",
        latitude=41.8819, longitude=-87.6278,
        instruments={"ONEH": "TrueShares Equity Hedge ETF (ETF)"}),

    # EQUITY — Europe; preserve existing EQ_IT and EQ_EU codes and their history.
    "EQ_EURONEXT": market("Euronext", "equity", "EUR", "Europa", city="Parigi (sede rappresentativa)",
        latitude=48.8566, longitude=2.3522,
        instruments={"AIR.PA": "Airbus", "SAN.PA": "Sanofi"}),
    "EQ_LSE": market("London Stock Exchange", "equity", "GBP", "Europa", city="Londra",
        latitude=51.5142, longitude=-0.0997,
        instruments={"VOD.L": "Vodafone", "AZN.L": "AstraZeneca"}),
    "EQ_EU": market("Deutsche Börse", "equity", "EUR", "Europa", city="Francoforte",
        latitude=50.1155, longitude=8.6842,
        instruments={"BAS.DE": "BASF", "VOW3.DE": "Volkswagen"}, benchmark="^STOXX50E"),
    "EQ_IT": market("Borsa Italiana", "equity", "EUR", "Europa", city="Milano",
        latitude=45.4642, longitude=9.1900,
        instruments={
            "ENEL.MI": "Enel", "ENI.MI": "Eni", "ISP.MI": "Intesa Sanpaolo",
            "STLAM.MI": "Stellantis", "G.MI": "Generali",
        }, benchmark="FTSEMIB.MI"),

    # EQUITY — Asia
    "EQ_TOKYO": market("Tokyo Stock Exchange", "equity", "JPY", "Asia", city="Tokyo",
        latitude=35.6812, longitude=139.7681,
        instruments={"7203.T": "Toyota Motor", "6758.T": "Sony Group"}),
    "EQ_HONGKONG": market("Hong Kong Stock Exchange", "equity", "HKD", "Asia", city="Hong Kong",
        latitude=22.2830, longitude=114.1588,
        instruments={"0700.HK": "Tencent", "0005.HK": "HSBC Holdings"}),
    "EQ_SHANGHAI": market("Shanghai Stock Exchange", "equity", "CNY", "Asia", city="Shanghai",
        latitude=31.2304, longitude=121.4737,
        instruments={"600519.SS": "Kweichow Moutai"}),

    # EQUITY — Other relevant international markets
    "EQ_TSX": market("Toronto Stock Exchange", "equity", "CAD", "Nord America", city="Toronto",
        latitude=43.6487, longitude=-79.3817,
        instruments={"RY.TO": "Royal Bank of Canada"}),
    "EQ_ASX": market("Australian Securities Exchange", "equity", "AUD", "Oceania", city="Sydney",
        latitude=-33.8688, longitude=151.2093,
        instruments={"BHP.AX": "BHP Group"}),

    # FIXED INCOME — ETF proxies for an exploratory pricing dashboard.
    "FI_TREASURY": market("US Treasury Market (ETF proxy)", "fixed_income", "USD", "Nord America",
        kind="category", instruments={
            "IEF": "iShares 7-10 Year Treasury Bond ETF (proxy)",
            "TLT": "iShares 20+ Year Treasury Bond ETF (proxy)",
        }),
    "FI_EU_GOV": market("European Government Bonds (ETF proxy)", "fixed_income", "EUR", "Europa",
        kind="category", instruments={
            "IEGA.AS": "iShares Core Euro Government Bond UCITS ETF (proxy)"
        }),
    "FI_CORPORATE": market("Corporate Bonds (ETF proxy)", "fixed_income", "USD", "Globale",
        kind="category", instruments={
            "LQD": "iShares USD Investment Grade Corporate Bond ETF (proxy)",
            "HYG": "iShares USD High Yield Corporate Bond ETF (proxy)",
        }),

    # DERIVATIVES — two venues with Yahoo futures examples.
    "DER_CME": market("CME", "derivative", "USD", "Nord America", city="Chicago",
        latitude=41.8819, longitude=-87.6278,
        instruments={"ES=F": "E-mini S&P 500 Futures", "NQ=F": "E-mini Nasdaq-100 Futures"}),
    "DER_CBOT": market("CBOT", "derivative", "USD", "Nord America", city="Chicago",
        latitude=41.8819, longitude=-87.6278,
        instruments={"ZN=F": "10-Year Treasury Note Futures", "ZB=F": "30-Year Treasury Bond Futures"}),
    "DER_EUREX": market("Eurex", "derivative", "EUR", "Europa", city="Eschborn / Francoforte",
        latitude=50.1422, longitude=8.5745, instruments={}),
    "DER_CBOE_OPTIONS": market("Cboe Options Exchange", "derivative", "USD", "Nord America", city="Chicago",
        latitude=41.8819, longitude=-87.6278, instruments={}),

    # COMMODITIES — existing COMM code now means NYMEX; move historical
    # gold and wheat series to COMEX and the agricultural grouping below.
    "COMM": market("NYMEX", "commodity", "USD", "Nord America", city="New York",
        latitude=40.7069, longitude=-74.0113,
        instruments={"CL=F": "WTI Crude Oil Futures", "NG=F": "Natural Gas Futures"}),
    "COMM_COMEX": market("COMEX", "commodity", "USD", "Nord America", city="New York",
        latitude=40.7069, longitude=-74.0113,
        instruments={"GC=F": "Gold Futures", "SI=F": "Silver Futures"}),
    "COMM_LME": market("LME", "commodity", "USD", "Europa", city="Londra",
        latitude=51.5142, longitude=-0.0997, instruments={}),
    "COMM_ICE": market("ICE Futures", "commodity", "USD", "Nord America", city="New York",
        latitude=40.7069, longitude=-74.0113,
        instruments={"SB=F": "Sugar No. 11 Futures (ICE)"}),
    "COMM_AGRI": market("Agricultural Commodities Markets", "commodity", "USD", "Globale",
        kind="category", instruments={
            "ZW=F": "Wheat Futures (CBOT)", "ZC=F": "Corn Futures (CBOT)"
        }),

    # FX — OTC global categories, not physical exchanges; no invented pins.
    "FX": market("Major pairs", "fx", "-", "Globale", kind="otc", instruments={
        "EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD", "USDJPY=X": "USD/JPY"
    }),
    "FX_MINOR": market("Minor pairs", "fx", "-", "Globale", kind="otc", instruments={
        "EURGBP=X": "EUR/GBP", "EURJPY=X": "EUR/JPY"
    }),
    "FX_EM": market("Emerging market currency pairs", "fx", "-", "Globale", kind="otc", instruments={
        "USDZAR=X": "USD/ZAR", "USDMXN=X": "USD/MXN"
    }),
}

# Benchmarks downloaded as well; each ticker belongs to one catalogue entry.
BENCHMARKS = {
    "FTSEMIB.MI": "FTSE MIB",
    "^STOXX50E": "EURO STOXX 50 (benchmark europeo)",
}

# Verify the PK constraint in advance instead of silently moving instruments.
seen = {}
for code, entry in MARKETS.items():
    for ticker in (*entry["instruments"], *((entry["benchmark"],) if entry["benchmark"] else ())):
        if ticker in seen:
            raise ValueError(f"Ticker duplicato {ticker}: {seen[ticker]} e {code}")
        seen[ticker] = code

TRADING_DAYS = 252
RISK_FREE_RATE = 0.02
