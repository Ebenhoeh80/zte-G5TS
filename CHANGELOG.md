# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- CI job `Frontend build` (`npm ci`, `npm run build`, `npm audit --audit-level=high`). The five open major npm PRs were CI-green only because no workflow built the dashboard; local verification showed three `npm ci` ERESOLVE conflicts, a TypeScript 7 `tsc` error and a Tailwind 4 PostCSS error. Those PRs stay open until the build gate passes.
- Test for a plain `OSError` with `errno = 104` assigned after construction. `OSError(104, ...)` is mapped to `ConnectionResetError` on Linux, which made line 359 platform-dependent (CI 99.83 %, Windows 99.86 %). Coverage is now 99.86 % on both platforms.
- `pytest>=9.2,<10` so the documented 619 subtests are also reported by CI (built-in subtests plugin); previously CI printed only the 676 tests.

### Changed
- Floating action refs pinned to reviewed commit SHAs (`hassfest@master`, `hacs/action@main`) with version comments so Dependabot can still propose updates.
- Dashboard translations: hard-coded German messages in Settings, Cell Lock, Diagnostics and SMS now use the existing `translations.ts` dictionaries. The mode indicator is explicitly labelled as demo-only because `src/` never connects to a real router.
- Architecture and README documentation updated: CI frontend gate, live-installation result from v2.5.0, working table-of-contents anchors, GitHub Sponsors badge in both README headers and an honest quality-scale wording in the dashboard. `.gitignore` now covers release zips and coverage reports.

### Security
- Stats dashboard (not part of the Home Assistant integration): `vite` 5.4 to 6.4.6 and `@vitejs/plugin-react` to 4.7. Closes eight open Dependabot alerts (path traversal and `server.fs` bypasses, `launch-editor` issues; one high). `npm audit` reports 0 vulnerabilities, `tsc && vite build` passes. Vite 5 no longer receives patches, so the major update was required. A `package-lock.json` is added so that installs and Dependabot are reproducible.
- `hassfest.yml` limits the `GITHUB_TOKEN` to `contents: read`.

### Tests
- 677 tests plus 619 subtests, 99.86 % total coverage on Windows and Linux, Ruff, Full-Strict-Mypy and `tsc && vite build` green. No new release: `custom_components/` changed only in a docstring since v2.5.0, so HACS users would receive an empty version.

## [2.5.0] - 2026-11-24

First stable release of the 2.5.0 line. All six beta releases were verified and
their remaining findings fixed; no known open points remain.

### Added
- Shared `coordinator.py` and `entity.py` for polling, availability logging,
  device info and unique IDs across all five platforms.
- Repair/reauth flow when the stored router password is rejected at the
  first refresh.
- Stale client trackers are removed from the entity registry after seven days
  of absence and recreated when the client returns.
- `wrong_device` config-flow error translation and the three missing Wi-Fi
  sensor names (`wifi_onoff`, `main2g_ssid`, `main5g_ssid`) in `strings.json`,
  `en.json` and `de.json`. New tests guard all flow error keys, all
  `SENSOR_DEFS` names and the supported model lists.

### Changed
- All entity icons now come from `icons.json`; `manifest.json` declares the
  HACS category `computers_network.routers_network`.
- All 15 source files pass Full-Strict-mypy; the quality scale audit is at
  43 `done`, 11 `exempt`, 0 `todo`.
- CI uses Actions v7, enforces a 95% total and per-module coverage floor and
  checks `ruff check .` plus `ruff format --check .` repo-wide (59 files).
- `.gitignore` ignores the CI-generated `coverage.json`.
- The config-flow description, README model lists and quality-scale audit now
  name the same ten supported models, including MC889, G51F and MC7510.
- `package.json` and `metadata.json` no longer carry upstream/old version
  strings; both identify the G5TS fork.
- The release-zip workflow now aborts when the pushed tag does not match the
  manifest version.

### Tests
- 676 tests plus 619 subtests; total coverage 99.86% with 14 of 15 modules at
  100% (`zte_api.py` 99% with four unreachable defensive lines).
- Independent sign-off by Claude Sonnet 5.5 on beta.6: FREIGABE, no open points.
- Live installation checked on HA 2026.11.2: entry `loaded`, session
  `authenticated`, both pollers successful, 92 entities (91 available), no
  diagnostics issues and no ZTE errors in the logbook. Relative to beta.6 only
  translations, docs/metadata and the release workflow guard changed; polling
  and entity behaviour are unchanged.

## [2.5.0-beta.6] - 2026-11-24

Cosmetic corrections from the final independent sign-off. Not recommended for
production use yet.

### Changed
- `quality_scale.yaml` header now references the current release.
- Release notes describe the repo-wide Ruff formatting scope precisely: 58
  files, of which 47 are Python and 11 are Markdown.

### Tests
- Unchanged: 672 tests plus 296 subtests, 99.86% coverage, Full-Strict-mypy,
  repo-wide `ruff check .` and `ruff format --check .` all green.

## [2.5.0-beta.5] - 2026-11-24

Final hygiene pass: no known open findings remain. Not recommended for
production use yet.

### Changed
- `ruff check .` and `ruff format --check .` are now clean across the entire
  repository (58 files), including `tools/`. The two ASYNC109 findings in
  `tools/ha_e2e.py` are documented polling deadlines, not library timeouts.
- CI lint now checks the whole repository (`ruff check .`) and enforces
  formatting (`ruff format --check .`), not just `custom_components` and `tests`.

### Tests
- 672 tests plus 296 subtests, 99.86% coverage, Full-Strict-mypy and Python
  syntax checks on all 47 files remain green.

## [2.5.0-beta.4] - 2026-11-24

Small follow-up quick wins after beta.3. Not recommended for production use yet.

### Added
- `tests/test_device_tracker_coverage.py`: registry cleanup for foreign
  entities, MAC name fallback, restore skips and invalid `last_seen` values.
  `device_tracker.py` now has 100% coverage; 14 of 15 modules are at 100%.

### Changed
- GitHub Actions `checkout` v4 -> v7 and `setup-python` v5 -> v7 across all
  workflows; this removes the Node.js 20 deprecation warnings in CI.
- `quality_scale.yaml`: header and strict-typing note updated to the current
  release, including that core `.strict-typing` registration is N/A for custom
  components with no manifest requirements.
- `.gitignore` now ignores the CI-generated `coverage.json`.

### Tests
- 672 tests plus 296 subtests; total coverage 99.86% (`zte_api.py` 99% with
  four unreachable defensive lines). Ruff, Full-Strict-mypy and CI stay green.

## [2.5.0-beta.3] - 2026-11-24

Final quality-scale test release: no `todo` rules remain. Not recommended for
production use yet.

### Added
- Offline coverage tests for `zte_api.py`, `sensor.py`, `switch.py`, `button.py`,
  `config_flow.py` and `identity.py`: 668 tests plus 289 subtests, 99% total
  coverage and at least 97% in every module.
- CI now enforces a 95% total *and* per-module coverage floor, plus a full
  strict-mypy job.

### Changed
- All 15 source files pass `mypy --config-file pyproject.toml
  custom_components/zte_5g_router` with `strict = true`; API payloads are typed
  with casts and typed locals, behaviour is unchanged.
- `quality_scale.yaml`: `test-coverage` and `strict-typing` are now `done` (0
  `todo` rules, 43 `done`, 11 `exempt`).

### Fixed
- Closed an unawaited `AsyncMock` coroutine in the API coverage tests, so the
  suite runs without warnings.

## [2.5.0-beta.2] - 2026-11-24

Follow-up quick wins for the beta. Not recommended for production use yet.

### Added
- `categories: ["computers_network.routers_network"]` in `manifest.json`, which
  removes the hassfest "no categories" annotation.
- Offline tests for `__init__.py` and `text.py` (setup, auth repair, SMS events,
  pause behaviour, unload, text entity state and input validation).

### Fixed
- Removed the last three hardcoded `icon=` values from `text.py`'s entity
  descriptions; `icons.json` is now authoritative for every entity icon.

### Tests
- 151 tests plus 97 subtests pass; coverage rose from ~56% to ~64%.
  `__init__.py`, `text.py` and `repairs.py` now have 100% coverage.

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
