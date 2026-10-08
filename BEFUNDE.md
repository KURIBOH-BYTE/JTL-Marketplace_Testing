# Befunde JTL-Import und -Export

Protokoll der Versuche aus [README.md](README.md). Dies ist das eigentliche
Ergebnis dieses Ordners: ohne festgehaltene Befunde bleibt das Wissen bei der
Person, die den Versuch gemacht hat.

**Keine Kundendaten hier eintragen** – Feldnamen, Längen, Fehlermeldungen ja;
Namen und Adressen nein.

Stand: noch nichts am System getestet. Die **Struktur** des Auftragsimports ist
inzwischen aus der offiziellen JTL-Doku bekannt
([JTL-Schnittstellen-Referenz](https://github.com/KURIBOH-BYTE/JTL-Marketplace-Integration/blob/main/docs/jtl-schnittstelle-reference.md)) –
offen ist das **Verhalten** am DEV-System.

Durch die Doku bereits geklärt, hier nur zur Gegenprüfung am System:

| Frage | Antwort aus der Doku |
| --- | --- |
| Wurzelelement | `<tBestellungen>` mit `<tBestellung>` je Auftrag |
| Schema | `OldWawi.xsd`, JTL-Programmordner > Importdateien |
| Feld für die Marktplatz-Bestellnummer | `cExterneBestellNr` |
| Doppelimport-Schutz | eingebaut, über `cExterneBestellNr` + Import-Option |
| MWST | `fMwSt` ist der **Satz** in Prozent, nicht der Betrag |
| Versandkosten | eigene Position mit `cPosTyp=versandkosten` |
| Encoding im Doku-Beispiel | `ISO-8859-1` |
| Datumsformat | `JJJJ-MM-TT` |
| Automatischer Weg (XML) | Tabelle `tXMLBestellImport`, JTL-Worker holt es ab |
| **Gewählter Weg** | **Ameise-Importvorlage, CSV** – offiziell unterstützt |
| Ameise-CSV-Aufbau | eine Zeile je Position, Spaltennamen frei, Zuordnung in der Vorlage |
| Positionstypen | `Artikel`, `Versandposition` (u. a.) |
| MWST bei Zur Rose | **erledigt** – Ameise nimmt brutto, Satz kommt aus dem Artikelstamm |

---

## Umgebung

| | |
| --- | --- |
| JTL-Wawi-Version | 2.0.0 |
| DEV-System | _noch nicht bestätigt_ |
| Import-Weg | tXMLBestellImport hinter einem Server mit JSON-Request (neu zu bauen) |
| Getestet von | |
| Datum | |

---

## Versuch 1: Importvorlage anlegen

**Status:** offen

| Frage | Antwort |
| --- | --- |
| Feld für externe Bestellnummer vorhanden? | |
| Weitere Felder im Bereich *Bestellung* | |
| Vorhandene Versandarten | |
| Vorhandene Zahlungsarten | |
| Kundennummer Galaxus | |
| Kundennummer Zur Rose | |
| Vorlagen-ID (IMP…) | |

Die Versand- und Zahlungsarten plus die Kundennummern sind die Werte, die den
ersten Import freischalten – ohne sie lehnt JTL ab.

---

## Versuch 2: Erster Import im Dialog

**Status:** offen

| Frage | Antwort |
| --- | --- |
| Trockenlauf fehlerfrei? | |
| Fehlermeldung im Wortlaut | |
| Auftrag dem festen Kunden zugeordnet? | |
| Lieferadresse am Auftrag? | |
| Versandkostenposition korrekt? | |
| Eigene Bestellnummer übernommen? | |
| MWST aus dem Artikelstamm korrekt? | |

---

## Versuch 3: Import über die Kommandozeile

**Status:** offen

| Frage | Antwort |
| --- | --- |
| Verhalten wie im Dialog? | |
| Logdateien bei Fehlern brauchbar? | |
| `--mode=test` = Trockenlauf? | |
| Sammeldatei korrekt getrennt? | |

---

## Versuch 4: Doppelimport

**Status:** offen

| Frage | Antwort |
| --- | --- |
| Zwei Aufträge oder Ablehnung? | |
| Meldung im Wortlaut | |
| Von echtem Fehler unterscheidbar? | |
| Hilft die externe Bestellnummer? | |

**Folge:** entscheidet, ob `JtlConnector.order_exists` gebraucht wird.

---

## Versuch 5: Artikelzuordnung

**Status:** offen

| Frage | Antwort |
| --- | --- |
| JTL-Artikelnummer = Marktplatz-Artikelnummer? | |
| EAN als Ausweichweg nutzbar? | |
| Verhalten bei unbekanntem Artikel | |

---

## Versuch 6: Artikelnamen-Länge

**Status:** offen

| Frage | Antwort |
| --- | --- |
| Grenze in Zeichen | |
| Fehler oder stilles Kürzen? | |
| Fehlermeldung im Wortlaut | |

---

## Versuch 7: Export und Versanddaten

**Status:** offen – die grösste verbleibende Lücke

| Frage | Antwort |
| --- | --- |
| Vorhandene Exportvorlagen (IDs) | |
| Vorlage mit Tracking/Versanddatum/Versandart möglich? | |
| Auf „versandt" filterbar? | |
| Woran erkennt man „versandt, nicht gemeldet"? | |
| Teillieferungen abgebildet als | |

### Zuordnung Versanddienstleister

Zur Rose erlaubt nur `POST`, `DPD`, `PLANZER`, `DHL PARCEL`; Galaxus 42 Werte
(Liste in der [Galaxus-Referenz](https://github.com/KURIBOH-BYTE/JTL-Marketplace-Integration/blob/main/docs/galaxus-opentrans-reference.md)).

| Versandart in JTL | → Galaxus | → Zur Rose |
| --- | --- | --- |
| | `swisspost` | `POST` |
| | | |

**Daraus zu bauen:** diese Tabelle als Konfiguration, nicht als Code.

---

## Versuch 8: Produktexport

**Status:** offen, für Phase 1 nicht nötig

| Frage | Antwort |
| --- | --- |
| Vorlagen-ID | |
| Spaltennamen | |

---

## Sonstige Beobachtungen

Alles, was auffällt und nicht in einen Versuch passt – unerwartete Meldungen,
Verhalten bei leeren Feldern, Zeitzonen, Rundungen.

| Datum | Beobachtung | Folge |
| --- | --- | --- |
| | | |
