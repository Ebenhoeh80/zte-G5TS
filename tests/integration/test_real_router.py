"""Opt-in tests against real ZTE hardware; never run as mock/unit tests."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from tools.router_probe import probe_scheme
    from tools.router_test_support import (
        load_api_class,
        print_json,
        router_settings,
        safe_api,
        track_api_batches,
    )
    _TOOLS_AVAILABLE = True
except ModuleNotFoundError:
    _TOOLS_AVAILABLE = False


_RUN_LIVE = os.environ.get("RUN_REAL_ROUTER_TESTS") == "1"
_PASSWORD = os.environ.get("ZTEPWD", "")
if not _TOOLS_AVAILABLE:
    _SKIP_REASON = "install aiohttp to run real-router tests"
elif not _RUN_LIVE:
    _SKIP_REASON = "set RUN_REAL_ROUTER_TESTS=1 to enable real-router tests"
elif not _PASSWORD:
    _SKIP_REASON = "set ZTEPWD in the environment; the value is never printed"
else:
    _SKIP_REASON = ""


@unittest.skipIf(bool(_SKIP_REASON), _SKIP_REASON)
class RealRouterTests(unittest.IsolatedAsyncioTestCase):
    """Run only when explicitly enabled and a router password is present."""

    async def asyncSetUp(self) -> None:
        base_url, password, fingerprint = router_settings(require_password=True)
        self.base_url = base_url
        self.fingerprint = fingerprint
        api_class = load_api_class()
        self.api = api_class(
            base_url=base_url,
            password=password,
            verify_tls=True,
            tls_fingerprint=fingerprint,
        )
        self.api_batches = track_api_batches(self.api)

    async def asyncTearDown(self) -> None:
        await self.api.async_close()

    async def test_http_https_status_and_redirect_behavior(self) -> None:
        from urllib.parse import urlsplit

        parsed = urlsplit(self.base_url)
        host = parsed.hostname
        self.assertIsNotNone(host)
        http_origin = os.environ.get("ZTE_HTTP_URL", f"http://{host}").rstrip("/")
        https_origin = os.environ.get("ZTE_HTTPS_URL", self.base_url).rstrip("/")

        results = await asyncio.gather(
            probe_scheme(http_origin, None),
            probe_scheme(https_origin, self.fingerprint),
        )
        print_json(
            {
                "test": "reachability",
                "checks": results,
                "tls_mode": "fingerprint" if self.fingerprint else "system_ca",
            }
        )
        https_result = next(item for item in results if item["scheme"] == "https")
        self.assertTrue(https_result["ok"], "HTTPS router probe failed")

    async def test_login_live_apis_and_session_reauthentication(self) -> None:
        await self.api.async_login()
        self.assertTrue(self.api.is_logged_in)
        self.assertIn(self.api.login_method, {"ubus", "goform"})

        fast_data = await self.api.async_update_fast()
        slow_data = await self.api.async_update_all()
        summary = safe_api(
            {
                "login_method": self.api.login_method,
                "session_established": self.api.is_logged_in,
                "fast_data": fast_data or {},
                "slow_data": slow_data or {},
            }
        )
        print_json({"test": "authenticated_read_only_apis", **summary})
        print_json({"test": "api_method_results", "batches": self.api_batches})
        self.assertIsInstance(fast_data, dict)
        self.assertTrue(
            any(isinstance(slow_data.get(key), dict) for key in ("netinfo", "wan")),
            "router returned no usable network/WAN API data",
        )
        self.assertTrue(self.api.is_logged_in)

        self.api._mark_session_stale()
        refreshed = await self.api.async_update_fast()
        self.assertTrue(self.api.is_logged_in)
        self.assertEqual(self.api.login_method, summary["login_method"])
        self.assertIsInstance(refreshed, dict)
        print_json(
            {
                "test": "session_reauthentication",
                "ok": True,
                "method": self.api.login_method,
                "session_established": self.api.is_logged_in,
            }
        )

    @unittest.skipUnless(
        os.environ.get("ZTE_TEST_GOFORM") == "1",
        "set ZTE_TEST_GOFORM=1 to make one explicit GoForm login attempt",
    )
    async def test_goform_login_when_explicitly_enabled(self) -> None:
        password_posts: list[bool] = []
        original_set = self.api._async_goform_set

        async def record_password_post(*args, **kwargs):
            password_posts.append(True)
            return await original_set(*args, **kwargs)

        self.api._async_goform_set = record_password_post
        try:
            await self.api._async_goform_login()
        except Exception as err:
            summary = self.api.safe_error_summary(err)
            self.assertIn("HTML", summary)
            self.assertFalse(
                password_posts,
                "Do not send credentials when the GoForm endpoint returns HTML.",
            )
            print_json(
                {
                    "test": "goform_capability",
                    "supported": False,
                    "password_sent": False,
                    "failure_summary": summary,
                }
            )
            return
        self.assertTrue(self.api.is_logged_in)
        self.assertEqual(self.api.login_method, "goform")
        print_json(
            {
                "test": "goform_capability",
                "supported": True,
                "session_established": True,
                "password_sent": True,
                "cookies_present": bool(self.api._goform_session.cookie_jar),
            }
        )

    @unittest.skipUnless(
        os.environ.get("ZTE_ROUTER_RESTARTED") == "1",
        "restart the router manually, then set ZTE_ROUTER_RESTARTED=1",
    )
    async def test_reauthentication_after_manual_router_restart(self) -> None:
        await self.api.async_login()
        data = await self.api.async_update_fast()
        self.assertTrue(self.api.is_logged_in)
        self.assertIsInstance(data, dict)
        print_json(
            {
                "test": "manual_router_restart_recovery",
                "ok": True,
                "method": self.api.login_method,
            }
        )
