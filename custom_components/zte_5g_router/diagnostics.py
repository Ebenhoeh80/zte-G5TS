from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD
from homeassistant.core import HomeAssistant

if TYPE_CHECKING:
    from . import ZteNgRouterConfigEntry

TO_REDACT = {
    CONF_PASSWORD,
    "password",
    "cookie",
    "cookies",
    "token",
    "access_token",
    "session",
    "session_id",
    "ubus_rpc_session",
    "webtoken",
    "csrf",
    "csrf_token",
    "salt",
    "zte_web_sault",
    "latitude",
    "longitude",
    "phone_number",
    "number",
    # Device-owned identifiers are personal data. Since v2.4.0 the entry
    # unique_id contains the router's WLAN MAC, so guard it as well.
    "unique_id",
    "wlan_mac_address",
    "lan_mac_address",
    "mac_address",
    "device_mac",
    "mac",
    "imei",
    "serial_number",
    "serial_no",
    "sn",
    "iccid",
    "sim_iccid",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ZteNgRouterConfigEntry,
) -> dict[str, Any]:
    """Return useful, redacted connection diagnostics without router payloads."""
    runtime_data = entry.runtime_data
    slow_data = runtime_data.coordinator.data or {}
    firmware_data = slow_data.get("common_config") or slow_data.get("device") or {}
    firmware = {
        key: firmware_data[key]
        for key in ("model", "model_name", "hardware_version", "wa_inner_version")
        if isinstance(firmware_data, dict) and firmware_data.get(key) is not None
    }

    return {
        "config": async_redact_data(
            {"data": entry.data, "options": entry.options},
            TO_REDACT,
        ),
        "connection": {
            "login_method": runtime_data.api.login_method,
            "session_status": (
                "authenticated" if runtime_data.api.is_logged_in else "not_authenticated"
            ),
            "slow_polling_success": runtime_data.coordinator.last_update_success,
            "fast_polling_success": runtime_data.coordinator_fast.last_update_success,
            "firmware": firmware,
        },
    }
