# Architecture Overview

## Repository boundaries

This repository contains two separate products:

1. **Home Assistant custom integration** in `custom_components/zte_ng_router`.
   This is the installable integration; the release workflow packages this
   directory as `zte_ng_router.zip`.
2. **React/Vite dashboard and router simulator** in `src/`, with project
   metadata and build configuration at the repository root. The simulator
   stores state in memory and does not connect to Home Assistant or a physical
   router. Its connection test displays a canned success result.

The Python tests in `tests/` exercise the integration with mocked Home
Assistant modules and synthetic router responses. `tests/diagnose_login.py`
is a separate, manually run network diagnostic; it is not part of the test
suite.

## Home Assistant integration

### Setup and lifecycle

- `config_flow.py` creates entries and edits options, including router address,
  credentials, TLS behavior, polling intervals, and optional client tracking.
- `__init__.py` creates one `ZteRouterApi` per config entry, then creates slow
  and fast `DataUpdateCoordinator` instances. Integration-owned interval
  callbacks refresh those coordinators; unload cancels polling and closes the
  API sessions.
- `const.py`, `manifest.json`, `strings.json`, and `translations/` define
  integration constants, metadata, and localized config/entity labels.

### Router transport and protocol

- `zte_api.py` is the integration's transport, authentication, and data
  adaptation boundary.
- UBUS uses JSON-RPC requests, a router session identifier, the
  `web_login_info`/`web_login` challenge flow, and an optional RSA-negotiated
  HTTP encryption key for SMS.
- GoForm is the fallback protocol. It establishes a separate cookie-bearing
  session, obtains an `LD` challenge, hashes the password, and reads fields
  through individual endpoints.
- Both slow and fast coordinator updates enter the same API object. API writes
  and polling use `_request_lock`; authentication uses `_auth_lock`.
- Router-specific payloads are normalized into a shared dictionary consumed
  by entity platforms. The API supports firmware variation by combining UBUS
  and GoForm paths and checking alternate field names.

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
- The frontend build is checked separately with TypeScript and Vite.

## Root-cause status for the reported login failure

The error text proves that both the initial UBUS challenge and GoForm session
initialization failed, but does not identify why. The current diagnostic path
does not retain enough safe transport detail to distinguish connection,
TLS, HTTP status, redirect, HTML response, or router-level authentication
failure. In particular, `async_init_session()` logs and suppresses its
connection exception, while the login fallback reports the GoForm exception
without structured response metadata. A live result from the login diagnostic
on the affected router is required before changing protocol behavior.

The security review did establish a separate, code-level root cause: new
entries default to HTTP and TLS certificate verification is disabled. This
transport configuration is addressed independently of the unconfirmed login
failure.
