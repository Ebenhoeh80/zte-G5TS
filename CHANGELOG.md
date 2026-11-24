# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.5.0-beta.1] - 2026-11-24

Test/pre-release for the remaining quality-scale work. Not recommended for
production use yet.

### Added
- `coordinator.py`: shared `ZteDataUpdateCoordinator` with one-time connection
  loss and recovery logging (`log-when-unavailable`).
- `entity.py`: shared device info and unique-ID helpers for all platforms
  (`common-modules`).
- `icons.json`: all button, switch and text icons come from translation keys;
  no hardcoded `_attr_icon` assignments remain.
- `repairs.py`: a config-entry-scoped repair with a reauth fix flow when the
  stored router password is rejected at first refresh.
- Stale client trackers are removed from the entity registry after seven days
  of continuous absence and are recreated if the client returns.
- `[tool.mypy]` strict configuration; the new/shared modules pass a strict run.

### Changed
- All five platforms now use the shared entity helpers; entity IDs and device
  identifiers are unchanged.
- Quality scale audit updated: `common-modules`, `log-when-unavailable`,
  `icon-translations`, `repair-issues` and `stale-devices` are `done`.
  `discovery` / `discovery-update-info` and `inject-websession` are documented
  `exempt` with the reasons from the audit.
- `test-coverage` and `strict-typing` stay `todo` with concrete measured gaps.

### Tests
- New tests for shared coordinator/entity/icon helpers, repairs and stale
  client removal. 132 tests plus 95 subtests pass; CI coverage is ~56% with a
  50% floor.

## [2.4.1] - 2026-11-23

### Added
- README (en/de): section on removing the integration and a privacy-friendly
  automation example for the `zte_5g_router_sms_received` event.

### Changed
- All five entity platforms now declare `PARALLEL_UPDATES = 1`, so entity
  updates are serialized through the shared coordinator.
- Quality scale audit updated: `parallel-updates`, `entity-unavailable`,
  `docs-removal-instructions` and `docs-examples` are now marked `done`.

## [2.4.0] - 2026-11-23

### Added
- **Stable device identity.** The config entry is now identified by the router's
  own WLAN MAC (`wlan_mac_address` from `get_sim_info`, already polled - no extra
  request) instead of its URL. Moving the router to a new IP no longer creates a
  duplicate entry. Legacy URL-based entries are migrated in place on the next
  setup; entity IDs, areas and long-term statistics are preserved. Firmwares
  without a device MAC keep the URL-based ID.
- **Reconfigure flow** (Settings → Devices & services → Reconfigure) changes the
  router address, password and TLS settings without removing the entry. An
  endpoint reporting a different device MAC is rejected with `wrong_device`.
- `quality_scale.yaml`: audited all 54 Home Assistant integration quality scale
  rules with an honest `done` / `todo` / `exempt` status and comments.

### Security
- Diagnostics redaction now also covers device-owned identifiers: MAC addresses,
  IMEI, serial numbers, ICCID and the entry `unique_id` (which now contains the
  router MAC). Previously only credentials, tokens and session data were masked.

### Tests
- New identity tests (MAC normalization, identifier priority, migration and
  cross-router guard) and config-flow tests (MAC-based unique ID, URL fallback,
  reconfigure success and `wrong_device` rejection).
- Extended diagnostics tests for identifier redaction. 123 tests plus 63
  subtests pass.

## [2.3.1] - 2026-11-23

### Fixed
- **Reduced ubus core-batch warning noise on firmwares that omit optional
  endpoints.** Soft nonzero router responses for known optional core calls
  (`uci.get zwrt_common_info/common_config`, `zwrt_led.get_ODU_switch_state`,
  `uci.get wireless/main_2g`, `uci.get wireless/main_5g`) are logged once per
  session at INFO as optional unsupported/unavailable calls, with a note that
  related entities may be unavailable or show defaults on that firmware. This
  avoids repeated coordinator WARNINGs during normal polling; at Home
  Assistant's default WARNING log level the one-time INFO trace is not shown.
  Downgrade applies only to soft responses without transport/RPC/HTTP errors
  and without unexpected ubus status codes (expected: `1,2,3,4,5,8`).
  Transport failures, explicit RPC/HTTP errors, unexpected ubus statuses, and
  `error=None` responses remain WARNINGs.

### Added
- Regression tests for ubus batch failure classification, covering once-per-
  session optional INFO logging, genuine core failures, transport/RPC errors,
  non-core batches, unhashable params, mixed failures, `error=None`, and a
  drift guard for optional core call definitions.

## [2.3.0] - 2026-11-17

### Security
- **SMS sender numbers and message texts are no longer stored in entity state or
  attributes.** The `Latest Received SMS` sensor leaked the sender's number (state)
  and the sender, text and a five-message preview (attributes) into the recorder,
  where every Home Assistant user can read them (SMS often carries one-time codes).
  Reported by the HACS reviewer.

### Changed
- The integration is now listed as **ZTE 5G Router (G5TS fork)** (manifest and
  HACS name) so it can be told apart from the upstream **ZTE NG Router** when both
  are installed. The domain (`zte_5g_router`) and existing entries are unchanged.
- **Breaking:** the sensor state is now only the newest message's timestamp, and the
  attributes `latest_number`, `latest_text` and `recent_messages` are removed.
  Automations that read them must switch to the new event.

### Added
- `zte_5g_router_sms_received` event for every newly received SMS (`entry_id`,
  `name`, `id`, `number`, `date`, `text`). The inbox present at startup is only
  recorded, so a restart does not replay old messages.
- README section (en/de) on running this integration side by side with
  [rosenrot00/ha-zte-ng-router](https://github.com/rosenrot00/ha-zte-ng-router)
  and switching between them.

## [2.2.0] - 2026-11-15

### Fixed
- **Authentication errors now trigger reauthentication.** A rejected router
  password raises a typed `ZteAuthError`, which the coordinator maps to
  `ConfigEntryAuthFailed`. Home Assistant now prompts to re-enter the password
  instead of retrying a doomed login forever. The config flow reports
  `invalid_auth` only for genuine password rejections and `unknown` for other
  unexpected failures (previously every error was shown as `invalid_auth`).

### Added
- **Continuous integration.** A `CI` workflow runs Ruff and the ~96-test suite
  (with a coverage floor) on every push and pull request, so the previously
  dormant tests now gate changes. Adds `pyproject.toml`, `requirements_test.txt`,
  and tests covering the typed auth error and the config-flow error mapping.

### Removed
- Dropped the obsolete "upgrade from `zte_ng_router`" migration notice from the
  README and architecture docs (no release ever shipped under that domain).

## [2.1.4] - 2026-11-15

### Changed
- Marketplace/HACS submission prep: the HACS validation action now runs without
  the `topics` ignore (repository topics are set), so it passes cleanly.

## [2.1.3] - 2026-11-14

### Fixed
- `_to_bit_per_s` now rejects non-finite or negative throughput values
  (consistent with the byte counters), guarding the data-rate sensors against a
  theoretical `OverflowError` on malformed router input.

## [2.1.2] - 2026-11-14

### Fixed
- **Monthly data counters** now use `state_class = total_increasing` instead of
  `measurement`, so Home Assistant records long-term statistics for them and
  shows them in the Energy / consumption dashboards (consistent with the daily
  counters).
- **Failed switch actions are now surfaced in the UI.** Turning a switch or a
  4G/5G cell lock on or off that the router rejects now raises
  `HomeAssistantError` instead of only writing a log line, so the user sees why
  the toggle snapped back.

### Added
- The detected router firmware version is stored as the device `sw_version`
  and shown on the Home Assistant device page.

### Changed
- Made the config-flow port validation explicit (no behaviour change).

## [2.1.1] - 2026-11-14

### Added
- Brand **icon and logo** for the integration, shown in HACS and on the Home
  Assistant integrations page: a 5G router with antennas, signal waves and a
  "5G" label (`custom_components/zte_5g_router/brand/`).

### Fixed
- Synced the `package.json` version (was stuck at `2.0.2`) with the integration
  version.

## [2.1.0] - 2026-11-13

### Added
- **Connection test during setup.** The config flow now performs a real login
  against the router and reports `cannot_connect` / `invalid_auth` in the dialog,
  instead of creating an entry that only fails afterwards on the first update.
- **Reauthentication flow.** When the router rejects the stored password, Home
  Assistant prompts for the current password (`reauth_confirm`) and verifies it
  with a live login before saving.
- The options flow re-verifies the login with a live request whenever the host
  or the password is changed.

### Fixed
- **Options now apply immediately.** An update listener reloads the config entry
  when its options change, so a new host, password, or polling interval takes
  effect without a manual reload or a Home Assistant restart.

### Changed
- Modernised the options flow to the Home Assistant 2024.11+ API
  (`self.config_entry` instead of storing the entry in `__init__`), removing a
  deprecated pattern.
- Declared a minimum Home Assistant version of `2024.11.0` in `hacs.json`.

## [2.0.2] and earlier

See the Git history and GitHub releases for changes up to and including 2.0.2.
