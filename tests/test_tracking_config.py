"""Config/options schema regressions using real voluptuous validation.

The config flow is loaded with lightweight stand-ins for ``homeassistant``,
``aiohttp`` and the heavy ``zte_api`` module, so these tests exercise the real
flow logic (validation, login-error mapping, reauth) without a running Home
Assistant or a real router.
"""
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

import voluptuous as vol


ROOT = Path(__file__).resolve().parents[1] / "custom_components/zte_5g_router"


class MockRouterApi:
    """Stand-in for ZteRouterApi; ``login_exc`` controls async_login()."""

    login_exc: Exception | None = None

    def __init__(self, **kwargs):
        pass

    async def async_login(self):
        if MockRouterApi.login_exc is not None:
            raise MockRouterApi.login_exc

    async def async_close(self):
        pass

    def safe_error_summary(self, exc):
        return str(exc)


class MockClientError(Exception):
    """Stand-in for aiohttp.ClientError (maps to cannot_connect)."""


def load_flow():
    class Flow:
        hass = None
        context: dict = {}

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

        def async_update_reload_and_abort(self, entry, **kwargs):
            return {"type": "abort", "entry": entry, **kwargs}

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
    core.HomeAssistant = object
    aiohttp_mod = types.ModuleType("aiohttp")
    aiohttp_mod.ClientError = MockClientError
    zte_api_mod = types.ModuleType("zte_config_test.zte_api")
    zte_api_mod.ZteRouterApi = MockRouterApi
    package = types.ModuleType("zte_config_test")
    package.__path__ = [str(ROOT)]
    spec = importlib.util.spec_from_file_location("zte_config_test.config_flow", ROOT / "config_flow.py")
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"homeassistant": ha, "homeassistant.config_entries": entries,
                                 "homeassistant.const": const, "homeassistant.core": core,
                                 "aiohttp": aiohttp_mod,
                                 "zte_config_test": package, spec.name: module,
                                 "zte_config_test.zte_api": zte_api_mod}):
        spec.loader.exec_module(module)
    return module


flow = load_flow()


def make_options_flow(entry):
    """Instantiate the options flow and attach the entry (HA 2024.11+ style)."""
    handler = flow.ZteNgRouterOptionsFlow()
    handler.config_entry = entry
    return handler


class TrackingConfigTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        MockRouterApi.login_exc = None

    async def test_initial_schema_defaults_to_opt_out_and_persists_opt_in(self):
        config = flow.ZteNgRouterConfigFlow()
        form = await config.async_step_user()
        values = form["data_schema"]({"name": "Router", "host": "https://192.0.2.1", "password": "test"})
        self.assertFalse(values["track_wifi_clients"])
        self.assertTrue(values["verify_tls"])
        self.assertFalse(values["allow_insecure_http"])
        self.assertEqual(values["host"], "https://192.0.2.1")
        self.assertEqual(values["tls_fingerprint"], "")
        self.assertEqual(values["client_consider_home"], 180)
        values.update(track_wifi_clients=True, client_consider_home=120)
        result = await config.async_step_user(values)
        self.assertEqual(result["type"], "create_entry")
        self.assertTrue(result["data"]["track_wifi_clients"])
        self.assertTrue(result["data"]["verify_tls"])
        self.assertEqual(result["data"]["client_consider_home"], 120)
        self.assertEqual(result["data"]["tls_fingerprint"], "")

    async def test_tls_fingerprint_is_validated_and_normalized(self):
        fingerprint = "AA" * 32
        colon_separated = ":".join(
            fingerprint[index:index + 2] for index in range(0, 64, 2)
        )
        normalized, error = flow._validate_tls_fingerprint(colon_separated)
        self.assertEqual(normalized, fingerprint.lower())
        self.assertIsNone(error)

        normalized, error = flow._validate_tls_fingerprint("not-a-fingerprint")
        self.assertIsNone(normalized)
        self.assertEqual(error, "invalid_tls_fingerprint")

        config = flow.ZteNgRouterConfigFlow()
        form = await config.async_step_user()
        values = form["data_schema"]({
            "name": "Router",
            "host": "https://192.0.2.1",
            "password": "test",
            "tls_fingerprint": fingerprint,
        })
        result = await config.async_step_user(values)
        self.assertEqual(result["data"]["tls_fingerprint"], fingerprint.lower())

        http_config = flow.ZteNgRouterConfigFlow()
        http_values = form["data_schema"]({
            "name": "Router",
            "host": "http://192.0.2.1",
            "password": "test",
            "allow_insecure_http": True,
            "tls_fingerprint": fingerprint,
        })
        rejected = await http_config.async_step_user(http_values)
        self.assertEqual(rejected["errors"]["base"], "tls_fingerprint_requires_https")

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

    async def test_login_error_is_mapped_to_cannot_connect_and_invalid_auth(self):
        form = await flow.ZteNgRouterConfigFlow().async_step_user()

        MockRouterApi.login_exc = MockClientError("no route")
        cfg = flow.ZteNgRouterConfigFlow()
        values = form["data_schema"]({"name": "R", "host": "https://192.0.2.1", "password": "x"})
        rejected = await cfg.async_step_user(values)
        self.assertEqual(rejected["errors"]["base"], "cannot_connect")

        MockRouterApi.login_exc = RuntimeError("401 rejected")
        cfg = flow.ZteNgRouterConfigFlow()
        rejected = await cfg.async_step_user(values)
        self.assertEqual(rejected["errors"]["base"], "invalid_auth")

        MockRouterApi.login_exc = None
        cfg = flow.ZteNgRouterConfigFlow()
        accepted = await cfg.async_step_user(values)
        self.assertEqual(accepted["type"], "create_entry")

    async def test_reauth_confirm_verifies_password(self):
        entry = types.SimpleNamespace(
            title="Router",
            data={"host": "https://192.0.2.1", "password": "old"},
            options={},
        )
        config = flow.ZteNgRouterConfigFlow()
        config.context = {"entry_id": "abc"}
        config.hass = types.SimpleNamespace(
            config_entries=types.SimpleNamespace(async_get_entry=lambda eid: entry)
        )

        MockRouterApi.login_exc = RuntimeError("bad password")
        rejected = await config.async_step_reauth_confirm({"password": "wrong"})
        self.assertEqual(rejected["errors"]["base"], "invalid_auth")

        MockRouterApi.login_exc = None
        result = await config.async_step_reauth_confirm({"password": "new"})
        self.assertEqual(result["type"], "abort")
        self.assertEqual(result["data"]["password"], "new")

    async def test_options_preserve_credentials_and_existing_choices(self):
        entry = types.SimpleNamespace(data={"host": "http://192.0.2.1", "password": "original",
                                           "track_wifi_clients": True, "client_consider_home": 240},
                                      options={"password": "override", "other_option": "keep"})
        options = make_options_flow(entry)
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
        form = await make_options_flow(types.SimpleNamespace(data={}, options={})).async_step_init()
        for invalid in (-1, 3601, "invalid"):
            with self.assertRaises(vol.Invalid):
                form["data_schema"]({"client_consider_home": invalid})
        for valid in (0, 180, 3600):
            self.assertEqual(form["data_schema"]({"client_consider_home": valid})["client_consider_home"], valid)
        for path in (ROOT / "strings.json", ROOT / "translations/en.json", ROOT / "translations/de.json"):
            translations = json.loads(path.read_text(encoding="utf-8"))
            for section, step in (("config", "user"), ("options", "init")):
                labels = translations[section]["step"][step]["data"]
                self.assertIn("track_wifi_clients", labels)
                self.assertIn("client_consider_home", labels)
                self.assertIn("verify_tls", labels)
                self.assertIn("tls_fingerprint", labels)
                self.assertIn("allow_insecure_http", labels)
            # Reauth step and its success abort must exist in every locale
            self.assertIn("reauth_confirm", translations["config"]["step"])
            self.assertIn("reauth_successful", translations["config"]["abort"])


if __name__ == "__main__":
    unittest.main()
