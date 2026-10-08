# JTL Marketplace Testing

Testumgebung für die JTL-Seite der Marktplatz-Anbindung.

## Zwei Repositories

| Repository | Inhalt |
| --- | --- |
| [JTL-Marketplace-Integration](https://github.com/KURIBOH-BYTE/JTL-Marketplace-Integration) | die Middleware, Spezifikation und Referenzdokumente |
| **JTL-Marketplace_Testing** (dieses) | Versuche gegen ein echtes JTL-DEV-System |

`build_import.py` nutzt bewusst den Code der Middleware, damit hier getestet
wird, was später produktiv läuft. Dafür muss das andere Repository erreichbar
sein – am einfachsten liegen beide nebeneinander:

```
<irgendein Ordner>/
├── JTL-Marketplace-Integration/
└── JTL-Marketplace_Testing/
```

Dann wird die Middleware automatisch gefunden. Sonst `--middleware <Pfad>`,
die Umgebungsvariable `JTL_MIDDLEWARE` oder `[paths] middleware` in der
`config.ini`.

## Entschieden: alles über JTL-Ameise

| Richtung | Weg |
| --- | --- |
| Aufträge nach JTL | Ameise-Importvorlage, CSV – *Import > Aufträge > Aufträge* |
| Daten aus JTL | Ameise-Exportvorlage, CSV |

Die JTL-Doku beschreibt genau unseren Fall: „ein nicht an JTL-eazyAuction
angebundener Marktplatz, über den Sie regelmässig Aufträge bekommen".

**Das hat das MWST-Problem gelöst.** Ameise nimmt Bruttopreise und holt den
Steuersatz aus dem Artikelstamm. Der XML-Weg verlangte Nettopreise, und für
Zur Rose fehlte der Satz zur Umrechnung.

**Der Preis dafür:** jede Vorlage muss vorher in der grafischen Oberfläche
angelegt werden. Ohne Vorlage kein Import und kein Export, und die Vorlage legt
die Feldzuordnung fest – nicht die Kommandozeile.

Getestet wird ausschliesslich im **DEV-System**, nie live. Vor jedem Import
eine Datenbanksicherung; das verlangt die JTL-Doku ausdrücklich.

> ### Keine echten Bestelldaten committen
> Echte Bestellungen enthalten Namen und Adressen von Endkunden. `samples/` und
> `config.ini` sind per `.gitignore` ausgenommen.
>
> Befunde gehören nach [BEFUNDE.md](BEFUNDE.md), und zwar **ohne** Kundendaten:
> Feldnamen, Längen, Fehlermeldungen – keine Adressen.

## Aufbau

```
JTL-Marketplace_Testing/
├── README.md              dieser Versuchsplan
├── BEFUNDE.md             Protokoll der Ergebnisse  ← das eigentliche Ergebnis
├── setup.ps1              venv anlegen
├── requirements.txt
├── config.example.ini     Zugangsdaten und Ameise-Vorlagen-IDs
├── samples/
│   ├── jtl-vorlagen/      was JTL uns liefert
│   ├── import/            was wir an JTL schicken (erzeugt von build_import.py)
│   └── export/            was JTL ausgibt, plus Ameise-Logs
└── tools/
    ├── build_import.py    Auftrags-CSV aus einer Marktplatz-Bestellung erzeugen
    ├── jtl_import.py      CSV über die Ameise-Kommandozeile importieren
    ├── jtl_export.py      Export über die Ameise-Kommandozeile
    ├── inspect_csv.py     CSV inspizieren (Ameise-Exporte)
    ├── inspect_xml.py     Struktur einer XML-Datei ableiten
    ├── compare_structure.py  erzeugte Datei gegen eine Vorlage vergleichen
    └── hello_jtl.py       optional, liest die Datenbank direkt – nicht der
                           gewählte Weg, nur zur Diagnose
```

## Einrichten

```powershell
powershell -ExecutionPolicy Bypass -File setup.ps1
```

Legt ein venv an, installiert die Abhängigkeiten, zieht die der Middleware dazu
(falls daneben vorhanden) und erzeugt die `config.ini`. Ein venv lässt sich
nicht vorbauen und mitliefern: es enthält absolute Pfade und
plattformspezifische Binärdateien.

Zur Abkürzung in den Beispielen unten:

```powershell
$MW = "..\JTL-Marketplace-Integration\jtl-integration"
$PY = ".venv\Scripts\python.exe"
```

Auf macOS/Linux stattdessen `$MW/.venv/bin/python` und Schrägstriche.

## Der Arbeitsablauf

```
1. Zuordnung ansehen       →  jtl_import.py --mapping
2. CSV erzeugen            →  build_import.py
3. Vorlage anlegen         →  Ameise-Oberfläche, Vorlage speichern
4. Importieren             →  Trockenlauf, dann jtl_import.py --confirm
5. Beobachten & notieren   →  BEFUNDE.md
6. Erzeuger korrigieren    →  Middleware: connectors/jtl_csv.py
7. Zurück zu 2, bis es durchläuft
```

Schritt 6 ist der Punkt: **jede Erkenntnis endet im Code oder in einer
Konfigurationsdatei**, nicht in einem Kommentar. Spaltenaufbau und Werte liegen
in `connectors/jtl_csv.py` und in `config.yaml` unter `jtl.csv`.

---

## Versuch 1: Importvorlage anlegen

Ohne Vorlage geht nichts. Zuerst die nötige Zuordnung ausgeben lassen:

```powershell
& $PY tools\jtl_import.py --mapping
```

Das listet jede Spalte unserer CSV, wohin sie im Ameise-Dialog gehört, und die
Einstellungen für Schritt 2 und 4.

Dann eine Beispieldatei erzeugen, damit die Vorlage gegen echte Spalten
angelegt werden kann:

```powershell
& $PY tools\build_import.py --platform galaxus $MW\tests\fixtures\GORDP_123456_9316271.xml
```

In JTL-Ameise: *Import > Aufträge > Aufträge*, Datei wählen, zuordnen,
**Vorlage speichern**. Die ID beginnt mit `IMP` und gehört in die `config.ini`
unter `[ameise] import_orders`.

**Zu beantworten:**

- [ ] Bietet der Bereich *Bestellung* ein Feld für die **externe
      Bestellnummer**? Davon hängt ab, ob JTL den Doppelimport selbst
      verhindert oder nur unsere SQLite-Verfolgung.
- [ ] Welche Felder bietet der Bereich *Bestellung* sonst noch? Die Doku zählt
      sie nicht auf.
- [ ] Welche **Versand- und Zahlungsarten** existieren? Die Standardwerte in
      Schritt 2 müssen bestehende Namen treffen.
- [ ] Kundennummern von Galaxus und Zur Rose?
- [ ] Vorlagen-ID notiert?

## Versuch 2: Erster Import im Dialog

Mit der gerade angelegten Vorlage: **Testen/Trockenlauf**, dann *Import
starten*. Vorher eine Datenbanksicherung.

**Zu beantworten:**

- [ ] Läuft der Trockenlauf fehlerfrei? Sonst Meldung im Wortlaut festhalten
- [ ] Wird der Auftrag dem festen Kunden zugeordnet, oder entsteht ein neuer?
- [ ] Landet die Lieferadresse am Auftrag, nicht am Kundenstamm?
- [ ] Erscheint die Versandkostenposition als `Versandposition`?
- [ ] Übernimmt JTL unsere `Bestellnummer` (`GAL-9316271`) oder vergibt es eine
      eigene? Sie geht als `SUPPLIER_ORDER_ID` an Galaxus zurück und wird dort
      als Code-39-Barcode auf Retourenlabels gedruckt.
- [ ] Stimmt der MWST-Satz, den JTL aus dem Artikelstamm zieht?

## Versuch 3: Import über die Kommandozeile

Jetzt automatisiert, mit der gespeicherten Vorlage:

```powershell
& $PY tools\jtl_import.py samples\import\galaxus_9316271.csv --template IMP7
```

Zeigt nur den Aufruf. Mit `--confirm` wird wirklich importiert.

Mehrere Bestellungen in einem Aufruf:

```powershell
& $PY tools\build_import.py --platform zur_rose --batch <datei1> <datei2>
& $PY tools\jtl_import.py samples\import\auftraege_*.csv --confirm
```

**Zu beantworten:**

- [ ] Verhält sich der Kommandozeilen-Import wie der Dialog?
- [ ] Was steht bei einem Fehler in den Logdateien? (`--loglevel 1`)
- [ ] Greift `--mode=test` wie der Trockenlauf im Dialog?
- [ ] Werden mehrere Aufträge aus einer Sammeldatei korrekt getrennt?

## Versuch 4: Doppelimport

Dieselbe Datei zweimal importieren.

**Zu beantworten:**

- [ ] Entstehen zwei Aufträge oder lehnt Ameise den zweiten ab?
- [ ] Falls abgelehnt: mit welcher Meldung? Von einem echten Fehler
      unterscheidbar? Die Middleware muss „schon da" als Erfolg behandeln,
      nicht als Fehler – siehe `JtlImportRejected`.
- [ ] Hilft die externe Bestellnummer dabei?

## Versuch 5: Artikelzuordnung

Galaxus schickt `SUPPLIER_PID`, Zur Rose `sellerProductId`. Beides landet bei
uns in der Spalte `Artikelnummer`, dazu die GTIN in `EAN`.

**Zu beantworten:**

- [ ] Entspricht die JTL-Artikelnummer der, die die Marktplätze schicken? Oder
      braucht es eine Zuordnungstabelle?
- [ ] Funktioniert die EAN als Ausweichweg, wenn die Artikelnummer abweicht?
- [ ] Was passiert bei einem unbekannten Artikel? Die Vorlage sollte auf
      *Import abbrechen* stehen – lieber sichtbar scheitern als eine Position
      verlieren.

## Versuch 6: Artikelnamen-Länge

Das bekannte Problem der bestehenden CH–DE-Übermittlung. Wir kürzen auf 80
Zeichen, die echte Grenze ist unbekannt. Galaxus liefert bis zu 150.

```powershell
& $PY tools\build_import.py --platform galaxus --article-name-max 150 <bestellung>
```

**Zu beantworten:**

- [ ] Bei welcher Länge schlägt der Import fehl?
- [ ] Schlägt er fehl oder kürzt JTL selbst stillschweigend?
- [ ] Danach `jtl.article_name_max_length` in `config.yaml` setzen

## Versuch 7: Export und Versanddaten

Die grösste verbleibende Lücke: niemand bemerkt, dass ein Auftrag versandt
wurde. Gebraucht werden Lieferscheinnummer, Versanddatum, Tracking-Nummer und
Versandart.

Dafür braucht es eine **Exportvorlage** – sie legt fest, welche Spalten
herauskommen. Ameise kennt auch eigene SQL-Exporte, womit beliebige Felder
erreichbar sind.

```powershell
& $PY tools\jtl_export.py --template EXP1 --dry-run
```

Ohne `--dry-run` läuft Ameise, und die Exportdatei wird anschliessend
automatisch inspiziert (Spalten, Füllgrad, Beispielwerte).

**Zu beantworten:**

- [ ] Welche Exportvorlagen existieren schon? IDs in `config.ini` eintragen
- [ ] Lässt sich eine Vorlage für Aufträge mit Tracking-Nummer, Versanddatum
      und Versandart anlegen? Kann sie auf „versandt" filtern?
- [ ] Wie erkennt man „versandt, aber noch nicht gemeldet"?
- [ ] Gibt es Teillieferungen, und wie sind sie abgebildet?

### Zuordnung Versanddienstleister

Die JTL-Versandarten müssen auf die erlaubten Werte der Marktplätze abgebildet
werden – Galaxus kennt 42, Zur Rose vier (`POST`, `DPD`, `PLANZER`,
`DHL PARCEL`). Diese Tabelle ist ein Ergebnis dieses Versuchs und gehört
anschliessend in die Konfiguration, nicht in den Code.

## Versuch 8: Produktexport

Für Phase 1 nicht nötig – Produktdaten laufen über den Webshop. Interessant zur
Kontrolle, welche Artikelnummern und GTINs im Sortiment stehen.

```powershell
& $PY tools\jtl_export.py --template-key export_articles
& $PY tools\inspect_csv.py samples\export\export_articles_*.csv
```

---

## Erledigt

**MWST-Satz für Zur Rose.** War der kritische offene Punkt des XML-Wegs: dort
erwartet `fPreisEinzelNetto` netto, Zur Rose liefert nur brutto ohne Satz, und
im Apotheken-Sortiment sind 8.1 % und 2.6 % gemischt. Mit Ameise entfällt das –
die CSV liefert `PreisBrutto`, JTL nimmt den Satz aus dem Artikelstamm.

**Struktur des Auftragsimports.** Offiziell dokumentiert, siehe
[JTL-Schnittstellen-Referenz](https://github.com/KURIBOH-BYTE/JTL-Marketplace-Integration/blob/main/docs/jtl-schnittstelle-reference.md).

## Falls der XML-Weg doch gebraucht wird

Der OldWawi-XML-Weg bleibt im Code erhalten (`jtl.import_format: xml`) und ist
gegen die Doku gebaut. Dann zusätzlich nötig:

```powershell
copy "C:\Program Files\JTL-Software\Importdateien\OldWawi.xsd" samples\jtl-vorlagen\
& $PY tools\build_import.py --platform galaxus --format xml <bestellung>
& $PY tools\inspect_xml.py samples\jtl-vorlagen\OldWawi.xsd
```

In der XSD stehen die erlaubten Werte für `cWaehrung` (ist `CHF` dabei?),
`cPosTyp` und alle Feldlängen.

## Wenn ein Versuch etwas ergibt

1. In [BEFUNDE.md](BEFUNDE.md) eintragen – Datum, Versuch, Ergebnis.
2. Erzeuger bzw. Konfiguration der Middleware anpassen.
3. **Einen Test ergänzen**, der den Befund festhält. Sonst geht er beim nächsten
   Umbau wieder verloren:
   ```powershell
   cd $MW; .venv\Scripts\python -m pytest tests -q
   ```
4. Offenen Punkt in der
   [Spezifikation](https://github.com/KURIBOH-BYTE/JTL-Marketplace-Integration/blob/main/JTL-Galaxus-ZurRose-Integration-Spec.md)
   abhaken.
