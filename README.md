# JTL Marketplace Testing

Testumgebung für die JTL-Seite der Marktplatz-Anbindung.

Hier wird ausprobiert, wie JTL-Wawi Importe und Exporte tatsächlich behandelt.

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

## Worum es geht

Die Struktur des Auftragsimports ist seit der Recherche in der offiziellen Doku
bekannt – siehe [JTL-Schnittstellen-Referenz](https://github.com/KURIBOH-BYTE/JTL-Marketplace-Integration/blob/main/docs/jtl-schnittstelle-reference.md).
Was bleibt, ist das Verhalten: Feldlängen, Pflichtfelder in der Praxis,
Fehlermeldungen, der Weg über die Datenbank und der Lesezugriff auf Versanddaten.

Getestet wird ausschliesslich im **DEV-System**, nie live. `jtl_import_db.py`
schreibt in die Datenbank – ohne `--confirm` passiert nichts.

> ### Keine echten Bestelldaten committen
> Echte Bestellungen enthalten Namen und Adressen von Endkunden. `samples/` und
> `config.ini` sind per `.gitignore` ausgenommen – bis auf die
> `.gitkeep`-Dateien landet dort nichts im Repository, auch nicht in einem
> privaten.
>
> Befunde gehören nach [BEFUNDE.md](BEFUNDE.md), und zwar **ohne** Kundendaten:
> Feldnamen, Längen, Fehlermeldungen – keine Adressen.

## Aufbau

```
JTL-Marketplace_Testing/
├── README.md              dieser Versuchsplan
├── BEFUNDE.md             Protokoll der Ergebnisse  ← das eigentliche Ergebnis
├── setup.ps1              venv anlegen (nur für den vollen Werkzeugkasten)
├── requirements.txt       pyodbc
├── config.example.ini     Zugangsdaten und Ameise-Vorlagen-IDs
├── samples/
│   ├── jtl-vorlagen/      was JTL/FOC uns liefert (OldWawi.xsd, Beispieldateien)
│   ├── import/            was wir an JTL schicken (erzeugt von build_import.py)
│   └── export/            was JTL ausgibt
└── tools/
    ├── hello_jtl.py       erster Kontakt: kommt Python an die Datenbank?
    ├── build_import.py    Import-XML aus einer Marktplatz-Bestellung erzeugen
    ├── jtl_import_db.py   XML in die Tabelle tXMLBestellImport schreiben
    ├── jtl_export.py      Export über die Ameise-Kommandozeile
    ├── inspect_xml.py     Struktur einer XML-Datei ableiten
    ├── compare_structure.py  unsere Datei gegen eine echte Vorlage vergleichen
    └── inspect_csv.py     CSV inspizieren (Ameise-Exporte)
```

## Einrichten

**Für Versuch 0 ist nichts einzurichten** – `tools\hello_jtl.py` läuft mit
System-Python ohne Zusatzpakete.

Für den vollen Werkzeugkasten auf Windows:

```powershell
powershell -ExecutionPolicy Bypass -File setup.ps1
```

Das legt ein venv an, installiert `pyodbc`, zieht die Abhängigkeiten der
Middleware dazu (falls daneben vorhanden) und erzeugt die `config.ini`.
Ein venv lässt sich nicht vorbauen und mitliefern: es enthält absolute Pfade
und plattformspezifische Binärdateien.

Von Hand, oder auf macOS/Linux — die Werkzeuge nutzen das venv der Middleware.
Windows-Schreibweise der Befehle:
[DEV-SERVER.md](https://github.com/KURIBOH-BYTE/JTL-Marketplace-Integration/blob/main/DEV-SERVER.md).

```bash
git clone https://github.com/KURIBOH-BYTE/JTL-Marketplace-Integration.git
git clone https://github.com/KURIBOH-BYTE/JTL-Marketplace_Testing.git

cd JTL-Marketplace-Integration/jtl-integration
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

Die Werkzeuge mit demselben Python aufrufen. Zur Abkürzung in den Beispielen
unten:

```bash
cd ../../JTL-Marketplace_Testing
MW=../JTL-Marketplace-Integration/jtl-integration
PY=$MW/.venv/bin/python
```

Nur `jtl_import_db.py` braucht zwei Dinge mehr: `pip install pyodbc` und den
*ODBC Driver 17 for SQL Server* von Microsoft.

```bash
cp config.example.ini config.ini
```

In `config.ini` gehören die DEV-Datenbankzugänge und die Ameise-Vorlagen-IDs.

## Der Arbeitsablauf

```
1. Unsere Datei erzeugen   →  build_import.py
2. In JTL importieren      →  Dialog oder jtl_import_db.py
3. Beobachten & notieren   →  BEFUNDE.md
4. Template korrigieren    →  $MW/config/templates/jtl_order_import.xml.j2
5. Zurück zu 1, bis es durchläuft
```

Schritt 4 ist der Punkt: **jede Erkenntnis endet in einer Konfigurationsdatei,
nicht in einem Kommentar.** Das Template ist der einzige Ort, der sich ändern
muss – Modell und Ablauf der Middleware bleiben gleich.

---

## Versuch 0: Kommt Python überhaupt an JTL?

Der kleinste sinnvolle Test. **Braucht keine Installation und kein venv:**

```powershell
py tools\hello_jtl.py
```

Zwei Gründe, warum das ohne Vorbereitung geht:

* **Anmeldung** über die Windows-Anmeldung des angemeldeten Benutzers.
  Bei JTL ist Windows-Authentifizierung der Standard, und der Account, der
  den SQL Server installiert hat, hat üblicherweise Zugriff. Kein Passwort
  in einer Datei.
* **Zugriffsweg** über `pyodbc`, falls vorhanden – sonst über `sqlcmd.exe`,
  das mit jeder SQL-Server-Installation mitkommt. Das Skript wählt selbst.

Falls der Windows-Benutzer keine Rechte hat:

```powershell
py tools\hello_jtl.py --user sa --password GEHEIM
```

Anderer Instanzname: `--server "SERVERNAME\JTLWAWI"`.

Das Skript zeigt Verbindung, SQL-Server-Version, Anzahl Tabellen, ob die sechs
relevanten Tabellen existieren, die Spalten von `tArtikel`, drei echte Artikel
und die vorhandenen Versand- und Zahlungsarten.

**Erfolg heisst:** am Ende steht „Der Weg Python -> JTL ist offen."

Jeder Abschnitt läuft einzeln; scheitert einer, meldet das Skript ihn und macht
weiter – so sieht man in einem Durchlauf, was geht und was nicht.

**Zu beantworten:**

- [ ] Steht die Verbindung? Über welchen Weg (pyodbc oder sqlcmd)?
- [ ] Genügt die Windows-Anmeldung, oder braucht es `sa`?
- [ ] Heisst die Datenbank wirklich `eazybusiness`?
- [ ] Existiert `tXMLBestellImport`? (Das ist der automatische Importweg.)
- [ ] Wie heisst die Artikelnummer-Spalte in `tArtikel` – `cArtNr`?
- [ ] **Welche Versand- und Zahlungsarten gibt es?** Das Skript listet sie.
      Diese Namen muss das Import-XML exakt treffen, sonst lehnt JTL ab.

Erst wenn das läuft, lohnen die weiteren Versuche.

### Warum direkt in die Datenbank und nicht über Ameise?

Beides hat seinen Platz, aber nicht denselben:

| | Direkt per SQL | JTL-Ameise |
| --- | --- | --- |
| Zugangsdaten | Windows-Anmeldung, kein Passwort nötig | `-u` und `-p` auf der Kommandozeile – **vermeidet das Passwort also nicht** |
| Vorbereitung | keine | Vorlage muss vorher in der grafischen Oberfläche angelegt werden |
| Abfragen | beliebig | nur was die Vorlage hergibt |
| Ergebnis | direkt im Programm | CSV-Datei |
| Offiziell unterstützt | nein (Lesen ist unkritisch, kann aber bei JTL-Updates brechen) | ja |

Daraus die Aufteilung:

* **Lesen** (erkunden, später Versanddaten holen) → direkt per SQL. Kein
  Vorlagenbau, keine Zwischendateien, und auf einem Server ohne grafische
  Oberfläche ist das der einzige praktikable Weg.
* **Aufträge schreiben** → `tXMLBestellImport`. Das ist der von JTL
  **dokumentierte** automatische Importweg und selbst ein Datenbankzugriff.
  Die ursprüngliche Vorgabe „kein direkter Datenbankzugriff" bezog sich auf
  eigene Schreibzugriffe in Geschäftstabellen, nicht auf diesen Posteingang.
* **Ameise** → wenn die IT ein offiziell unterstütztes Werkzeug verlangt, oder
  für grössere Produktdaten-Exporte, wo eine feste Vorlage ohnehin sinnvoll
  ist. `tools/jtl_export.py` deckt das ab.

Sollte der direkte Lesezugriff nicht erwünscht sein, sag Bescheid – dann baue
ich Versuch 7 auf Ameise um. Das kostet eine Exportvorlage pro Abfrage.

## Versuch 1: OldWawi.xsd besorgen

Die Schemadatei liegt auf jedem JTL-Rechner unter *JTL-Software >
Importdateien* im Programmordner und in jedem Updatepaket. Sie ist die letzte
Instanz für erlaubte Werte und Feldlängen.

```bash
cp "C:\Program Files\JTL-Software\Importdateien\OldWawi.xsd" samples/jtl-vorlagen/
```

**Zu beantworten:**

- [ ] Ist `CHF` bei `cWaehrung` erlaubt? (Die Doku-Beispiele zeigen nur EUR.)
- [ ] Welche Werte kennt `cPosTyp` ausser `standard` und `versandkosten`?
- [ ] Welche Feldlängen gelten – besonders `cName` der Position (Versuch 2)?
- [ ] Ist `ger`/`fra`/`ita`/`eng` die richtige Schreibweise für `cSprache`?

## Versuch 2: Erster Import über den Dialog

Der sichere Weg zuerst: Datei erzeugen, über *Verkauf > Importieren: Aufträge
(\*.xml)* einlesen, beobachten.

```bash
$PY tools/build_import.py --platform galaxus \
    $MW/tests/fixtures/GORDP_123456_9316271.xml
```

Beim Import im Dialog diese Einstellungen (Begründung in Abschnitt 1.5 der
JTL-Referenz):

| Option | Stellung |
| --- | --- |
| Bestehende Kundendaten aktualisieren | **aus** |
| Identische externe Identifikationsnummern nicht importieren | **ein** |
| Lagerbestände nicht anpassen | aus |
| Rechnungen generieren | nach Absprache |

**Zu beantworten:**

- [ ] Läuft der Import durch? Falls nicht: Meldung im Wortlaut festhalten
- [ ] Werden `cVersandartName` und `cZahlungsartName` akzeptiert? Sie müssen
      bestehenden Einträgen entsprechen – vorhandene Werte vorher notieren
- [ ] Ist das Encoding ISO-8859-1 richtig, oder mag JTL UTF-8 lieber?
      (`build_import.py --encoding UTF-8`)
- [ ] Erscheinen die Positionen korrekt, inklusive Versandkostenposition?
- [ ] Landet die Lieferadresse am Auftrag, nicht am Kundenstamm?

## Versuch 3: Artikelnamen-Länge

Das bekannte Problem der bestehenden CH–DE-Übermittlung. Wir kürzen derzeit auf
80 Zeichen, die echte Grenze ist unbekannt. Galaxus liefert
`DESCRIPTION_SHORT` mit bis zu 150 Zeichen.

```bash
$PY tools/build_import.py --platform galaxus --article-name-max 150 \
    $MW/tests/fixtures/GORDP_123456_9316271.xml
```

**Zu beantworten:**

- [ ] Bei welcher Länge schlägt der Import fehl?
- [ ] Schlägt er fehl oder kürzt JTL selbst stillschweigend?
- [ ] Danach `jtl.article_name_max_length` in `config.yaml` korrekt setzen

## Versuch 4: Doppelimport-Schutz prüfen

Laut Doku kann JTL das selbst – über `cExterneBestellNr` und die Import-Option
„Bestellungen mit identischen externen Identifikationsnummern nicht
importieren". Greift das, braucht die Middleware kein eigenes `order_exists`.

Dieselbe Datei zweimal importieren, einmal mit und einmal ohne die Option.

```bash
$PY tools/jtl_import_db.py --check-order 9316271
```

**Zu beantworten:**

- [ ] Verhindert die Option den zweiten Auftrag zuverlässig?
- [ ] Greift sie auch auf dem Weg über `tXMLBestellImport`, oder nur im Dialog?
- [ ] Welche Meldung kommt bei Ablehnung? Von einem echten Fehler
      unterscheidbar? (Die Middleware muss „schon da" als Erfolg behandeln,
      nicht als Fehler – siehe `JtlImportRejected`.)
- [ ] Wofür nutzte FOC die zwei zusätzlichen Referenznummern?

## Versuch 5: Weg über die Datenbank

Der automatische Importweg. **Erst die Tabellenstruktur ansehen** – der
Spaltenname `cText` stammt aus Forenbeiträgen, nicht aus der offiziellen Doku.

```bash
# 1. Welche Spalten hat die Tabelle?
$PY tools/jtl_import_db.py --inspect

# 2. Trockenlauf
$PY tools/jtl_import_db.py samples/import/galaxus_9316271.xml

# 3. Wirklich schreiben
$PY tools/jtl_import_db.py samples/import/galaxus_9316271.xml --confirm

# 4. Hat der Worker einen Auftrag erzeugt?
$PY tools/jtl_import_db.py --check-order 9316271
```

**Zu beantworten:**

- [ ] Wie heissen die Spalten genau?
- [ ] Gibt es eine Statusspalte für Erfolg oder Fehler?
- [ ] Wie verhält sich der Worker bei ungültigem XML – bleibt der Datensatz
      liegen, wird er markiert, verschwindet er?
- [ ] Wie lange dauert es bis zur Verarbeitung?
- [ ] Welcher Datenbankbenutzer darf schreiben?

## Versuch 6: Auftragsnummer zurücklesen

Galaxus will unsere Auftragsnummer in der ORDR (`SUPPLIER_ORDER_ID`) – sie wird
dort als Code-39-Barcode auf Retourenlabels gedruckt und muss ISO/IEC 16388
erfüllen. Die Middleware setzt derzeit `GAL-<Bestellnummer>` als `cBestellNr`.

**Zu beantworten:**

- [ ] Übernimmt JTL unsere `cBestellNr`, oder vergibt es eine eigene Nummer?
- [ ] Falls eigene: über `cExterneBestellNr` nachschlagen – welche Abfrage?
- [ ] Erfüllt das Format die Code-39-Anforderung?

## Versuch 7: Export und Versanddaten

Das ist die zweite grosse Lücke: niemand bemerkt, dass ein Auftrag versandt
wurde. Gebraucht werden Lieferscheinnummer, Versanddatum, Tracking-Nummer und
Versandart.

Ameise braucht dafür eine **Exportvorlage, die vorher in der Oberfläche
erstellt werden muss** – sie legt fest, welche Spalten herauskommen.

```bash
# Vorhandene Vorlage ausprobieren (ID aus der Ameise-Oberfläche)
$PY tools/jtl_export.py --template EXP1

# Nur zeigen, was aufgerufen würde
$PY tools/jtl_export.py --template EXP1 --dry-run
```

Das Skript inspiziert die Exportdatei danach automatisch und zeigt Spalten,
Füllgrad und Beispielwerte.

**Zu beantworten:**

- [ ] Welche Exportvorlagen existieren schon? IDs in `config.ini` eintragen
- [ ] Lässt sich eine Vorlage für Aufträge mit `cTracking`, `dVersandDatum`
      und `cVersandartName` anlegen? Kann sie auf „versandt" filtern?
- [ ] Wie erkennt man „versandt, aber noch nicht gemeldet"? Ein Statusfeld, ein
      Datum, ein eigenes Kennzeichen?
- [ ] Gibt es Teillieferungen, und wie sind sie abgebildet?

### Zuordnung Versanddienstleister

Die JTL-Versandarten müssen auf die erlaubten Werte der Marktplätze abgebildet
werden – Galaxus kennt 42, Zur Rose vier (`POST`, `DPD`, `PLANZER`,
`DHL PARCEL`). Diese Tabelle ist ein Ergebnis dieses Versuchs und gehört
anschliessend in die Konfiguration, nicht in den Code.

## Versuch 8: Produktexport

Für Phase 1 nicht nötig – Produktdaten laufen über den Webshop. Interessant
wird es, falls sich das ändert oder zur Kontrolle, welche Artikelnummern und
GTINs überhaupt im Sortiment stehen.

```bash
$PY tools/jtl_export.py --template-key export_articles
$PY tools/inspect_csv.py samples/export/export_articles_*.csv
```

**Zu beantworten:**

- [ ] Entspricht die JTL-Artikelnummer der, die Galaxus als `SUPPLIER_PID`
      und Zur Rose als `sellerProductId` schickt? Oder braucht es eine
      Zuordnungstabelle?
- [ ] Steht der MWST-Satz am Artikel? Das beantwortet Versuch 8

## Versuch 9: MWST-Satz je Artikel

Zur Rose liefert nur Bruttopreise ohne Steuersatz, `fPreisEinzelNetto` erwartet
aber netto. Ein pauschaler Satz ist falsch: im Sortiment kommen 8.1 % und
2.6 % gemischt vor.

Die Middleware bricht darum ohne gesetzten Ersatzwert sichtbar ab. Zum Testen:

```bash
$PY tools/build_import.py --platform zur_rose --vat-percent 8.1 \
    "$MW/tests/fixtures/2026-10-07T170300.8V7NPS.order.json"
```

**Zu beantworten:**

- [ ] Nimmt der Import den Satz aus dem Artikelstamm, wenn `fMwSt` fehlt?
- [ ] Genügt `fPreis` (brutto) allein, wenn `fPreisEinzelNetto` nicht
      berechenbar ist?
- [ ] Sonst: wie lesen wir den Satz je Artikel vorher aus JTL?

---

## Wenn ein Versuch etwas ergibt

1. In [BEFUNDE.md](BEFUNDE.md) eintragen – Datum, Versuch, Ergebnis.
2. Template bzw. Konfiguration der Middleware anpassen.
3. **Einen Test ergänzen**, der den Befund festhält. Sonst geht er beim nächsten
   Umbau wieder verloren:
   ```bash
   cd ../JTL-Marketplace-Integration/jtl-integration && .venv/bin/python -m pytest tests -q
   ```
4. Offenen Punkt in [Spezifikation](https://github.com/KURIBOH-BYTE/JTL-Marketplace-Integration/blob/main/JTL-Galaxus-ZurRose-Integration-Spec.md)
   abhaken.
