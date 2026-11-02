"""Authentication failure diagnostics using mocked responses only."""

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch


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
        / "zte_ng_router"
        / "zte_api.py"
    )
    spec = importlib.util.spec_from_file_location("zte_login_test_api", path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"aiohttp": aiohttp, "homeassistant.core": core}):
        spec.loader.exec_module(module)
    return module.ZteRouterApi


ZteRouterApi = load_api()


def api():
    router = ZteRouterApi(session=object())
    router._logged_in = False
    return router


class LoginDiagnosticTests(unittest.IsolatedAsyncioTestCase):
    async def test_ubus_rpc_error_is_not_reported_as_missing_salt(self):
        router = api()
        router.async_call_ubus = AsyncMock(
            return_value={
                "success": False,
                "data": None,
                "error": {"message": "connection refused"},
            }
        )

        with self.assertRaisesRegex(RuntimeError, "connection refused"):
            await router._async_ubus_login()

    async def test_successful_ubus_response_without_salt_is_specific(self):
        router = api()
        router.async_call_ubus = AsyncMock(
            return_value={"success": True, "data": {"login_fail_num": 5}}
        )

        with self.assertRaisesRegex(RuntimeError, "did not contain zte_web_sault"):
            await router._async_ubus_login()

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


if __name__ == "__main__":
    unittest.main()
