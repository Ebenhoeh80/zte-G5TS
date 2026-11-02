"""Config/options schema regressions using real voluptuous validation."""
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

import voluptuous as vol


ROOT = Path(__file__).resolve().parents[1] / "custom_components/zte_ng_router"


def load_flow():
    class Flow:
        def __init_subclass__(cls, **kwargs):
            pass

        async def async_set_unique_id(self, unique_id):
            self.unique_id = unique_id

        def _abort_if_unique_id_configured(self):
            pass

        def async_create_entry(self, **kwargs):
            return {"type": "create_entry", **kwargs}

        def async_show_form(self, **kwargs):
            return {"type": "form", **kwargs}

    entries = types.ModuleType("homeassistant.config_entries")
    entries.ConfigFlow = Flow
    entries.OptionsFlow = Flow
    entries.ConfigEntry = object
    ha = types.ModuleType("homeassistant")
    ha.config_entries = entries
    const = types.ModuleType("homeassistant.const")
    const.CONF_HOST = "host"
    const.CONF_PASSWORD = "password"
    core = types.ModuleType("homeassistant.core")
    core.callback = lambda f: f
    package = types.ModuleType("zte_config_test")
    package.__path__ = [str(ROOT)]
    spec = importlib.util.spec_from_file_location("zte_config_test.config_flow", ROOT / "config_flow.py")
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"homeassistant": ha, "homeassistant.config_entries": entries,
                                 "homeassistant.const": const, "homeassistant.core": core,
                                 "zte_config_test": package, spec.name: module}):
        spec.loader.exec_module(module)
    return module


flow = load_flow()


class TrackingConfigTests(unittest.IsolatedAsyncioTestCase):
    async def test_initial_schema_defaults_to_opt_out_and_persists_opt_in(self):
        config = flow.ZteNgRouterConfigFlow()
        form = await config.async_step_user()
        values = form["data_schema"]({"name": "Router", "host": "https://192.0.2.1", "password": "test"})
        self.assertFalse(values["track_wifi_clients"])
        self.assertTrue(values["verify_tls"])
        self.assertFalse(values["allow_insecure_http"])
        self.assertEqual(values["host"], "https://192.0.2.1")
        self.assertEqual(values["client_consider_home"], 180)
        values.update(track_wifi_clients=True, client_consider_home=120)
        result = await config.async_step_user(values)
        self.assertTrue(result["data"]["track_wifi_clients"])
        self.assertTrue(result["data"]["verify_tls"])
        self.assertEqual(result["data"]["client_consider_home"], 120)

    async def test_http_requires_explicit_opt_in(self):
        config = flow.ZteNgRouterConfigFlow()
        form = await config.async_step_user()
        values = form["data_schema"]({
            "name": "Router",
            "host": "http://192.0.2.1",
            "password": "test",
        })

        rejected = await config.async_step_user(values)
        self.assertEqual(rejected["errors"]["base"], "insecure_http")

        values["allow_insecure_http"] = True
        accepted = await config.async_step_user(values)
        self.assertEqual(accepted["data"]["host"], "http://192.0.2.1")
        self.assertTrue(accepted["data"]["allow_insecure_http"])

    async def test_router_url_rejects_non_origin_and_embedded_credentials(self):
        for value in (
            "192.0.2.1",
            "ftp://192.0.2.1",
            "https://192.0.2.1/path",
            "https://192.0.2.1/?token=secret",
            "https://user:password@192.0.2.1",
        ):
            with self.subTest(host=value):
                normalized, error = flow._validate_router_url(
                    value,
                    allow_insecure_http=True,
                )
                self.assertIsNone(normalized)
                self.assertEqual(error, "invalid_host")

    async def test_options_preserve_credentials_and_existing_choices(self):
        entry = types.SimpleNamespace(data={"host": "http://192.0.2.1", "password": "original",
                                           "track_wifi_clients": True, "client_consider_home": 240},
                                      options={"password": "override", "other_option": "keep"})
        options = flow.ZteNgRouterOptionsFlow(entry)
        form = await options.async_step_init()
        values = form["data_schema"]({})
        self.assertTrue(values["track_wifi_clients"])
        self.assertTrue(values["allow_insecure_http"])
        self.assertEqual(values["client_consider_home"], 240)
        values["track_wifi_clients"] = False
        result = await options.async_step_init(values)
        self.assertFalse(result["data"]["track_wifi_clients"])
        self.assertTrue(result["data"]["allow_insecure_http"])
        self.assertEqual(result["data"]["password"], "override")
        self.assertEqual(result["data"]["other_option"], "keep")

    async def test_grace_bounds_and_translations(self):
        form = await flow.ZteNgRouterOptionsFlow(types.SimpleNamespace(data={}, options={})).async_step_init()
        for invalid in (-1, 3601, "invalid"):
            with self.assertRaises(vol.Invalid):
                form["data_schema"]({"client_consider_home": invalid})
        for valid in (0, 180, 3600):
            self.assertEqual(form["data_schema"]({"client_consider_home": valid})["client_consider_home"], valid)
        for path in (ROOT / "strings.json", ROOT / "translations/en.json", ROOT / "translations/de.json"):
            translations = json.loads(path.read_text())
            for section, step in (("config", "user"), ("options", "init")):
                labels = translations[section]["step"][step]["data"]
                self.assertIn("track_wifi_clients", labels)
                self.assertIn("client_consider_home", labels)
                self.assertIn("verify_tls", labels)
                self.assertIn("allow_insecure_http", labels)


if __name__ == "__main__":
    unittest.main()
