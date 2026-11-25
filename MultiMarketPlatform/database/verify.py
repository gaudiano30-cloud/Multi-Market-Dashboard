"""Quick read-only check of market coverage and historical-price availability.
Run from project root: python -m database.verify
"""
from collections import Counter
from config import MARKETS
from .connection import get_connection


def main():
    with get_connection(read_only=True) as connection:
        market_rows = connection.execute(
            "SELECT market_code, label, asset_class FROM markets ORDER BY asset_class, label"
        ).fetchall()
        actual_codes = {row["market_code"] for row in market_rows}
        missing = sorted(set(MARKETS) - actual_codes)
        print(f"Mercati nel DB: {len(market_rows)} / {len(MARKETS)} catalogati")
        print("Per classe:", dict(sorted(Counter(row["asset_class"] for row in market_rows).items())))
        print("Voci mancanti:", missing or "nessuna")
        print("\nSTATO CATALOGO (strumenti / ticker con prezzi):")
        for row in market_rows:
            code = row["market_code"]
            instruments = connection.execute(
                "SELECT COUNT(*) AS n FROM instruments WHERE market_code = ?", (code,)
            ).fetchone()["n"]
            loaded = connection.execute(
                """SELECT COUNT(DISTINCT p.ticker) AS n
                   FROM prices p JOIN instruments i ON i.ticker = p.ticker
                   WHERE i.market_code = ?""", (code,)
            ).fetchone()["n"]
            print(f"  {code:19} {instruments:2} strumenti / {loaded:2} con prezzi  {row['label']}")
        violations = connection.execute("PRAGMA foreign_key_check").fetchall()
        print("\nViolazioni FK:", len(violations))
        print("Osservazioni prezzi:", connection.execute("SELECT COUNT(*) FROM prices").fetchone()[0])
        if missing or violations:
            raise SystemExit("ERRORE: catalogo incompleto o vincoli violati")


if __name__ == "__main__":
    main()
