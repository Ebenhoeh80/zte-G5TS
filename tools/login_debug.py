"""Run one redacted ZTE login attempt against the configured router.

Set ZTEPWD in the process environment. No password is accepted on the command
line or printed. Automatic mode follows the integration's UBUS/GoForm policy;
GoForm can be tested explicitly with --protocol goform.
"""

from __future__ import annotations

import argparse
import asyncio

try:
    from .router_test_support import load_api_class, print_json, router_settings
except ImportError:
    from router_test_support import load_api_class, print_json, router_settings


async def async_main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--protocol",
        choices=("auto", "ubus", "goform"),
        default="auto",
        help="Use the normal protocol selection or make one explicit protocol attempt.",
    )
    args = parser.parse_args()
    try:
        base_url, password, fingerprint = router_settings(require_password=True)
    except RuntimeError as err:
        parser.error(str(err))

    api_class = load_api_class()
    api = api_class(
        base_url=base_url,
        password=password,
        verify_tls=True,
        tls_fingerprint=fingerprint,
    )
    try:
        if args.protocol == "auto":
            await api.async_login()
        elif args.protocol == "ubus":
            await api._async_ubus_login()
            api._api_mode = "ubus"
        else:
            await api._async_goform_login()
        print_json(
            {
                "ok": api.is_logged_in,
                "selected_protocol": api.login_method,
                "session_established": api.is_logged_in,
                "session_token_present": bool(api._session_id),
                "cookies_present": bool(api._session.cookie_jar),
                "fallback_used": args.protocol == "auto" and api.login_method == "goform",
            }
        )
        return 0
    except Exception as err:
        print_json(
            {
                "ok": False,
                "requested_protocol": args.protocol,
                "error_type": type(err).__name__,
                "summary": api.safe_error_summary(err),
            }
        )
        return 1
    finally:
        await api.async_close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(async_main()))
