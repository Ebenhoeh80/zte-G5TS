"""Authentication failure diagnostics using mocked responses only."""

import importlib.util
import hashlib
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import AsyncMock, Mock, patch


def load_api():
    aiohttp = types.ModuleType("aiohttp")
    aiohttp.ClientError = Exception
    aiohttp.ClientSession = object
    aiohttp.CookieJar = object
    core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = object
    path = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "zte_5g_router"
        / "zte_api.py"
    )
    spec = importlib.util.spec_from_file_location("zte_login_test_api", path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"aiohttp": aiohttp, "homeassistant.core": core}):
        spec.loader.exec_module(module)
    return module


router_module = load_api()
ZteRouterApi = router_module.ZteRouterApi


def api():
    router = ZteRouterApi(session=object())
    router._logged_in = False
    return router


class LoginDiagnosticTests(unittest.IsolatedAsyncioTestCase):
    async def test_http_requires_an_explicit_opt_in(self):
        with self.assertRaisesRegex(ValueError, "Unencrypted HTTP is disabled"):
            ZteRouterApi(base_url="http://192.0.2.1")

    async def test_http_can_be_enabled_explicitly_for_legacy_routers(self):
        router = ZteRouterApi(
            base_url="http://192.0.2.1",
            allow_insecure_http=True,
            session=object(),
        )
        self.assertTrue(router.allow_insecure_http)

    async def test_ubus_rpc_error_is_not_reported_as_missing_salt(self):
        router = api()
        router.async_call_ubus = AsyncMock(
            return_value={
                "success": False,
                "data": None,
                "error": {
                    "message": "connection refused",
                    "kind": "transport",
                },
            }
        )

        with self.assertRaisesRegex(RuntimeError, "connection refused"):
            await router._async_ubus_login()

    async def test_successful_ubus_response_without_salt_is_unsupported(self):
        router = api()
        router.async_call_ubus = AsyncMock(
            return_value={"success": True, "data": {"login_fail_num": 5}}
        )

        with self.assertRaisesRegex(RuntimeError, "recognized salt"):
            await router._async_ubus_login()

    async def test_ubus_login_uses_salt_challenge_and_never_logs_session_id(self):
        router = api()
        salt = "router-salt"
        session_id = "private-router-session"
        router.async_call_ubus = AsyncMock(side_effect=[
            {"success": True, "data": {"zte_web_sault": salt}},
            {"success": True, "data": {"ubus_rpc_session": session_id}},
        ])
        router._async_setup_http_encryption = AsyncMock()

        with self.assertLogs("zte_login_test_api", level="DEBUG") as captured:
            await router._async_ubus_login()

        password_hash = hashlib.sha256(router.password.encode()).hexdigest().upper()
        expected = hashlib.sha256(
            (password_hash + salt).encode()
        ).hexdigest().upper()
        login_call = router.async_call_ubus.call_args_list[1]
        self.assertEqual(login_call.args[0]["params"]["password"], expected)
        self.assertEqual(router._session_id, session_id)
        self.assertNotIn(session_id, "\n".join(captured.output))

    async def test_goform_login_uses_ld_cookie_session_and_uppercase_hash(self):
        router = api()
        router._async_goform_init_session = AsyncMock()
        router._async_goform_get = AsyncMock(return_value={"LD": "router-nonce"})
        router._async_goform_set = AsyncMock(return_value={"result": 0})

        await router._async_goform_login()

        password_hash = hashlib.sha256(router.password.encode()).hexdigest().upper()
        expected = hashlib.sha256(
            (password_hash + "router-nonce").encode()
        ).hexdigest().upper()
        router._async_goform_init_session.assert_awaited_once_with(raise_errors=True)
        router._async_goform_get.assert_awaited_once_with("LD", raise_errors=True)
        self.assertEqual(
            router._async_goform_set.call_args.args[0]["password"],
            expected,
        )
        self.assertTrue(router.is_logged_in)
        self.assertEqual(router.login_method, "goform")

    async def test_ubus_authentication_error_does_not_trigger_goform_fallback(self):
        router = api()
        router._async_ubus_login = AsyncMock(
            side_effect=RuntimeError("UBUS login rejected")
        )
        router._async_goform_login = AsyncMock()

        with self.assertRaisesRegex(RuntimeError, "UBUS login rejected"):
            await router.async_login()

        router._async_goform_login.assert_not_awaited()

    async def test_unsupported_ubus_protocol_uses_goform_fallback(self):
        router = api()
        router._async_goform_login = AsyncMock()
        router._async_ubus_login = AsyncMock(
            side_effect=router_module.UnsupportedLoginProtocol(
                "web_login_info response did not contain a recognized salt"
            )
        )

        await router.async_login()

        router._async_goform_login.assert_awaited_once()

    async def test_goform_login_uses_strict_challenge_requests(self):
        router = api()
        router._async_goform_init_session = AsyncMock()
        router._async_goform_get = AsyncMock(
            side_effect=RuntimeError("GoForm GET LD failed: response was HTML")
        )

        with self.assertRaisesRegex(RuntimeError, "response was HTML"):
            await router._async_goform_login()

        router._async_goform_init_session.assert_awaited_once_with(raise_errors=True)
        router._async_goform_get.assert_awaited_once_with("LD", raise_errors=True)

    async def test_ubus_batch_debug_logs_never_include_router_payloads(self):
        class FakeResponse:
            status = 200

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

            def raise_for_status(self):
                return None

            async def text(self):
                return json.dumps(
                    [{"id": 1, "result": [0, {"wifi_key": "do-not-log-this"}]}]
                )

        router = api()
        router._session_id = "do-not-log-session"
        router._logged_in = True
        router._session = Mock()
        router._session.post.return_value = FakeResponse()

        with self.assertLogs("zte_login_test_api", level="DEBUG") as captured:
            await router.async_call_ubus_batch(
                [{"service": "uci", "method": "get", "params": {"config": "wireless"}}]
            )

        output = "\n".join(captured.output)
        self.assertNotIn("do-not-log-this", output)
        self.assertNotIn("do-not-log-session", output)


if __name__ == "__main__":
    unittest.main()
