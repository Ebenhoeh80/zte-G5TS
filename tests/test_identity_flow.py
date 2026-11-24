"""Config entry identity and reconfigure flow regressions."""

from types import SimpleNamespace
import unittest

from test_tracking_config import load_flow

# A fresh module instance keeps these probes isolated from test_tracking_config.
flow = load_flow()

USER_INPUT = {
    "name": "Router",
    "host": "https://192.0.2.1",
    "password": "pw",
    "verify_tls": True,
    "scan_interval": 60,
    "fast_scan_interval": 5,
}


class ProbeApi:
    """Router stand-in that reports a fixed device identifier."""

    identifier = "aa:bb:cc:dd:ee:ff"
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        ProbeApi.instances.append(self)

    async def async_login(self):
        pass

    async def async_call_ubus(self, call):
        assert call["method"] == "get_sim_info"
        return {"success": True, "data": {"wlan_mac_address": self.identifier}}

    async def async_close(self):
        pass

    def safe_error_summary(self, exc):
        return str(exc)


flow.ZteRouterApi = ProbeApi


class ConfigFlowIdentityTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        ProbeApi.instances.clear()
        ProbeApi.identifier = "aa:bb:cc:dd:ee:ff"

    def _flow(self, entry=None):
        handler = flow.ZteNgRouterConfigFlow()
        handler.hass = SimpleNamespace()
        handler.async_show_form = lambda **kwargs: {"type": "form", **kwargs}
        handler.async_update_reload_and_abort = lambda entry, **kwargs: {
            "type": "abort",
            "entry": entry,
            **kwargs,
        }
        if entry is not None:
            handler._get_reconfigure_entry = lambda: entry
        return handler

    async def test_user_step_sets_mac_based_unique_id(self):
        handler = self._flow()
        result = await handler.async_step_user(dict(USER_INPUT))
        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(handler.unique_id, "zte_5g_router_aa:bb:cc:dd:ee:ff")
        self.assertTrue(ProbeApi.instances[0].kwargs["track_clients"] is False)

    async def test_user_step_falls_back_to_url_when_mac_is_missing(self):
        ProbeApi.identifier = "unavailable"
        handler = self._flow()
        await handler.async_step_user(dict(USER_INPUT))
        self.assertEqual(handler.unique_id, "zte_5g_router_https://192.0.2.1")

    async def test_reconfigure_accepts_same_router_at_a_new_address(self):
        entry = SimpleNamespace(
            unique_id="zte_5g_router_aa:bb:cc:dd:ee:ff",
            data={"host": "https://192.0.2.1", "password": "old"},
            options={"scan_interval": 60},
            title="Router",
        )
        handler = self._flow(entry)
        result = await handler.async_step_reconfigure(
            {
                "host": "https://192.0.2.2",
                "password": "",
                "verify_tls": True,
                "tls_fingerprint": "",
                "allow_insecure_http": False,
            }
        )
        self.assertEqual(result["type"], "abort")
        self.assertEqual(result["options"]["host"], "https://192.0.2.2")
        self.assertEqual(result["data"]["password"], "old")
        self.assertEqual(result["options"]["scan_interval"], 60)

    async def test_reconfigure_rejects_a_different_router(self):
        entry = SimpleNamespace(
            unique_id="zte_5g_router_aa:bb:cc:dd:ee:ff",
            data={"host": "https://192.0.2.1", "password": "old"},
            options={},
            title="Router",
        )
        ProbeApi.identifier = "11:22:33:44:55:66"
        handler = self._flow(entry)
        result = await handler.async_step_reconfigure(
            {
                "host": "https://192.0.2.2",
                "password": "",
                "verify_tls": True,
                "tls_fingerprint": "",
                "allow_insecure_http": False,
            }
        )
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["errors"], {"base": "wrong_device"})


if __name__ == "__main__":
    unittest.main()
