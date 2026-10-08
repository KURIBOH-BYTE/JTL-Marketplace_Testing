# Fertige Testdateien zum Herunterladen

Hier liegen erzeugte Dateien, damit man sie direkt auf dem DEV-Server
herunterladen kann, ohne vorher etwas einzurichten.

**Keine echten Bestelldaten.** Die zugrunde liegende Bestellung ist eine
Attrappe (Ulla Mustermann, Musterstrasse). Enthalten sind aber die echten
JTL-Werte für Kundennummer, Versand- und Zahlungsart, damit der Import
durchläuft.

| Datei | Was |
| --- | --- |
| `galaxus_9316271.xml` | Auftragsimport für JTL, Format OldWawi. Einlesen über *Verkauf > Importieren: Aufträge (\*.xml)* |

## Einstellungen beim Import

| Option | Stellung |
| --- | --- |
| Bestehende Kundendaten aktualisieren | **aus** |
| Identische externe Identifikationsnummern nicht importieren | **ein** |
| Lagerbestände nicht anpassen | aus |

Vorher eine Datenbanksicherung – das verlangt die JTL-Doku ausdrücklich.

## Selbst erzeugen

```powershell
run.cmd build_import --platform galaxus ..\JTL-Marketplace-Integration\jtl-integration\tests\fixtures\GORDP_123456_9316271.xml --customer-number 47057 --shipping-method "Paket ECO" --payment-method "Rechnung"
```
