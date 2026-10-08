#!/usr/bin/env python3
"""CSV-Datei inspizieren – für Ameise-Exporte und -Vorlagen.

Erkennt Encoding und Trennzeichen selbst, listet alle Spalten mit Füllgrad,
geratenem Typ und Beispielwerten. Spalten, die nie gefüllt sind, werden separat
ausgewiesen – bei Ameise-Vorlagen sind das meist die, die man weglassen kann.

    python3 tools/inspect_csv.py samples/export/auftraege.csv
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
from pathlib import Path

INT = re.compile(r"^-?\d+$")
DECIMAL = re.compile(r"^-?\d+[.,]\d+$")
DATE = re.compile(r"^(\d{4}-\d{2}-\d{2}|\d{2}\.\d{2}\.\d{4})")

ENCODINGS = ["utf-8-sig", "utf-8", "cp1252", "latin-1"]


def decode(raw: bytes) -> tuple[str, str]:
    """(Text, erkanntes Encoding). Reihenfolge ist Absicht: BOM zuerst."""
    for encoding in ENCODINGS:
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace"), "utf-8 (mit Ersatzzeichen)"


def sniff_delimiter(text: str) -> str:
    sample = "\n".join(text.splitlines()[:20])
    try:
        return csv.Sniffer().sniff(sample, delimiters=";,\t|").delimiter
    except csv.Error:
        # Fallback: häufigstes Kandidatenzeichen in der Kopfzeile
        header = text.splitlines()[0] if text.splitlines() else ""
        return max(";,\t|", key=header.count) if header else ";"


def guess_type(values: list[str]) -> str:
    if not values:
        return "–"
    if all(INT.fullmatch(v) for v in values):
        return "int"
    if all(DECIMAL.fullmatch(v) or INT.fullmatch(v) for v in values):
        return "decimal"
    if all(DATE.match(v) for v in values):
        return "date"
    if all(v.lower() in {"true", "false", "0", "1", "ja", "nein"} for v in values):
        return "bool"
    return f"string[{max(len(v) for v in values)}]"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--values", type=int, default=3)
    parser.add_argument("--rows", type=int, default=0,
                        help="nur die ersten N Zeilen lesen (0 = alle)")
    args = parser.parse_args(argv)

    for file_path in args.files:
        if not file_path.exists():
            print(f"{file_path}: nicht gefunden", file=sys.stderr)
            continue

        raw = file_path.read_bytes()
        text, encoding = decode(raw)
        delimiter = sniff_delimiter(text)
        line_ending = "CRLF" if "\r\n" in text else "LF"

        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        columns = reader.fieldnames or []
        rows = []
        for index, row in enumerate(reader):
            rows.append(row)
            if args.rows and index + 1 >= args.rows:
                break

        print(f"\n{'=' * 78}")
        print(f"{file_path.name}  ({len(raw)} Bytes)")
        print("=" * 78)
        print(f"Encoding      {encoding}")
        print(f"Trennzeichen  {delimiter!r}")
        print(f"Zeilenende    {line_ending}")
        print(f"Spalten       {len(columns)}")
        print(f"Datenzeilen   {len(rows)}{' (begrenzt)' if args.rows else ''}")

        if not rows:
            print("\nKeine Datenzeilen – nur Kopfzeile:")
            for column in columns:
                print(f"  {column}")
            continue

        print(f"\n{'Spalte':<34} {'Füllgrad':>9} {'Typ':<14} Beispielwerte")
        print("-" * 78)

        empty: list[str] = []
        for column in columns:
            values = [(row.get(column) or "").strip() for row in rows]
            filled = [v for v in values if v]
            if not filled:
                empty.append(column)
                continue
            rate = f"{len(filled)}/{len(values)}"
            samples = " | ".join(
                v if len(v) <= 22 else v[:19] + "..." for v in filled[:args.values]
            )
            name = column if len(column) <= 33 else column[:30] + "..."
            print(f"{name:<34} {rate:>9} {guess_type(filled):<14} {samples}")

        if empty:
            print(f"\n{len(empty)} Spalte(n) immer leer:")
            for column in empty:
                print(f"  {column}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
