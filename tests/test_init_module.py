"""Offline setup/unload tests for the integration entry point."""

from datetime import UTC, datetime, timedelta
import importlib.util
from pathlib import Path
import sys
import types
from typing import Generic, TypeVar
import unittest
from unittest.mock import AsyncMock, Mock, patch

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "zte_5g_router"


def load_init():
    T = TypeVar("T")

    class ConfigEntry(Generic[T]):
        pass

    class ConfigEntryAuthFailed(Exception):
        pass

    class UpdateFailed(Exception):
        pass

    class ZteAuthError(Exception):
        pass

    class FakeCoordinator:
        def __init__(self, hass, logger, *, name, update_method, update_interval):
            self.hass = hass
            self.logger = logger
            self.name = name
            self.update_method = update_method
            self.update_interval = update_interval
            self.data = None
            self.last_update_success = False

        async def _async_update_data(self):
            return await self.update_method()

        async def async_config_entry_first_refresh(self):
            self.data = await self._async_update_data()
            self.last_update_success = True

        def async_add_listener(self, listener):
            return lambda: None

    class FakeApi:
        instances = []
        error = None
        fast_error = None
        all_data = None
        fast_data = {"fast": True}
        empty_all = False
        empty_fast = False

        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.closed = False
            self.error = FakeApi.error
            self.fast_error = FakeApi.fast_error
            self.all_data = (
                FakeApi.all_data
                if FakeApi.all_data is not None
                else {
                    "common_config": {"wa_inner_version": "V1.0"},
                    "sms": {
                        "messages": [
                            {
                                "id": "1",
                                "mem_store": "SM",
                                "date": "2026-01-01 10:00",
                                "tag": "0",
                                "number": "+43123456789",
                                "content_decoded": "Hello",
                            }
                        ]
                    },
                }
            )
            self.fast_data = None if FakeApi.empty_fast else FakeApi.fast_data
            if FakeApi.empty_all:
                self.all_data = None
            FakeApi.instances.append(self)

        async def async_update_all(self):
            if self.error:
                raise self.error
            return self.all_data

        async def async_update_fast(self):
            if self.fast_error:
                raise self.fast_error
            return self.fast_data

        def safe_error_summary(self, err):
            return f"summary:{err}"

        async def async_close(self):
            self.closed = True

        @classmethod
        def reset(cls):
            cls.instances.clear()
            cls.error = cls.fast_error = None
            cls.all_data = None
            cls.fast_data = {"fast": True}
            cls.empty_all = cls.empty_fast = False

    repairs_calls = {"create": [], "delete": []}
    repairs = types.ModuleType("zte_init_test.repairs")
    repairs.async_create_auth_issue = lambda hass, entry_id, name: repairs_calls["create"].append(
        (hass, entry_id, name)
    )
    repairs.async_delete_auth_issue = lambda hass, entry_id: repairs_calls["delete"].append(
        (hass, entry_id)
    )

    coordinator = types.ModuleType("zte_init_test.coordinator")
    coordinator.ZteDataUpdateCoordinator = FakeCoordinator

    zte_api = types.ModuleType("zte_init_test.zte_api")
    zte_api.ZteAuthError = ZteAuthError
    zte_api.ZteRouterApi = FakeApi

    device = types.SimpleNamespace(id="device-1")
    registry_calls = []
    device_registry = types.ModuleType("homeassistant.helpers.device_registry")
    device_registry.async_get = lambda hass: types.SimpleNamespace(
        async_get_device=lambda identifiers: (
            device if identifiers == {("zte_5g_router", "entry")} else None
        ),
        async_update_device=lambda device_id, **kwargs: registry_calls.append((device_id, kwargs)),
    )

    ha = types.ModuleType("homeassistant")
    helpers = types.ModuleType("homeassistant.helpers")
    util = types.ModuleType("homeassistant.util")
    ha.helpers = helpers
    ha.util = util
    helpers.device_registry = device_registry
    util.dt = types.SimpleNamespace(utcnow=lambda: datetime.now(UTC))

    symbols = {
        "homeassistant": ha,
        "homeassistant.helpers": helpers,
        "homeassistant.util": util,
        "homeassistant.config_entries": {"ConfigEntry": ConfigEntry},
        "homeassistant.const": {"CONF_HOST": "host", "CONF_PASSWORD": "password"},
        "homeassistant.core": {"HomeAssistant": object},
        "homeassistant.exceptions": {"ConfigEntryAuthFailed": ConfigEntryAuthFailed},
        "homeassistant.helpers.device_registry": device_registry,
        "homeassistant.helpers.config_validation": {
            "config_entry_only_config_schema": lambda domain: lambda config: config
        },
        "homeassistant.helpers.typing": {"ConfigType": dict},
        "homeassistant.helpers.update_coordinator": {
            "DataUpdateCoordinator": object,
            "UpdateFailed": UpdateFailed,
        },
        "homeassistant.util.dt": util.dt,
        "zte_init_test.coordinator": coordinator,
        "zte_init_test.repairs": repairs,
        "zte_init_test.zte_api": zte_api,
    }
    modules = {}
    for name, attributes in symbols.items():
        module = types.ModuleType(name) if isinstance(attributes, dict) else attributes
        if isinstance(attributes, dict):
            module.__dict__.update(attributes)
        modules[name] = module

    for modname, filename in (
        ("const", "const.py"),
        ("identity", "identity.py"),
        ("sms_events", "sms_events.py"),
    ):
        spec = importlib.util.spec_from_file_location(f"zte_init_test.{modname}", ROOT / filename)
        module = importlib.util.module_from_spec(spec)
        modules[spec.name] = module
        with patch.dict(sys.modules, modules):
            spec.loader.exec_module(module)

    spec = importlib.util.spec_from_file_location("zte_init_test", ROOT / "__init__.py")
    package = importlib.util.module_from_spec(spec)
    modules["zte_init_test"] = package
    with patch.dict(sys.modules, modules):
        spec.loader.exec_module(package)
    return package, FakeApi, repairs_calls, registry_calls, device


init, Api, repair_calls, registry_calls, device = load_init()


class InitModuleTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        Api.reset()
        repair_calls["create"].clear()
        repair_calls["delete"].clear()
        registry_calls.clear()

    def make_hass_entry(self, data=None, options=None):
        hass = types.SimpleNamespace(
            bus=types.SimpleNamespace(async_fire=Mock()),
            config_entries=types.SimpleNamespace(
                async_forward_entry_setups=AsyncMock(return_value=True),
                async_reload=AsyncMock(),
                async_unload_platforms=AsyncMock(return_value=True),
                async_update_entry=Mock(),
            ),
        )
        entry = types.SimpleNamespace(
            entry_id="entry",
            data=data
            or {
                "name": "Router",
                "host": "https://192.168.0.1",
                "password": "pw",
            },
            options=options or {},
            unique_id="zte_5g_router_https://192.168.0.1",
            runtime_data=None,
            async_on_unload=Mock(),
            add_update_listener=Mock(return_value=lambda: None),
        )
        return hass, entry

    async def test_setup_is_noop(self):
        hass, _ = self.make_hass_entry()
        self.assertTrue(await init.async_setup(hass, {}))

    async def test_successful_setup_wires_entities_and_clears_repair(self):
        hass, entry = self.make_hass_entry()
        self.assertTrue(await init.async_setup_entry(hass, entry))
        api = Api.instances[0]
        self.assertEqual(api.kwargs["base_url"], "https://192.168.0.1")
        self.assertEqual(api.kwargs["password"], "pw")
        self.assertEqual(entry.runtime_data.name, "Router")
        self.assertEqual(
            entry.runtime_data.coordinator.data["common_config"]["wa_inner_version"],
            "V1.0",
        )
        self.assertEqual(entry.runtime_data.coordinator_fast.data, {"fast": True})
        self.assertEqual(entry.runtime_data.coordinator.update_interval, timedelta(seconds=60))
        self.assertEqual(entry.runtime_data.coordinator_fast.update_interval, timedelta(seconds=5))
        hass.config_entries.async_forward_entry_setups.assert_awaited_once_with(
            entry, init.PLATFORMS
        )
        self.assertEqual(repair_calls["delete"], [(hass, "entry")])
        self.assertEqual(registry_calls, [("device-1", {"sw_version": "V1.0"})])
        self.assertFalse(api.closed)

    async def test_credentials_can_be_overridden_by_options(self):
        hass, entry = self.make_hass_entry(options={"host": "https://10.0.0.1", "password": "new"})
        await init.async_setup_entry(hass, entry)
        self.assertEqual(Api.instances[0].kwargs["base_url"], "https://10.0.0.1")
        self.assertEqual(Api.instances[0].kwargs["password"], "new")

    async def test_first_poll_records_inbox_without_firing_events(self):
        hass, entry = self.make_hass_entry()
        await init.async_setup_entry(hass, entry)
        self.assertEqual(hass.bus.async_fire.call_count, 0)

    async def test_new_sms_is_fired_as_event(self):
        hass, entry = self.make_hass_entry()
        await init.async_setup_entry(hass, entry)
        store = entry.runtime_data
        data = {
            "sms": {
                "messages": [
                    {
                        "id": "2",
                        "mem_store": "SM",
                        "date": "2026-01-02 10:00",
                        "tag": "1",
                        "number": "+43123456789",
                        "content_decoded": "Second",
                    }
                ]
            }
        }
        init._fire_sms_events(hass, entry, store, data)
        hass.bus.async_fire.assert_called_once()
        event_name, payload = hass.bus.async_fire.call_args.args
        self.assertEqual(event_name, "zte_5g_router_sms_received")
        self.assertEqual(payload["entry_id"], "entry")
        self.assertEqual(payload["text"], "Second")
        self.assertEqual(payload["number"], "+43123456789")

    async def test_paused_poll_reuses_last_snapshot(self):
        hass, entry = self.make_hass_entry()
        await init.async_setup_entry(hass, entry)
        store = entry.runtime_data
        store.pause_until = datetime.now(UTC) + timedelta(minutes=5)
        self.assertEqual(await store.coordinator.update_method(), store.coordinator.data)
        self.assertEqual(await store.coordinator_fast.update_method(), store.coordinator_fast.data)

    async def test_auth_failure_raises_repair_and_closes_api(self):
        Api.error = init.ZteAuthError("bad password")
        hass, entry = self.make_hass_entry()
        with self.assertRaises(init.ConfigEntryAuthFailed):
            await init.async_setup_entry(hass, entry)
        self.assertEqual(len(repair_calls["create"]), 1)
        self.assertEqual(repair_calls["create"][0][1:], ("entry", "Router"))
        self.assertTrue(Api.instances[0].closed)
        hass.config_entries.async_forward_entry_setups.assert_not_awaited()

    async def test_fast_auth_failure_raises_repair(self):
        Api.fast_error = init.ZteAuthError("bad password")
        hass, entry = self.make_hass_entry()
        with self.assertRaises(init.ConfigEntryAuthFailed):
            await init.async_setup_entry(hass, entry)
        self.assertEqual(len(repair_calls["create"]), 1)
        self.assertTrue(Api.instances[0].closed)

    async def test_empty_payload_and_unexpected_error_become_update_failed(self):
        Api.empty_all = True
        hass, entry = self.make_hass_entry()
        with self.assertRaises(init.UpdateFailed):
            await init.async_setup_entry(hass, entry)
        self.assertTrue(Api.instances[0].closed)

        Api.reset()
        Api.error = RuntimeError("boom")
        hass, entry = self.make_hass_entry()
        with self.assertRaises(init.UpdateFailed):
            await init.async_setup_entry(hass, entry)
        self.assertTrue(Api.instances[0].closed)

        Api.reset()
        Api.empty_fast = True
        hass, entry = self.make_hass_entry()
        with self.assertRaises(init.UpdateFailed):
            await init.async_setup_entry(hass, entry)
        self.assertTrue(Api.instances[0].closed)

        Api.reset()
        Api.fast_error = RuntimeError("boom")
        hass, entry = self.make_hass_entry()
        with self.assertRaises(init.UpdateFailed):
            await init.async_setup_entry(hass, entry)
        self.assertTrue(Api.instances[0].closed)

    async def test_legacy_unique_id_is_migrated(self):
        hass, entry = self.make_hass_entry()
        init._async_migrate_entry_identity(
            hass, entry, {"device": {"wlan_mac_address": "00:11:22:33:44:55"}}
        )
        hass.config_entries.async_update_entry.assert_called_once_with(
            entry, unique_id="zte_5g_router_00:11:22:33:44:55"
        )
        hass.config_entries.async_update_entry.reset_mock()
        init._async_migrate_entry_identity(hass, entry, {})
        hass.config_entries.async_update_entry.assert_not_called()

    async def test_unload_and_reload_listener(self):
        hass, entry = self.make_hass_entry()
        await init.async_setup_entry(hass, entry)
        api = Api.instances[0]
        self.assertTrue(await init.async_unload_entry(hass, entry))
        self.assertTrue(api.closed)

        api.closed = False
        hass.config_entries.async_unload_platforms.return_value = False
        self.assertFalse(await init.async_unload_entry(hass, entry))
        self.assertFalse(api.closed)

        await init._async_update_listener(hass, entry)
        hass.config_entries.async_reload.assert_awaited_once_with("entry")


if __name__ == "__main__":
    unittest.main()
