#!/usr/bin/env python3
"""Struktur einer XML-Datei ableiten.

Nimmt eine beliebige XML-Datei und zeigt, was tatsächlich drinsteht: jeden
Elementpfad, wie oft er vorkommt, welche Attribute auftreten, welcher Datentyp
plausibel ist und Beispielwerte.

Gedacht für den Moment, in dem eine echte Datei auftaucht – die
tXMLBestellImport-Beispieldatei, ein Ameise-Export oder die erste echte ORDP.
Statt die Datei von Hand zu lesen, sieht man die Struktur auf einen Blick und
kann sie mit unseren Annahmen vergleichen (dafür compare_structure.py).

    python3 tools/inspect_xml.py samples/jtl-vorlagen/beispiel.xml
    python3 tools/inspect_xml.py samples/export/*.xml --values 5
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET

INT = re.compile(r"^-?\d+$")
DECIMAL = re.compile(r"^-?\d+[.,]\d+$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DATETIME = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2})?")
DATE_DE = re.compile(r"^\d{2}\.\d{2}\.\d{4}")
BOOL = {"true", "false", "0", "1", "ja", "nein", "y", "n"}


def guess_type(values: list[str]) -> str:
    """Datentyp aus den beobachteten Werten raten."""
    if not values:
        return "–"
    checks = [
        ("datetime", lambda v: DATETIME.match(v)),
        ("date", lambda v: DATE.fullmatch(v)),
        ("date-de", lambda v: DATE_DE.match(v)),
        ("int", lambda v: INT.fullmatch(v)),
        ("decimal", lambda v: DECIMAL.fullmatch(v)),
        ("bool", lambda v: v.lower() in BOOL),
    ]
    for name, test in checks:
        if all(test(v) for v in values):
            return name
    return f"string[{max(len(v) for v in values)}]"


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def namespace_of(tag: str) -> str | None:
    if tag.startswith("{"):
        return tag[1:].split("}", 1)[0]
    return None


class Stats:
    def __init__(self):
        # Pfad -> Gesamtzahl der Vorkommen
        self.count: dict[str, int] = defaultdict(int)
        # Pfad -> wie oft pro Elterninstanz (für Kardinalität)
        self.per_parent: dict[str, list[int]] = defaultdict(list)
        self.values: dict[str, list[str]] = defaultdict(list)
        self.attributes: dict[str, set[str]] = defaultdict(set)
        self.attr_values: dict[str, set[str]] = defaultdict(set)
        self.namespaces: set[str] = set()
        self.has_children: set[str] = set()


def walk(element: ET.Element, path: str, stats: Stats, max_values: int) -> None:
    stats.count[path] += 1

    ns = namespace_of(element.tag)
    if ns:
        stats.namespaces.add(ns)

    for name, value in element.attrib.items():
        attr = local_name(name)
        stats.attributes[path].add(attr)
        stats.attr_values[f"{path}@{attr}"].add(value)

    children = list(element)
    if children:
        stats.has_children.add(path)
        groups: dict[str, int] = defaultdict(int)
        for child in children:
            groups[local_name(child.tag)] += 1
        for child_name, occurrences in groups.items():
            stats.per_parent[f"{path}/{child_name}"].append(occurrences)
        for child in children:
            walk(child, f"{path}/{local_name(child.tag)}", stats, max_values)
    else:
        text = (element.text or "").strip()
        if text and len(stats.values[path]) < max_values:
            stats.values[path].append(text)
        elif text:
            # Trotzdem für die Typ- und Längenschätzung mitnehmen
            stats.values[path].append(text)


def cardinality(stats: Stats, path: str) -> str:
    occurrences = stats.per_parent.get(path)
    if not occurrences:
        return ""
    low, high = min(occurrences), max(occurrences)
    # Kommt der Pfad seltener vor als sein Elternelement, ist er optional.
    parent = path.rsplit("/", 1)[0]
    parent_count = stats.count.get(parent, 0)
    if parent_count and len(occurrences) < parent_count:
        low = 0
    if low == high:
        return str(low)
    return f"{low}..{high}"


def report(path: Path, stats: Stats, max_values: int) -> None:
    print(f"\n{'=' * 78}")
    print(f"{path.name}  ({path.stat().st_size} Bytes)")
    print("=" * 78)

    if stats.namespaces:
        print("\nNamespaces:")
        for ns in sorted(stats.namespaces):
            print(f"  {ns}")

    print(f"\n{'Pfad':<52} {'Anz':>4} {'Kard':>6}  Typ / Beispielwerte")
    print("-" * 78)

    for element_path in sorted(stats.count):
        depth = element_path.count("/")
        name = element_path.rsplit("/", 1)[-1]
        indent = "  " * depth
        label = f"{indent}{name}"
        if len(label) > 51:
            label = label[:48] + "..."

        count = stats.count[element_path]
        card = cardinality(stats, element_path)

        if element_path in stats.has_children:
            detail = ""
        else:
            values = stats.values.get(element_path, [])
            kind = guess_type(values)
            shown = values[:max_values]
            samples = " | ".join(v if len(v) <= 28 else v[:25] + "..." for v in shown)
            detail = f"{kind}" + (f"  → {samples}" if samples else "  → (leer)")

        print(f"{label:<52} {count:>4} {card:>6}  {detail}")

        for attr in sorted(stats.attributes.get(element_path, ())):
            seen = sorted(stats.attr_values[f"{element_path}@{attr}"])[:max_values]
            print(f"{indent}  @{attr:<48} {'':>4} {'':>6}  {' | '.join(seen)}")

    leaves = [p for p in stats.count if p not in stats.has_children]
    empty = [p for p in leaves if not stats.values.get(p)]
    print(f"\n{len(stats.count)} Pfade, davon {len(leaves)} Blätter.")
    if empty:
        print(f"{len(empty)} Blätter immer leer – evtl. optional oder unbenutzt:")
        for element_path in sorted(empty):
            print(f"  {element_path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--values", type=int, default=3,
                        help="Beispielwerte pro Feld (Standard 3)")
    parser.add_argument("--merge", action="store_true",
                        help="alle Dateien zu einer Struktur zusammenfassen – "
                             "zeigt, welche Felder nur manchmal vorkommen")
    args = parser.parse_args(argv)

    merged = Stats() if args.merge else None

    for file_path in args.files:
        if not file_path.exists():
            print(f"{file_path}: nicht gefunden", file=sys.stderr)
            continue
        try:
            root = ET.fromstring(file_path.read_bytes())
        except ET.ParseError as exc:
            print(f"{file_path.name}: kein gültiges XML – {exc}", file=sys.stderr)
            continue

        target = merged if merged is not None else Stats()
        walk(root, local_name(root.tag), target, args.values)
        if merged is None:
            report(file_path, target, args.values)

    if merged is not None:
        label = Path(f"{len(args.files)} Dateien zusammengefasst")
        print(f"\n{'=' * 78}\n{label}\n{'=' * 78}")
        report_merged(merged, args.values)
    return 0


def report_merged(stats: Stats, max_values: int) -> None:
    print(f"\n{'Pfad':<52} {'Anz':>4} {'Kard':>6}  Typ / Beispielwerte")
    print("-" * 78)
    for element_path in sorted(stats.count):
        depth = element_path.count("/")
        name = element_path.rsplit("/", 1)[-1]
        label = f"{'  ' * depth}{name}"[:51]
        values = stats.values.get(element_path, [])
        detail = "" if element_path in stats.has_children else guess_type(values)
        print(f"{label:<52} {stats.count[element_path]:>4} "
              f"{cardinality(stats, element_path):>6}  {detail}")


if __name__ == "__main__":
    raise SystemExit(main())
