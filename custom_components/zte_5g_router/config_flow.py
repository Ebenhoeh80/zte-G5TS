from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlsplit

import aiohttp
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import HomeAssistant, callback
import voluptuous as vol

from .const import (
    CONF_ALLOW_INSECURE_HTTP,
    CONF_CLIENT_CONSIDER_HOME,
    CONF_FAST_SCAN_INTERVAL,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    CONF_TLS_FINGERPRINT,
    CONF_TRACK_CLIENTS,
    CONF_VERIFY_TLS,
    DEFAULT_CLIENT_CONSIDER_HOME,
    DEFAULT_FAST_SCAN_INTERVAL,
    DEFAULT_ROUTER_URL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_VERIFY_TLS,
    DOMAIN,
    MAX_FAST_SCAN_INTERVAL,
    MAX_SCAN_INTERVAL,
    MIN_FAST_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .identity import (
    device_identifier_from_payload,
    entry_unique_id,
    is_other_router,
)
from .zte_api import ZteAuthError, ZteRouterApi

_LOGGER = logging.getLogger(__name__)


def _validate_tls_fingerprint(value: str) -> tuple[str | None, str | None]:
    """Validate an optional SHA-256 certificate fingerprint."""
    fingerprint = value.strip().replace(":", "").lower()
    if not fingerprint:
        return "", None
    if len(fingerprint) != 64 or any(
        character not in "0123456789abcdef" for character in fingerprint
    ):
        return None, "invalid_tls_fingerprint"
    return fingerprint, None


def _validate_router_url(
    value: str, *, allow_insecure_http: bool
) -> tuple[str | None, str | None]:
    """Validate an origin-only router URL and require explicit HTTP opt-in."""
    host = value.strip()
    try:
        parsed = urlsplit(host)
        hostname = parsed.hostname
        _ = parsed.port  # Accessing .port raises ValueError on an invalid port.
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


async def _async_validate_login(
    hass: HomeAssistant,
    *,
    host: str,
    password: str,
    verify_tls: bool,
    tls_fingerprint: str,
    allow_insecure_http: bool,
    probe_identifier: bool = False,
) -> tuple[str | None, str | None]:
    """Try to log in; return ``(error key or None, device identifier or None)``.

    The identifier probe is best-effort: a firmware that omits the field still
    gets a working (URL-based) entry. The error value is intentionally a tuple
    so setup and reconfigure can use the same login check.
    """
    api = ZteRouterApi(
        hass=hass,
        base_url=host,
        password=password,
        tls_fingerprint=tls_fingerprint or None,
        allow_insecure_http=allow_insecure_http,
        verify_tls=verify_tls,
        track_clients=False,
    )
    identifier: str | None = None
    try:
        await api.async_login()
        if probe_identifier:
            try:
                reply = await api.async_call_ubus(
                    {"service": "zwrt_zte_mdm.api", "method": "get_sim_info"}
                )
                if reply.get("success"):
                    identifier = device_identifier_from_payload(reply.get("data"))
            except Exception:  # noqa: BLE001 - identifier is optional
                _LOGGER.debug("ZTE config flow: device identifier probe unavailable")
        return None, identifier
    except ZteAuthError as exc:
        _LOGGER.debug("ZTE config flow: invalid auth: %s", api.safe_error_summary(exc))
        return "invalid_auth", None
    except (TimeoutError, aiohttp.ClientError, OSError) as exc:
        _LOGGER.debug("ZTE config flow: cannot connect: %s", api.safe_error_summary(exc))
        return "cannot_connect", None
    except Exception as exc:  # noqa: BLE001 - unexpected failures map to "unknown"
        _LOGGER.debug("ZTE config flow: unexpected login error: %s", api.safe_error_summary(exc))
        return "unknown", None
    finally:
        await api.async_close()


# HA flow classes are Any in this environment; the keyword argument belongs to
# the untyped HA base class.
class ZteNgRouterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg, misc]
    """Config flow for ZTE NG Router."""

    VERSION = 1

    # Flow results are HA-controlled (untyped here), so they stay Any.
    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> Any:
        """Handle the initial step where the user enters basic config."""
        errors: dict[str, str] = {}

        if user_input is not None:
            allow_insecure_http = user_input.get(CONF_ALLOW_INSECURE_HTTP, False)
            host, host_error = _validate_router_url(
                user_input[CONF_HOST],
                allow_insecure_http=allow_insecure_http,
            )
            tls_fingerprint, fingerprint_error = _validate_tls_fingerprint(
                user_input.get(CONF_TLS_FINGERPRINT, "")
            )
            name = user_input[CONF_NAME]
            scan_interval = user_input[CONF_SCAN_INTERVAL]
            fast_scan_interval = user_input.get(CONF_FAST_SCAN_INTERVAL, DEFAULT_FAST_SCAN_INTERVAL)

            if host_error:
                errors["base"] = host_error
            elif fingerprint_error:
                errors["base"] = fingerprint_error
            elif tls_fingerprint and urlsplit(host or "").scheme != "https":
                errors["base"] = "tls_fingerprint_requires_https"
            elif scan_interval < MIN_SCAN_INTERVAL or scan_interval > MAX_SCAN_INTERVAL:
                errors["base"] = "invalid_scan_interval"
            elif fast_scan_interval < MIN_FAST_SCAN_INTERVAL or fast_scan_interval > MAX_FAST_SCAN_INTERVAL:
                errors["base"] = "invalid_fast_scan_interval"
            else:
                assert host is not None
                assert tls_fingerprint is not None

                login_error, identifier = await _async_validate_login(
                    self.hass,
                    host=host,
                    password=user_input[CONF_PASSWORD],
                    verify_tls=user_input[CONF_VERIFY_TLS],
                    tls_fingerprint=tls_fingerprint,
                    allow_insecure_http=allow_insecure_http,
                    probe_identifier=True,
                )
                if login_error:
                    errors["base"] = login_error
                else:
                    # Prefer the device-owned MAC. Firmwares without a MAC keep
                    # the historic URL-based ID.
                    unique_id = (
                        entry_unique_id(identifier) if identifier else f"zte_5g_router_{host}"
                    )
                    await self.async_set_unique_id(unique_id)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=name,
                        data={
                            CONF_NAME: name,
                            CONF_HOST: host,
                            CONF_PASSWORD: user_input[CONF_PASSWORD],
                            CONF_VERIFY_TLS: user_input[CONF_VERIFY_TLS],
                            CONF_TLS_FINGERPRINT: tls_fingerprint,
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
                vol.Optional(CONF_TLS_FINGERPRINT, default=""): str,
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

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> Any:
        """Start reauthentication after the stored password stopped working."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> Any:
        """Ask for the router password again and verify it with a live login."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        assert entry is not None
        errors: dict[str, str] = {}

        if user_input is not None:
            data = entry.data
            options = entry.options
            host = options.get(CONF_HOST, data[CONF_HOST])
            verify_tls = options.get(
                CONF_VERIFY_TLS, data.get(CONF_VERIFY_TLS, DEFAULT_VERIFY_TLS)
            )
            tls_fingerprint = options.get(
                CONF_TLS_FINGERPRINT, data.get(CONF_TLS_FINGERPRINT, "")
            )
            allow_insecure_http = options.get(
                CONF_ALLOW_INSECURE_HTTP,
                data.get(CONF_ALLOW_INSECURE_HTTP, _uses_http(host)),
            )
            password = user_input[CONF_PASSWORD]

            login_error, _ = await _async_validate_login(
                self.hass,
                host=host,
                password=password,
                verify_tls=verify_tls,
                tls_fingerprint=tls_fingerprint,
                allow_insecure_http=allow_insecure_http,
            )
            if login_error:
                errors["base"] = login_error
            else:
                # Store the new password in data and drop any stale options copy
                new_options = {
                    key: value
                    for key, value in entry.options.items()
                    if key != CONF_PASSWORD
                }
                return self.async_update_reload_and_abort(
                    entry,
                    data={**entry.data, CONF_PASSWORD: password},
                    options=new_options,
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            errors=errors,
            description_placeholders={"name": entry.title},
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> Any:
        """Change the router address or credentials without losing entity history.

        The new endpoint must report the same device identifier, otherwise the
        flow refuses to reconfigure this entry (a different router belongs in a
        new entry).
        """
        entry = self._get_reconfigure_entry()
        data = entry.data
        options = entry.options
        errors: dict[str, str] = {}

        if user_input is not None:
            allow_insecure_http = user_input.get(CONF_ALLOW_INSECURE_HTTP, False)
            host, host_error = _validate_router_url(
                user_input[CONF_HOST], allow_insecure_http=allow_insecure_http
            )
            fingerprint, fingerprint_error = _validate_tls_fingerprint(
                user_input.get(CONF_TLS_FINGERPRINT, "")
            )
            if host_error:
                errors["base"] = host_error
            elif fingerprint_error:
                errors["base"] = fingerprint_error
            elif fingerprint and urlsplit(host or "").scheme != "https":
                errors["base"] = "tls_fingerprint_requires_https"
            else:
                assert host is not None
                assert fingerprint is not None
                new_password = user_input.get(CONF_PASSWORD, "").strip()
                password = new_password or options.get(CONF_PASSWORD, data[CONF_PASSWORD])
                login_error, identifier = await _async_validate_login(
                    self.hass,
                    host=host,
                    password=password,
                    verify_tls=user_input[CONF_VERIFY_TLS],
                    tls_fingerprint=fingerprint,
                    allow_insecure_http=allow_insecure_http,
                    probe_identifier=True,
                )
                if login_error:
                    errors["base"] = login_error
                elif identifier and is_other_router(entry.unique_id, identifier):
                    errors["base"] = "wrong_device"
                else:
                    new_options = {
                        key: value
                        for key, value in options.items()
                        if key != CONF_PASSWORD
                    }
                    new_options.update({
                        CONF_HOST: host,
                        CONF_VERIFY_TLS: user_input[CONF_VERIFY_TLS],
                        CONF_TLS_FINGERPRINT: fingerprint,
                        CONF_ALLOW_INSECURE_HTTP: allow_insecure_http,
                    })
                    if new_password:
                        new_options[CONF_PASSWORD] = new_password
                    return self.async_update_reload_and_abort(
                        entry,
                        data={**data, CONF_PASSWORD: password},
                        options=new_options,
                    )

        current_host = options.get(CONF_HOST, data.get(CONF_HOST, DEFAULT_ROUTER_URL))
        schema = vol.Schema({
            vol.Required(
                CONF_HOST, default=(user_input or {}).get(CONF_HOST, current_host)
            ): str,
            vol.Optional(CONF_PASSWORD, default=""): str,
            vol.Required(
                CONF_VERIFY_TLS,
                default=(user_input or {}).get(
                    CONF_VERIFY_TLS,
                    options.get(
                        CONF_VERIFY_TLS, data.get(CONF_VERIFY_TLS, DEFAULT_VERIFY_TLS)
                    ),
                ),
            ): bool,
            vol.Optional(
                CONF_TLS_FINGERPRINT,
                default=(user_input or {}).get(
                    CONF_TLS_FINGERPRINT,
                    options.get(CONF_TLS_FINGERPRINT, data.get(CONF_TLS_FINGERPRINT, "")),
                ),
            ): str,
            vol.Optional(
                CONF_ALLOW_INSECURE_HTTP,
                default=(user_input or {}).get(
                    CONF_ALLOW_INSECURE_HTTP,
                    options.get(
                        CONF_ALLOW_INSECURE_HTTP,
                        data.get(CONF_ALLOW_INSECURE_HTTP, _uses_http(current_host)),
                    ),
                ),
            ): bool,
        })
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            errors=errors,
            description_placeholders={"name": entry.title},
        )

    @staticmethod
    @callback  # type: ignore[untyped-decorator]  # HA decorator is Any here
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> ZteNgRouterOptionsFlow:
        """Return the options flow handler."""
        return ZteNgRouterOptionsFlow()


class ZteNgRouterOptionsFlow(config_entries.OptionsFlow):  # type: ignore[misc]  # HA base is Any here
    """Options flow for adjusting settings after initial setup.

    Uses the base-class ``self.config_entry`` property (Home Assistant 2024.11+);
    storing the entry manually in ``__init__`` is deprecated.
    """

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> Any:
        """Handle options for the config entry (host, password, verify_tls, scan_interval)."""
        entry: ConfigEntry = self.config_entry
        data = entry.data
        options = entry.options
        errors: dict[str, str] = {}

        if user_input is not None:
            allow_insecure_http = user_input.get(CONF_ALLOW_INSECURE_HTTP, False)
            host, host_error = _validate_router_url(
                user_input[CONF_HOST],
                allow_insecure_http=allow_insecure_http,
            )
            tls_fingerprint, fingerprint_error = _validate_tls_fingerprint(
                user_input.get(CONF_TLS_FINGERPRINT, "")
            )
            if host_error or fingerprint_error:
                errors["base"] = host_error or fingerprint_error or ""
            elif tls_fingerprint and urlsplit(host or "").scheme != "https":
                errors["base"] = "tls_fingerprint_requires_https"
            else:
                assert host is not None
                assert tls_fingerprint is not None
                new_password = user_input.get(CONF_PASSWORD, "").strip()
                effective_password = new_password or options.get(
                    CONF_PASSWORD, data[CONF_PASSWORD]
                )

                # Re-verify the login whenever the host or password changed.
                host_changed = host != options.get(CONF_HOST, data.get(CONF_HOST))
                login_error = None
                if host_changed or new_password:
                    login_error, _ = await _async_validate_login(
                        self.hass,
                        host=host,
                        password=effective_password,
                        verify_tls=user_input[CONF_VERIFY_TLS],
                        tls_fingerprint=tls_fingerprint,
                        allow_insecure_http=allow_insecure_http,
                    )

                if login_error:
                    errors["base"] = login_error
                else:
                    existing = dict(options)
                    existing[CONF_HOST] = host
                    existing[CONF_TLS_FINGERPRINT] = tls_fingerprint
                    existing[CONF_ALLOW_INSECURE_HTTP] = allow_insecure_http
                    if new_password:
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
        current_host = options.get(CONF_HOST, data.get(CONF_HOST, DEFAULT_ROUTER_URL))
        current_allow_insecure_http = options.get(
            CONF_ALLOW_INSECURE_HTTP,
            data.get(CONF_ALLOW_INSECURE_HTTP, _uses_http(current_host)),
        )
        current_tls_fingerprint = options.get(
            CONF_TLS_FINGERPRINT, data.get(CONF_TLS_FINGERPRINT, "")
        )
        current_verify_tls = options.get(
            CONF_VERIFY_TLS, data.get(CONF_VERIFY_TLS, DEFAULT_VERIFY_TLS)
        )
        current_scan_interval = options.get(
            CONF_SCAN_INTERVAL, data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )
        current_fast_scan_interval = options.get(
            CONF_FAST_SCAN_INTERVAL,
            data.get(CONF_FAST_SCAN_INTERVAL, DEFAULT_FAST_SCAN_INTERVAL),
        )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=current_host): str,
                vol.Optional(CONF_PASSWORD, default=""): str,
                vol.Optional(CONF_TLS_FINGERPRINT, default=current_tls_fingerprint): str,
                vol.Optional(
                    CONF_ALLOW_INSECURE_HTTP, default=current_allow_insecure_http
                ): bool,
                vol.Required(CONF_VERIFY_TLS, default=current_verify_tls): bool,
                vol.Required(CONF_SCAN_INTERVAL, default=current_scan_interval): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                ),
                vol.Required(
                    CONF_FAST_SCAN_INTERVAL, default=current_fast_scan_interval
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
                    default=options.get(
                        CONF_CLIENT_CONSIDER_HOME,
                        data.get(CONF_CLIENT_CONSIDER_HOME, DEFAULT_CLIENT_CONSIDER_HOME),
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=0, max=3600)),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
