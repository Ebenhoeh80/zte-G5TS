# ZTE 5G Router für Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Benutzerdefiniert-orange.svg)](https://hacs.xyz/)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.11%2B-blue.svg)](https://www.home-assistant.io/)
[![Aktuelles Release](https://img.shields.io/github/v/release/Ebenhoeh80/zte-G5TS)](https://github.com/Ebenhoeh80/zte-G5TS/releases/latest)
[![Lizenz: MIT](https://img.shields.io/badge/Lizenz-MIT-blue.svg)](./LICENSE)
[![Spenden via PayPal](https://img.shields.io/badge/❤%20Spenden-PayPal-00457C.svg?logo=paypal&logoColor=white)](https://www.paypal.com/pool/9p84qTHCFr?sr=wccr)

Eine Home-Assistant-Custom-Integration zur Überwachung und Steuerung
unterstützter ZTE-4G- und 5G-Router über deren lokale Web-API.

Dieses Repository basiert auf dem
[ursprünglichen Projekt von rosenrot00](https://github.com/rosenrot00/ha-zte-ng-router).

[English documentation](./README.md)

## Inhalt

- [Funktionen](#funktionen)
- [Kompatibilität](#kompatibilität)
- [Voraussetzungen und Netzwerkzugriff](#voraussetzungen-und-netzwerkzugriff)
- [Installation](#installation)
- [Einrichtung](#einrichtung)
- [Sicherheit und Datenschutz](#sicherheit-und-datenschutz)
- [Diagnose und Tests](#diagnose-und-tests)
- [Fehlerbehebung](#fehlerbehebung)
- [Support](#support)
- [Lizenz](#lizenz)

## Funktionen

- WAN-Status, IP-Adressen, Betriebszeit, 4G-/5G-Signalwerte, Funkzelle und
  Bandinformationen.
- Upload-/Download-Raten, Datenzähler, Datenlimits und Routerstatistiken.
- Optionales Tracking verbundener WLAN- und LAN-Geräte.
- Routersteuerung für Mobilfunkdaten, WLAN-Funkmodule, LEDs und Neustart.
- Optionale 4G-/5G-Zellenfixierung (Cell Lock).
- SMS-Posteingang und Versand bei unterstützter Firmware, dazu ein Event
  `zte_5g_router_sms_received` für jede neu empfangene Nachricht.
- Hardware-, Temperatur-, Firmware- und GNSS-Informationen, soweit verfügbar.
- Getrennte Koordinatoren für schnelle und langsame Abfragen. Standardmäßig
  5 bzw. 60 Sekunden; beide Intervalle lassen sich in den Integrationsoptionen
  anpassen.

Welche Daten und Steuerungen verfügbar sind, hängt von Modell und Firmware ab.
Nicht jede Funktion ist auf jedem Gerät vorhanden.

## Kompatibilität

Die Integration unterstützt ZTE-Routerfamilien mit kompatiblen lokalen UBUS-
oder GoForm-Web-APIs. Als funktionierend gemeldet wurden unter anderem:

- G5TS, G5TC, G5C, G5 Max und G5 Ultra
- MC801A, MC888 und MC889
- G51F und MC7510

Die Kompatibilität kann sich je nach Hardware-Revision, Provider-Anpassungen
und Firmware-Version unterscheiden. Die Modellliste garantiert nicht, dass
alle Entitäten und Steuerungen verfügbar sind. Dies ist eine Community-
Integration ohne Verbindung zu oder Empfehlung durch ZTE.

## Voraussetzungen und Netzwerkzugriff

- Home Assistant 2024.11 oder neuer.
- Ein ZTE-Router mit kompatibler lokaler Web-API und Administratorpasswort.
- Netzwerkzugriff vom **Home-Assistant-Host oder der HA-VM** zum Router. Ein
  erfolgreicher Test von einem anderen PC beweist nicht, dass Home Assistant
  den Router ebenfalls erreicht.

Verwende nach Möglichkeit HTTPS. Bei einem selbstsignierten Zertifikat prüfe
den SHA-256-Fingerabdruck anhand einer vertrauenswürdigen, unabhängigen Quelle
und trage ihn in der Integration ein. Wenn HTTPS nicht verfügbar ist, muss
HTTP ausdrücklich freigegeben werden; Zugangsdaten und Sitzungsdaten werden
dann unverschlüsselt übertragen.

Manche ZTE-Firmware erlaubt nur eine aktive WebUI-Sitzung. Abfragen der
Integration können eine Browser-Sitzung abmelden. Falls das auf deinem Router
auftritt, aktiviere vor dem Öffnen der WebUI **Abfrage pausieren (5 Min.)**.

## Installation

### HACS

1. Öffne in Home Assistant **HACS → Integrationen**.
2. Öffne das Menü und wähle **Benutzerdefinierte Repositories**.
3. Füge `https://github.com/Ebenhoeh80/zte-G5TS` mit der Kategorie
   **Integration** hinzu.
4. Suche nach **ZTE 5G Router (G5TS fork)**, lade die Integration herunter
   und starte Home Assistant neu.

### Parallelbetrieb mit der Upstream-Integration

Dieses Projekt teilt sich seinen Router-Protokollcode mit
[rosenrot00/ha-zte-ng-router](https://github.com/rosenrot00/ha-zte-ng-router)
(Domain `zte_ng_router`, im HACS-Standardkatalog als **ZTE NG Router** gelistet).
Beide lassen sich nebeneinander installieren, etwa zum Vergleichen oder zum
Umschalten:

- Sie nutzen unterschiedliche Domains (`zte_5g_router` und `zte_ng_router`);
  Dateien, Config Entries, Geräte, Entitäten, Events und Diagnose sind getrennt.
  Nichts wird geteilt oder überschrieben.
- Entitäten werden nicht zwischen beiden migriert. Jede Integration legt ihre
  eigenen an; nach dem Umschalten Automationen und Dashboards auf die anderen
  Entitäten umstellen (oder die Entitäts-IDs unter
  **Einstellungen → Geräte & Dienste → Entitäten** umbenennen).
- **Immer nur eine aktiv.** Beide sprechen mit demselben Router, und der Router
  erlaubt womöglich nur wenige gleichzeitige Web-Sitzungen; laufen beide, können
  sie sich gegenseitig abmelden (nicht verifiziert). Zum Umschalten unter
  **Einstellungen → Geräte & Dienste** den ZTE-Eintrag öffnen, im Drei-Punkte-Menü
  einen Eintrag **Deaktivieren** und den anderen **Aktivieren**.

### Manuelle Installation

1. Lade `zte_5g_router.zip` aus dem
   [aktuellsten GitHub-Release](https://github.com/Ebenhoeh80/zte-G5TS/releases/latest)
   herunter.
2. Entpacke den Inhalt nach `<config>/custom_components/zte_5g_router/`.
   In diesem Verzeichnis müssen `manifest.json` und die Python-Dateien der
   Integration direkt liegen.
3. Starte Home Assistant neu.

### Integration entfernen

1. Öffne **Einstellungen → Geräte & Dienste** und den Eintrag „ZTE 5G Router“.
2. Wähle **Löschen** und bestätige. Damit werden Eintrag, Entitäten und Gerät aus
   Home Assistant entfernt; an den Router werden keine Daten gesendet.
3. Lösche `<config>/custom_components/zte_5g_router/` und starte Home Assistant
   neu. Das Verzeichnis wird nicht automatisch entfernt.
4. Deaktivierte oder umbenannte Entitäten behalten ihre Anpassungen in der
   Entitätsregistrierung. Entferne sie dort ebenfalls, wenn du die Integration
   nicht erneut installieren möchtest.

## Einrichtung

1. Öffne **Einstellungen → Geräte & Dienste → Integration hinzufügen**.
2. Suche nach **ZTE 5G Router** und folge dem Einrichtungsdialog.
3. Trage Router-URL, Administratorpasswort und Abfrageintervalle ein.

Verwende als URL den HTTPS-Ursprung des Routers, zum Beispiel
`https://192.168.0.1`. Bei einem selbstsignierten Zertifikat kannst du dessen
verifizierten SHA-256-Fingerabdruck eintragen (64 Hex-Zeichen; Doppelpunkte
sind erlaubt). Ohne Fingerabdruck wird die normale Zertifizierungsstellen-
prüfung verwendet. Deaktiviere die TLS-Prüfung nicht als Behelfslösung.

**Unsicheres HTTP erlauben** darf nur aktiviert werden, wenn HTTPS nicht
verwendet werden kann. Zugangsdaten und Sitzungsdaten sind dann für Systeme
mit Zugriff auf das Netzwerk mitlesbar.

Die Standardintervalle sind 60 Sekunden (langsam) und 5 Sekunden (schnell).
Das Tracking von Netzwerkgeräten ist optional und standardmäßig deaktiviert.

Die Einrichtung prüft die Verbindung: Die Integration meldet sich am Router an,
bevor der Eintrag angelegt wird – ein falsches Passwort oder ein nicht
erreichbarer Router wird so direkt im Formular gemeldet statt erst nach der
Einrichtung. Lehnt der Router später das gespeicherte Passwort ab, fordert Home
Assistant zur erneuten Eingabe auf (Neuanmeldung). Geänderte Optionen wirken
sofort, ohne manuelles Neuladen.

Der Eintrag wird über die eigene WLAN-MAC des Routers identifiziert, nicht über
seine Adresse. Hat der Router eine neue IP erhalten, aktualisiere Adresse oder
Passwort über **Neu konfigurieren** am Integrationseintrag – Entity-IDs, Bereiche
und langfristige Statistiken bleiben erhalten. „Neu konfigurieren" lehnt eine
Adresse ab, die zu einem anderen Router gehört; füge in diesem Fall einen neuen
Integrationseintrag hinzu. Bestehende Einträge mit URL-basierter Kennung werden
beim nächsten Start automatisch migriert.

## Sicherheit und Datenschutz

- Die Integration kommuniziert lokal mit dem Router und benötigt kein
  Cloudkonto.
- Das Routerpasswort wird von Home Assistant im Config Entry gespeichert.
- Bevorzuge HTTPS mit verifiziertem Zertifikat oder Fingerabdruck. HTTP und
  deaktivierte Zertifikatsprüfung schwächen den Schutz von Zugangsdaten und
  Sitzung.
- Absendernummern und Nachrichtentexte sind bewusst **nicht** Teil von Zustand oder
  Attributen einer Entität (der Recorder speichert sie, und jeder Benutzer kann sie
  lesen). Der Sensor „Neueste empfangene SMS“ zeigt nur den Zeitstempel der neuesten
  Nachricht. Nutze stattdessen das Event `zte_5g_router_sms_received` (Daten:
  `entry_id`, `name`, `id`, `number`, `date`, `text`) als Automations-Trigger;
  Nachrichten, die beim Start bereits im Posteingang liegen, werden nicht erneut gemeldet.
- Veröffentliche keine Passwörter, Zugriffstokens, Cookies, Session-IDs oder
  unredigierte Diagnoseausgaben.
- Firmware-Update und Router-Neustart ändern den Gerätezustand. Verwende diese
  Funktionen nur, wenn du sie ausdrücklich auslösen möchtest.

## Diagnose und Tests

Das Repository enthält optionale Werkzeuge in [`tools/`](./tools/) für
Verbindungsprüfungen, API-Erkennung und Login-Diagnose. Sie sind für
Entwicklung und Fehlersuche gedacht und werden für den normalen Betrieb nicht
benötigt. Verwende eine Python-Umgebung mit installiertem `aiohttp` und stelle
`ZTEPWD` über die Prozessumgebung bereit – niemals als Kommandozeilenargument,
im Quellcode oder in einem Bericht. Bei selbstsigniertem HTTPS darf
`ZTE_TLS_FINGERPRINT` erst nach unabhängiger Prüfung gesetzt werden.

Die Tests gegen echte Routerhardware müssen ausdrücklich aktiviert werden:

```powershell
$env:RUN_REAL_ROUTER_TESTS = "1"
python -m unittest discover -s tests\integration -v
```

Der Home-Assistant-API-Test in `tools/ha_e2e.py` benötigt `HA_URL` und
`HA_TOKEN`; zum Anlegen eines Eintrags wird zusätzlich `ZTEPWD` benötigt.
Verwende für die HA-API möglichst HTTPS. Home Assistant wird nur neu gestartet,
wenn sowohl `--restart` als auch `HA_ALLOW_RESTART=1` gesetzt sind.

## Automationsbeispiele

Neue SMS eingegangen – Benachrichtigung ohne den Nachrichtentext in den Recorder
oder eine Notification zu kopieren (das Event selbst enthält `entry_id`, `name`,
`id`, `number`, `date` und `text`):

```yaml
alias: ZTE-Router - neue SMS
triggers:
  - trigger: event
    event_type: zte_5g_router_sms_received
actions:
  - action: persistent_notification.create
    data:
      title: Neue SMS am ZTE-Router
      message: Sieh im Router-WebUI nach der Nachricht.
mode: single
```

Für Automatisierungen mit Sensoren sieh die Entity-ID unter **Einstellungen →
Geräte & Dienste → Entitäten** nach; die Sensor-IDs enthalten den bei der
Einrichtung gewählten Namen und unterscheiden sich daher zwischen Installationen.
Verwende Messwerte der schnellen Abfrage (Durchsatz, CPU/RAM) nicht für
langfristige Statistiken – sie sind für die Echtzeitanzeige gedacht.

## Fehlerbehebung

### Timeout bei `web_login_info`

1. Prüfe Router-URL und Protokoll.
2. Teste den Routerzugriff vom **Home-Assistant-Host oder der HA-VM**, nicht
   nur von einem PC oder Hypervisor. Prüfe den passenden Port: HTTP verwendet
   standardmäßig Port 80, HTTPS Port 443.
3. Prüfe Routing, VLANs und Firewallregeln in beide Richtungen zwischen
   Home Assistant und Router.
4. Prüfe bei HTTPS die Zertifikatsvalidierung. Bei einem selbstsignierten
   Zertifikat kann der verifizierte Fingerabdruck eingetragen werden.
5. Ist der Endpunkt erreichbar, der Login schlägt aber weiterhin fehl, notiere
   Fehlermeldung, Routermodell und Firmware-Version. Keine Zugangsdaten,
   Cookies, Tokens oder Session-IDs weitergeben.

### Home Assistant findet die Integration nicht

Prüfe, ob die Dateien unter
`<config>/custom_components/zte_5g_router/` liegen und sich dort
`manifest.json` befindet. Starte Home Assistant nach Installation oder Update
neu.

## Support

Füge beim [Erstellen eines Issues](https://github.com/Ebenhoeh80/zte-G5TS/issues)
nach Möglichkeit folgende Angaben hinzu:

- Routermodell und Firmware-Version.
- Home-Assistant-Version und Installationsart.
- Integrationsversion und betroffene Funktion.
- Relevante, redigierte Logs und Information, ob der Router vom HA-Host aus
  erreichbar ist.

Passwörter, Tokens, Cookies, Session-IDs und unredigierte Routerantworten
dürfen nicht angehängt werden.

## Dank und Lizenz

Dieses Projekt steht unter der [MIT-Lizenz](./LICENSE). Der ursprüngliche
Copyright- und Lizenzhinweis für rosenrot00 bleibt in `LICENSE` erhalten, ergänzt um
das Copyright für die Änderungen (© 2026 Daniel Ebenhöh). Die
MIT-Lizenz verlangt, diesen Copyright-Hinweis und den Lizenztext bei der
Weitergabe von Kopien oder wesentlichen Teilen der Software beizubehalten.

---

## ❤️ Projekt unterstützen

<div align="center">

**Ich entwickle und pflege diese Integration in meiner Freizeit – und trage die laufenden Kosten aus eigener Tasche.**

Wenn sie dir Zeit oder Ärger erspart, hält eine kleine freiwillige Spende das Projekt am Leben und motiviert zu neuen Funktionen.
Jeder Beitrag, egal wie klein, freut mich riesig. Vielen Dank! 🙏

<a href="https://www.paypal.com/pool/9p84qTHCFr?sr=wccr">
  <img src="https://img.shields.io/badge/Spendier%20mir%20einen%20Kaffee-PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white" alt="Spenden via PayPal" height="42">
</a>

</div>
