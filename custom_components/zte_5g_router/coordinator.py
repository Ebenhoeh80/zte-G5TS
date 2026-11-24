"""Shared coordinator helpers for the ZTE router integration.

Both pollers (slow full snapshot and fast WAN stats) use the same router API
instance. Centralising the coordinator here gives every platform identical
error handling and a single place for availability transition logging.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import logging
from typing import Any, TypeVar, cast

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_T = TypeVar("_T")


class ZteDataUpdateCoordinator(DataUpdateCoordinator[_T]):  # type: ignore[misc]
    """DataUpdateCoordinator that logs connection loss and recovery once.

    Home Assistant's base coordinator logs every failed update. That is noisy
    for a local router that is simply offline. We keep the standard behaviour
    for the entity state (``last_update_success``), but emit a single ERROR
    when the router becomes unavailable and a single INFO when it returns.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        logger: logging.Logger,
        *,
        name: str,
        update_method: Callable[[], Awaitable[_T]],
        update_interval: Any,
    ) -> None:
        super().__init__(
            hass,
            logger,
            name=name,
            update_method=update_method,
            update_interval=update_interval,
        )
        self._was_unavailable = False

    async def _async_update_data(self) -> _T:
        """Update data and log only availability transitions."""
        try:
            data = await super()._async_update_data()
        except Exception:
            if not self._was_unavailable:
                self._was_unavailable = True
                self.logger.error(
                    "ZTE router %s is unavailable; retrying in the background",
                    self.name,
                )
            raise
        if self._was_unavailable:
            self._was_unavailable = False
            self.logger.info("ZTE router %s is available again", self.name)
        return cast(_T, data)
