from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import SMS_COMPOSE_DEFAULT
from .entity import device_info, entity_unique_id

# All router I/O goes through the shared coordinator; serialize entity updates.
PARALLEL_UPDATES = 1

if TYPE_CHECKING:
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

    from . import ZteNgRouterConfigEntry
    from .zte_api import ZteRouterApi

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ZteActionButtonDef:
    key: str
    name: str
    action: dict[str, Any]
    kind: str = "action"


BUTTON_DEFS: list[ZteActionButtonDef] = [
    ZteActionButtonDef(
        key="restart",
        name="Restart",
        kind="action",
        action={
            "service": "zwrt_mc.device.manager",
            "method": "device_reboot",
            "params": {"moduleName": "web"},
        },
    ),
    ZteActionButtonDef(
        key="send_sms",
        name="Send SMS",
        kind="send_sms",
        action={},
    ),
    ZteActionButtonDef(
        key="check_firmware_update",
        name="Check Firmware Update",
        kind="check_firmware",
        action={},
    ),
    ZteActionButtonDef(
        key="start_firmware_update",
        name="Start Firmware Update",
        kind="start_firmware",
        action={},
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ZteNgRouterConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime_data = entry.runtime_data

    async_add_entities(
        [
            ZteActionButton(
                runtime_data.coordinator,
                runtime_data.api,
                entry,
                runtime_data.name,
                btn_def,
            )
            for btn_def in BUTTON_DEFS
        ]
    )


class ZteActionButton(CoordinatorEntity, ButtonEntity):  # type: ignore[misc]  # HA bases are Any here
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict[str, Any]],
        api: ZteRouterApi,
        entry: ZteNgRouterConfigEntry,
        device_name: str,
        btn_def: ZteActionButtonDef,
    ) -> None:
        super().__init__(coordinator)
        self.hass = coordinator.hass
        self._entry = entry
        self._entry_id = entry.entry_id
        self._api = api
        self._btn_def = btn_def

        self._attr_name = btn_def.name
        self._attr_translation_key = btn_def.key
        self._attr_unique_id = entity_unique_id(entry.entry_id, btn_def.key)
        if btn_def.kind in {"check_firmware", "start_firmware"}:
            self._attr_entity_category = EntityCategory.CONFIG

        self._attr_device_info = device_info(entry.entry_id, device_name)

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        if self._btn_def.kind in {"check_firmware", "start_firmware"}:
            firmware = (self.coordinator.data or {}).get("firmware")
            if not isinstance(firmware, dict) or not firmware:
                return False
            if self._btn_def.kind == "start_firmware":
                return self._api.firmware_update_action(firmware) is not None
        return True

    async def async_press(self) -> None:
        _LOGGER.info("Executing ZTE action button: %s", self._btn_def.key)

        if self._btn_def.kind in {"check_firmware", "start_firmware"}:
            try:
                if self._btn_def.kind == "check_firmware":
                    ok = await self._api.async_check_firmware_update()
                else:
                    ok = await self._api.async_start_firmware_update()
            except ValueError as exc:
                raise HomeAssistantError(str(exc)) from exc
            if not ok:
                raise HomeAssistantError(
                    "Router rejected the firmware command; see integration logs"
                )
            await self.coordinator.async_request_refresh()
            return

        if self._btn_def.kind == "send_sms":
            compose_value = str(self._entry.runtime_data.sms_compose or "")
            if compose_value.strip() == SMS_COMPOSE_DEFAULT:
                _LOGGER.warning("Cannot send SMS, compose value is still default helper text")
                return
            try:
                number, message = self._api.parse_sms_compose_input(compose_value)
            except ValueError as exc:
                _LOGGER.warning(
                    "Cannot send SMS: invalid compose value error_type=%s",
                    type(exc).__name__,
                )
                return

            try:
                ok = await self._api.async_send_sms(number=number, message=message)
            except ValueError as exc:
                raise HomeAssistantError(str(exc)) from exc
            if not ok:
                _LOGGER.warning("ZTE action button failed: %s", self._btn_def.key)
            else:
                await self.coordinator.async_request_refresh()
            return

        ok = await self._api.async_execute_action_def(self._btn_def.action)
        if not ok:
            _LOGGER.warning("ZTE action button failed: %s", self._btn_def.key)
