# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
