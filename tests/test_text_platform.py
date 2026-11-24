"""Offline text-entity tests; no router writes are executed."""

import dataclasses
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "zte_5g_router"


def load_text():
    package = types.ModuleType("zte_text_test")
    package.__path__ = [str(ROOT)]
    modules = {"zte_text_test": package}

    @dataclasses.dataclass(frozen=True, kw_only=True)
    class TextEntityDescription:
        key: str = ""
        name: str | None = None
        icon: str | None = None
        entity_category: object | None = None

    class CoordinatorEntity:
        def __init__(self, coordinator):
            self.coordinator = coordinator

    class FakeApi:
        """Controllable stand-in for the router's parsing helpers."""

        active_4g = False
        active_5g = False
        value_4g = ""
        value_5g = ""
        suggestion_4g = ""
        suggestion_5g = ""
        sms_result = ("+43123456789", "Hello")
        parse_error = None
        last_parsed = None

        @classmethod
        def reset(cls):
            cls.active_4g = cls.active_5g = False
            cls.value_4g = cls.value_5g = ""
            cls.suggestion_4g = cls.suggestion_5g = ""
            cls.sms_result = ("+43123456789", "Hello")
            cls.parse_error = cls.last_parsed = None

        @classmethod
        def _parse(cls, value):
            cls.last_parsed = value
            if cls.parse_error:
                raise ValueError(cls.parse_error)
            return value

        @classmethod
        def is_4g_cell_lock_active(cls, node):
            return cls.active_4g

        @classmethod
        def is_5g_cell_lock_active(cls, node):
            return cls.active_5g

        @classmethod
        def get_4g_cell_lock_value(cls, node):
            return cls.value_4g

        @classmethod
        def get_5g_cell_lock_value(cls, node):
            return cls.value_5g

        @classmethod
        def suggest_4g_cell_lock_text(cls, node):
            return cls.suggestion_4g

        @classmethod
        def suggest_5g_cell_lock_text(cls, node):
            return cls.suggestion_5g

        @classmethod
        def parse_4g_cell_lock_input(cls, value):
            return cls._parse(value)

        @classmethod
        def parse_5g_cell_lock_input(cls, value):
            return cls._parse(value)

        @classmethod
        def parse_sms_compose_input(cls, value):
            cls._parse(value)
            return cls.sms_result

    symbols = {
        "homeassistant.components.text": {
            "TextEntity": type("TextEntity", (), {}),
            "TextEntityDescription": TextEntityDescription,
        },
        "homeassistant.core": {"HomeAssistant": object},
        "homeassistant.helpers.entity": {
            "EntityCategory": types.SimpleNamespace(CONFIG="config"),
            "DeviceInfo": dict,
        },
        "homeassistant.helpers.update_coordinator": {"CoordinatorEntity": CoordinatorEntity},
        "zte_text_test.zte_api": {"ZteRouterApi": FakeApi},
    }
    for name, attributes in symbols.items():
        module = types.ModuleType(name)
        module.__dict__.update(attributes)
        modules[name] = module

    for modname, filename in (("const", "const.py"), ("entity", "entity.py")):
        spec = importlib.util.spec_from_file_location(f"zte_text_test.{modname}", ROOT / filename)
        module = importlib.util.module_from_spec(spec)
        modules[spec.name] = module
        with patch.dict(sys.modules, modules):
            spec.loader.exec_module(module)

    spec = importlib.util.spec_from_file_location("zte_text_test.text", ROOT / "text.py")
    module = importlib.util.module_from_spec(spec)
    modules[spec.name] = module
    with patch.dict(sys.modules, modules):
        spec.loader.exec_module(module)
    return module, FakeApi


text, Api = load_text()


class TextPlatformTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        Api.reset()

    def make_entity(self, kind, data=None, sms_compose=""):
        description = next(item for item in text.TEXTS if item.kind == kind)
        coordinator = types.SimpleNamespace(data=data or {})
        runtime = types.SimpleNamespace(
            coordinator=coordinator,
            api=Api,
            name="Router",
            sms_compose=sms_compose,
        )
        entry = types.SimpleNamespace(entry_id="entry", runtime_data=runtime)
        entity = text.ZteTextEntity(object(), coordinator, Api, entry, "Router", description)
        entity.async_write_ha_state = Mock()
        return entity, runtime

    async def test_setup_creates_all_three_entities(self):
        runtime = types.SimpleNamespace(
            coordinator=types.SimpleNamespace(data={}),
            api=Api,
            name="Router",
            sms_compose="",
        )
        entry = types.SimpleNamespace(entry_id="entry", runtime_data=runtime)
        added = []
        await text.async_setup_entry(object(), entry, added.extend)
        self.assertEqual(len(added), 3)
        self.assertEqual(runtime.sms_compose, text.SMS_COMPOSE_DEFAULT)
        self.assertEqual(
            [entity._attr_unique_id for entity in added],
            [
                "entry_cell_lock_4g_text",
                "entry_cell_lock_5g_text",
                "entry_sms_compose_text",
            ],
        )

    async def test_setup_keeps_existing_compose_value(self):
        runtime = types.SimpleNamespace(
            coordinator=types.SimpleNamespace(data={}),
            api=Api,
            name="Router",
            sms_compose="+43123456789,Existing",
        )
        entry = types.SimpleNamespace(entry_id="entry", runtime_data=runtime)
        await text.async_setup_entry(object(), entry, lambda entities: None)
        self.assertEqual(runtime.sms_compose, "+43123456789,Existing")

    def test_entity_identity_and_input_constraints(self):
        for kind, unique_id, pattern in (
            ("4g", "entry_cell_lock_4g_text", r"^[0-9]+,[0-9]+$"),
            ("5g", "entry_cell_lock_5g_text", r"^[0-9]+,[0-9]+,[0-9]+$"),
        ):
            with self.subTest(kind=kind):
                entity, _ = self.make_entity(kind)
                self.assertEqual(entity._attr_unique_id, unique_id)
                self.assertEqual(
                    entity._attr_device_info["identifiers"],
                    {("zte_5g_router", "entry")},
                )
                self.assertEqual(entity._attr_mode, "text")
                self.assertEqual(entity._attr_native_min, 0)
                self.assertEqual(entity._attr_native_max, 32)
                self.assertEqual(entity._attr_pattern, pattern)
        sms, _ = self.make_entity("sms")
        self.assertEqual(sms._attr_unique_id, "entry_sms_compose_text")
        self.assertEqual(sms._attr_native_max, 255)

    def test_native_value_priority(self):
        entity, runtime = self.make_entity("sms", sms_compose="+43123456789,Hi")
        self.assertEqual(entity.native_value, "+43123456789,Hi")
        runtime.sms_compose = ""
        self.assertEqual(entity.native_value, text.SMS_COMPOSE_DEFAULT)

        Api.value_4g = "1,2"
        Api.suggestion_4g = "3,4"
        entity, _ = self.make_entity("4g")
        self.assertEqual(entity.native_value, "3,4")
        entity._user_value = "5,6"
        self.assertEqual(entity.native_value, "5,6")
        Api.active_4g = True
        self.assertEqual(entity.native_value, "1,2")

        Api.value_5g = "7,8,9"
        entity, _ = self.make_entity("5g")
        self.assertEqual(entity.native_value, "7,8,9")
        Api.active_5g = True
        self.assertEqual(entity.native_value, "7,8,9")

    async def test_set_value_validates_and_stores(self):
        entity, _ = self.make_entity("4g")
        await entity.async_set_value(" 1,2 ")
        self.assertEqual(Api.last_parsed, "1,2")
        self.assertEqual(entity._user_value, "1,2")
        entity.async_write_ha_state.assert_called_once()

        entity, _ = self.make_entity("5g")
        await entity.async_set_value("1,2,3")
        self.assertEqual(entity._user_value, "1,2,3")

        entity, runtime = self.make_entity("sms")
        await entity.async_set_value("+43123456789,Hi")
        self.assertEqual(runtime.sms_compose, "+43123456789,Hi")
        self.assertIsNone(entity._user_value)

    async def test_invalid_value_is_rejected(self):
        entity, runtime = self.make_entity("4g")
        Api.parse_error = "bad input"
        with self.assertRaises(ValueError):
            await entity.async_set_value("bad")
        self.assertIsNone(entity._user_value)
        entity.async_write_ha_state.assert_not_called()

        entity, runtime = self.make_entity("sms")
        with self.assertRaises(ValueError):
            await entity.async_set_value("bad")
        self.assertEqual(runtime.sms_compose, "")

    def test_extra_state_attributes(self):
        sms, _ = self.make_entity("sms", sms_compose="+43123456789,Hi")
        attributes = sms.extra_state_attributes
        self.assertTrue(attributes["is_valid"])
        self.assertEqual(attributes["parsed_number"], "+43123456789")
        self.assertEqual(attributes["message_length"], 5)

        Api.parse_error = "bad input"
        sms, _ = self.make_entity("sms", sms_compose="bad")
        self.assertFalse(sms.extra_state_attributes["is_valid"])

        Api.reset()
        Api.value_4g = "1,2"
        Api.suggestion_4g = "3,4"
        entity, _ = self.make_entity("4g")
        attributes = entity.extra_state_attributes
        self.assertEqual(attributes["lock_lte_cell"], "1,2")
        self.assertFalse(attributes["lock_active"])
        self.assertEqual(attributes["suggested"], "3,4")

        Api.value_5g = "7,8,9"
        entity, _ = self.make_entity("5g")
        attributes = entity.extra_state_attributes
        self.assertEqual(attributes["lock_nr_cell"], "7,8,9")


if __name__ == "__main__":
    unittest.main()
