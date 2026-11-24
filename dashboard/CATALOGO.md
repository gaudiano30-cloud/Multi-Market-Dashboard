# Catalogo dei mercati

Sono previsti tutti i mercati della consegna più TSX e ASX come mercati aggiuntivi.

Le voci con `0` strumenti sono da integrare con una fonte dati specifica.

## Equity

| Codice | Mercato | Regione | Strumenti (ticker) |
|---|---|---|---|
| `EQ_US_NYSE` | NYSE | Nord America | `JPM`, `KO` |
| `EQ_US_AMERICAN` | NYSE American | Nord America | `BTG` |
| `EQ_US_ARCA` | NYSE Arca | Nord America | `SPY` |
| `EQ_US_NASDAQ` | NASDAQ | Nord America | `AAPL`, `MSFT`, `NVDA` |
| `EQ_US_BZX` | Cboe BZX Exchange | Nord America | `ONEH` |
| `EQ_EURONEXT` | Euronext | Europa | `AIR.PA`, `SAN.PA` |
| `EQ_LSE` | London Stock Exchange | Europa | `VOD.L`, `AZN.L` |
| `EQ_EU` | Deutsche Börse | Europa | `BAS.DE`, `VOW3.DE`, `^STOXX50E` |
| `EQ_IT` | Borsa Italiana | Europa | `ENEL.MI`, `ENI.MI`, `ISP.MI`, `STLAM.MI`, `G.MI`, `FTSEMIB.MI` |
| `EQ_TOKYO` | Tokyo Stock Exchange | Asia | `7203.T`, `6758.T` |
| `EQ_HONGKONG` | Hong Kong Stock Exchange | Asia | `0700.HK`, `0005.HK` |
| `EQ_SHANGHAI` | Shanghai Stock Exchange | Asia | `600519.SS` |
| `EQ_TSX` | Toronto Stock Exchange | Nord America | `RY.TO` |
| `EQ_ASX` | Australian Securities Exchange | Oceania | `BHP.AX` |

## Fixed Income

| Codice | Mercato | Regione | Strumenti (ticker) |
|---|---|---|---|
| `FI_TREASURY` | US Treasury Market (ETF proxy) | Nord America | `IEF`, `TLT` |
| `FI_EU_GOV` | European Government Bonds (ETF proxy) | Europa | `IEGA.AS` |
| `FI_CORPORATE` | Corporate Bonds (ETF proxy) | Globale | `LQD`, `HYG` |

## Derivatives

| Codice | Mercato | Regione | Strumenti (ticker) |
|---|---|---|---|
| `DER_CME` | CME | Nord America | `ES=F`, `NQ=F` |
| `DER_CBOT` | CBOT | Nord America | `ZN=F`, `ZB=F` |
| `DER_EUREX` | Eurex | Europa | Da integrare |
| `DER_CBOE_OPTIONS` | Cboe Options Exchange | Nord America | Da integrare |

## Commodities

| Codice | Mercato | Regione | Strumenti (ticker) |
|---|---|---|---|
| `COMM` | NYMEX | Nord America | `CL=F`, `NG=F` |
| `COMM_COMEX` | COMEX | Nord America | `GC=F`, `SI=F` |
| `COMM_LME` | LME | Europa | Da integrare |
| `COMM_ICE` | ICE Futures | Nord America | `SB=F` |
| `COMM_AGRI` | Agricultural Commodities Markets | Globale | `ZW=F`, `ZC=F` |

## Foreign Exchange

| Codice | Mercato | Regione | Strumenti (ticker) |
|---|---|---|---|
| `FX` | Major pairs | Globale | `EURUSD=X`, `GBPUSD=X`, `USDJPY=X` |
| `FX_MINOR` | Minor pairs | Globale | `EURGBP=X`, `EURJPY=X` |
| `FX_EM` | Emerging market currency pairs | Globale | `USDZAR=X`, `USDMXN=X` |
