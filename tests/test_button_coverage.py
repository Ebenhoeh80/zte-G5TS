"""Offline coverage tests for the button platform; no router action is executed."""

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "zte_5g_router"


def load_button():
    """Load button.py with stubbed Home Assistant and API dependencies."""
    package = types.ModuleType("zte_button_cov_test")
    package.__path__ = [str(ROOT)]
    modules = {"zte_button_cov_test": package}

    class ButtonEntity:
        pass

    class CoordinatorEntity:
        def __init__(self, coordinator):
            self.coordinator = coordinator

        @property
        def available(self):
            return bool(getattr(self.coordinator, "last_update_success", True))

    class HomeAssistantError(Exception):
        pass

    class FakeApi:
        """Controllable stand-in; all router actions are recorded, never sent."""

        check_result = True
        start_result = True
        sms_result = True
        action_result = True
        check_error = None
        start_error = None
        sms_error = None
        parse_error = None
        firmware_action = {"method": "start_firmware_update"}
        calls = []

        @classmethod
        def reset(cls):
            cls.check_result = True
            cls.start_result = True
            cls.sms_result = True
            cls.action_result = True
            cls.check_error = None
            cls.start_error = None
            cls.sms_error = None
            cls.parse_error = None
            cls.firmware_action = {"method": "start_firmware_update"}
            cls.calls = []

        def firmware_update_action(self, firmware):
            self.calls.append(("firmware_update_action", firmware))
            return self.firmware_action

        async def async_check_firmware_update(self):
            self.calls.append(("check_firmware",))
            if self.check_error is not None:
                raise self.check_error
            return self.check_result

        async def async_start_firmware_update(self):
            self.calls.append(("start_firmware",))
            if self.start_error is not None:
                raise self.start_error
            return self.start_result

        def parse_sms_compose_input(self, value):
            self.calls.append(("parse_sms", value))
            if self.parse_error is not None:
                raise ValueError(self.parse_error)
            number, message = value.split(",", 1)
            return number, message

        async def async_send_sms(self, number, message):
            self.calls.append(("send_sms", number, message))
            if self.sms_error is not None:
                raise self.sms_error
            return self.sms_result

        async def async_execute_action_def(self, action):
            self.calls.append(("execute_action_def", action))
            return self.action_result

    symbols = {
        "homeassistant.components.button": {"ButtonEntity": ButtonEntity},
        "homeassistant.core": {"HomeAssistant": object},
        "homeassistant.exceptions": {"HomeAssistantError": HomeAssistantError},
        "homeassistant.helpers.entity": {
            "DeviceInfo": dict,
            "EntityCategory": types.SimpleNamespace(CONFIG="config"),
        },
        "homeassistant.helpers.update_coordinator": {"CoordinatorEntity": CoordinatorEntity},
        "zte_button_cov_test.zte_api": {"ZteRouterApi": FakeApi},
    }
    for name, attributes in symbols.items():
        module = types.ModuleType(name)
        module.__dict__.update(attributes)
        modules[name] = module

    for modname, filename in (("const", "const.py"), ("entity", "entity.py")):
        spec = importlib.util.spec_from_file_location(
            f"zte_button_cov_test.{modname}", ROOT / filename
        )
        module = importlib.util.module_from_spec(spec)
        modules[spec.name] = module
        with patch.dict(sys.modules, modules):
            spec.loader.exec_module(module)

    spec = importlib.util.spec_from_file_location("zte_button_cov_test.button", ROOT / "button.py")
    module = importlib.util.module_from_spec(spec)
    modules[spec.name] = module
    with patch.dict(sys.modules, modules):
        spec.loader.exec_module(module)
    return module, FakeApi, HomeAssistantError


buttons, Api, HomeAssistantError = load_button()


class ButtonCoverageTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        Api.reset()
        self.api = Api()
        self.hass = types.SimpleNamespace()

    def coordinator(self, data=None, available=True):
        return types.SimpleNamespace(
            hass=types.SimpleNamespace(),
            data={} if data is None else data,
            last_update_success=available,
            async_request_refresh=AsyncMock(),
        )

    def runtime(self, data=None, sms_compose="", available=True):
        return types.SimpleNamespace(
            coordinator=self.coordinator(data, available),
            api=self.api,
            name="Router",
            sms_compose=sms_compose,
        )

    def entry(self, runtime=None, sms_compose=""):
        return types.SimpleNamespace(
            entry_id="entry",
            runtime_data=runtime or self.runtime(sms_compose=sms_compose),
        )

    def entity(self, key, data=None, sms_compose="", available=True):
        definition = next(
            item for item in buttons.BUTTON_DEFS if key in {item.key, item.kind}
        )
        runtime = self.runtime(data, sms_compose, available)
        entry = self.entry(runtime)
        entity = buttons.ZteActionButton(
            runtime.coordinator, self.api, entry, "Router", definition
        )
        return entity, runtime.coordinator

    async def test_setup_entry_creates_all_button_entities(self):
        runtime = self.runtime()
        entry = self.entry(runtime)
        added = []

        await buttons.async_setup_entry(self.hass, entry, added.extend)

        self.assertEqual(buttons.PARALLEL_UPDATES, 1)
        self.assertEqual(len(added), 4)
        self.assertEqual(
            [entity._attr_unique_id for entity in added],
            [
                "entry_restart",
                "entry_send_sms",
                "entry_check_firmware_update",
                "entry_start_firmware_update",
            ],
        )
        self.assertEqual(
            [entity._attr_translation_key for entity in added],
            [item.key for item in buttons.BUTTON_DEFS],
        )
        self.assertEqual(
            [entity._attr_name for entity in added],
            [item.name for item in buttons.BUTTON_DEFS],
        )
        self.assertEqual(
            [getattr(entity, "_attr_entity_category", None) for entity in added],
            [None, None, "config", "config"],
        )
        for entity in added:
            self.assertIs(entity.hass, runtime.coordinator.hass)
            self.assertEqual(entity._attr_device_info["identifiers"], {("zte_5g_router", "entry")})
            self.assertEqual(entity._attr_device_info["name"], "Router")

    def test_available_tracks_coordinator_and_firmware_capability(self):
        entity, coordinator = self.entity("restart")
        self.assertTrue(entity.available)
        coordinator.last_update_success = False
        self.assertFalse(entity.available)
        coordinator.last_update_success = True

        for firmware in (None, "broken", {}):
            check, check_coordinator = self.entity("check_firmware", {"firmware": firmware})
            with self.subTest(firmware=firmware):
                self.assertFalse(check.available)
                check_coordinator.last_update_success = False
                self.assertFalse(check.available)

        check, _ = self.entity("check_firmware", {"firmware": {"version": "V2"}})
        self.assertTrue(check.available)

        firmware = {"version": "V2"}
        Api.firmware_action = None
        start, _ = self.entity("start_firmware", {"firmware": firmware})
        self.assertFalse(start.available)

        Api.firmware_action = {"method": "start_firmware_update"}
        start, _ = self.entity("start_firmware", {"firmware": firmware})
        self.assertTrue(start.available)
        self.assertIn(("firmware_update_action", firmware), Api.calls)

    async def test_check_firmware_press_success_rejection_and_value_error(self):
        firmware = {"firmware": {"version": "V2"}}

        entity, coordinator = self.entity("check_firmware", firmware)
        await entity.async_press()
        self.assertEqual(Api.calls, [("check_firmware",)])
        coordinator.async_request_refresh.assert_awaited_once()

        Api.reset()
        self.api = Api()
        Api.check_result = False
        entity, coordinator = self.entity("check_firmware", firmware)
        with self.assertRaisesRegex(HomeAssistantError, "Router rejected the firmware command"):
            await entity.async_press()
        self.assertEqual(Api.calls, [("check_firmware",)])
        coordinator.async_request_refresh.assert_not_awaited()

        Api.reset()
        self.api = Api()
        Api.check_error = ValueError("check failed")
        entity, coordinator = self.entity("check_firmware", firmware)
        with self.assertRaisesRegex(HomeAssistantError, "check failed"):
            await entity.async_press()
        coordinator.async_request_refresh.assert_not_awaited()

    async def test_start_firmware_press_success_rejection_and_value_error(self):
        firmware = {"firmware": {"version": "V2"}}

        entity, coordinator = self.entity("start_firmware", firmware)
        await entity.async_press()
        self.assertEqual(Api.calls, [("start_firmware",)])
        coordinator.async_request_refresh.assert_awaited_once()

        Api.reset()
        self.api = Api()
        Api.start_result = False
        entity, coordinator = self.entity("start_firmware", firmware)
        with self.assertRaisesRegex(HomeAssistantError, "Router rejected the firmware command"):
            await entity.async_press()
        coordinator.async_request_refresh.assert_not_awaited()

        Api.reset()
        self.api = Api()
        Api.start_error = ValueError("start failed")
        entity, coordinator = self.entity("start_firmware", firmware)
        with self.assertRaisesRegex(HomeAssistantError, "start failed"):
            await entity.async_press()
        coordinator.async_request_refresh.assert_not_awaited()

    async def test_sms_press_with_default_compose_does_nothing(self):
        entity, coordinator = self.entity(
            "send_sms", sms_compose=buttons.SMS_COMPOSE_DEFAULT
        )

        await entity.async_press()

        self.assertEqual(Api.calls, [])
        coordinator.async_request_refresh.assert_not_awaited()

    async def test_sms_press_with_invalid_compose_does_not_send(self):
        Api.parse_error = "bad format"
        entity, coordinator = self.entity("send_sms", sms_compose="  bad format  ")

        await entity.async_press()

        self.assertEqual(Api.calls, [("parse_sms", "  bad format  ")])
        coordinator.async_request_refresh.assert_not_awaited()

    async def test_sms_press_reports_send_value_error(self):
        Api.sms_error = ValueError("sms failed")
        compose = "+43123456789,Hello"
        entity, coordinator = self.entity("send_sms", sms_compose=compose)

        with self.assertRaisesRegex(HomeAssistantError, "sms failed"):
            await entity.async_press()

        self.assertEqual(
            Api.calls,
            [
                ("parse_sms", compose),
                ("send_sms", "+43123456789", "Hello"),
            ],
        )
        coordinator.async_request_refresh.assert_not_awaited()

    async def test_sms_press_failure_and_success_handle_refresh(self):
        compose = "+43123456789,Hello"
        Api.sms_result = False
        entity, coordinator = self.entity("send_sms", sms_compose=compose)
        await entity.async_press()
        coordinator.async_request_refresh.assert_not_awaited()

        Api.reset()
        self.api = Api()
        entity, coordinator = self.entity("send_sms", sms_compose=compose)
        await entity.async_press()
        self.assertEqual(
            Api.calls,
            [
                ("parse_sms", compose),
                ("send_sms", "+43123456789", "Hello"),
            ],
        )
        coordinator.async_request_refresh.assert_awaited_once()

    async def test_generic_action_press_success_and_failure(self):
        entity, coordinator = self.entity("restart")
        await entity.async_press()
        self.assertEqual(Api.calls, [("execute_action_def", entity._btn_def.action)])
        coordinator.async_request_refresh.assert_not_awaited()

        Api.reset()
        self.api = Api()
        Api.action_result = False
        entity, coordinator = self.entity("restart")
        await entity.async_press()
        self.assertEqual(Api.calls, [("execute_action_def", entity._btn_def.action)])
        coordinator.async_request_refresh.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
