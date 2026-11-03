# ZTE 5G Router for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue.svg)](https://www.home-assistant.io/)
[![Latest release](https://img.shields.io/github/v/release/Ebenhoeh80/zte-G5TS)](https://github.com/Ebenhoeh80/zte-G5TS/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)

A Home Assistant custom integration for monitoring and controlling supported ZTE
4G and 5G routers over their local web API.

This repository is derived from the
[original project by rosenrot00](https://github.com/rosenrot00/ha-zte-ng-router).

[Deutsche Dokumentation](./README.de.md)

## Contents

- [Features](#features)
- [Compatibility](#compatibility)
- [Requirements and network access](#requirements-and-network-access)
- [Installation](#installation)
- [Configuration](#configuration)
- [Security and privacy](#security-and-privacy)
- [Diagnostics and tests](#diagnostics-and-tests)
- [Troubleshooting](#troubleshooting)
- [Support](#support)
- [License](#license)

## Features

- WAN status, addresses, uptime, 4G/5G signal measurements, serving cell and
  band information.
- Upload/download rates, traffic counters, data limits, and router statistics.
- Optional Wi-Fi and wired-LAN device tracking.
- Router controls for mobile data, Wi-Fi radios, LEDs, and reboot.
- Optional 4G/5G cell locking.
- SMS inbox and send controls on supported firmware.
- Hardware, temperature, firmware, and GNSS information where available.
- Separate fast and slow polling coordinators. Defaults are 5 seconds and
  60 seconds; both intervals can be changed in the integration options.

Some controls and data depend on the router model and firmware. Do not assume
that every listed feature is available on every device.

## Compatibility

The integration targets ZTE router families that expose compatible UBUS or
GoForm web APIs. Models reported to work include:

- G5TS, G5TC, G5C, G5 Max, and G5 Ultra
- MC801A, MC888, and MC889
- G51F and MC7510

Compatibility can vary by hardware revision, provider customizations, and
firmware version. The model list is not a guarantee that every entity or
control is supported. This is a community integration and is not affiliated
with or endorsed by ZTE.

## Requirements and network access

- Home Assistant 2024.1 or later.
- A ZTE router with a compatible local web API and administrator password.
- Network access from the **Home Assistant host or VM** to the router. Testing
  from a separate PC does not prove that Home Assistant can reach it.

Use HTTPS whenever possible. For a router with a self-signed certificate,
verify its SHA-256 certificate fingerprint using a trusted, independent source
and configure the fingerprint in the integration. If HTTPS is unavailable,
HTTP requires an explicit opt-in and sends credentials and session traffic
without encryption.

Some ZTE firmware permits only one active WebUI session. Polling may log out a
browser session; use the integration's **Pause polling (5 min)** control before
opening the router WebUI if this occurs.

## Installation

### HACS

1. In Home Assistant, open **HACS → Integrations**.
2. Open the menu and choose **Custom repositories**.
3. Add `https://github.com/Ebenhoeh80/zte-G5TS` with category **Integration**.
4. Find **ZTE 5G Router**, download it, and restart Home Assistant.

### Manual installation

1. Download `zte_5g_router.zip` from the
   [latest GitHub release](https://github.com/Ebenhoeh80/zte-G5TS/releases/latest).
2. Extract its contents into `<config>/custom_components/zte_5g_router/`.
   The resulting directory should contain `manifest.json` and the integration
   Python files directly.
3. Restart Home Assistant.

### Upgrade from `zte_ng_router`

Version 2.0.0 changed the integration domain to `zte_5g_router`. Home Assistant
does not automatically migrate the old config entry. Remove the old entry and
`custom_components/zte_ng_router` directory, install the new integration, and
add the router again. Review entity IDs and automations after reconfiguration.

## Configuration

1. Go to **Settings → Devices & services → Add integration**.
2. Search for **ZTE 5G Router** and follow the setup form.
3. Enter the router URL, administrator password, and polling preferences.

Use the router's HTTPS origin, for example `https://192.168.0.1`. For a
self-signed certificate, enter its verified SHA-256 fingerprint (64
hexadecimal characters; colons are accepted). Leave the fingerprint blank to
use normal certificate-authority validation. Do not disable TLS verification
as a workaround.

Enable **Allow insecure HTTP** only when HTTPS cannot be used. Credentials and
session data will then be exposed to other systems able to observe the
network.

The default polling intervals are 60 seconds (slow) and 5 seconds (fast).
Network-client tracking is optional and disabled by default.

## Security and privacy

- The integration communicates with the router locally; it does not require a
  cloud account.
- The router password is stored by Home Assistant in the config entry.
- Prefer HTTPS with a verified certificate or fingerprint. HTTP and disabled
  certificate verification weaken credential and session security.
- Do not publish passwords, access tokens, cookies, session identifiers, or
  unredacted diagnostic output.
- Firmware update and router reboot controls can change device state. Use them
  only when intended.

## Diagnostics and tests

The repository includes optional tools in [`tools/`](./tools/) for probing
connectivity, inspecting API availability, and testing login. They are intended
for development and troubleshooting, not required for normal installation.
Use a Python environment with `aiohttp` installed and provide `ZTEPWD` through
the process environment; never put the password in a command-line argument,
source file, or report. For self-signed HTTPS, provide
`ZTE_TLS_FINGERPRINT` only after independently verifying the fingerprint.

The live-router test suite is opt-in:

```powershell
$env:RUN_REAL_ROUTER_TESTS = "1"
python -m unittest discover -s tests\integration -v
```

The Home Assistant API check in `tools/ha_e2e.py` requires `HA_URL` and
`HA_TOKEN`; creating an entry also requires `ZTEPWD`. Prefer HTTPS for the HA
API. The script does not restart Home Assistant unless both `--restart` and
`HA_ALLOW_RESTART=1` are supplied.

## Troubleshooting

### `web_login_info` times out

1. Check that the router URL and scheme are correct.
2. Test the router endpoint from the **Home Assistant host or VM**, not only
   from a workstation or hypervisor. Check the relevant port: HTTP uses port
   80 by default; HTTPS uses port 443 by default.
3. Verify routing, VLANs, and firewall rules in both directions between
   Home Assistant and the router.
4. For HTTPS, check certificate validation and configure a verified
   fingerprint if the certificate is self-signed.
5. If the endpoint is reachable but login still fails, collect the integration
   error and router model/firmware version. Do not include credentials,
   cookies, tokens, or session IDs.

### Home Assistant cannot find the integration

Confirm that the files are under
`<config>/custom_components/zte_5g_router/` and that the directory contains
`manifest.json`. Restart Home Assistant after installation or an update.

## Support

Before [opening an issue](https://github.com/Ebenhoeh80/zte-G5TS/issues), include:

- Router model and firmware version.
- Home Assistant version and installation type.
- Integration version and a description of the affected feature.
- Relevant redacted logs and whether the router is reachable from the HA host.

Never attach passwords, tokens, cookies, session IDs, or unredacted router
responses.

## Credits and license

This project is distributed under the [MIT License](./LICENSE). The original
copyright and license notice for rosenrot00 is retained in `LICENSE`. The MIT
license requires preserving that notice and the permission notice when
redistributing copies or substantial portions of the software.
