#!/usr/bin/env python3
"""Erster Kontakt: kommt Python überhaupt an die JTL-Datenbank?

Liest nur, schreibt nichts. Zeigt der Reihe nach:

  1. ob die Verbindung steht
  2. welche SQL-Server-Version läuft
  3. ob die Tabellen da sind, die uns interessieren
  4. die Spalten von tArtikel
  5. drei Artikel als Beweis, dass echte Daten herauskommen
  6. die vorhandenen Versand- und Zahlungsarten – die Namen braucht
     der Auftragsimport

Braucht im Normalfall **keine Installation**:

* **Anmeldung** über die Windows-Anmeldung des angemeldeten Benutzers
  (Windows-Authentifizierung ist bei JTL der Standard). Kein Passwort
  irgendwo in einer Datei.
* **Zugriffsweg** über `pyodbc`, falls vorhanden; sonst über `sqlcmd.exe`,
  das mit jeder SQL-Server-Installation mitkommt.

    python hello_jtl.py --server "(local)\\JTLWAWI"

Mit SQL-Anmeldung statt Windows-Anmeldung:

    python hello_jtl.py --server "(local)\\JTLWAWI" --user sa --password GEHEIM
"""

from __future__ import annotations

import argparse
import configparser
import re
import shutil
import subprocess
import sys
from pathlib import Path

TESTING = Path(__file__).resolve().parent.parent

#: Trennzeichen für die sqlcmd-Ausgabe. Soll in echten Daten nicht vorkommen.
SEP = "\x1f"
ROWS_AFFECTED = re.compile(r"^\(\d+ rows? affected\)$|^\(\d+ Zeilen betroffen\)$")

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


class QueryError(Exception):
    pass


# -- Zugriffswege -----------------------------------------------------------


class PyodbcBackend:
    """Zugriff über pyodbc. Sauberer, braucht aber ein Paket und einen Treiber."""

    name = "pyodbc"

    def __init__(self, server, database, user, password):
        import pyodbc

        drivers = [d for d in pyodbc.drivers() if "SQL Server" in d]
        if not drivers:
            raise QueryError(
                "pyodbc ist da, aber kein ODBC-Treiber für SQL Server. "
                f"Vorhanden: {', '.join(pyodbc.drivers()) or '(keine)'}"
            )
        self.driver = sorted(drivers, reverse=True)[0]

        auth = (f"UID={user};PWD={password};" if user
                else "Trusted_Connection=yes;")
        try:
            self.connection = pyodbc.connect(
                f"DRIVER={{{self.driver}}};SERVER={server};DATABASE={database};"
                f"{auth}TrustServerCertificate=yes;",
                timeout=10,
            )
        except pyodbc.Error as exc:
            raise QueryError(describe_error(exc.args[0] if exc.args else "", exc))

    @property
    def detail(self) -> str:
        return self.driver

    def query(self, sql: str) -> list[tuple]:
        cursor = self.connection.cursor()
        cursor.execute(sql)
        return [tuple(row) for row in cursor.fetchall()]

    def close(self) -> None:
        self.connection.close()


class SqlcmdBackend:
    """Zugriff über sqlcmd.exe – kommt mit jeder SQL-Server-Installation mit.

    Damit braucht dieser Test auf dem DEV-Server keine Installation. Für den
    Produktivbetrieb ist pyodbc die bessere Wahl, aber für einen Lesetest ist
    ein Unterprozess vollkommen in Ordnung.
    """

    name = "sqlcmd"

    def __init__(self, server, database, user, password):
        self.exe = shutil.which("sqlcmd")
        if not self.exe:
            raise QueryError(
                "sqlcmd.exe nicht im PATH gefunden.\n"
                "Üblicher Ort: C:\\Program Files\\Microsoft SQL Server\\Client SDK\\"
                "ODBC\\<version>\\Tools\\Binn\\sqlcmd.exe\n"
                "Entweder in den PATH aufnehmen oder pyodbc installieren "
                "(pip install pyodbc)."
            )
        self.base = [self.exe, "-S", server, "-d", database,
                     "-h", "-1", "-W", "-s", SEP, "-C"]
        self.base += ["-U", user, "-P", password] if user else ["-E"]
        # Verbindung sofort prüfen, damit der Fehler hier auftaucht und nicht
        # erst bei der ersten inhaltlichen Abfrage.
        self.query("SELECT 1")

    @property
    def detail(self) -> str:
        return self.exe

    def query(self, sql: str) -> list[tuple]:
        result = subprocess.run(
            self.base + ["-Q", sql], capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            output = (result.stdout + result.stderr).strip()
            raise QueryError(describe_error("", output))
        rows = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line or ROWS_AFFECTED.match(line):
                continue
            rows.append(tuple(
                None if cell.strip() == "NULL" else cell.strip()
                for cell in line.split(SEP)
            ))
        return rows

    def close(self) -> None:
        pass


def describe_error(state: str, detail) -> str:
    text = str(detail)
    hints = [
        ("28000", "Anmeldung abgelehnt."),
        ("Login failed", "Anmeldung abgelehnt – hat dein Windows-Benutzer "
                         "Rechte auf der Datenbank? Sonst --user sa --password …"),
        ("08001", "Server nicht erreichbar."),
        ("Named Pipes Provider", "Server nicht erreichbar – Instanzname richtig? "
                                 "Meist (local)\\JTLWAWI oder SERVERNAME\\JTLWAWI."),
        ("Cannot open database", "Datenbank nicht gefunden oder kein Zugriff. "
                                 "Heisst sie wirklich 'eazybusiness'?"),
        ("42000", "Datenbank nicht gefunden oder kein Zugriff."),
    ]
    for needle, hint in hints:
        if needle in state or needle in text:
            return f"{hint}\n\n{text}"
    return text


def open_backend(choice, server, database, user, password):
    """Zugriffsweg wählen. 'auto' nimmt pyodbc, sonst sqlcmd."""
    attempts = {"auto": ["pyodbc", "sqlcmd"]}.get(choice, [choice])
    problems = []
    for name in attempts:
        backend = {"pyodbc": PyodbcBackend, "sqlcmd": SqlcmdBackend}[name]
        try:
            return backend(server, database, user, password)
        except ImportError:
            problems.append(f"{name}: Paket nicht installiert")
        except QueryError as exc:
            problems.append(f"{name}: {exc}")
    raise SystemExit(
        "Kein Zugriffsweg hat funktioniert.\n\n"
        + "\n\n".join(problems)
    )


# -- Ablauf -----------------------------------------------------------------


def from_config() -> dict[str, str]:
    path = TESTING / "config.ini"
    if not path.exists():
        return {}
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(path, encoding="utf-8")
    if "jtl" not in parser:
        return {}
    return {k: v for k, v in parser["jtl"].items() if v.strip()}


def main(argv: list[str] | None = None) -> int:
    defaults = from_config()
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--server", default=defaults.get("server", "(local)\\JTLWAWI"))
    parser.add_argument("--database", default=defaults.get("database", "eazybusiness"))
    parser.add_argument("--user", default=defaults.get("user"),
                        help="nur für SQL-Anmeldung; ohne das wird die "
                             "Windows-Anmeldung verwendet")
    parser.add_argument("--password", default=defaults.get("password"))
    parser.add_argument("--backend", default="auto",
                        choices=["auto", "pyodbc", "sqlcmd"])
    args = parser.parse_args(argv)

    if args.user and not args.password:
        raise SystemExit("--user ohne --password angegeben.")

    print("=" * 70)
    print("Erster Kontakt zu JTL-Wawi")
    print("=" * 70 + "\n")
    print(f"Server          {args.server}")
    print(f"Datenbank       {args.database}")
    print(f"Anmeldung       {'SQL-Benutzer ' + args.user if args.user else 'Windows-Anmeldung (angemeldeter Benutzer)'}")

    backend = open_backend(args.backend, args.server, args.database,
                           args.user, args.password)
    print(f"Zugriffsweg     {backend.name} ({backend.detail})\n")
    print("Verbindung steht.\n")

    try:
        return report(backend)
    finally:
        backend.close()


def section(title: str, function) -> None:
    """Abschnitt ausführen und Fehler benennen, statt den Lauf abzubrechen.

    Ein Diagnosewerkzeug soll zeigen, was geht, und sagen was nicht. Ein
    Traceback wäre hier das schlechteste Ergebnis.
    """
    print(f"{title}:")
    try:
        function()
    except QueryError as exc:
        print(f"  fehlgeschlagen: {exc}")
    except Exception as exc:                        # noqa: BLE001
        print(f"  unerwartet fehlgeschlagen: {exc!r}")
    print()


def one_value(backend, sql):
    rows = backend.query(sql)
    if not rows or not rows[0]:
        raise QueryError(f"keine Antwort auf: {sql}")
    return rows[0][0]


def table_exists(backend, table: str) -> bool:
    sql = ("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES "
           "WHERE TABLE_NAME = '{}'".format(table))
    return bool(int(one_value(backend, sql)))


def report(backend) -> int:
    missing: list[str] = []

    def show_version():
        version = str(one_value(backend, "SELECT @@VERSION"))
        print(f"  {version.splitlines()[0]}")

    def show_table_count():
        sql = ("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES "
               "WHERE TABLE_TYPE = 'BASE TABLE'")
        print(f"  {one_value(backend, sql)}")

    def check_tables():
        for table, purpose in TABLES_OF_INTEREST:
            try:
                found = table_exists(backend, table)
            except (QueryError, ValueError) as exc:
                print(f"  [?] {table:<22} nicht prüfbar: {exc}")
                continue
            if found:
                count = one_value(backend, f"SELECT COUNT(*) FROM [{table}]")
                print(f"  [x] {table:<22} {str(count):>9} Datensätze")
            else:
                print(f"  [ ] {table:<22} nicht gefunden")
                missing.append(table)
            print(f"      {purpose}")

    def show_columns():
        rows = backend.query(
            "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_NAME = 'tArtikel' ORDER BY ORDINAL_POSITION"
        )
        if not rows:
            print("  keine Spalten gefunden – heisst die Tabelle anders?")
            return
        print(f"  {len(rows)} Spalten, die ersten 12:")
        for row in rows[:12]:
            data_type = row[1] if len(row) > 1 else "?"
            print(f"    {str(row[0]):<30} {data_type}")

    def show_articles():
        for row in backend.query(
            "SELECT TOP 3 kArtikel, cArtNr, cBarcode FROM tArtikel"
        ):
            values = list(row) + [None] * (3 - len(row))
            print(f"  kArtikel {str(values[0]):<8} "
                  f"cArtNr {str(values[1] or '-'):<20} "
                  f"cBarcode {values[2] or '-'}")

    def show_names(table: str):
        def run():
            rows = backend.query(
                f"SELECT TOP 20 cName FROM [{table}] ORDER BY cName"
            )
            if not rows:
                print("  keine Einträge")
            for row in rows:
                print(f"  {row[0]}")
        return run

    section("SQL Server", show_version)
    section("Tabellen in der Datenbank", show_table_count)
    section("Für die Anbindung relevante Tabellen", check_tables)
    section("Spalten von tArtikel", show_columns)
    section("Drei Artikel", show_articles)

    # Das sind die Werte, die der Auftragsimport treffen muss.
    for table, label in (("tVersandArt", "Versandarten (cVersandartName)"),
                         ("tZahlungsart", "Zahlungsarten (cZahlungsartName)")):
        if table not in missing:
            section(label, show_names(table))

    print("=" * 70)
    if missing:
        print(f"Geklappt, aber diese Tabellen fehlen: {', '.join(missing)}")
        print("Vermutlich heissen sie anders – Namen in BEFUNDE.md festhalten.")
        return 1
    print("Alles gelesen. Der Weg Python -> JTL ist offen.")
    print("Versand- und Zahlungsarten oben nach BEFUNDE.md übertragen –")
    print("die braucht der Auftragsimport.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
