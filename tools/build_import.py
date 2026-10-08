#!/usr/bin/env python3
"""Auftrags-CSV für den Import über JTL-Ameise erzeugen.

Nutzt den Code der Middleware, damit hier getestet wird, was später auch
produktiv läuft – und nicht eine Nachbildung davon.

Erzeugt standardmässig die Ameise-CSV (*Import > Aufträge > Aufträge*).
Mit `--format xml` stattdessen das OldWawi-XML, das als Alternative erhalten
bleibt, aber nicht der gewählte Weg ist.

Die nötige Zuordnung für die Ameise-Importvorlage zeigt:
    python tools/jtl_import.py --mapping

    python3 tools/build_import.py --platform galaxus \\
        $MW/tests/fixtures/GORDP_123456_9316271.xml

    python3 tools/build_import.py --platform zur_rose \\
        $MW/tests/fixtures/*.order.json -o samples/import

Die erzeugte Datei kann man in JTL-Wawi importieren und beobachten, was dabei
passiert. Befunde gehören nach BEFUNDE.md.
"""

from __future__ import annotations

import argparse
import configparser
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TESTING = HERE.parent

#: Kandidaten für die Middleware, in dieser Reihenfolge durchsucht. Sie liegt in
#: einem eigenen Repository (JTL-Marketplace-Integration), darum ist der Pfad
#: nicht fest: er kommt aus --middleware, der Umgebungsvariablen
#: JTL_MIDDLEWARE, der config.ini oder einer dieser üblichen Ablagen.
SIBLING_CANDIDATES = [
    TESTING.parent / "JTL-Marketplace-Integration" / "jtl-integration",
    TESTING.parent / "jtl-integration",
    TESTING / "jtl-integration",
]


def find_middleware(explicit: str | None = None) -> Path:
    """Verzeichnis der Middleware bestimmen (das mit src/ und config/)."""
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    if os.environ.get("JTL_MIDDLEWARE"):
        candidates.append(Path(os.environ["JTL_MIDDLEWARE"]).expanduser())

    config_file = TESTING / "config.ini"
    if config_file.exists():
        parser = configparser.ConfigParser(interpolation=None)
        parser.read(config_file, encoding="utf-8")
        configured = parser.get("paths", "middleware", fallback="").strip()
        if configured:
            candidates.append(Path(configured).expanduser())

    candidates.extend(SIBLING_CANDIDATES)

    for candidate in candidates:
        if (candidate / "src" / "jtl_integration").is_dir():
            return candidate.resolve()

    raise SystemExit(
        "Middleware nicht gefunden.\n\n"
        "Sie liegt im Repository JTL-Marketplace-Integration, Unterordner\n"
        "jtl-integration. Gesucht wurde in:\n"
        + "\n".join(f"  {c}" for c in candidates)
        + "\n\nAbhilfe – eines davon:\n"
        "  --middleware <Pfad>\n"
        "  Umgebungsvariable JTL_MIDDLEWARE\n"
        "  In config.ini:  [paths]\\n  middleware = <Pfad>\n"
        "  Beide Repositories nebeneinander auschecken"
    )


def load_middleware(middleware: Path):
    """Middleware importieren. Erst nach find_middleware aufrufbar."""
    sys.path.insert(0, str(middleware / "src"))
    try:
        from jtl_integration.connectors.base import ConnectorError
        from jtl_integration.connectors.galaxus import GalaxusConnector
        from jtl_integration.connectors.jtl import JtlConnector, JtlDataIncomplete
        from jtl_integration.connectors.zur_rose import ZurRoseConnector
        from jtl_integration.mapping import MappingError
    except ImportError as exc:
        raise SystemExit(
            f"Middleware unter {middleware} gefunden, aber nicht importierbar: {exc}\n"
            f"Abhängigkeiten installiert?\n"
            f"  cd {middleware} && python3 -m venv .venv && "
            f".venv/bin/pip install -r requirements.txt\n"
            f"Und dieses Skript mit demselben Python aufrufen."
        )
    return {
        "ConnectorError": ConnectorError,
        "GalaxusConnector": GalaxusConnector,
        "JtlConnector": JtlConnector,
        "JtlDataIncomplete": JtlDataIncomplete,
        "ZurRoseConnector": ZurRoseConnector,
        "MappingError": MappingError,
    }


def build_connector(api: dict, config_dir: Path, platform: str):
    if platform == "galaxus":
        return api["GalaxusConnector"](
            supplier_id="000000",
            mapping_path=config_dir / "mapping_galaxus_ordp.yaml",
            template_dir=config_dir / "templates",
        )
    return api["ZurRoseConnector"](
        xml_mapping_path=config_dir / "mapping_zurrose_order_xml.yaml"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--platform", required=True, choices=["galaxus", "zur_rose"])
    parser.add_argument("-o", "--out", type=Path, default=TESTING / "samples" / "import")
    parser.add_argument("--middleware", default=None,
                        help="Pfad zum Ordner jtl-integration des "
                             "Integration-Repositorys")
    parser.add_argument("--article-name-max", type=int, default=80,
                        help="Artikelname kürzen auf N Zeichen – zum Ausprobieren, "
                             "wo die Grenze von JTL wirklich liegt")
    parser.add_argument("--format", default="csv", choices=["csv", "xml"],
                        help="csv = Ameise (Standard), xml = OldWawi")
    parser.add_argument("--batch", action="store_true",
                        help="alle Bestellungen in eine CSV schreiben – so "
                             "braucht Ameise nur einen Aufruf")
    parser.add_argument("--vat-percent", default=None,
                        help="MWST-Satz, nur für den XML-Weg. Die Ameise-CSV "
                             "nimmt Bruttopreise, JTL holt den Satz aus dem "
                             "Artikelstamm – dort also nicht nötig.")
    parser.add_argument("--encoding", default=None,
                        help="Encoding; Standard ISO-8859-1 für XML, "
                             "utf-8-sig für CSV")
    args = parser.parse_args(argv)

    middleware = find_middleware(args.middleware)
    api = load_middleware(middleware)
    config_dir = middleware / "config"
    print(f"Middleware: {middleware}")

    connector = build_connector(api, config_dir, args.platform)
    jtl = api["JtlConnector"](
        template_dir=config_dir / "templates",
        mode="dry_run",
        dry_run_dir=args.out,
        article_name_max_length=args.article_name_max,
        customer_numbers={"galaxus": "K-GALAXUS", "zur_rose": "K-ZURROSE"},
        shipping_method="Standard",
        payment_method="Rechnung",
        company_id="1",
        import_format=args.format,
        encoding=args.encoding or "ISO-8859-1",
        vat_percent_fallback=args.vat_percent,
    )

    args.out.mkdir(parents=True, exist_ok=True)
    failures = 0
    collected: list = []

    for file_path in args.files:
        if not file_path.exists():
            print(f"{file_path}: nicht gefunden", file=sys.stderr)
            failures += 1
            continue
        try:
            order = connector.parse_order(file_path.read_bytes(),
                                          source_filename=file_path.name)
        except api["MappingError"] as exc:
            print(f"{file_path.name}: Mapping-Fehler", file=sys.stderr)
            for problem in exc.problems:
                print(f"  - {problem}", file=sys.stderr)
            failures += 1
            continue
        except api["ConnectorError"] as exc:
            print(f"{file_path.name}: {exc}", file=sys.stderr)
            failures += 1
            continue

        if args.batch:
            # Alle Aufträge zusammen in eine Datei – Ameise braucht dann nur
            # einen Aufruf. Geschrieben wird erst nach der Schleife.
            collected.append(order)
            continue

        try:
            jtl.import_order(order)      # dry_run: schreibt die Datei
        except api["JtlDataIncomplete"] as exc:
            print(f"{file_path.name}: {exc}", file=sys.stderr)
            failures += 1
            continue
        target = args.out / f"{order.platform.value}_{order.order_id}.{args.format}"
        print(f"{file_path.name}  ->  {target}")

    if args.batch and collected:
        if args.format != "csv":
            print("--batch gibt es nur für csv", file=sys.stderr)
            return 2
        from datetime import datetime
        target = args.out / f"auftraege_{datetime.now():%Y%m%d-%H%M%S}.csv"
        try:
            target.write_bytes(jtl.build_import_batch(collected))
        except api["JtlDataIncomplete"] as exc:
            print(f"{exc}", file=sys.stderr)
            return 1
        print(f"{len(collected)} Bestellung(en)  ->  {target}")

    if failures:
        print(f"\n{failures} Datei(en) fehlgeschlagen", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
