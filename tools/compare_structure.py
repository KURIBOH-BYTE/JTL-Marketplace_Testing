#!/usr/bin/env python3
"""Zwei XML-Dateien strukturell vergleichen.

Der eigentliche Zweck: sobald die echte tXMLBestellImport-Beispieldatei da ist,
zeigt dieses Skript in einem Durchlauf, welche Elemente wir erfunden haben und
welche wir übersehen. Unser Template ist geraten – das ist der Abgleich mit der
Wirklichkeit.

    # Unser geratenes Template gegen die echte Datei
    python3 tools/build_import.py --platform galaxus <bestellung> -o samples/import
    python3 tools/compare_structure.py samples/import/*.xml samples/jtl-vorlagen/echte.xml

Links = unsere Datei (Soll), rechts = Referenz (Ist). Verglichen werden
Elementpfade und Attribute, nicht Werte.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from xml.etree import ElementTree as ET


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def paths_of(element: ET.Element, prefix: str = "") -> set[str]:
    """Alle Elementpfade und Attribute als flache Menge."""
    path = f"{prefix}/{local_name(element.tag)}" if prefix else local_name(element.tag)
    found = {path}
    found.update(f"{path}@{local_name(name)}" for name in element.attrib)
    for child in element:
        found |= paths_of(child, path)
    return found


def load(file_path: Path) -> set[str]:
    try:
        return paths_of(ET.fromstring(file_path.read_bytes()))
    except ET.ParseError as exc:
        print(f"{file_path.name}: kein gültiges XML – {exc}", file=sys.stderr)
        raise SystemExit(1)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("ours", type=Path, help="unsere erzeugte Datei")
    parser.add_argument("reference", type=Path, help="Referenzdatei (echte Vorlage)")
    args = parser.parse_args(argv)

    for file_path in (args.ours, args.reference):
        if not file_path.exists():
            print(f"{file_path}: nicht gefunden", file=sys.stderr)
            return 1

    ours = load(args.ours)
    reference = load(args.reference)

    invented = sorted(ours - reference)
    missing = sorted(reference - ours)
    shared = sorted(ours & reference)

    print(f"unsere Datei:  {args.ours}")
    print(f"Referenz:      {args.reference}\n")

    if invented:
        print(f"ERFUNDEN – bei uns, nicht in der Referenz ({len(invented)}):")
        for path in invented:
            print(f"  + {path}")
        print("  → entweder falsch benannt oder gibt es dort nicht. Template anpassen.\n")

    if missing:
        print(f"FEHLT – in der Referenz, nicht bei uns ({len(missing)}):")
        for path in missing:
            print(f"  - {path}")
        print("  → prüfen, ob Pflichtfeld. Dann ins Template und ggf. ins Modell.\n")

    print(f"ÜBEREINSTIMMEND: {len(shared)} Pfade")
    if not invented and not missing:
        print("\nStruktur identisch.")
        return 0

    print(f"\nFazit: {len(invented)} zu korrigieren, {len(missing)} zu ergänzen.")
    # Exitcode 1, damit das Skript auch in einem Prüflauf verwendbar ist.
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
