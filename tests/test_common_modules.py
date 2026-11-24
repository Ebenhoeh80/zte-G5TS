"""Shared coordinator, entity and icon helpers behave consistently."""

import importlib.util
import json
from pathlib import Path
import sys
import types
from typing import Generic, TypeVar
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "zte_5g_router"


def load_coordinator():
    """Load coordinator.py with a minimal DataUpdateCoordinator stand-in."""

    T = TypeVar("T")

    class BaseCoordinator(Generic[T]):
        def __init__(self, hass, logger, *, name, update_method, update_interval):
            self.hass = hass
            self.logger = logger
            self.name = name
            self.update_method = update_method
            self.update_interval = update_interval

        async def _async_update_data(self):
            return await self.update_method()

    core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = object
    update = types.ModuleType("homeassistant.helpers.update_coordinator")
    update.DataUpdateCoordinator = BaseCoordinator
    helpers = types.ModuleType("homeassistant.helpers")
    helpers.update_coordinator = update
    spec = importlib.util.spec_from_file_location("zte_coordinator_test", ROOT / "coordinator.py")
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {
        "homeassistant.core": core,
        "homeassistant.helpers": helpers,
        "homeassistant.helpers.update_coordinator": update,
    }):
        spec.loader.exec_module(module)
    return module


coordinator_mod = load_coordinator()


def load_entity():
    package = types.ModuleType("zte_entity_test")
    package.__path__ = [str(ROOT)]
    entity_mod = types.ModuleType("homeassistant.helpers.entity")
    entity_mod.DeviceInfo = dict
    spec = importlib.util.spec_from_file_location("zte_entity_test.entity", ROOT / "entity.py")
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {
        "zte_entity_test": package,
        "homeassistant.helpers.entity": entity_mod,
    }):
        spec.loader.exec_module(module)
    return module


entity_mod = load_entity()


class CoordinatorAvailabilityTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.logger = Mock()
        self.payload = {"ok": True}
        self.fail_next = False

    async def _update(self):
        if self.fail_next:
            self.fail_next = False
            raise RuntimeError("offline")
        return self.payload

    def _coordinator(self):
        return coordinator_mod.ZteDataUpdateCoordinator(
            Mock(), self.logger,
            name="test_router",
            update_method=self._update,
            update_interval=60,
        )

    async def test_logs_loss_and_recovery_only_on_transition(self):
        coordinator = self._coordinator()
        self.assertEqual(await coordinator._async_update_data(), self.payload)
        self.logger.error.assert_not_called()
        self.logger.info.assert_not_called()

        self.fail_next = True
        with self.assertRaises(RuntimeError):
            await coordinator._async_update_data()
        self.logger.error.assert_called_once()
        self.assertIn("unavailable", self.logger.error.call_args.args[0])

        self.fail_next = True
        with self.assertRaises(RuntimeError):
            await coordinator._async_update_data()
        self.logger.error.assert_called_once()

        self.assertEqual(await coordinator._async_update_data(), self.payload)
        self.logger.info.assert_called_once()
        self.assertIn("available again", self.logger.info.call_args.args[0])

        self.assertEqual(await coordinator._async_update_data(), self.payload)
        self.logger.info.assert_called_once()


class EntityHelperTests(unittest.TestCase):
    def test_unique_id_and_device_info_are_stable(self):
        self.assertEqual(
            entity_mod.entity_unique_id("entry-1", "wifi_aa:bb"),
            "entry-1_wifi_aa:bb",
        )
        info = entity_mod.device_info("entry-1", "Router")
        self.assertEqual(info["identifiers"], {("zte_5g_router", "entry-1")})
        self.assertEqual(info["name"], "Router")
        self.assertEqual(info["manufacturer"], "ZTE")


class IconTranslationTests(unittest.TestCase):
    def test_icons_json_matches_translation_keys_and_no_hardcoded_icons(self):
        icons = json.loads((ROOT / "icons.json").read_text(encoding="utf-8"))["entity"]
        strings = json.loads((ROOT / "strings.json").read_text(encoding="utf-8"))["entity"]
        self.assertTrue(icons)
        for platform, keys in icons.items():
            self.assertIn(platform, strings)
            for key in keys:
                with self.subTest(platform=platform, key=key):
                    self.assertIn(key, strings[platform])
                    self.assertIn("default", icons[platform][key])
                    self.assertTrue(icons[platform][key]["default"].startswith("mdi:"))
        for name in ("button.py", "switch.py", "sensor.py", "text.py", "device_tracker.py"):
            with self.subTest(source=name):
                source = (ROOT / name).read_text(encoding="utf-8")
                self.assertNotIn("_attr_icon", source)
                # Entity descriptions must not override icons.json either.
                self.assertNotIn("icon=", source)


if __name__ == "__main__":
    unittest.main()
