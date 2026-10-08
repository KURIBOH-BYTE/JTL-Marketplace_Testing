#!/usr/bin/env python3
"""Auftrags-XML in die Tabelle tXMLBestellImport schreiben.

Das ist der automatische Importweg: man schreibt das OldWawi-XML in eine Spalte
der Tabelle `tXMLBestellImport` in der Datenbank `eazybusiness`, der JTL-Worker
holt es beim nächsten Lauf ab und erzeugt den Auftrag.

**Dieses Skript schreibt in die Datenbank. Nur gegen das DEV-System einsetzen.**
Ohne `--confirm` passiert nichts; der Standard ist ein Trockenlauf.

Der Spaltenname ist nicht offiziell dokumentiert. In JTL-Foren wird `cText`
genannt – darum beginnt das Skript mit `--inspect`, das die tatsächliche
Tabellenstruktur anzeigt. Zuerst das, dann schreiben.

    # 1. Was hat die Tabelle für Spalten?
    python tools\\jtl_import_db.py --inspect

    # 2. Trockenlauf: zeigt das SQL, schreibt nichts
    python tools\\jtl_import_db.py samples\\import\\galaxus_9316271.xml

    # 3. Wirklich schreiben
    python tools\\jtl_import_db.py samples\\import\\galaxus_9316271.xml --confirm

    # 4. Wurde der Auftrag angelegt?
    python tools\\jtl_import_db.py --check-order 9316271

Doku: docs/jtl-schnittstelle-reference.md im Repository
JTL-Marketplace-Integration, Abschnitt 2.
"""

from __future__ import annotations

import argparse
import configparser
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TESTING = HERE.parent
DEFAULT_CONFIG = TESTING / "config.ini"

#: In Foren genannter Spaltenname. Mit --inspect gegenprüfen und bei Abweichung
#: über --column korrigieren.
DEFAULT_COLUMN = "cText"
TABLE = "tXMLBestellImport"


def load_config(path: Path) -> configparser.ConfigParser:
    if not path.exists():
        raise SystemExit(
            f"{path} nicht gefunden.\n"
            f"config.example.ini kopieren nach config.ini und ausfüllen."
        )
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(path, encoding="utf-8")
    return parser


def connect(config: configparser.ConfigParser):
    try:
        import pyodbc
    except ImportError:
        raise SystemExit(
            "pyodbc fehlt. Installieren mit:\n"
            "  ..\\jtl-integration\\.venv\\Scripts\\pip install pyodbc\n"
            "Zusätzlich braucht Windows den 'ODBC Driver 17 for SQL Server' "
            "(oder 18) von Microsoft."
        )

    jtl = config["jtl"]
    drivers = [d for d in pyodbc.drivers() if "SQL Server" in d]
    if not drivers:
        raise SystemExit(
            "Kein SQL-Server-ODBC-Treiber installiert. "
            "'ODBC Driver 17 for SQL Server' von Microsoft nachinstallieren."
        )
    # Neuester zuerst: "ODBC Driver 18" vor "17" vor "SQL Server".
    driver = sorted(drivers, reverse=True)[0]

    connection_string = (
        f"DRIVER={{{driver}}};"
        f"SERVER={jtl['server']};"
        f"DATABASE={jtl['database']};"
        f"UID={jtl['user']};"
        f"PWD={jtl['password']};"
        f"TrustServerCertificate=yes;"
    )
    print(f"Verbindung über {driver} zu {jtl['server']}/{jtl['database']}")
    return pyodbc.connect(connection_string, timeout=10)


def inspect_table(connection, table: str = TABLE) -> int:
    """Spalten der Tabelle anzeigen – vor dem ersten Schreiben zu klären."""
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE
          FROM INFORMATION_SCHEMA.COLUMNS
         WHERE TABLE_NAME = ?
         ORDER BY ORDINAL_POSITION
        """,
        table,
    )
    rows = cursor.fetchall()
    if not rows:
        print(f"Tabelle {table} nicht gefunden.", file=sys.stderr)
        print("Mit folgender Abfrage nach ähnlichen Namen suchen:", file=sys.stderr)
        print("  SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
              "WHERE TABLE_NAME LIKE '%Bestellimport%'", file=sys.stderr)
        return 1

    print(f"\nSpalten von {table}:")
    print(f"  {'Spalte':<28} {'Typ':<14} {'Länge':>8}  NULL?")
    print(f"  {'-' * 62}")
    for name, data_type, length, nullable in rows:
        size = "max" if length == -1 else (str(length) if length else "")
        print(f"  {name:<28} {data_type:<14} {size:>8}  {nullable}")

    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    print(f"\n  {cursor.fetchone()[0]} Datensätze in der Tabelle")
    print("\nSpaltennamen bitte in BEFUNDE.md festhalten (Abschnitt 2 der "
          "JTL-Referenz).")
    return 0


def check_order(connection, external_number: str) -> int:
    """Nachsehen, ob der Worker einen Auftrag zur Marktplatz-Bestellnummer erzeugt hat.

    Genau diese Abfrage fehlt der Middleware noch für `order_exists`.
    """
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT cBestellNr, cExterneBestellNr, dErstellt
              FROM tBestellung
             WHERE cExterneBestellNr = ?
            """,
            external_number,
        )
    except Exception as exc:
        print(f"Abfrage fehlgeschlagen: {exc}", file=sys.stderr)
        print("Tabellen- oder Spaltenname abweichend? Mit --inspect-table "
              "tBestellung nachsehen.", file=sys.stderr)
        return 1

    rows = cursor.fetchall()
    if not rows:
        print(f"Kein Auftrag mit cExterneBestellNr = {external_number}")
        print("Entweder ist der Worker noch nicht gelaufen, oder der Import "
              "ist fehlgeschlagen.")
        return 1
    for order_number, external, created in rows:
        print(f"Auftrag {order_number}  extern {external}  erstellt {created}")
    if len(rows) > 1:
        print(f"\nACHTUNG: {len(rows)} Aufträge zur selben externen Nummer – "
              f"der Doppelimport-Schutz hat nicht gegriffen. "
              f"Das ist ein Befund für Versuch 3.", file=sys.stderr)
    return 0


def insert_xml(connection, column: str, payload: str, confirm: bool) -> int:
    statement = f"INSERT INTO {TABLE} ({column}) VALUES (?)"
    print(f"\nSQL:  {statement}")
    print(f"XML:  {len(payload)} Zeichen")

    if not confirm:
        print("\nTrockenlauf – nichts geschrieben.")
        print("Zum wirklichen Schreiben --confirm anhängen. "
              "Vorher sicherstellen, dass dies das DEV-System ist.")
        return 0

    cursor = connection.cursor()
    cursor.execute(statement, payload)
    connection.commit()
    print("\nGeschrieben. Der JTL-Worker verarbeitet den Datensatz beim nächsten Lauf.")
    print("Danach prüfen mit:  --check-order <Marktplatz-Bestellnummer>")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("file", nargs="?", type=Path, help="Auftrags-XML")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--column", default=DEFAULT_COLUMN,
                        help=f"Zielspalte (Standard {DEFAULT_COLUMN}, mit "
                             f"--inspect gegenprüfen)")
    parser.add_argument("--encoding", default="ISO-8859-1",
                        help="Encoding der XML-Datei (Standard ISO-8859-1)")
    parser.add_argument("--inspect", action="store_true",
                        help=f"Spalten von {TABLE} anzeigen und beenden")
    parser.add_argument("--inspect-table", metavar="TABELLE",
                        help="Spalten einer beliebigen Tabelle anzeigen")
    parser.add_argument("--check-order", metavar="EXTERNE_NR",
                        help="prüfen, ob ein Auftrag zur Marktplatz-Bestellnummer "
                             "existiert")
    parser.add_argument("--confirm", action="store_true",
                        help="wirklich schreiben (ohne dies nur Trockenlauf)")
    args = parser.parse_args(argv)

    config = load_config(args.config)

    payload: str | None = None
    if args.file:
        if not args.file.exists():
            raise SystemExit(f"{args.file} nicht gefunden")
        payload = args.file.read_text(encoding=args.encoding)
        if "<tBestellungen" not in payload:
            print(f"Warnung: {args.file.name} enthält kein <tBestellungen> – "
                  f"ist das eine Auftrags-XML im OldWawi-Format?", file=sys.stderr)

    if not any([args.inspect, args.inspect_table, args.check_order, payload]):
        parser.error("Entweder eine XML-Datei, --inspect, --inspect-table "
                     "oder --check-order angeben.")

    connection = connect(config)
    try:
        if args.inspect:
            return inspect_table(connection)
        if args.inspect_table:
            return inspect_table(connection, args.inspect_table)
        if args.check_order:
            return check_order(connection, args.check_order)
        return insert_xml(connection, args.column, payload, args.confirm)
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
