# ZTE 5G Router – Home Assistant Integration

[![HACS Default](https://img.shields.io/badge/HACS-Benutzerdefiniert-orange.svg)](https://github.com/hacs/integration)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue.svg)](https://www.home-assistant.io/)
[![Sprache: DE/EN](https://img.shields.io/badge/Sprache-Deutsch%20%7C%20Englisch-green.svg)](#)

[🇬🇧 Switch to English Documentation (README.md)](./README.md)

Eine robuste, vollständige Home Assistant Custom Integration für neuere **ZTE Next-Gen 5G & 4G Router-Plattformen** mit gemeinsamer Firmware- und API-Architektur (UBUS und GoForm).

---

## 📱 Unterstützte Router-Modelle

- **ZTE G5TS** – 5G Indoor CPE (Wi-Fi 6)
- **ZTE G5TC** – 5G FWA / Outdoor & Indoor CPE
- **ZTE G5C** / **ZTE G5 Max** / **ZTE G5 Ultra**
- **ZTE MC801A** / **MC888** / **MC889**
- **ZTE G51F / MC7510** (mit automatischer AES-GCM-SMS-Verschlüsselung)

> ⚠️ **Einzelsitzungs-Hinweis:** Die ZTE-Router-Firmware erlaubt nur eine einzige aktive Anmeldesitzung gleichzeitig. Wenn die Integration im Hintergrund abfragt, wird eine geöffnete Browser-Sitzung im Router-WebUI abgemeldet. Nutze den Schalter **Abfrage pausieren (5 Min.)**, bevor du dich im Browser am Router anmeldest!

---

## ✨ Funktionen & Leistungsmerkmale

### 🌐 Netzwerk- & 5G-Signal-Telemetrie
- **Verbindungsstatus & Betriebszeit:** WAN-Verbindungsstatus, IPv4- und IPv6-Adressen, Boot-Zeitstempel und Dauer der aktiven Sitzung.
- **5G / 4G Funkmetriken:**
  - Signalbalken, RSRP (dBm), RSRQ (dB), SINR (dB) und RSSI (dBm) für 4G LTE und 5G NR.
  - Funkzellen-Identifikatoren: PCI, EARFCN / ARFCN, Zell-ID, LAC-Code, RMCC / RMNC.
  - Zusammenfassung aktiver Bänder (z. B. `B3 + B20 + n78`) und aggregierte Gesamtbandbreite (MHz).

### ⚡ Durchsatz- & Datenverbrauch-Überwachung
- **Echtzeit-Durchsatz:** Schnell abgefragte Download- und Upload-Raten (Mbit/s, bit/s).
- **Tages- & Monatszähler:** Heutiger Download/Upload (nach Router-Tagesgrenze), Paketfehler- und Paketverwerfungszähler.
- **Datenlimits & Rückstellungsplan:** Monatliche Limit-Einstellungen, Warnschwelle in Prozent, Überschreitungsstatus und Abrechnungs-Rückstellungstag.

### 🎛️ Schalter & Steuerungen
- **Mobilfunkdaten-Schalter:** Mobilen Internetzugang ein- oder ausschalten.
- **WLAN-Haupt- & Frequenzschalter:** Master-WLAN-Schalter sowie separate 2,4 GHz- und 5 GHz-Bandschalter.
- **Router-LED-Schalter:** Status-LEDs des Routers aktivieren oder deaktivieren.
- **Abfrage pausieren (5 Min.):** Pausiert das Hintergrundpolling für 5 Minuten für ungestörten WebUI-Zugriff.
- **Router neu starten:** Sicheren Neustart des Routers per UBUS-Aufruf auslösen.

### 🔒 4G- & 5G-Zellenfixierung (Cell Lock)
- Eingabe gewünschter Funkzellenparameter oder Übernahme vorgeschlagener Werte der aktuellen Zelle:
  - **4G-Zellenfixierung:** `PCI,EARFCN`
  - **5G-Zellenfixierung:** `PCI,ARFCN,BAND`
- Eigene Schalter zum Aktivieren und Deaktivieren der Zellensperre.

### 👥 Netzwerkgeräte-Tracking (WLAN & LAN)
- Schreibgeschützter Scanner für verbundene WLAN- und kabelgebundene LAN-Geräte.
- Eindeutige Erkennung über normalisierte MAC-Adresse; Hostname, IPv4, IPv6 und Schnittstelle.
- Konfigurierbare **Abwesenheitsfrist** (Standard: 180 Sekunden), um Fehlabwesenheiten im Schlafmodus mobiler Geräte zu verhindern.

### ✉️ SMS-Zentrale
- Posteingang mit Gesamtzahl, ungelesenen Nachrichten und Speicherkapazität (SIM vs. NV-Speicher).
- Vorschau der neuesten Nachricht und vollständige Dekodierung (UTF-16BE / UCS-2 / GSM-7).
- Automatische Erkennung von **AES-GCM-Verschlüsselung** bei abgesicherten Firmware-Versionen (z. B. G51F / MC7510).
- Verfassen und Senden von SMS über Texteingabe und Button (`Rufnummer,Nachricht`).

### 🛠️ Hardware- & Firmware-Diagnose
- CPU-Auslastung und exakter RAM-Verbrauch (berechnet aus `meminfo` wie im WebUI).
- Modem-Temperatur (°C), CPU-Temperatur und Temperaturwarnstufen (PA/TJ).
- Anzeige von Hardware-Version und innerer Firmware-Version.
- Firmware-Update-Prüfung und Start des Downloads.
- GNSS-Positionsfix und Koordinaten (falls vom Gerät unterstützt).

---

## ⏱️ Polling-Architektur (Schnell & Langsam)

Um den Prozessor des Routers zu schonen und Antwortverzögerungen zu vermeiden, nutzt die Integration zwei separate Koordinatoren:

| Abfragegruppe | Standard-Intervall | Enthaltene Metriken |
|:---|:---:|:---|
| **Schnelles Polling** | **5 Sekunden** | Download- & Upload-Raten, Verbindungsdauer, CPU- & RAM-Auslastung, Tagesverbrauch, Paketfehler/Drops |
| **Langsames Polling** | **60 Sekunden** | Signalmetriken (RSRP, SINR, PCI, Bänder), WAN-IP, Monatslimits, SMS-Posteingang, Gerätetracking, Firmware |

Beide Intervalle können in den Integrations-Optionen angepasst werden.

---

## 🚀 Installation

### Variante 1: Über HACS (Empfohlen)
1. Öffne in Home Assistant **HACS** > **Integrationen**.
2. Klicke oben rechts auf das Drei-Punkte-Menü > **Benutzerdefinierte Repositories**.
3. Füge die Repository-URL ein, wähle Kategorie **Integration** und klicke auf **Hinzufügen**.
4. Suche nach `ZTE 5G Router` und klicke auf **Herunterladen**.
5. Starte Home Assistant neu.

> **Breaking Change in 2.0.0:** Die Integrations-Domain wurde von
> `zte_ng_router` in `zte_5g_router` umbenannt. Home Assistant migriert den
> bisherigen Eintrag nicht automatisch. Entferne den alten Integrationseintrag
> und das Verzeichnis `custom_components/zte_ng_router`, installiere die neue
> Integration unter `custom_components/zte_5g_router` und richte den Router
> erneut ein. Prüfe danach Entity-IDs und Automationen.

### Variante 2: Manuelle Installation
1. Lade das Release-Archiv `zte_5g_router.zip` herunter.
2. Entpacke den Ordner in dein Home Assistant Konfigurationsverzeichnis:
   ```
   <config_dir>/custom_components/zte_5g_router/
   ```
3. Starte Home Assistant neu.

---

## ⚙️ Einrichtung in Home Assistant

1. Gehe zu **Einstellungen** > **Geräte & Dienste** > **Integration hinzufügen**.
2. Suche nach **ZTE 5G Router**.
3. Fülle das Einrichtungsformular aus:
   - **Name:** Eindeutiger Name (z. B. `ZTE 5G Router`)
   - **Router-URL:** `https://192.168.0.1` (oder der HTTPS-Ursprung deines Routers)
   - **Passwort:** Admin-Passwort der Router-Weboberfläche
   - **TLS prüfen:** Standardmäßig aktiviert. Bei selbstsigniertem TLS den SHA-256-Fingerabdruck des Zertifikats aus einer vertrauenswürdigen Quelle verifizieren und eintragen; exakt dieses Zertifikat wird dann gepinnt.
   - **TLS-Fingerabdruck:** Optionaler SHA-256-Zertifikat-Fingerabdruck mit 64 Hex-Zeichen (Doppelpunkte sind erlaubt). Leer lassen für die normale Prüfung über Zertifizierungsstellen. TLS-Prüfung möglichst nicht deaktivieren.
   - **Unsicheres HTTP erlauben:** Nur aktivieren, wenn der Router kein HTTPS unterstützt. Zugangsdaten und Sitzung werden unverschlüsselt übertragen.
   - **Langsames Abfrageintervall:** 60 Sekunden (Standard)
   - **Schnelles Abfrageintervall:** 5 Sekunden (Standard)
   - **Netzwerkgeräte verfolgen:** Aktivieren für WLAN-/LAN-Tracker
   - **Abwesenheitsfrist:** 180 Sekunden (Standard)

### Reale Router-Diagnose

Die optionalen Werkzeuge in `tools/` verwenden standardmäßig den echten Router
unter `https://192.168.0.1`. Verwende Python mit installiertem `aiohttp`
(zum Beispiel die Python-Umgebung von Home Assistant). Setze `ZTEPWD` als
Umgebungsvariable, niemals als Kommandozeilenargument. Bei einem selbstsignierten Zertifikat setze
`ZTE_TLS_FINGERPRINT` auf den unabhängig verifizierten SHA-256-Fingerabdruck
aus der Zertifikatsanzeige. Der Fingerabdruck gehört nur zu diesem Router und
darf nicht für andere Geräte übernommen werden.

```powershell
$env:ZTEPWD = "<Router-Passwort>"
$env:ZTE_TLS_FINGERPRINT = "<64-stelliger-SHA-256-Fingerabdruck>"
python tools/router_probe.py
python tools/api_discovery.py
python tools/login_debug.py
python tools/api_discovery.py --authenticate
```

Authentifizierte Befehle melden sich einmal an und lesen Routerdaten, geben
aber keine Antwortinhalte, Passwörter, Cookies oder Tokens aus. Die
automatisierten Hardwaretests sind nur mit `RUN_REAL_ROUTER_TESTS=1` aktiv:

```powershell
$env:RUN_REAL_ROUTER_TESTS = "1"
python -m unittest discover -s tests\integration -v
```

Ein GoForm-Login wird nur mit dem expliziten Schalter `ZTE_TEST_GOFORM=1`
versucht. Router-Neustarts werden von diesen Werkzeugen nie ausgelöst.
Home-Assistant-Neustarts benötigen die separate explizite Freigabe weiter unten.

Für einen Live-Test des Home-Assistant-Config-Flows und der Entitäten nutze
`tools/ha_e2e.py` mit `HA_URL` und `HA_TOKEN` als Umgebungsvariablen. Das Skript
erstellt den neuen Integrationseintrag, falls noch keiner existiert. Home
Assistant wird nur neu gestartet, wenn sowohl `--restart` als auch
`HA_ALLOW_RESTART=1` gesetzt sind:

```powershell
python tools/ha_e2e.py
# Nur während eines freigegebenen Wartungsfensters:
$env:HA_ALLOW_RESTART = "1"
python tools/ha_e2e.py --restart
```

`HA_TOKEN` und `ZTEPWD` niemals in Reports oder Chats einfügen.

---

## 🌍 Zweisprachige Unterstützung (Deutsch & Englisch)

Die Integration ist von Grund auf zweisprachig aufgebaut:
- **Deutsch** (`translations/de.json`)
- **Englisch** (`translations/en.json`)

Sämtliche Entitätsnamen, Konfigurationsschritte, Beschreibungen und Fehlermeldungen erscheinen automatisch in der in Home Assistant eingestellten Benutzersprache.

---

## 📄 Lizenz

Dieses Projekt steht unter der Apache 2.0 Lizenz. Siehe [LICENSE](./LICENSE) für Details.
