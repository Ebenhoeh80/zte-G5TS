"""Shared entity identity helpers.

Entity unique IDs and the device identifier are deliberately based on the
config entry ID, not on the router address or MAC. This keeps entity IDs,
areas and long-term statistics stable when the router moves or is reconfigured.
Centralising the construction avoids drift between the five platforms.
"""

from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN


def device_info(entry_id: str, router_name: str) -> DeviceInfo:
    """Return the single device entry used by every platform."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry_id)},
        name=router_name,
        manufacturer="ZTE",
    )


def entity_unique_id(entry_id: str, key: str) -> str:
    """Return a stable, collision-free entity unique ID."""
    return f"{entry_id}_{key}"
