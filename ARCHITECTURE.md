# Architecture Overview

## Repository boundaries

This repository contains two separate products:

1. **Home Assistant custom integration** in `custom_components/zte_5g_router`.
   This is the installable integration; the release workflow packages this
   directory as `zte_5g_router.zip`.
2. **React/Vite dashboard and router simulator** in `src/`, with project
   metadata and build configuration at the repository root. The simulator
   stores state in memory and does not connect to Home Assistant or a physical
   router. Its connection test displays a canned success result.

The Python tests in `tests/` exercise the integration with mocked Home
Assistant modules and synthetic router responses. Optional live-router tests
are in `tests/integration/`. The safe, opt-in tools in `tools/` probe real
HTTP/HTTPS endpoints, authentication, and read-only APIs; they redact router
payloads and require `ZTEPWD` for authenticated checks. `tools/ha_e2e.py`
exercises the real HA config flow, entry setup, entity registry, and optionally
restart recovery; HA restart requires an explicit environment opt-in.

## Home Assistant integration

### Setup and lifecycle

- `config_flow.py` creates entries and edits options, including router address,
  credentials, TLS validation/pinning, polling intervals, and optional client
  tracking.
- `__init__.py` creates one `ZteRouterApi` per config entry and stores the API,
  coordinators, and entry state in typed `ConfigEntry.runtime_data`. Slow and
  fast `DataUpdateCoordinator` instances own their polling intervals. The
  pause switch makes coordinator updates return cached data; unload closes the
  router sessions.
- `const.py`, `manifest.json`, `strings.json`, and `translations/` define
  integration constants, metadata, and localized config/entity labels.
- `diagnostics.py` exports only redacted configuration, coordinator status,
  and non-sensitive firmware identity; it never includes router payloads.

### Router transport and protocol

- `zte_api.py` is the integration's transport, authentication, and data
  adaptation boundary.
- UBUS uses JSON-RPC at `/ubus/`, a bootstrap session identifier, the
  `web_login_info`/`web_login` challenge flow, and an optional RSA-negotiated
  HTTP encryption key for SMS. The password hash is
  `SHA256(uppercase(SHA256(password)) + salt)`, sent as uppercase hex.
- GoForm is used only when UBUS is explicitly unsupported (for example HTTP
  404/405/501 or JSON-RPC method-not-found). It establishes its own cookie
  session, obtains an `LD` challenge, sends the uppercase SHA-256 challenge
  hash, and reads fields through individual endpoints.
- Both slow and fast coordinator updates enter the same API object. API writes
  and polling use `_request_lock`; authentication uses `_auth_lock`.
- Router-specific payloads are normalized into a shared dictionary consumed
  by entity platforms. Firmware alternatives are handled by checking
  alternate field names and by selecting a protocol only when capability
  evidence supports it.
- HTTPS certificate verification is enabled by default. An optional
  out-of-band verified SHA-256 certificate fingerprint supports self-signed
  router certificates without disabling peer identity verification. HTTP and
  unverified HTTPS remain explicit opt-ins.
- Logs include protocol, endpoint, method, status, and safe session state.
  Request/response bodies, cookies, passwords, tokens, and session IDs are
  never logged.

### Entity platforms

- `sensor.py` maps normalized payloads to diagnostic, measurement, and
  timestamp entities. Some sensors use the fast coordinator.
- `switch.py` provides router controls, polling pause, and cell-lock controls.
- `button.py` provides router actions, SMS sending, and firmware actions.
- `text.py` provides cell-lock inputs and SMS composition.
- `device_tracker.py` optionally discovers WLAN/LAN clients and applies an
  absence grace period.

All router entities share one device identifier based on the config entry.
Dynamic client trackers use normalized MAC addresses and are disabled by
default.

## Validation and release

- GitHub Actions run Home Assistant `hassfest` and HACS validation.
- The tagged-release workflow packages only the Home Assistant integration.
- The Python unit tests cover authentication diagnostics, config flow,
  coordinators, entity behavior, tracking, SMS handling, and router features.
- Real hardware tests are skipped unless `RUN_REAL_ROUTER_TESTS=1` is set.
  GoForm-specific login tests require the explicit `ZTE_TEST_GOFORM=1` opt-in.
  Tests do not print credentials, cookies, tokens, session IDs, SMS, or router
  response bodies. They never initiate router restarts. Home Assistant restart
  recovery is exercised only when explicitly authorized by the HA test runner.
- The live HA test needs `HA_URL`, `HA_TOKEN`, and, for new entry creation,
  `ZTEPWD`. It does not expose token or router payloads. `--restart` additionally
  requires `HA_ALLOW_RESTART=1`.
- The frontend build is checked separately with TypeScript and Vite.

## Domain migration and versioning

Version 2.0.0 renames the integration domain to `zte_5g_router`. Home Assistant
does not automatically migrate existing config entries, so users must remove
the old entry and old `custom_components/zte_ng_router` directory, install
`custom_components/zte_5g_router`, and configure the integration again. The
major version reflects that breaking change.

Version 2.0.1 records a follow-up live UBUS login over HTTP after network
routing to the router was restored. The login and session succeeded from the
development PC. This does not establish reachability from the Home Assistant
VM; HTTP also exposes credentials and session traffic and should only be used
on a trusted network. Prefer HTTPS with the router certificate verified by
fingerprint.

## Root-cause status for the reported login failure

The reported error alone did not establish the failure stage. A live,
unauthenticated probe against the configured router established:

1. With normal TLS verification, requests to `/index.html`, `/ubus/`, and the
   GoForm endpoint all fail with `CERTIFICATE_VERIFY_FAILED`. This is the
   verified transport blocker when the secure default is used with the
   router's untrusted/self-signed certificate.
2. With certificate verification disabled for this probe only, `/ubus/`
   returns HTTP 200 and a valid `web_login_info` challenge containing
   `zte_web_sault`, including with the integration's UBUS headers and user
   agent.
3. The same probe's unauthenticated GoForm `LD` request returns HTML after
   redirecting to `/`, not the expected GoForm JSON. It is not evidence that
   GoForm is a valid fallback for this router.
4. After the router certificate fingerprint was independently verified, one
   authenticated test using the integration's UBUS login implementation
   succeeded over pinned HTTPS. It established a UBUS session; the API selected
   `ubus`, and did not invoke GoForm.
5. On 2026-11-03, the opt-in live tests confirmed HTTP and pinned HTTPS both
   return status 200 without redirects. Without the fingerprint, HTTPS fails
   with `ClientConnectorCertificateError`, while HTTP still returns 200.
6. With the verified pin, `web_login_info` returns HTTP 200, JSON-RPC result
   code 0, and the `zte_web_sault` challenge field. The login tool then
   established a real UBUS session without logging its token.
7. The live router identified itself as model `G5TS`, firmware
   `BD_MEDDEG5TSV1.0.0B07`. Fast and full read-only API updates returned WAN,
   network, signal, device, and traffic statistics. A forced stale-session
   cycle caused the integration to authenticate again and resume fast polling.
   After a user-performed router restart, the integration also established a
   new UBUS session and resumed fast polling.
8. GoForm discovery returned HTTP 200 only after a 307 redirect and served
   HTML instead of the expected `LD` JSON. The explicit GoForm test stopped at
   that response and verified that it did not send the password.
9. Five optional UBUS reads returned router errors without an error code:
   four `uci.get` calls for wireless/GNSS sections and
   `zwrt_led.get_ODU_switch_state`. Other tested core, WAN, signal, device,
   traffic, SIM, and SMS reads succeeded. The failing methods are reported
   rather than treated as login failures; their support on this firmware is
   unresolved.
10. After a network route to the router was added, a fresh UBUS login over
    `http://192.168.0.1` from the development PC succeeded and established a
    session. A prior test from the Proxmox host had timed out before HTTP; the
    live HA timeout therefore still needs validation from the HA VM itself.

The previous implementation swallowed the initial page-load failure and
attempted GoForm after *any* UBUS error. That combined unrelated transport and
protocol failures, obscuring the actionable TLS cause and producing the
misleading second GoForm error. Version 2.0.0 removes that preflight request,
preserves safe transport/status metadata, and attempts GoForm only when UBUS
capability is explicitly absent. The router's self-signed/untrusted HTTPS
certificate was the confirmed transport blocker under the secure default; the
pinned authenticated test confirms the UBUS challenge/hash/session path works
with this router. Use only a fingerprint verified out of band; do not disable
certificate verification merely to make authentication succeed. The live test
validated the real API client but did not exercise an installed Home Assistant
instance, HA restart, or actual session expiration duration.

## External protocol comparison

- The current
  [rosenrot00/ha-zte-ng-router](https://github.com/rosenrot00/ha-zte-ng-router)
  source uses the same UBUS `web_login_info` challenge and GoForm API family.
  Its fallback-on-any-UBUS-exception behavior is not suitable when an error is
  a TLS or credential failure.
- The
  [Kajkac ZTE-MC Home Assistant integration](https://github.com/Kajkac/ZTE-MC-Home-assistant-repo)
  covers MC888/MC889 and G5 variants; its G5 Ultra client uses uppercase
  hexadecimal SHA-256 challenge hashes. This supports retaining the firmware
  protocol's fast SHA-256 (rather than substituting a generic password KDF),
  while the local implementation now makes protocol selection stricter.
- The
  [MU5250 OpenUI project](https://github.com/dklasens/MU5250-OpenUI) also
  demonstrates the ZTE `web_login_info` salt flow. It is a different router
  UI, not proof that its endpoint behavior applies to this G5TS firmware.
- Searches found no directly comparable, maintained MU5001 Home Assistant
  integration or PlayFaster UBUS implementation exposing `web_login_info`.
  Those projects therefore provide no evidence to replace the observed G5TS
  UBUS protocol with a different login algorithm.
