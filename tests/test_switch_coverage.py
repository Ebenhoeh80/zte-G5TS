"""Offline coverage tests for the switch platform; no router action is executed."""

from datetime import UTC, datetime, timedelta
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import AsyncMock, Mock, patch

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "zte_5g_router"
NOW = datetime(2026, 1, 1, tzinfo=UTC)


def load_switch():
    """Load switch.py with stubbed Home Assistant and API dependencies."""
    package = types.ModuleType("zte_switch_cov_test")
    package.__path__ = [str(ROOT)]
    modules = {"zte_switch_cov_test": package}

    class SwitchEntity:
        def async_write_ha_state(self):
            pass

    class CoordinatorEntity:
        def __init__(self, coordinator):
            self.coordinator = coordinator

    class HomeAssistantError(Exception):
        pass

    class FakeApi:
        """Controllable stand-in; all router actions are recorded, never sent."""

        execute_result = True
        execute_error = None
        cell_result = True
        cell_error = None
        active_4g = False
        active_5g = False
        value_4g = ""
        value_5g = ""
        suggestion_4g = ""
        suggestion_5g = ""
        calls = []
        cell_calls = []
        invalidations = 0

        @classmethod
        def reset(cls):
            cls.execute_result = True
            cls.execute_error = None
            cls.cell_result = True
            cls.cell_error = None
            cls.active_4g = cls.active_5g = False
            cls.value_4g = cls.value_5g = ""
            cls.suggestion_4g = cls.suggestion_5g = ""
            cls.calls = []
            cls.cell_calls = []
            cls.invalidations = 0

        async def async_execute_action_def(self, action):
            self.calls.append(action)
            if self.execute_error is not None:
                raise self.execute_error
            return self.execute_result

        async def async_set_4g_cell_lock_enabled(self, enabled, value=None):
            self.cell_calls.append(("4g", enabled, value))
            if self.cell_error is not None:
                raise self.cell_error
            return self.cell_result

        async def async_set_5g_cell_lock_enabled(self, enabled, value=None):
            self.cell_calls.append(("5g", enabled, value))
            if self.cell_error is not None:
                raise self.cell_error
            return self.cell_result

        def safe_error_summary(self, err):
            return f"error={type(err).__name__}"

        def invalidate_session(self):
            self.invalidations += 1

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

    dt_util = types.ModuleType("homeassistant.util.dt")
    dt_util.utcnow = lambda: NOW

    symbols = {
        "homeassistant.components.switch": {"SwitchEntity": SwitchEntity},
        "homeassistant.core": {"HomeAssistant": object},
        "homeassistant.exceptions": {"HomeAssistantError": HomeAssistantError},
        "homeassistant.helpers.entity": {"DeviceInfo": dict},
        "homeassistant.helpers.entity_registry": {"async_get": None},
        "homeassistant.helpers.event": {"async_call_later": None},
        "homeassistant.helpers.update_coordinator": {"CoordinatorEntity": CoordinatorEntity},
        "homeassistant.util": {"dt": dt_util},
        "zte_switch_cov_test.const": {"DOMAIN": "zte_5g_router"},
        "zte_switch_cov_test.entity": {
            "device_info": lambda entry_id, name: {
                "identifiers": {("zte_5g_router", entry_id)},
                "name": name,
                "manufacturer": "ZTE",
            },
            "entity_unique_id": lambda entry_id, key: f"{entry_id}_{key}",
        },
        "zte_switch_cov_test.zte_api": {"ZteRouterApi": FakeApi},
    }
    for name, attributes in symbols.items():
        module = types.ModuleType(name)
        module.__dict__.update(attributes)
        modules[name] = module

    spec = importlib.util.spec_from_file_location("zte_switch_cov_test.switch", ROOT / "switch.py")
    module = importlib.util.module_from_spec(spec)
    modules[spec.name] = module
    with patch.dict(sys.modules, modules):
        spec.loader.exec_module(module)
    return module, FakeApi, HomeAssistantError


switches, Api, HomeAssistantError = load_switch()


class SwitchCoverageTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        Api.reset()
        self.api = Api()
        self.hass = types.SimpleNamespace(states=types.SimpleNamespace(get=Mock(return_value=None)))

    def coordinator(self, data=None):
        return types.SimpleNamespace(
            data=data,
            async_request_refresh=AsyncMock(),
            async_set_updated_data=Mock(),
        )

    def runtime(self, data=None):
        return types.SimpleNamespace(
            coordinator=self.coordinator(data),
            coordinator_fast=self.coordinator(),
            api=self.api,
            name="Router",
            pause_until=None,
            reset_client_absence=Mock(),
        )

    def entry(self, runtime=None):
        return types.SimpleNamespace(entry_id="entry", runtime_data=runtime or self.runtime())

    def action_entity(self, key, data=None):
        definition = next(item for item in switches.SWITCH_DEFS if item.key == key)
        entity = switches.ZteActionSwitch(
            self.coordinator(data), self.api, self.entry(), "Router", definition
        )
        return entity, entity.coordinator

    def pause_entity(self, runtime=None):
        self.runtime_data = runtime or self.runtime()
        entity = switches.ZtePausePollingSwitch(self.hass, self.entry(self.runtime_data), "Router")
        entity.async_write_ha_state = Mock()
        return entity, self.runtime_data

    def cell_entity(self, kind, data=None):
        coordinator = self.coordinator(data)
        entity = switches.ZteCellLockSwitch(
            self.hass, coordinator, self.api, self.entry(), "Router", kind=kind
        )
        return entity, coordinator

    # --- setup and entity identity -------------------------------------------------

    async def test_setup_entry_creates_action_pause_and_cell_entities(self):
        runtime = self.runtime()
        entry = self.entry(runtime)
        added = []
        await switches.async_setup_entry(self.hass, entry, added.extend)
        self.assertEqual(len(added), 8)
        self.assertEqual(
            [entity._attr_unique_id for entity in added],
            [
                "entry_odu_led",
                "entry_wifi_master",
                "entry_wifi_main_2g",
                "entry_wifi_main_5g",
                "entry_mobile_data",
                "entry_pause_polling",
                "entry_cell_lock_4g_enabled",
                "entry_cell_lock_5g_enabled",
            ],
        )
        self.assertEqual(
            [type(entity) for entity in added[5:]],
            [
                switches.ZtePausePollingSwitch,
                switches.ZteCellLockSwitch,
                switches.ZteCellLockSwitch,
            ],
        )
        for entity in added:
            self.assertEqual(entity._attr_device_info["identifiers"], {("zte_5g_router", "entry")})
            self.assertEqual(entity._attr_device_info["name"], "Router")
        self.assertEqual(switches.PARALLEL_UPDATES, 1)

    def test_action_switch_definitions_are_distinct_and_complete(self):
        self.assertEqual(len(switches.SWITCH_DEFS), 5)
        self.assertEqual(
            [item.key for item in switches.SWITCH_DEFS],
            ["odu_led", "wifi_master", "wifi_main_2g", "wifi_main_5g", "mobile_data"],
        )
        entity, _ = self.action_entity("odu_led")
        self.assertEqual(entity._attr_name, "LED")
        self.assertEqual(entity._attr_translation_key, "odu_led")
        self.assertEqual(entity._attr_unique_id, "entry_odu_led")
        self.assertTrue(entity._attr_has_entity_name)

    # --- ZteActionSwitch states ----------------------------------------------------

    def test_generic_is_on_reads_state_key_and_stringifies(self):
        entity, coordinator = self.action_entity(
            "odu_led", {"odu_led": {"switch": "1", "offtime": "7"}}
        )
        self.assertTrue(entity.is_on)
        coordinator.data = {"odu_led": {"switch": 1}}
        self.assertTrue(entity.is_on)
        coordinator.data = {"odu_led": {"switch": "0"}}
        self.assertFalse(entity.is_on)
        coordinator.data = {}
        self.assertFalse(entity.is_on)
        coordinator.data = None
        self.assertFalse(entity.is_on)

    def test_wifi_master_state_prefers_wifi_module_over_wlan(self):
        entity, coordinator = self.action_entity(
            "wifi_master", {"wifi_module": {"wifi_onoff": "1"}, "wlan": {"wifi_onoff": "0"}}
        )
        self.assertTrue(entity.is_on)
        coordinator.data = {"wifi_module": {}, "wlan": {"wifi_onoff": "1"}}
        self.assertTrue(entity.is_on)
        coordinator.data = {"wlan": {"wifi_onoff": "0"}}
        self.assertFalse(entity.is_on)
        coordinator.data = None
        self.assertFalse(entity.is_on)

    def test_mobile_data_state_uses_cellular_connect_status(self):
        entity, coordinator = self.action_entity(
            "mobile_data", {"wwaniface": {"connect_status": "ipv4_connected"}}
        )
        for status in ("ipv4_connected", "ipv6_connected", "ipv4_ipv6_connected"):
            coordinator.data = {"wwaniface": {"connect_status": status, "enable": "0"}}
            self.assertTrue(entity.is_on)
        coordinator.data = {
            "wan": {"current_wan_status": "ipv4_connected", "lte_connect_status": "disconnected"},
            "wwaniface": {"connect_status": "disconnected", "enable": "1"},
        }
        self.assertFalse(entity.is_on)
        coordinator.data = {"wan": {"lte_connect_status": "ipv4_ipv6_connected"}}
        self.assertTrue(entity.is_on)
        coordinator.data = {"wan": {"current_wan_status": "ipv4_connected"}}
        self.assertTrue(entity.is_on)
        coordinator.data = {"wan": {"current_wan_status": "ppp_disconnected"}}
        self.assertFalse(entity.is_on)
        coordinator.data = None
        self.assertFalse(entity.is_on)

    def test_band_state_respects_wifi_master_and_inverted_disabled_flag(self):
        for key in ("wifi_main_2g", "wifi_main_5g"):
            with self.subTest(key=key):
                entity, coordinator = self.action_entity(
                    key, {"wifi_module": {"wifi_onoff": "1"}, key: {"disabled": "0"}}
                )
                self.assertTrue(entity.is_on)
                coordinator.data = {"wlan": {"wifi_onoff": "1"}, key: {"disabled": 0}}
                self.assertTrue(entity.is_on)
                coordinator.data = {"wifi_module": {"wifi_onoff": "1"}, key: {"disabled": "1"}}
                self.assertFalse(entity.is_on)
                coordinator.data = {"wifi_module": {"wifi_onoff": "0"}, key: {"disabled": "0"}}
                self.assertFalse(entity.is_on)
                coordinator.data = {"wlan": {"wifi_onoff": "0"}, key: {"disabled": "0"}}
                self.assertFalse(entity.is_on)
                coordinator.data = {key: {"disabled": "0"}}
                self.assertFalse(entity.is_on)

    def test_extra_state_attributes_return_definition_node(self):
        entity, coordinator = self.action_entity(
            "odu_led", {"odu_led": {"switch": "1", "offtime": "9"}}
        )
        self.assertEqual(entity.extra_state_attributes, {"switch": "1", "offtime": "9"})
        coordinator.data = None
        self.assertEqual(entity.extra_state_attributes, {})
        entity, _ = self.action_entity("wifi_master", {"wifi_module": {"wifi_onoff": "1"}})
        self.assertEqual(entity.extra_state_attributes, {"wifi_onoff": "1"})

    # --- ZteActionSwitch actions ---------------------------------------------------

    async def test_turn_on_and_off_update_state_optimistically_without_refresh(self):
        cases = [
            (
                "odu_led",
                {"odu_led": {}},
                {"switch": "1", "offtime": "15"},
                {"switch": "0", "offtime": "15"},
            ),
            (
                "wifi_master",
                {"wifi_module": {"wifi_onoff": "0"}},
                {"wifi_onoff": "1", "lbd": "1", "mlo": "0"},
                {"wifi_onoff": "0"},
            ),
            ("wifi_main_2g", {"wifi_main_2g": {}}, {"disabled": "0"}, {"disabled": "1"}),
            ("wifi_main_5g", {"wifi_main_5g": {}}, {"disabled": "0"}, {"disabled": "1"}),
        ]
        for key, data, on_values, off_values in cases:
            with self.subTest(key=key):
                Api.reset()
                self.api = Api()
                entity, coordinator = self.action_entity(key, data)
                entity._api = self.api
                await entity.async_turn_on()
                self.assertEqual(
                    self.api.calls[0]["method"],
                    "set" if key != "odu_led" else "set_ODU_switch_state",
                )
                for expected_key, expected_value in on_values.items():
                    section = self.api.calls[0]["params"]
                    if key == "wifi_master":
                        section = section["zte_mbb"]
                    elif key.startswith("wifi_main_"):
                        section = section[key.removeprefix("wifi_")]
                    self.assertEqual(str(section[expected_key]), str(expected_value))
                self.assertEqual(coordinator.async_set_updated_data.call_count, 1)
                coordinator.async_request_refresh.assert_not_awaited()

                Api.reset()
                self.api = Api()
                entity, coordinator = self.action_entity(key, data)
                entity._api = self.api
                await entity.async_turn_off()
                for expected_key, expected_value in off_values.items():
                    section = self.api.calls[0]["params"]
                    if key == "wifi_master":
                        section = section["zte_mbb"]
                    elif key.startswith("wifi_main_"):
                        section = section[key.removeprefix("wifi_")]
                    self.assertEqual(str(section[expected_key]), str(expected_value))
                self.assertEqual(coordinator.async_set_updated_data.call_count, 1)
                coordinator.async_request_refresh.assert_not_awaited()

    async def test_mobile_data_actions_do_not_write_optimistic_data(self):
        for method in ("async_turn_on", "async_turn_off"):
            with self.subTest(method=method):
                Api.reset()
                self.api = Api()
                entity, coordinator = self.action_entity(
                    "mobile_data", {"wwaniface": {"enable": 0}}
                )
                entity._api = self.api
                await getattr(entity, method)()
                self.assertEqual(
                    self.api.calls[0]["params"]["enable"], 1 if method.endswith("on") else 0
                )
                coordinator.async_set_updated_data.assert_not_called()
                coordinator.async_request_refresh.assert_awaited_once()

    async def test_rejected_actions_raise_and_do_not_refresh(self):
        for method, fragment in (
            ("async_turn_on", "turning on 'odu_led'"),
            ("async_turn_off", "turning off 'odu_led'"),
        ):
            with self.subTest(method=method):
                Api.reset()
                self.api = Api()
                self.api.execute_result = False
                entity, coordinator = self.action_entity("odu_led", {"odu_led": {}})
                entity._api = self.api
                with self.assertRaisesRegex(HomeAssistantError, fragment):
                    await getattr(entity, method)()
                coordinator.async_set_updated_data.assert_not_called()
                coordinator.async_request_refresh.assert_not_awaited()

    async def test_api_exception_from_action_propagates(self):
        self.api.execute_error = ValueError("transport down")
        entity, coordinator = self.action_entity("mobile_data")
        with self.assertRaisesRegex(ValueError, "transport down"):
            await entity.async_turn_on()
        coordinator.async_request_refresh.assert_not_awaited()

    def test_optimistic_state_fallbacks(self):
        entity, coordinator = self.action_entity("mobile_data")
        self.assertFalse(entity._apply_optimistic_state({"params": {"enable": "1"}}))
        coordinator.async_set_updated_data.assert_not_called()

        entity, coordinator = self.action_entity("odu_led", {"odu_led": {"switch": "0"}})
        self.assertFalse(entity._apply_optimistic_state({}))
        self.assertFalse(entity._apply_optimistic_state({"params": None}))
        self.assertFalse(entity._apply_optimistic_state({"params": {"unrelated": "1"}}))
        coordinator.async_set_updated_data.assert_not_called()

        entity, coordinator = self.action_entity("odu_led", {"odu_led": "not-a-node"})
        self.assertFalse(entity._apply_optimistic_state({"params": {"switch": "1"}}))
        coordinator.async_set_updated_data.assert_not_called()

        original = {"wifi_module": {"wifi_onoff": "0"}}
        entity, coordinator = self.action_entity("wifi_master", original)
        self.assertTrue(
            entity._apply_optimistic_state({"params": {"zte_mbb": {"wifi_onoff": "1"}}})
        )
        self.assertEqual(
            coordinator.async_set_updated_data.call_args.args[0]["wifi_module"]["wifi_onoff"], "1"
        )
        self.assertEqual(original, {"wifi_module": {"wifi_onoff": "0"}})

        entity, coordinator = self.action_entity("wifi_master", {"wlan": {"wifi_onoff": "0"}})
        self.assertTrue(
            entity._apply_optimistic_state({"params": {"zte_mbb": {"wifi_onoff": "1"}}})
        )
        self.assertEqual(
            coordinator.async_set_updated_data.call_args.args[0]["wlan"]["wifi_onoff"], "1"
        )

        entity, coordinator = self.action_entity(
            "wifi_main_5g", {"wifi_main_5g": {"disabled": "1"}}
        )
        self.assertTrue(entity._apply_optimistic_state({"params": {"main_5g": {"disabled": "0"}}}))
        self.assertEqual(
            coordinator.async_set_updated_data.call_args.args[0]["wifi_main_5g"]["disabled"], "0"
        )

        entity, coordinator = self.action_entity("odu_led", {"odu_led": {"switch": "0"}})
        self.assertTrue(entity._apply_optimistic_state({"params": {"switch": "1"}}))
        self.assertEqual(
            coordinator.async_set_updated_data.call_args.args[0]["odu_led"], {"switch": "1"}
        )

    def test_led_action_preserves_reported_offtime_without_mutating_definition(self):
        definition = next(item for item in switches.SWITCH_DEFS if item.key == "odu_led")
        entity, _ = self.action_entity("odu_led", {"odu_led": {"switch": "1", "offtime": "22"}})
        self.assertEqual(entity._action_for_turn_on()["params"]["offtime"], "22")
        self.assertEqual(entity._action_for_turn_off()["params"]["offtime"], "22")
        self.assertEqual(definition.turn_on["params"]["offtime"], "15")
        self.assertEqual(definition.turn_off["params"]["offtime"], "15")

        for data in ({"odu_led": {"offtime": ""}}, {"odu_led": {}}, None):
            entity, _ = self.action_entity("odu_led", data)
            self.assertEqual(entity._action_for_turn_on()["params"]["offtime"], "15")
            self.assertEqual(entity._action_for_turn_off()["params"]["offtime"], "15")

    def test_wifi_master_action_preserves_lbd_and_mlo_from_available_sources(self):
        definition = next(item for item in switches.SWITCH_DEFS if item.key == "wifi_master")

        def params(data):
            entity, _ = self.action_entity("wifi_master", data)
            return entity._action_for_turn_on()["params"]["zte_mbb"]

        self.assertEqual(params({"wifi_module": {"lbd": "0", "mlo": "1"}, "wlan": {}})["lbd"], "0")
        self.assertEqual(params({"wifi_module": {"lbd": "0", "mlo": "1"}, "wlan": {}})["mlo"], "1")
        self.assertEqual(params({"wlan": {"lbd_enable": "0", "mlo_enable": "1"}})["lbd"], "0")
        self.assertEqual(params({"wlan": {"lbd": "0", "mlo": "1"}})["mlo"], "1")
        self.assertEqual(params({})["lbd"], "1")
        self.assertEqual(params({})["mlo"], "0")
        self.assertEqual(params(None)["lbd"], "1")
        self.assertEqual(params({"wifi_module": {"lbd": "maybe", "mlo": "x"}})["lbd"], "1")
        self.assertEqual(params({"wifi_module": {"lbd": "maybe", "mlo": "x"}})["mlo"], "0")
        self.assertEqual(
            definition.turn_on["params"]["zte_mbb"], {"wifi_onoff": "1", "lbd": "1", "mlo": "0"}
        )

        # Empty definition values exercise the final fallback of both chains.
        custom = switches.ZteActionSwitchDef(
            key="wifi_master",
            name="WiFi",
            state_key="wifi_onoff",
            on_value="1",
            off_value="0",
            get_path=definition.get_path,
            turn_on={"service": "zwrt_wlan", "method": "set", "params": {"zte_mbb": {}}},
            turn_off={"service": "zwrt_wlan", "method": "set", "params": {"zte_mbb": {}}},
        )
        entity = switches.ZteActionSwitch(
            self.coordinator(), self.api, self.entry(), "Router", custom
        )
        self.assertEqual(
            entity._action_for_turn_on()["params"]["zte_mbb"], {"lbd": "1", "mlo": "0"}
        )

    def test_band_actions_include_webui_metadata_and_keep_source_module(self):
        definition = next(item for item in switches.SWITCH_DEFS if item.key == "wifi_main_2g")
        for key in ("wifi_main_2g", "wifi_main_5g"):
            with self.subTest(key=key):
                section_name = key.removeprefix("wifi_")
                entity, _ = self.action_entity(
                    key,
                    {
                        key: {"qrImageShow": "", "wifiSyncparasFlag": "flag"},
                        "wifi_module": {"wifi_onoff": "1"},
                    },
                )
                for action in (entity._action_for_turn_on(), entity._action_for_turn_off()):
                    params = action["params"]
                    section = params[section_name]
                    self.assertIs(section["isTest"], False)
                    self.assertEqual(section["wifiSyncparasFlag"], "flag")
                    self.assertNotIn("qrImageShow", section)
                    self.assertEqual(params["source_module"], "web")
                self.assertNotIn("isTest", definition.turn_on["params"].get(section_name, {}))

                entity, _ = self.action_entity(key, {"wifi_module": {"wifi_onoff": "1"}})
                action = entity._action_for_turn_on()
                self.assertEqual(action["params"]["source_module"], "web")
                self.assertNotIn("qrImageShow", action["params"][section_name])
                action["params"]["source_module"] = "cli"
                self.assertEqual(entity._action_for_turn_on()["params"]["source_module"], "web")

    def test_mobile_and_wifi_off_actions_are_plain_definition_copies(self):
        for key in ("mobile_data", "wifi_master"):
            entity, _ = self.action_entity(key)
            action = entity._action_for_turn_off()
            definition = next(item for item in switches.SWITCH_DEFS if item.key == key)
            self.assertEqual(action, definition.turn_off)
            self.assertIsNot(action, definition.turn_off)

    # --- ZtePausePollingSwitch ------------------------------------------------------

    def test_pause_switch_identity_and_state(self):
        entity, runtime = self.pause_entity()
        self.assertEqual(entity._attr_name, "Pause polling (5 min)")
        self.assertEqual(entity._attr_translation_key, "pause_polling")
        self.assertEqual(entity._attr_unique_id, "entry_pause_polling")
        self.assertTrue(entity._attr_has_entity_name)
        self.assertIs(entity._store, runtime)
        self.assertFalse(entity.is_on)
        runtime.pause_until = NOW - timedelta(seconds=1)
        self.assertFalse(entity.is_on)
        runtime.pause_until = NOW + timedelta(seconds=1)
        self.assertTrue(entity.is_on)

    async def test_pause_turn_on_schedules_auto_off_and_resumes(self):
        entity, runtime = self.pause_entity()
        callback = None

        def call_later(_hass, delay, func):
            self.assertEqual(delay, 300)
            nonlocal callback
            callback = func
            return Mock()

        with patch.object(switches, "async_call_later", side_effect=call_later):
            await entity.async_turn_on()
        self.assertEqual(runtime.pause_until, NOW + timedelta(minutes=5))
        runtime.reset_client_absence.assert_called_once_with()
        entity.async_write_ha_state.assert_called_once_with()
        self.assertIsNotNone(entity._unsub_auto_off)
        self.assertTrue(entity.is_on)

        await callback(None)
        self.assertIsNone(runtime.pause_until)
        self.assertIsNone(entity._unsub_auto_off)
        self.assertEqual(self.api.invalidations, 1)
        runtime.coordinator.async_request_refresh.assert_awaited_once()
        runtime.coordinator_fast.async_request_refresh.assert_awaited_once()
        self.assertEqual(entity.async_write_ha_state.call_count, 2)
        self.assertFalse(entity.is_on)

        await entity.async_will_remove_from_hass()
        self.assertIsNone(entity._unsub_auto_off)

    async def test_pause_turn_on_cancels_previous_timer_and_handles_missing_reset(self):
        entity, runtime = self.pause_entity()
        previous_unsub = Mock()
        entity._unsub_auto_off = previous_unsub
        runtime.reset_client_absence = None
        with patch.object(switches, "async_call_later", return_value=Mock()):
            await entity.async_turn_on()
        previous_unsub.assert_called_once_with()
        self.assertIsNot(entity._unsub_auto_off, previous_unsub)

    async def test_pause_turn_off_cancels_timer_and_resumes_immediately(self):
        for with_timer in (True, False):
            with self.subTest(with_timer=with_timer):
                self.api = Api()
                runtime = self.runtime()
                runtime.pause_until = NOW + timedelta(minutes=5)
                entity, runtime = self.pause_entity(runtime)
                unsub = Mock()
                entity._unsub_auto_off = unsub if with_timer else None
                await entity.async_turn_off()
                if with_timer:
                    unsub.assert_called_once_with()
                self.assertIsNone(entity._unsub_auto_off)
                self.assertIsNone(runtime.pause_until)
                self.assertFalse(entity.is_on)
                self.assertEqual(self.api.invalidations, 1)
                runtime.coordinator.async_request_refresh.assert_awaited_once()
                runtime.coordinator_fast.async_request_refresh.assert_awaited_once()
                entity.async_write_ha_state.assert_called_once_with()

    async def test_pause_removal_cancels_pending_timer(self):
        entity, _ = self.pause_entity()
        await entity.async_will_remove_from_hass()
        unsub = Mock()
        entity._unsub_auto_off = unsub
        await entity.async_will_remove_from_hass()
        unsub.assert_called_once_with()
        self.assertIsNone(entity._unsub_auto_off)

    # --- ZteCellLockSwitch ----------------------------------------------------------

    def test_cell_lock_identity_and_kind_validation(self):
        for kind, name in (("4g", "Cell Lock 4G"), ("5g", "Cell Lock 5G")):
            with self.subTest(kind=kind):
                entity, _ = self.cell_entity(kind)
                self.assertEqual(entity._attr_name, name)
                self.assertEqual(entity._attr_translation_key, f"cell_lock_{kind}")
                self.assertEqual(entity._attr_unique_id, f"entry_cell_lock_{kind}_enabled")
                self.assertEqual(
                    entity._attr_device_info["identifiers"], {("zte_5g_router", "entry")}
                )
                self.assertIsNone(entity._text_entity_id)
                self.assertTrue(entity._attr_has_entity_name)
        with self.assertRaisesRegex(ValueError, "kind must be"):
            self.cell_entity("6g")

    def test_cell_lock_netinfo_and_state(self):
        entity, coordinator = self.cell_entity("4g")
        self.assertEqual(entity._netinfo(), {})
        coordinator.data = {"netinfo": "broken"}
        self.assertEqual(entity._netinfo(), {})
        coordinator.data = {"netinfo": {"lock_lte_cell": "1,2"}}
        self.assertEqual(entity._netinfo(), {"lock_lte_cell": "1,2"})

        Api.active_4g = True
        Api.active_5g = True
        four_g, _ = self.cell_entity("4g", {"netinfo": {}})
        five_g, _ = self.cell_entity("5g", {"netinfo": {}})
        self.assertTrue(four_g.is_on)
        self.assertTrue(five_g.is_on)
        Api.active_4g = False
        self.assertFalse(four_g.is_on)

    def test_cell_lock_extra_state_attributes(self):
        Api.value_4g = "1,2"
        Api.suggestion_4g = "3,4"
        Api.value_5g = "5,6,7"
        Api.suggestion_5g = "8,9,10"
        four_g, _ = self.cell_entity("4g", {"netinfo": {}})
        five_g, _ = self.cell_entity("5g", {"netinfo": {}})
        self.assertEqual(
            four_g.extra_state_attributes, {"lock_lte_cell": "1,2", "suggested": "3,4"}
        )
        self.assertEqual(
            five_g.extra_state_attributes, {"lock_nr_cell": "5,6,7", "suggested": "8,9,10"}
        )

    async def test_cell_lock_resolves_text_entity_with_cache_and_error(self):
        for kind in ("4g", "5g"):
            with self.subTest(kind=kind):
                entity, _ = self.cell_entity(kind)
                registry = Mock()
                registry.async_get_entity_id.return_value = f"text.cell_lock_{kind}"
                with patch.object(
                    switches, "async_get_entity_registry", return_value=registry
                ) as getter:
                    self.assertEqual(
                        await entity._resolve_text_entity_id(), f"text.cell_lock_{kind}"
                    )
                    self.assertEqual(
                        await entity._resolve_text_entity_id(), f"text.cell_lock_{kind}"
                    )
                getter.assert_called_once_with(self.hass)
                registry.async_get_entity_id.assert_called_once_with(
                    "text", "zte_5g_router", f"entry_cell_lock_{kind}_text"
                )

        entity, _ = self.cell_entity("4g")
        with patch.object(
            switches, "async_get_entity_registry", side_effect=RuntimeError("no registry")
        ):
            self.assertIsNone(await entity._resolve_text_entity_id())
        with patch.object(switches, "async_get_entity_registry", return_value=Mock()) as getter:
            getter.return_value.async_get_entity_id.return_value = None
            self.assertIsNone(await entity._resolve_text_entity_id())

    async def test_cell_lock_turn_on_reads_companion_text_value(self):
        for kind in ("4g", "5g"):
            with self.subTest(kind=kind):
                Api.reset()
                self.api = Api()
                entity, coordinator = self.cell_entity(kind)
                entity._api = self.api
                text_id = f"text.cell_lock_{kind}"
                self.hass.states.get = Mock(return_value=types.SimpleNamespace(state=" 1,2,3 "))
                with patch.object(
                    switches,
                    "async_get_entity_registry",
                    return_value=Mock(async_get_entity_id=Mock(return_value=text_id)),
                ):
                    await entity.async_turn_on()
                self.hass.states.get.assert_called_once_with(text_id)
                self.assertEqual(self.api.cell_calls, [(kind, True, "1,2,3")])
                coordinator.async_request_refresh.assert_awaited_once()

    async def test_cell_lock_turn_on_without_state_sends_empty_value(self):
        entity, _ = self.cell_entity("4g")
        with patch.object(
            switches,
            "async_get_entity_registry",
            return_value=Mock(async_get_entity_id=Mock(return_value="text.cell_lock_4g")),
        ):
            self.hass.states.get.return_value = None
            await entity.async_turn_on()
            self.assertEqual(self.api.cell_calls, [("4g", True, "")])
            self.hass.states.get.return_value = types.SimpleNamespace(state=None)
            await entity.async_turn_on()
            self.assertEqual(self.api.cell_calls[-1], ("4g", True, ""))

    async def test_cell_lock_turn_on_rejects_missing_companion(self):
        for kind in ("4g", "5g"):
            with self.subTest(kind=kind):
                entity, coordinator = self.cell_entity(kind)
                with (
                    patch.object(
                        switches,
                        "async_get_entity_registry",
                        return_value=Mock(async_get_entity_id=Mock(return_value=None)),
                    ),
                    self.assertRaisesRegex(HomeAssistantError, "companion text entity not found"),
                ):
                    await entity.async_turn_on()
                self.assertEqual(self.api.cell_calls, [])
                coordinator.async_request_refresh.assert_not_awaited()

    async def test_cell_lock_turn_on_handles_api_errors_and_rejection(self):
        for kind in ("4g", "5g"):
            with self.subTest(kind=kind):
                entity, coordinator = self.cell_entity(kind)
                method = f"async_set_{kind}_cell_lock_enabled"
                with patch.object(switches, "async_get_entity_registry") as getter:
                    getter.return_value.async_get_entity_id.return_value = f"text.cell_lock_{kind}"
                    with (
                        patch.object(
                            self.api, method, new=AsyncMock(side_effect=ValueError("down"))
                        ),
                        self.assertRaisesRegex(HomeAssistantError, "error=ValueError"),
                    ):
                        await entity.async_turn_on()
                    with (
                        patch.object(self.api, method, new=AsyncMock(return_value=False)),
                        self.assertRaisesRegex(HomeAssistantError, "Router rejected enabling"),
                    ):
                        await entity.async_turn_on()
                coordinator.async_request_refresh.assert_not_awaited()

    async def test_cell_lock_turn_off_success_error_and_rejection(self):
        for kind in ("4g", "5g"):
            with self.subTest(kind=kind):
                Api.reset()
                self.api = Api()
                entity, coordinator = self.cell_entity(kind)
                entity._api = self.api
                await entity.async_turn_off()
                self.assertEqual(self.api.cell_calls, [(kind, False, None)])
                coordinator.async_request_refresh.assert_awaited_once()

                self.api.cell_error = RuntimeError("offline")
                with self.assertRaisesRegex(HomeAssistantError, "Failed to disable cell lock"):
                    await entity.async_turn_off()
                self.api.cell_error = None
                self.api.cell_result = False
                with self.assertRaisesRegex(HomeAssistantError, "Router rejected disabling"):
                    await entity.async_turn_off()
                self.assertEqual(coordinator.async_request_refresh.await_count, 1)


if __name__ == "__main__":
    unittest.main()
