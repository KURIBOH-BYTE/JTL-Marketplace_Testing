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
| Automatischer Weg | XML in Tabelle `tXMLBestellImport`, JTL-Worker holt es ab |

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

## Versuch 0: Kommt Python an JTL?

**Status:** offen

| Frage | Antwort |
| --- | --- |
| Verbindung steht? | |
| Zugriffsweg (pyodbc oder sqlcmd) | |
| Genügt die Windows-Anmeldung? | |
| Datenbankname | |
| `tXMLBestellImport` vorhanden? | |
| Artikelnummer-Spalte in `tArtikel` | |
| Vorhandene Versandarten (`tVersandArt.cName`) | |
| Vorhandene Zahlungsarten (`tZahlungsart.cName`) | |

Die letzten zwei Zeilen sind die, die den ersten Import freischalten – ohne
passende Namen lehnt JTL ihn ab.

---

## Versuch 1: Struktur von tXMLBestellImport

**Status:** offen – Beispiel-XML fehlt

| Frage | Antwort |
| --- | --- |
| Wurzelelement | |
| Pflichtfelder | |
| Encoding / Zeilenende | |
| MWST: Satz oder Betrag? | |
| Abweichende Lieferadresse | |

**Abweichungen gegenüber unserem Template** (aus `compare_structure.py`):

```
noch nicht ausgeführt
```

**Daraus geändert:**

- [ ] `jtl-integration/config/templates/jtl_order_import.xml.j2`
- [ ] ggf. `jtl-integration/src/jtl_integration/connectors/jtl.py`

---

## Versuch 2: Artikelnamen-Länge

**Status:** offen

| Frage | Antwort |
| --- | --- |
| Grenze in Zeichen | |
| Fehler oder stilles Kürzen? | |
| Fehlermeldung im Wortlaut | |

**Daraus geändert:**

- [ ] `jtl.article_name_max_length` in `config.yaml`

---

## Versuch 3: Doppelte Bestellnummer

**Status:** offen

| Frage | Antwort |
| --- | --- |
| Zwei Aufträge oder Ablehnung? | |
| Fehlermeldung im Wortlaut | |
| Von echten Fehlern unterscheidbar? | |
| Feld für die Marktplatz-Bestellnummer | |
| Wofür nutzte FOC die zwei Zusatzreferenzen? | |

**Folge für die Middleware:** entscheidet, ob `JtlConnector.order_exists`
gebraucht wird oder ob JTL den Doppelimport selbst abfängt.

---

## Versuch 4: Auftragsnummer zurücklesen

**Status:** offen

| Frage | Antwort |
| --- | --- |
| Wird die Auftragsnummer zurückgegeben? | |
| Format | |
| Code-39-tauglich (ISO/IEC 16388)? | |

---

## Versuch 5: Versanddaten herauslesen

**Status:** offen – der zweite kritische Punkt neben Versuch 1

| Frage | Antwort |
| --- | --- |
| Verfügbarer Weg (Ameise / Webservice / SQL) | |
| Woran erkennt man „versandt, nicht gemeldet"? | |
| Feld für Lieferscheinnummer | |
| Feld für Tracking-Nummer | |
| Feld für Versanddatum | |
| Teillieferungen abgebildet als | |

### Zuordnung Versanddienstleister

Die Werte in JTL müssen auf die erlaubten Werte der Marktplätze abgebildet
werden. Zur Rose erlaubt nur `POST`, `DPD`, `PLANZER`, `DHL PARCEL`; Galaxus 42
Werte (vollständige Liste in
[Galaxus-Referenz](https://github.com/KURIBOH-BYTE/JTL-Marketplace-Integration/blob/main/docs/galaxus-opentrans-reference.md)).

| Wert in JTL | → Galaxus | → Zur Rose |
| --- | --- | --- |
| | `swisspost` | `POST` |
| | | |

**Daraus zu bauen:** diese Tabelle als Konfiguration, nicht als Code.

---

## Versuch 6: MWST für Zur Rose

**Status:** offen

| Frage | Antwort |
| --- | --- |
| Satz aus Artikelstamm, wenn weggelassen? | |
| Sonst: Woher lesen? | |

---

## Sonstige Beobachtungen

Alles, was auffällt und nicht in einen Versuch passt – unerwartete Meldungen,
Verhalten bei leeren Feldern, Zeitzonen, Rundungen.

| Datum | Beobachtung | Folge |
| --- | --- | --- |
| | | |
