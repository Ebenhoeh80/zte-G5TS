from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlsplit

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import callback

from .const import (
    DOMAIN,
    CONF_NAME,
    CONF_VERIFY_TLS,
    CONF_ALLOW_INSECURE_HTTP,
    DEFAULT_ROUTER_URL,
    DEFAULT_VERIFY_TLS,
    CONF_SCAN_INTERVAL,
    CONF_FAST_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_FAST_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    MAX_SCAN_INTERVAL,
    MIN_FAST_SCAN_INTERVAL,
    MAX_FAST_SCAN_INTERVAL,
    CONF_TRACK_CLIENTS,
    CONF_CLIENT_CONSIDER_HOME,
    DEFAULT_CLIENT_CONSIDER_HOME,
)

_LOGGER = logging.getLogger(__name__)


def _validate_router_url(
    value: str, *, allow_insecure_http: bool
) -> tuple[str | None, str | None]:
    """Validate an origin-only router URL and require explicit HTTP opt-in."""
    host = value.strip()
    try:
        parsed = urlsplit(host)
        hostname = parsed.hostname
        parsed.port
    except ValueError:
        return None, "invalid_host"

    if (
        parsed.scheme not in {"http", "https"}
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        return None, "invalid_host"

    if parsed.scheme == "http" and not allow_insecure_http:
        return None, "insecure_http"

    return host.rstrip("/"), None


def _uses_http(host: str) -> bool:
    """Return whether a stored router URL uses HTTP."""
    try:
        return urlsplit(host).scheme.lower() == "http"
    except ValueError:
        return False


class ZteNgRouterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for ZTE NG Router."""

    VERSION = 1
    options_flow_reloads = True

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial step where the user enters basic config."""
        errors: dict[str, str] = {}

        if user_input is not None:
            allow_insecure_http = user_input.get(CONF_ALLOW_INSECURE_HTTP, False)
            host, host_error = _validate_router_url(
                user_input[CONF_HOST],
                allow_insecure_http=allow_insecure_http,
            )
            name = user_input[CONF_NAME]
            scan_interval = user_input[CONF_SCAN_INTERVAL]
            fast_scan_interval = user_input.get(CONF_FAST_SCAN_INTERVAL, DEFAULT_FAST_SCAN_INTERVAL)

            if host_error:
                errors["base"] = host_error
            elif scan_interval < MIN_SCAN_INTERVAL or scan_interval > MAX_SCAN_INTERVAL:
                errors["base"] = "invalid_scan_interval"
            elif fast_scan_interval < MIN_FAST_SCAN_INTERVAL or fast_scan_interval > MAX_FAST_SCAN_INTERVAL:
                errors["base"] = "invalid_fast_scan_interval"
            else:
                assert host is not None
                await self.async_set_unique_id(f"zte_ng_router_{host}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=name,
                    data={
                        CONF_NAME: name,
                        CONF_HOST: host,
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_VERIFY_TLS: user_input[CONF_VERIFY_TLS],
                        CONF_ALLOW_INSECURE_HTTP: allow_insecure_http,
                        CONF_SCAN_INTERVAL: scan_interval,
                        CONF_FAST_SCAN_INTERVAL: fast_scan_interval,
                        CONF_TRACK_CLIENTS: user_input.get(CONF_TRACK_CLIENTS, False),
                        CONF_CLIENT_CONSIDER_HOME: user_input.get(
                            CONF_CLIENT_CONSIDER_HOME, DEFAULT_CLIENT_CONSIDER_HOME
                        ),
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default="ZTE 5G Router"): str,
                vol.Required(CONF_HOST, default=DEFAULT_ROUTER_URL): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Optional(CONF_VERIFY_TLS, default=DEFAULT_VERIFY_TLS): bool,
                vol.Optional(CONF_ALLOW_INSECURE_HTTP, default=False): bool,
                vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                ),
                vol.Required(CONF_FAST_SCAN_INTERVAL, default=DEFAULT_FAST_SCAN_INTERVAL): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_FAST_SCAN_INTERVAL, max=MAX_FAST_SCAN_INTERVAL),
                ),
                vol.Optional(CONF_TRACK_CLIENTS, default=False): bool,
                vol.Optional(CONF_CLIENT_CONSIDER_HOME, default=DEFAULT_CLIENT_CONSIDER_HOME): vol.All(
                    vol.Coerce(int), vol.Range(min=0, max=3600),
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Return the options flow handler."""
        return ZteNgRouterOptionsFlow(config_entry)


class ZteNgRouterOptionsFlow(config_entries.OptionsFlow):
    """Options flow for adjusting settings after initial setup."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Store the config entry in a private attribute."""
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Handle options for the config entry (host, password, verify_tls, scan_interval)."""
        errors: dict[str, str] = {}
        if user_input is not None:
            allow_insecure_http = user_input.get(CONF_ALLOW_INSECURE_HTTP, False)
            host, host_error = _validate_router_url(
                user_input[CONF_HOST],
                allow_insecure_http=allow_insecure_http,
            )
            if host_error:
                errors["base"] = host_error
            else:
                assert host is not None
                existing = dict(self._config_entry.options)
                existing[CONF_HOST] = host
                existing[CONF_ALLOW_INSECURE_HTTP] = allow_insecure_http

                new_password = user_input.get(CONF_PASSWORD, "")
                if new_password.strip():
                    existing[CONF_PASSWORD] = new_password

                existing[CONF_VERIFY_TLS] = user_input[CONF_VERIFY_TLS]
                existing[CONF_SCAN_INTERVAL] = user_input[CONF_SCAN_INTERVAL]
                existing[CONF_FAST_SCAN_INTERVAL] = user_input.get(
                    CONF_FAST_SCAN_INTERVAL, DEFAULT_FAST_SCAN_INTERVAL
                )
                existing[CONF_TRACK_CLIENTS] = user_input.get(CONF_TRACK_CLIENTS, False)
                existing[CONF_CLIENT_CONSIDER_HOME] = user_input.get(
                    CONF_CLIENT_CONSIDER_HOME, DEFAULT_CLIENT_CONSIDER_HOME
                )
                return self.async_create_entry(title="", data=existing)

        # Current values: prefer options, fallback to data
        data = self._config_entry.data
        options = self._config_entry.options

        current_host = options.get(CONF_HOST, data.get(CONF_HOST, DEFAULT_ROUTER_URL))
        current_allow_insecure_http = options.get(
            CONF_ALLOW_INSECURE_HTTP,
            data.get(CONF_ALLOW_INSECURE_HTTP, _uses_http(current_host)),
        )
        # We never show the current password in plain text; user can overwrite it if needed.
        current_verify_tls = options.get(
            CONF_VERIFY_TLS,
            data.get(CONF_VERIFY_TLS, DEFAULT_VERIFY_TLS),
        )
        current_scan_interval = options.get(
            CONF_SCAN_INTERVAL,
            data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        current_fast_scan_interval = options.get(
            CONF_FAST_SCAN_INTERVAL,
            data.get(CONF_FAST_SCAN_INTERVAL, DEFAULT_FAST_SCAN_INTERVAL),
        )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOST,
                    default=current_host,
                ): str,
                vol.Optional(
                    CONF_PASSWORD,
                    default="",
                ): str,
                vol.Optional(
                    CONF_ALLOW_INSECURE_HTTP,
                    default=current_allow_insecure_http,
                ): bool,
                vol.Required(
                    CONF_VERIFY_TLS,
                    default=current_verify_tls,
                ): bool,
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=current_scan_interval,
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                ),
                vol.Required(
                    CONF_FAST_SCAN_INTERVAL,
                    default=current_fast_scan_interval,
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_FAST_SCAN_INTERVAL, max=MAX_FAST_SCAN_INTERVAL),
                ),
                vol.Optional(
                    CONF_TRACK_CLIENTS,
                    default=options.get(CONF_TRACK_CLIENTS, data.get(CONF_TRACK_CLIENTS, False)),
                ): bool,
                vol.Optional(
                    CONF_CLIENT_CONSIDER_HOME,
                    default=options.get(CONF_CLIENT_CONSIDER_HOME, data.get(
                        CONF_CLIENT_CONSIDER_HOME, DEFAULT_CLIENT_CONSIDER_HOME
                    )),
                ): vol.All(vol.Coerce(int), vol.Range(min=0, max=3600)),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
