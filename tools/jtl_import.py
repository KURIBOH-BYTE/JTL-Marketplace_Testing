#!/usr/bin/env python3
"""Auftrags-CSV über die Kommandozeile von JTL-Ameise importieren.

Der gewählte Importweg: *Import > Aufträge > Aufträge*. Ameise arbeitet mit
Importvorlagen, die vorher in der grafischen Oberfläche angelegt werden müssen
– **die Vorlage legt fest, welche Spalte in welches JTL-Feld geht.** Welche
Zuordnung die Vorlage braucht, zeigt `--mapping`.

Reihenfolge beim ersten Mal:

    # 1. Welche Zuordnung muss die Vorlage haben?
    python tools\\jtl_import.py --mapping

    # 2. CSV erzeugen (Middleware-Repository daneben nötig)
    python tools\\build_import.py --platform galaxus <bestellung>

    # 3. Vorlage in der Ameise-Oberfläche anlegen und speichern -> ID notieren
    #    Dabei dort "Testen/Trockenlauf" nutzen, bevor echt importiert wird.

    # 4. Danach automatisiert, mit der gespeicherten Vorlage
    python tools\\jtl_import.py samples\\import\\galaxus_9316271.csv --template IMP7

Vor jedem Import eine Datenbanksicherung – das verlangt die JTL-Doku
ausdrücklich. Ohne `--confirm` wird nichts ausgeführt.
"""

from __future__ import annotations

import argparse
import configparser
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
TESTING = HERE.parent
DEFAULT_CONFIG = TESTING / "config.ini"

#: Spalte der erzeugten CSV -> Zuordnung in der Ameise-Importvorlage.
#: Gespiegelt aus connectors/jtl_csv.py (COLUMN_MAPPING) des
#: Middleware-Repositorys, damit dieses Skript ohne es auskommt.
COLUMN_MAPPING = [
    ("Bestellnummer", "Bestellung > Bestell Nr."),
    ("ExterneBestellnummer", "Bestellung > Externe Bestellnummer "
                             "(falls die Vorlage das Feld anbietet)"),
    ("Kundennummer", "Kundendaten laden > Kundennummer"),
    ("Firma", "Lieferadresse > Firma"),
    ("Vorname", "Lieferadresse > Vorname"),
    ("Name", "Lieferadresse > Name"),
    ("Strasse", "Lieferadresse > Strasse"),
    ("Adresszusatz", "Lieferadresse > Adresszusatz"),
    ("PLZ", "Lieferadresse > PLZ"),
    ("Ort", "Lieferadresse > Ort"),
    ("Land", "Lieferadresse > Land"),
    ("Telefon", "Lieferadresse > Telefon (optional)"),
    ("Artikelnummer", "Bestellung Position Artikel-ID Spalten > Artikelnummer"),
    ("EAN", "Bestellung Position Artikel-ID Spalten > EAN (Ausweichweg)"),
    ("Artikelname", "Bestellung Position > Name"),
    ("Menge", "Bestellung Position > Menge"),
    ("PreisBrutto", "Bestellung Position > VK Brutto"),
    ("Positionstyp", "Bestellung Position > Positionstyp"),
    ("Versandart", "Bestellung > Versandart"),
    ("Lieferdatum", "Bestellung > Lieferdatum (optional)"),
    ("Kommentar", "Bestellung > Kommentar"),
]

SETTINGS_HINTS = [
    ("Kopfzeile enthalten", "Ja – die erste Zeile sind die Spaltennamen"),
    ("Spaltenbegrenzer", "Semikolon ;"),
    ("Quote-Zeichen", 'Doppeltes Anführungszeichen "'),
    ("Datei-Encoding", "UTF-8 (die Datei hat ein BOM)"),
    ("Dezimaltrennzeichen", "Punkt . – muss zu jtl.csv.decimal_separator passen"),
    ("Positionstyp", "über die Feldzuordnung, nicht als Standardwert – die "
                     "Datei enthält Artikel und Versandpositionen gemischt"),
    ("Währung", "Standardwert CHF, exakt wie in JTL hinterlegt"),
    ("Identifizierung der Artikel", "Artikelnummer; EAN als Ausweichweg prüfen"),
    ("Bei nicht vorhandenen Artikeln", "Import abbrechen – lieber sichtbar "
                                       "scheitern als eine Position verlieren"),
    ("Preis darf 0 sein", "Ja – wir liefern immer einen Preis mit"),
    ("Als Angebot importieren", "Nein"),
]


def print_mapping() -> int:
    print("Zuordnung für die Ameise-Importvorlage")
    print("=" * 72)
    print("\nSchritt 3 im Ameise-Dialog, Bereich für Bereich:\n")
    width = max(len(name) for name, _ in COLUMN_MAPPING)
    for column, target in COLUMN_MAPPING:
        print(f"  {column:<{width}}  ->  {target}")
    print("\nEinstellungen (Schritt 2 und 4):\n")
    width = max(len(name) for name, _ in SETTINGS_HINTS)
    for setting, value in SETTINGS_HINTS:
        print(f"  {setting:<{width}}  {value}")
    print("\nVorlage anschliessend speichern (Schritt 5). Die angezeigte ID")
    print("beginnt mit IMP und gehört in die config.ini unter [ameise].")
    return 0


def load_config(path: Path) -> configparser.ConfigParser:
    if not path.exists():
        raise SystemExit(
            f"{path} nicht gefunden.\n"
            f"config.example.ini kopieren nach config.ini und ausfüllen."
        )
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(path, encoding="utf-8")
    return parser


def build_command(config, template, source: Path, log: Path, loglevel: int,
                  test_mode: bool) -> list[str]:
    jtl = config["jtl"]
    ameise = config["ameise"]["exe"]
    if not Path(ameise).exists():
        print(f"Hinweis: {ameise} existiert nicht – Pfad in config.ini prüfen.",
              file=sys.stderr)
    command = [
        ameise,
        "-s", jtl["server"],
        "-d", jtl["database"],
        "-u", jtl["user"],
        "-p", jtl["password"],
        "-t", template,
        "-i", str(source),
        f"--loglevel={loglevel}",
        f"--log={log}",
        f"--log_errors={log.with_name(log.stem + '_fehler.txt')}",
        f"--csv_errors={log.with_suffix('.fehler.csv')}",
    ]
    profile = jtl.get("wawiprofile", "").strip()
    if profile:
        command[1:1] = ["-w", profile]
    if test_mode:
        command.append("--mode=test")
    return command


def redacted(command: list[str]) -> str:
    safe = list(command)
    if "-p" in safe:
        safe[safe.index("-p") + 1] = "***"
    return " ".join(f'"{p}"' if " " in p else p for p in safe)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("file", nargs="?", type=Path, help="Auftrags-CSV")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--template", default=None, help="Vorlagen-ID, z.B. IMP7")
    parser.add_argument("--template-key", default="import_orders",
                        help="Schlüssel in [ameise] der config.ini")
    parser.add_argument("--mapping", action="store_true",
                        help="zeigt, wie die Importvorlage zugeordnet werden "
                             "muss, und beendet sich")
    parser.add_argument("--loglevel", type=int, default=1, choices=[1, 3, 5],
                        help="1 ausführlich (Standard beim Testen)")
    parser.add_argument("--test-mode", action="store_true",
                        help="--mode=test an Ameise übergeben")
    parser.add_argument("--confirm", action="store_true",
                        help="wirklich importieren; ohne das nur Trockenlauf")
    args = parser.parse_args(argv)

    if args.mapping:
        return print_mapping()
    if not args.file:
        parser.error("Entweder eine CSV-Datei oder --mapping angeben.")
    if not args.file.exists():
        raise SystemExit(f"{args.file} nicht gefunden")

    config = load_config(args.config)
    template = args.template or config["ameise"].get(args.template_key, "").strip()
    if not template:
        raise SystemExit(
            f"Keine Importvorlage angegeben.\n"
            f"Entweder --template IMP7 oder in config.ini unter [ameise] den "
            f"Schlüssel {args.template_key} setzen.\n\n"
            f"Noch keine Vorlage angelegt? Die nötige Zuordnung zeigt:\n"
            f"  python tools/jtl_import.py --mapping"
        )
    if not template.upper().startswith("IMP"):
        print(f"Warnung: '{template}' sieht nicht wie eine Importvorlage aus "
              f"(Import-IDs beginnen mit IMP).", file=sys.stderr)

    rows = args.file.read_text(encoding="utf-8-sig").count("\n")
    print(f"Datei      {args.file} ({rows} Zeile(n) inkl. Kopfzeile)")
    print(f"Vorlage    {template}\n")

    log = TESTING / "samples" / "export" / (
        f"import_{datetime.now():%Y%m%d-%H%M%S}.log"
    )
    log.parent.mkdir(parents=True, exist_ok=True)
    command = build_command(config, template, args.file, log,
                            args.loglevel, args.test_mode)
    print(f"Aufruf: {redacted(command)}\n")

    if not args.confirm:
        print("Trockenlauf – nichts ausgeführt.")
        print("Vor dem echten Import:")
        print("  1. Datenbanksicherung (verlangt die JTL-Doku ausdrücklich)")
        print("  2. sicherstellen, dass dies das DEV-System ist")
        print("  3. --confirm anhängen")
        return 0

    try:
        result = subprocess.run(command, capture_output=True, text=True)
    except FileNotFoundError:
        raise SystemExit(
            f"{command[0]} nicht gefunden. Pfad in config.ini unter "
            f"[ameise] exe korrigieren."
        )

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    print(f"Exitcode {result.returncode}")

    for path in (log, log.with_name(log.stem + "_fehler.txt"),
                 log.with_suffix(".fehler.csv")):
        if path.exists() and path.stat().st_size:
            print(f"  {path}  ({path.stat().st_size} Bytes)")

    print("\nJetzt in JTL-Wawi nachsehen, ob der Auftrag angekommen ist.")
    print("Befunde nach BEFUNDE.md.")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
