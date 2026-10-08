#!/usr/bin/env python3
"""Export aus JTL-Wawi über die Kommandozeile von JTL-Ameise.

Ameise arbeitet mit Vorlagen, die vorher in der grafischen Oberfläche erstellt
werden müssen. **Die Vorlage legt fest, welche Spalten der Export enthält** –
das lässt sich nicht über die Kommandozeile steuern. Jede Vorlage hat eine ID,
sichtbar beim Laden und Speichern; Export-IDs beginnen mit `EXP`.

Nach dem Export wird die Datei automatisch inspiziert, damit man sofort sieht,
welche Spalten tatsächlich herauskamen und wie sie gefüllt sind.

    # Artikel exportieren (Vorlagen-ID aus config.ini)
    python tools\\jtl_export.py --template-key export_articles

    # Beliebige Vorlage direkt
    python tools\\jtl_export.py --template EXP7 -o samples\\export\\artikel.csv

    # Nur zeigen, was aufgerufen würde
    python tools\\jtl_export.py --template EXP7 --dry-run

Doku: docs/jtl-schnittstelle-reference.md im Repository
JTL-Marketplace-Integration, Abschnitt 3.
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
DEFAULT_OUT = TESTING / "samples" / "export"


def load_config(path: Path) -> configparser.ConfigParser:
    if not path.exists():
        raise SystemExit(
            f"{path} nicht gefunden.\n"
            f"config.example.ini kopieren nach config.ini und ausfüllen."
        )
    parser = configparser.ConfigParser()
    # Passwörter und Pfade enthalten oft Zeichen, die der Interpolation
    # in die Quere kommen (%, $).
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(path, encoding="utf-8")
    return parser


def build_command(config: configparser.ConfigParser, template: str,
                  output: Path, log: Path, loglevel: int, test_mode: bool) -> list[str]:
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
        # Laut Doku erwartet -o einen Dateipfad, keinen Ordner.
        "-o", str(output),
        f"--loglevel={loglevel}",
        f"--log={log}",
    ]
    profile = jtl.get("wawiprofile", "").strip()
    if profile:
        command[1:1] = ["-w", profile]
    if test_mode:
        # Ameise kennt test und production; Standard ist production.
        command.append("--mode=test")
    return command


def redacted(command: list[str]) -> str:
    """Kommandozeile fürs Log – ohne Passwort."""
    safe = list(command)
    if "-p" in safe:
        safe[safe.index("-p") + 1] = "***"
    return " ".join(f'"{part}"' if " " in part else part for part in safe)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--template", help="Vorlagen-ID, z.B. EXP7")
    group.add_argument("--template-key",
                       help="Schlüssel aus dem Abschnitt [ameise] der config.ini")
    parser.add_argument("-o", "--out", type=Path, default=None,
                        help="Zieldatei; Standard: samples/export/<key>_<zeit>.csv")
    parser.add_argument("--loglevel", type=int, default=3, choices=[1, 3, 5],
                        help="1 ausführlich, 3 kompakt, 5 nur Fehler (Standard 3)")
    parser.add_argument("--test-mode", action="store_true",
                        help="--mode=test an Ameise übergeben")
    parser.add_argument("--dry-run", action="store_true",
                        help="nur den Aufruf zeigen, nichts ausführen")
    parser.add_argument("--no-inspect", action="store_true",
                        help="erzeugte Datei nicht automatisch inspizieren")
    args = parser.parse_args(argv)

    config = load_config(args.config)

    if args.template_key:
        template = config["ameise"].get(args.template_key, "").strip()
        if not template:
            raise SystemExit(
                f"'{args.template_key}' ist in config.ini nicht gesetzt.\n"
                f"Die Vorlagen-ID steht in der Ameise-Oberfläche beim Laden "
                f"oder Speichern der Exportvorlage und beginnt mit EXP."
            )
        label = args.template_key
    else:
        template = args.template
        label = template

    if not template.upper().startswith("EXP"):
        print(f"Warnung: '{template}' sieht nicht wie eine Exportvorlage aus "
              f"(Export-IDs beginnen mit EXP).", file=sys.stderr)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output = args.out or DEFAULT_OUT / f"{label}_{stamp}.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    log = output.with_suffix(".log")

    command = build_command(config, template, output, log, args.loglevel, args.test_mode)
    print(f"Aufruf: {redacted(command)}\n")

    if args.dry_run:
        print("--dry-run: nichts ausgeführt.")
        return 0

    try:
        result = subprocess.run(command, capture_output=True, text=True)
    except FileNotFoundError:
        raise SystemExit(
            f"{command[0]} nicht gefunden. Pfad in config.ini unter [ameise] exe "
            f"korrigieren."
        )

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    print(f"Exitcode {result.returncode}")

    if log.exists():
        print(f"Ameise-Log: {log}")

    if not output.exists():
        print(f"\nKeine Ausgabedatei erzeugt ({output}).", file=sys.stderr)
        print("Mögliche Ursachen: falsche Vorlagen-ID, Vorlage ist ein Import, "
              "Datenbankzugang, oder der Export war leer.", file=sys.stderr)
        return result.returncode or 1

    size = output.stat().st_size
    print(f"\nExportdatei: {output} ({size} Bytes)")
    if size == 0:
        print("Datei ist leer – Filter der Vorlage prüfen.", file=sys.stderr)
        return 1

    if not args.no_inspect:
        print("\nStruktur der Exportdatei:")
        sys.argv = ["inspect_csv.py", str(output)]
        sys.path.insert(0, str(HERE))
        import inspect_csv

        inspect_csv.main([str(output)])

    print("\nBefunde bitte in BEFUNDE.md eintragen (Versuch 5).")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
