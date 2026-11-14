from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_ALLOW_INSECURE_HTTP,
    CONF_FAST_SCAN_INTERVAL,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    CONF_TLS_FINGERPRINT,
    CONF_TRACK_CLIENTS,
    CONF_VERIFY_TLS,
    DEFAULT_FAST_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_VERIFY_TLS,
    DOMAIN,
)
from .zte_api import ZteRouterApi

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
PLATFORMS: list[str] = ["sensor", "button", "switch", "text", "device_tracker"]


@dataclass
class ZteNgRouterRuntimeData:
    """Data owned by a loaded ZTE router config entry."""

    api: ZteRouterApi
    coordinator: DataUpdateCoordinator[dict[str, Any]]
    coordinator_fast: DataUpdateCoordinator[dict[str, Any]]
    name: str
    pause_until: datetime | None = None
    reset_client_absence: Callable[[], None] | None = None
    sms_compose: str = ""


ZteNgRouterConfigEntry = ConfigEntry[ZteNgRouterRuntimeData]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up integration from YAML (not used, config flow only)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ZteNgRouterConfigEntry) -> bool:
    """Set up ZTE NG Router from a config entry."""
    data = entry.data
    options = entry.options

    name: str = data[CONF_NAME]
    host: str = options.get(CONF_HOST, data[CONF_HOST])
    password: str = options.get(CONF_PASSWORD, data[CONF_PASSWORD])
    verify_tls: bool = options.get(
        CONF_VERIFY_TLS,
        data.get(CONF_VERIFY_TLS, DEFAULT_VERIFY_TLS),
    )
    tls_fingerprint: str = options.get(
        CONF_TLS_FINGERPRINT,
        data.get(CONF_TLS_FINGERPRINT, ""),
    )
    allow_insecure_http: bool = options.get(
        CONF_ALLOW_INSECURE_HTTP,
        data.get(
            CONF_ALLOW_INSECURE_HTTP,
            host.strip().lower().startswith("http://"),
        ),
    )
    scan_interval: int = options.get(
        CONF_SCAN_INTERVAL,
        data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )
    fast_scan_interval: int = options.get(
        CONF_FAST_SCAN_INTERVAL,
        data.get(CONF_FAST_SCAN_INTERVAL, DEFAULT_FAST_SCAN_INTERVAL),
    )

    api = ZteRouterApi(
        hass=hass,
        base_url=host,
        password=password,
        tls_fingerprint=tls_fingerprint or None,
        allow_insecure_http=allow_insecure_http,
        verify_tls=verify_tls,
        track_clients=options.get(
            CONF_TRACK_CLIENTS, data.get(CONF_TRACK_CLIENTS, False)
        ),
    )

    async def _async_update_data() -> dict[str, Any]:
        """Fetch data from the router."""
        if store.pause_until is not None and dt_util.utcnow() < store.pause_until:
            return coordinator.data or {}
        try:
            result = await api.async_update_all()
            if result is None:
                raise UpdateFailed("No data returned from router")
            return result
        except UpdateFailed:
            raise
        except Exception as err:
            summary = api.safe_error_summary(err)
            _LOGGER.error("Error updating ZTE router data: %s", summary)
            raise UpdateFailed(summary) from err

    async def _async_update_fast() -> dict[str, Any]:
        """Fetch fast-changing WAN stats from the router."""
        if store.pause_until is not None and dt_util.utcnow() < store.pause_until:
            return coordinator_fast.data or {}
        try:
            result = await api.async_update_fast()
            if result is None:
                raise UpdateFailed("No fast data returned from router")
            return result
        except UpdateFailed:
            raise
        except Exception as err:
            summary = api.safe_error_summary(err)
            _LOGGER.error("Error updating ZTE router fast data: %s", summary)
            raise UpdateFailed(summary) from err

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"zte_5g_router_{name}",
        update_method=_async_update_data,
        update_interval=timedelta(seconds=scan_interval),
    )
    coordinator_fast = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"zte_5g_router_{name}_fast",
        update_method=_async_update_fast,
        update_interval=timedelta(seconds=fast_scan_interval),
    )
    store = ZteNgRouterRuntimeData(
        api=api,
        coordinator=coordinator,
        coordinator_fast=coordinator_fast,
        name=name,
    )

    try:
        await coordinator.async_config_entry_first_refresh()
        await coordinator_fast.async_config_entry_first_refresh()
        entry.runtime_data = store
        entry.async_on_unload(entry.add_update_listener(_async_update_listener))
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        firmware_data = coordinator.data or {}
        firmware = firmware_data.get("common_config") or firmware_data.get("device") or {}
        firmware_version = next(
            (
                str(firmware[key])
                for key in ("wa_inner_version", "wa_version", "hardware_version")
                if isinstance(firmware, dict) and firmware.get(key)
            ),
            None,
        )
        if firmware_version:
            _LOGGER.info("ZTE router firmware identified: %s", firmware_version)
            device_registry = dr.async_get(hass)
            device = device_registry.async_get_device(
                identifiers={(DOMAIN, entry.entry_id)}
            )
            if device is not None:
                device_registry.async_update_device(
                    device.id, sw_version=firmware_version
                )
        return True
    except Exception:
        await api.async_close()
        raise


async def async_unload_entry(hass: HomeAssistant, entry: ZteNgRouterConfigEntry) -> bool:
    """Unload a config entry."""
    store = entry.runtime_data
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await store.api.async_close()
    return unload_ok


async def _async_update_listener(
    hass: HomeAssistant, entry: ZteNgRouterConfigEntry
) -> None:
    """Reload the entry when its options change so new settings take effect."""
    await hass.config_entries.async_reload(entry.entry_id)
