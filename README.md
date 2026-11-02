# ZTE NG Router – Home Assistant Integration

[![HACS Default](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue.svg)](https://www.home-assistant.io/)
[![Language: DE/EN](https://img.shields.io/badge/Language-German%20%7C%20English-green.svg)](#)

[🇩🇪 Zur deutschen Dokumentation (README.de.md)](./README.de.md)

A robust, feature-complete Home Assistant custom integration for recent **ZTE Next-Gen 5G & 4G router platforms** with shared firmware and API architecture (UBUS and GoForm).

---

## 📱 Supported Router Models

- **ZTE G5TS** – 5G Indoor CPE (Wi-Fi 6)
- **ZTE G5TC** – 5G FWA / Outdoor/Indoor CPE
- **ZTE G5C** / **ZTE G5 Max** / **ZTE G5 Ultra**
- **ZTE MC801A** / **MC888** / **MC889**
- **ZTE G51F / MC7510** (with AES-GCM encrypted SMS support)

> ⚠️ **Single Session Note:** ZTE router firmware enforces a single active login session. While this integration is actively polling, web browser sessions to the WebUI will be logged out. Use the **Pause polling (5 min)** switch before logging into the router's web interface!

---

## ✨ Features & Capabilities

### 🌐 Network & 5G Signal Telemetry
- **Connection Status & Uptime:** WAN connection state, IPv4 & IPv6 addresses, device boot time, connection duration.
- **5G / 4G Radio Metrics:**
  - Signal bars, RSRP (dBm), RSRQ (dB), SINR (dB), RSSI (dBm) for both 4G LTE and 5G NR.
  - Serving cell identifiers: PCI, EARFCN / ARFCN, Cell ID, LAC code, RMCC / RMNC.
  - Active carrier bands summary (e.g., `B3 + B20 + n78`) and aggregated total bandwidth (MHz).

### ⚡ Traffic & Bandwidth Monitoring
- **Real-Time Throughput:** Fast-polled download and upload data rates (bit/s, Mbit/s).
- **Daily & Monthly Traffic Counters:** Today's download/upload counters (router day boundary), lifetime packet error and packet drop counters.
- **Data Limits & Reset Schedule:** Monthly limit settings, warning threshold percentage, exceeded status, and configured billing reset day.

### 🎛️ Router Controls & Switches
- **Mobile Data Switch:** Enable or disable cellular WAN connectivity.
- **Wi-Fi Master & Band Switches:** Master Wi-Fi toggle, separate 2.4 GHz and 5 GHz radios.
- **ODU LED Switch:** Turn router status LEDs on or off.
- **Pause Polling (5 min):** Pauses background polling to allow WebUI access without getting logged out.
- **Router Reboot Button:** Remotely reboot the router safely via UBUS service calls.

### 🔒 4G & 5G Cell Lock
- Input target cell parameters directly or use auto-suggested serving cell values:
  - **4G Cell Lock:** `PCI,EARFCN`
  - **5G Cell Lock:** `PCI,ARFCN,BAND`
- Toggle switches to apply or release cell locks.

### 👥 Network Client Tracking (Wi-Fi & LAN)
- Read-only WLAN and wired LAN connected device scanner.
- Deduplication by normalized MAC address; detects hostname, IPv4, IPv6, and connection interface.
- Configurable **absence grace period** (default: 180s) to prevent false away detections during Wi-Fi power-saving sleeps.

### ✉️ SMS Center
- Inbox readout with message count, unread count, and capacity breakdown (SIM vs NV flash).
- Latest message preview and full content decoding (UTF-16BE / UCS-2 / GSM-7).
- Automatic **AES-GCM encryption** detection for protected firmware (e.g., G51F / MC7510).
- Compose & send SMS via text entity and button (`number,message`).

### 🛠️ Hardware & Firmware Diagnostics
- CPU usage percentage and accurate RAM percentage (from router `meminfo`).
- Modem temperature (°C), CPU temperature, and thermal protection levels.
- Hardware version and inner firmware version readouts.
- Firmware update check and start download actions.
- GNSS fix status and coordinates (where supported by hardware).

---

## ⏱️ Polling Architecture

To minimize router CPU load and prevent UI lag, polling is split into two asynchronous coordinators:

| Polling Group | Default Interval | Included Metrics |
|:---|:---:|:---|
| **Fast Polling** | **5 seconds** | Download & upload speeds, connected-since timer, CPU & RAM usage, daily traffic, packet errors/drops |
| **Slow Polling** | **60 seconds** | Signal metrics (RSRP, SINR, PCI, bands), WAN IP, data limits, SMS inbox, network clients, firmware status |

Both intervals are user-configurable in the integration options.

---

## 🚀 Installation

### Option 1: HACS (Recommended)
1. In Home Assistant, open **HACS** > **Integrations**.
2. Click the three dots in the top right > **Custom repositories**.
3. Add the repository URL, select category **Integration**, and click **Add**.
4. Search for `ZTE NG Router` and click **Download**.
5. Restart Home Assistant.

### Option 2: Manual Installation
1. Download the latest release `zte_ng_router.zip`.
2. Extract the archive into your Home Assistant directory:
   ```
   <config_dir>/custom_components/zte_ng_router/
   ```
3. Restart Home Assistant.

---

## ⚙️ Configuration

1. In Home Assistant, go to **Settings** > **Devices & services** > **Add integration**.
2. Search for **ZTE NG Router**.
3. Fill in the configuration dialog:
   - **Name:** Descriptive name (e.g., `ZTE 5G Router`)
   - **Router URL:** `http://192.168.0.1` (or your router's IP address)
   - **Password:** Router WebUI admin password
   - **Verify TLS:** Check only if using HTTPS with a trusted certificate
   - **Slow Polling Interval:** 60 seconds (default)
   - **Fast Polling Interval:** 5 seconds (default)
   - **Track Network Clients:** Toggle ON to discover Wi-Fi/LAN devices
   - **Client Absence Grace Period:** 180 seconds (default)

---

## 🌍 Bilingual Support (DE / EN)

This integration is fully bilingual:
- German (`translations/de.json`)
- English (`translations/en.json`)

All entity names, option dialogs, descriptions, and error messages automatically adapt to your Home Assistant user language.

---

## 📄 License

This project is licensed under the Apache License 2.0. See [LICENSE](./LICENSE) for details.
