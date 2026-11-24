# MFE — Estensione del database a 29 mercati

Questo pacchetto espande il progetto già esistente. Mantiene i vecchi codici
`EQ_IT`, `EQ_EU`, `COMM`, `FX` per non spezzare i riferimenti nello storico.

## File da sostituire

- `config.py` (nella radice del progetto)
- `database/connection.py`
- `database/schema.py`
- `database/populate.py`
- `database/repository.py`
- `app.py` (versione con sidebar, globo e breadcrumb cliccabili)

Il nuovo `database/verify.py` è opzionale, ma utile per la verifica.

**Non sostituire `style.py`, i provider, o `analytics/metrics.py`:** sono invariati.
Conserva `assets/MFEimage.png` come nel progetto attuale.

## 1. Proteggi i tuoi dati

Fai prima una copia di `database/market_data.db` e degli attuali `.py`.

Nel pacchetto trovi anche `database/market_data.db` **già aggiornato**, ottenuto
esclusivamente dalla copia del database che hai allegato: contiene 29 mercati,
51 strumenti (inclusi i benchmark), 54.501 righe prezzi e 141 righe dividendi.
Non contiene i nuovi storici scaricati da internet.

Se hai aggiunto dati dopo l'invio del file in chat, **non sovrascrivere il tuo
`.db` con il file presente nel pacchetto**: usa invece la migrazione sotto.

## 2. Aggiorna il tuo database senza perdere prezzi

Dal Terminale, entra nella cartella del progetto (quella con `config.py`).
Dopo aver sostituito i file `.py`, esegui:

```bash
python -m database.populate --catalog-only
```

Questa operazione crea le eventuali colonne geografiche mancanti nel DB e
aggiorna le righe dei mercati e degli strumenti, senza scaricare dati,
senza cancellare gli storici e senza `REPLACE` sulle chiavi esterne.
Puoi ripeterla: il risultato è idempotente.

## 3. Verifica

```bash
python -m database.verify
```

Vedrai le 29 voci con il numero di strumenti e ticker già dotati di prezzi.
**Un mercato nel catalogo non significa che il suo storico sia stato scaricato.**

## 4. Scarica i dati mancanti (facoltativo)

Per tutte le serie configurate con Yahoo, senza riscaricare quelle già esistenti:

```bash
python -m database.populate --new-only --start 2020-01-01
```

Per partire da una singola borsa:

```bash
python -m database.populate --market EQ_US_NASDAQ --new-only --start 2022-01-01
```

Altri esempi: `EQ_TOKYO`, `FI_TREASURY`, `COMM_ICE`, `DER_CME`.
Per consultare i codici vedi `CATALOGO.md`.

La fonte Yahoo non garantisce che ogni ticker sia disponibile. In caso di
mancata risposta, il programma registra il fallimento nei metadata senza
inventare i dati. Alcuni titoli hanno una storia più corta di quella richiesta.

**Non usare `--mock` per dati reali:** produce serie sintetiche adatte solo
alle prove della dashboard.

## 5. Avvia la dashboard

```bash
python app.py
```

La versione aggiornata di `app.py` legge **regione e coordinate direttamente
dal database**. Le 29 voci compaiono nei filtri della sidebar. I luoghi fisici
hanno una posizione sul globo. I mercati non localizzati, come FX OTC e
categorie obbligazionarie globali, si esplorano con i due menu a tendina.
I marketplace collocati nella stessa città possono sovrapporsi sul globo:
i menu restano il metodo più preciso per distinguerli.

## Limiti finanziari e metodologici

- **Fixed Income**: IEF, TLT, IEGA.AS, LQD, HYG sono ETF usati come *proxy*;
  non rappresentano tutte le emissioni obbligazionarie. I loro rendimenti
  sono rendimenti di ETF, non rendimenti a scadenza dei bond sottostanti.
- **Derivatives**: contratti futures generici Yahoo, non una term structure
  completa per scadenza. Eurex e Cboe Options sono già nel catalogo ma
  richiedono integrazione dati specialistica prima di mostrare prezzi.
- **Commodities**: LME è censita ma i prezzi specifici LME non sono garantiti
  da Yahoo. Futures agricoli rappresentati da contratti CBOT.
- **FX**: le coppie valutarie sono segmenti del mercato OTC globale, non borse
  geograficamente localizzate.
- Le coordinate Euronext indicano Parigi come localizzazione illustrativa:
  Euronext è un gruppo di sedi di negoziazione in più paesi.
- **Non confondere la presenza di una borsa nel database con la copertura
  integrale dei titoli quotati su quella borsa.** Gli strumenti sono esempi,
  non il listino completo.

## Compatibilità

La struttura `prices`, `dividends`, `fundamentals`, `metadata` è invariata.
Sono aggiunti solo 5 campi nella tabella `markets`: `region`, `city`,
`latitude`, `longitude`, `kind`. La migrazione usa `ALTER TABLE ADD COLUMN`
solo quando il campo manca. Tutti i dati esistenti restano invariati.
