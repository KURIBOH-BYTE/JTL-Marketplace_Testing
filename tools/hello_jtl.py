#!/usr/bin/env python3
"""Erster Kontakt: kommt Python überhaupt an die JTL-Datenbank?

Liest nur, schreibt nichts. Zeigt der Reihe nach:

  1. ob die Verbindung steht
  2. welche SQL-Server-Version läuft
  3. ob die Tabellen da sind, die uns interessieren
  4. die Spalten von tArtikel
  5. drei Artikel als Beweis, dass echte Daten herauskommen

Das ist der kleinste sinnvolle Test. Läuft er durch, ist der Weg Python → JTL
offen und alles Weitere ist nur noch Fleissarbeit.

    python tools\\hello_jtl.py --server "(local)\\JTLWAWI" --user sa --password GEHEIM

Oder die Zugangsdaten in config.ini eintragen, dann genügt:

    python tools\\hello_jtl.py

Voraussetzungen: `pip install pyodbc` und der "ODBC Driver 17 for SQL Server"
von Microsoft (bei einer JTL-Installation meist schon vorhanden).
"""

from __future__ import annotations

import argparse
import configparser
import sys
from pathlib import Path

TESTING = Path(__file__).resolve().parent.parent

#: Tabellen, auf die die Anbindung später zugreift.
TABLES_OF_INTEREST = [
    ("tArtikel", "Artikelstamm – hier steht cArtNr, das Gegenstück zu "
                 "SUPPLIER_PID bei Galaxus"),
    ("tBestellung", "Aufträge – hier landet cExterneBestellNr und später "
                    "cTracking"),
    ("tXMLBestellImport", "Posteingang für den automatischen Auftragsimport"),
    ("tkunde", "Kundenstamm – Galaxus und Zur Rose sind feste Kunden"),
    ("tVersandArt", "Versandarten – cVersandartName muss einen davon treffen"),
    ("tZahlungsart", "Zahlungsarten – dasselbe für cZahlungsartName"),
]


def from_config() -> dict[str, str]:
    """Zugangsdaten aus config.ini, falls vorhanden."""
    path = TESTING / "config.ini"
    if not path.exists():
        return {}
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(path, encoding="utf-8")
    if "jtl" not in parser:
        return {}
    return {key: value for key, value in parser["jtl"].items() if value.strip()}


def connect(server: str, database: str, user: str, password: str):
    try:
        import pyodbc
    except ImportError:
        raise SystemExit(
            "pyodbc fehlt.\n\n"
            "  pip install pyodbc\n\n"
            "Zusätzlich braucht Windows den 'ODBC Driver 17 for SQL Server' "
            "von Microsoft.\nBei einer JTL-Installation ist er meist schon da."
        )

    drivers = [d for d in pyodbc.drivers() if "SQL Server" in d]
    if not drivers:
        raise SystemExit(
            "Kein ODBC-Treiber für SQL Server gefunden.\n"
            "'ODBC Driver 17 for SQL Server' von Microsoft nachinstallieren.\n\n"
            f"Vorhandene Treiber: {', '.join(pyodbc.drivers()) or '(keine)'}"
        )
    driver = sorted(drivers, reverse=True)[0]

    print(f"ODBC-Treiber    {driver}")
    print(f"Server          {server}")
    print(f"Datenbank       {database}")
    print(f"Benutzer        {user}\n")

    try:
        return pyodbc.connect(
            f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};"
            f"UID={user};PWD={password};TrustServerCertificate=yes;",
            timeout=10,
        )
    except pyodbc.Error as exc:
        state = exc.args[0] if exc.args else ""
        hint = {
            "28000": "Anmeldung abgelehnt – Benutzer oder Passwort falsch.",
            "08001": "Server nicht erreichbar. Instanzname richtig? "
                     "Oft (local)\\JTLWAWI oder SERVERNAME\\JTLWAWI.",
            "42000": "Datenbank nicht gefunden oder kein Zugriff. "
                     "Heisst sie wirklich 'eazybusiness'?",
        }.get(state, "")
        raise SystemExit(f"Verbindung fehlgeschlagen ({state}).\n{hint}\n\n{exc}")


def main(argv: list[str] | None = None) -> int:
    defaults = from_config()
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--server", default=defaults.get("server"))
    parser.add_argument("--database", default=defaults.get("database", "eazybusiness"))
    parser.add_argument("--user", default=defaults.get("user"))
    parser.add_argument("--password", default=defaults.get("password"))
    args = parser.parse_args(argv)

    missing = [n for n in ("server", "user", "password") if not getattr(args, n)]
    if missing:
        raise SystemExit(
            f"Fehlt: {', '.join('--' + m for m in missing)}\n\n"
            f"Entweder als Parameter übergeben oder config.ini anlegen:\n"
            f"  copy config.example.ini config.ini"
        )

    print("=" * 68)
    print("Erster Kontakt zu JTL-Wawi")
    print("=" * 68 + "\n")

    connection = connect(args.server, args.database, args.user, args.password)
    cursor = connection.cursor()
    print("Verbindung steht.\n")

    # 1. Version
    cursor.execute("SELECT @@VERSION")
    print("SQL Server:")
    print(f"  {cursor.fetchone()[0].splitlines()[0]}\n")

    # 2. Grössenordnung
    cursor.execute(
        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'"
    )
    print(f"Tabellen in der Datenbank: {cursor.fetchone()[0]}\n")

    # 3. Sind die Tabellen da, die wir brauchen?
    print("Für die Anbindung relevante Tabellen:")
    missing_tables = []
    for table, purpose in TABLES_OF_INTEREST:
        cursor.execute(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = ?",
            table,
        )
        if cursor.fetchone()[0]:
            cursor.execute(f"SELECT COUNT(*) FROM [{table}]")
            print(f"  [x] {table:<22} {cursor.fetchone()[0]:>9} Datensätze")
        else:
            print(f"  [ ] {table:<22} nicht gefunden")
            missing_tables.append(table)
        print(f"      {purpose}")
    print()

    # 4. Spalten von tArtikel – zeigt, wie die Artikelnummer wirklich heisst
    cursor.execute(
        """
        SELECT COLUMN_NAME, DATA_TYPE
          FROM INFORMATION_SCHEMA.COLUMNS
         WHERE TABLE_NAME = 'tArtikel'
         ORDER BY ORDINAL_POSITION
        """
    )
    columns = cursor.fetchall()
    if columns:
        print(f"tArtikel hat {len(columns)} Spalten, die ersten 15:")
        for name, data_type in columns[:15]:
            print(f"  {name:<30} {data_type}")
        print()

    # 5. Echte Daten
    cursor.execute("SELECT TOP 3 kArtikel, cArtNr, cBarcode FROM tArtikel")
    print("Drei Artikel:")
    for row in cursor.fetchall():
        print(f"  kArtikel {row[0]:<8} cArtNr {row[1] or '-':<20} "
              f"cBarcode {row[2] or '-'}")

    connection.close()
    print("\n" + "=" * 68)
    if missing_tables:
        print(f"Geklappt, aber diese Tabellen fehlen: {', '.join(missing_tables)}")
        print("Vermutlich heissen sie anders – Namen in BEFUNDE.md festhalten.")
        return 1
    print("Alles gelesen. Der Weg Python -> JTL ist offen.")
    print("Nächster Schritt: Versuchsplan in README.md")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
