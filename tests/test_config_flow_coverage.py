"""Targeted coverage for config-flow validation, error and abort paths.

Uses the lightweight Home Assistant/aiohttp/zte_api stand-ins from
``test_tracking_config.load_flow`` so no real router or HA instance is needed.
"""

from types import SimpleNamespace
import unittest

from test_tracking_config import load_flow

# A fresh module instance keeps these probes isolated from the other flow tests.
flow = load_flow()

DEFAULT_IDENTIFIER = "aa:bb:cc:dd:ee:ff"
FINGERPRINT = "aa" * 32

USER_INPUT = {
    "name": "Router",
    "host": "https://192.0.2.1",
    "password": "pw",
    "verify_tls": True,
    "scan_interval": 60,
    "fast_scan_interval": 5,
}

RECONFIGURE_INPUT = {
    "host": "https://192.0.2.2",
    "password": "",
    "verify_tls": True,
    "tls_fingerprint": "",
    "allow_insecure_http": False,
}

OPTIONS_INPUT = {
    "host": "https://192.0.2.1",
    "password": "",
    "verify_tls": True,
    "tls_fingerprint": "",
    "allow_insecure_http": False,
    "scan_interval": 60,
    "fast_scan_interval": 5,
}


class FakeApi:
    """Router stand-in with controllable login failures and device identity."""

    login_exc: Exception | None = None
    identifier: str | None = DEFAULT_IDENTIFIER
    instances: list = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        FakeApi.instances.append(self)

    async def async_login(self):
        if FakeApi.login_exc is not None:
            raise FakeApi.login_exc

    async def async_call_ubus(self, call):
        return {"success": True, "data": {"wlan_mac_address": FakeApi.identifier}}

    async def async_close(self):
        pass

    def safe_error_summary(self, exc):
        return str(exc)


flow.ZteRouterApi = FakeApi


class ConfigFlowCoverageTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        FakeApi.login_exc = None
        FakeApi.identifier = DEFAULT_IDENTIFIER
        FakeApi.instances.clear()

    def _config_flow(self):
        handler = flow.ZteNgRouterConfigFlow()
        handler.hass = SimpleNamespace()
        return handler

    def _entry(self, **overrides):
        values = {
            "unique_id": f"zte_5g_router_{DEFAULT_IDENTIFIER}",
            "data": {"host": "https://192.0.2.1", "password": "old"},
            "options": {},
            "title": "Router",
        }
        values.update(overrides)
        return SimpleNamespace(**values)

    def _reconfigure_flow(self, entry):
        handler = self._config_flow()
        handler._get_reconfigure_entry = lambda: entry
        return handler

    def _options_flow(self, entry):
        handler = flow.ZteNgRouterOptionsFlow()
        handler.hass = SimpleNamespace()
        handler.config_entry = entry
        return handler

    async def test_url_validation_rejects_invalid_port(self):
        normalized, error = flow._validate_router_url(
            "https://192.0.2.1:notaport", allow_insecure_http=True
        )
        self.assertIsNone(normalized)
        self.assertEqual(error, "invalid_host")

    async def test_uses_http_falls_back_on_unparseable_url(self):
        self.assertFalse(flow._uses_http("http://[::1"))

    async def test_user_step_reports_fingerprint_and_interval_errors(self):
        cases = (
            ({"tls_fingerprint": "bad"}, "invalid_tls_fingerprint"),
            ({"scan_interval": 4}, "invalid_scan_interval"),
            ({"fast_scan_interval": 1}, "invalid_fast_scan_interval"),
        )
        for changes, expected in cases:
            with self.subTest(expected=expected):
                result = await self._config_flow().async_step_user(dict(USER_INPUT, **changes))
                self.assertEqual(result["errors"], {"base": expected})

    async def test_reauth_step_delegates_to_confirm(self):
        entry = self._entry(options={"password": "stale"})
        handler = self._config_flow()
        handler.context = {"entry_id": "abc"}
        handler.hass = SimpleNamespace(
            config_entries=SimpleNamespace(async_get_entry=lambda eid: entry)
        )

        result = await handler.async_step_reauth({"password": "new"})

        # The entry point delegates to the confirm step, which asks for the
        # password again before attempting a login.
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "reauth_confirm")
        self.assertEqual(result["description_placeholders"], {"name": "Router"})

    async def test_reconfigure_reports_validation_and_login_errors(self):
        cases = (
            ({"host": "not a url"}, "invalid_host"),
            ({"tls_fingerprint": "bad"}, "invalid_tls_fingerprint"),
            (
                {
                    "host": "http://192.0.2.2",
                    "allow_insecure_http": True,
                    "tls_fingerprint": FINGERPRINT,
                },
                "tls_fingerprint_requires_https",
            ),
        )
        for changes, expected in cases:
            with self.subTest(expected=expected):
                handler = self._reconfigure_flow(self._entry())
                result = await handler.async_step_reconfigure(dict(RECONFIGURE_INPUT, **changes))
                self.assertEqual(result["errors"], {"base": expected})

        FakeApi.login_exc = flow.ZteAuthError("bad password")
        handler = self._reconfigure_flow(self._entry())
        rejected = await handler.async_step_reconfigure(dict(RECONFIGURE_INPUT))
        self.assertEqual(rejected["errors"], {"base": "invalid_auth"})

    async def test_reconfigure_stores_a_replacement_password(self):
        handler = self._reconfigure_flow(self._entry(options={"other_option": "keep"}))

        result = await handler.async_step_reconfigure(
            dict(RECONFIGURE_INPUT, password="new-secret")
        )

        self.assertEqual(result["type"], "abort")
        self.assertEqual(result["options"]["password"], "new-secret")
        self.assertEqual(result["options"]["other_option"], "keep")
        self.assertEqual(result["data"]["password"], "new-secret")

    async def test_options_flow_reports_validation_errors(self):
        cases = (
            ({"host": "not a url"}, "invalid_host"),
            ({"tls_fingerprint": "bad"}, "invalid_tls_fingerprint"),
            (
                {
                    "host": "http://192.0.2.1",
                    "allow_insecure_http": True,
                    "tls_fingerprint": FINGERPRINT,
                },
                "tls_fingerprint_requires_https",
            ),
        )
        for changes, expected in cases:
            with self.subTest(expected=expected):
                result = await self._options_flow(self._entry()).async_step_init(
                    dict(OPTIONS_INPUT, **changes)
                )
                self.assertEqual(result["errors"], {"base": expected})

    async def test_options_flow_revalidates_changed_host_and_password(self):
        entry = self._entry()
        changed_host = await self._options_flow(entry).async_step_init(
            dict(OPTIONS_INPUT, host="https://192.0.2.2")
        )
        self.assertEqual(changed_host["type"], "create_entry")
        self.assertEqual(changed_host["data"]["host"], "https://192.0.2.2")

        new_password = await self._options_flow(entry).async_step_init(
            dict(OPTIONS_INPUT, password="new-secret")
        )
        self.assertEqual(new_password["type"], "create_entry")
        self.assertEqual(new_password["data"]["password"], "new-secret")

        FakeApi.login_exc = flow.ZteAuthError("bad password")
        rejected = await self._options_flow(entry).async_step_init(
            dict(OPTIONS_INPUT, host="https://192.0.2.2")
        )
        self.assertEqual(rejected["errors"], {"base": "invalid_auth"})

    async def test_options_flow_handler_is_returned_by_config_flow(self):
        handler = self._config_flow()
        options_flow = handler.async_get_options_flow(self._entry())
        self.assertIsInstance(options_flow, flow.ZteNgRouterOptionsFlow)


if __name__ == "__main__":
    unittest.main()
