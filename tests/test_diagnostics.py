"""Diagnostics must expose connection state without exporting router secrets."""

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


ROOT = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "zte_5g_router"
)


def load_diagnostics():
    def redact(value, keys):
        if isinstance(value, dict):
            return {
                key: "**REDACTED**" if key in keys else redact(item, keys)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [redact(item, keys) for item in value]
        return value

    diagnostics_component = types.ModuleType("homeassistant.components.diagnostics")
    diagnostics_component.async_redact_data = redact
    components = types.ModuleType("homeassistant.components")
    components.diagnostics = diagnostics_component
    const = types.ModuleType("homeassistant.const")
    const.CONF_PASSWORD = "password"
    core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = object
    homeassistant = types.ModuleType("homeassistant")
    homeassistant.components = components

    package = types.ModuleType("zte_diagnostics_test")
    package.__path__ = [str(ROOT)]
    spec = importlib.util.spec_from_file_location(
        "zte_diagnostics_test.diagnostics",
        ROOT / "diagnostics.py",
    )
    module = importlib.util.module_from_spec(spec)
    with patch.dict(
        sys.modules,
        {
            "homeassistant": homeassistant,
            "homeassistant.components": components,
            "homeassistant.components.diagnostics": diagnostics_component,
            "homeassistant.const": const,
            "homeassistant.core": core,
            "zte_diagnostics_test": package,
            spec.name: module,
        },
    ):
        spec.loader.exec_module(module)
    return module


diagnostics = load_diagnostics()


class DiagnosticsTests(unittest.IsolatedAsyncioTestCase):
    async def test_config_secrets_are_redacted_and_raw_router_data_is_omitted(self):
        class Coordinator:
            data = {
                "common_config": {
                    "model": "G5TS",
                    "wa_inner_version": "firmware-test",
                },
                "sms": {"content": "private message"},
                "network_clients": {"AA:BB:CC:DD:EE:FF": {"hostname": "private"}},
            }
            last_update_success = True

        class Api:
            login_method = "ubus"
            is_logged_in = True

        entry = types.SimpleNamespace(
            data={"host": "https://192.0.2.1", "password": "do-not-export"},
            options={"token": "do-not-export"},
            runtime_data=types.SimpleNamespace(
                coordinator=Coordinator(),
                coordinator_fast=Coordinator(),
                api=Api(),
            ),
        )

        result = await diagnostics.async_get_config_entry_diagnostics(None, entry)

        self.assertEqual(result["config"]["data"]["password"], "**REDACTED**")
        self.assertEqual(result["config"]["options"]["token"], "**REDACTED**")
        self.assertEqual(result["connection"]["login_method"], "ubus")
        self.assertEqual(result["connection"]["firmware"]["model"], "G5TS")
        self.assertNotIn("sms", result)
        self.assertNotIn("network_clients", result)


if __name__ == "__main__":
    unittest.main()
