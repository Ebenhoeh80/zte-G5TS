# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
