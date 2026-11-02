"""Discover unauthenticated ZTE login API behavior without printing tokens.

Use --authenticate to perform one real login and read the integration's
read-only status endpoints. Payloads, cookies, tokens, and session IDs are
never printed.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from urllib.parse import urlsplit

import aiohttp

try:
    from .router_test_support import (
        load_api_class,
        make_ssl_argument,
        print_json,
        router_settings,
        safe_api,
        track_api_batches,
    )
except ImportError:
    from router_test_support import (
        load_api_class,
        make_ssl_argument,
        print_json,
        router_settings,
        safe_api,
        track_api_batches,
    )


async def probe_endpoint(
    session: aiohttp.ClientSession,
    base_url: str,
    path: str,
    *,
    fingerprint: str | None,
    headers: dict[str, str] | None = None,
    json_body: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    url = f"{base_url}{path}"
    request_headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "User-Agent": "Mozilla/5.0 (Home Assistant; ZTE 5G Router)",
        "X-Requested-With": "XMLHttpRequest",
    }
    request_headers.update(headers or {})
    try:
        async with session.request(
            "POST" if json_body is not None else "GET",
            url,
            json=json_body,
            headers=request_headers,
            allow_redirects=True,
            max_redirects=5,
            ssl=make_ssl_argument(url, fingerprint),
        ) as response:
            body = await response.read()
            payload: object = None
            try:
                payload = json.loads(body)
            except (UnicodeDecodeError, json.JSONDecodeError):
                pass
            keys: list[str] = []
            result_code = None
            if isinstance(payload, list) and payload and isinstance(payload[0], dict):
                result = payload[0].get("result")
                if isinstance(result, list) and result:
                    result_code = result[0] if isinstance(result[0], int) else "non_numeric"
                    if len(result) > 1 and isinstance(result[1], dict):
                        keys = sorted(str(key) for key in result[1])
            elif isinstance(payload, dict):
                keys = sorted(str(key) for key in payload)
            return {
                "status": response.status,
                "content_type": response.content_type,
                "redirect_statuses": [item.status for item in response.history],
                "response_kind": (
                    "json_object"
                    if isinstance(payload, dict)
                    else "json_array"
                    if isinstance(payload, list)
                    else "non_json"
                ),
                "response_keys": keys,
                "request_header_names": sorted(request_headers),
                "rpc_result_code": result_code,
                "set_cookie_present": bool(response.cookies),
            }
    except Exception as err:
        return {"error_type": type(err).__name__}


async def async_discover(base_url: str, fingerprint: str | None) -> dict[str, object]:
    headers = {"User-Agent": "Mozilla/5.0 (Home Assistant; ZTE 5G Router)"}
    timeout = aiohttp.ClientTimeout(total=12)
    async with aiohttp.ClientSession(
        timeout=timeout, trust_env=False, headers=headers
    ) as session:
        index = await probe_endpoint(
            session, base_url, "/index.html", fingerprint=fingerprint
        )
        ubus_headers = {
            "Content-Type": "application/json",
            "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
            "Origin": base_url,
            "Referer": f"{base_url}/",
            "Z-Mode": "0",
            "Z-Tag": "web_login_info",
        }
        ubus = await probe_endpoint(
            session,
            base_url,
            f"/ubus/?t={int(time.time() * 1000)}",
            fingerprint=fingerprint,
            headers=ubus_headers,
            json_body=[
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "call",
                    "params": ["0" * 32, "zwrt_web", "web_login_info", {}],
                }
            ],
        )
        goform = await probe_endpoint(
            session,
            base_url,
            "/goform/goform_get_cmd_process?isTest=false&cmd=LD&multi_data=1",
            fingerprint=fingerprint,
            headers={"Referer": f"{base_url}/index.html"},
        )
    return {
        "router_host": urlsplit(base_url).hostname,
        "endpoints": {
            "index": index,
            "ubus_web_login_info": ubus,
            "goform_ld": goform,
        },
        "secrets_redacted": True,
    }


async def async_authenticated_discovery(
    base_url: str, password: str, fingerprint: str | None
) -> dict[str, object]:
    api_class = load_api_class()
    api = api_class(
        base_url=base_url,
        password=password,
        verify_tls=True,
        tls_fingerprint=fingerprint,
    )
    batches = track_api_batches(api)
    try:
        await api.async_login()
        fast_data = await api.async_update_fast()
        slow_data = await api.async_update_all()
        return {
            **safe_api(
            {
                "login_method": api.login_method,
                "session_established": api.is_logged_in,
                "fast_data": fast_data or {},
                "slow_data": slow_data or {},
            }
            ),
            "api_calls": batches,
        }
    finally:
        await api.async_close()


async def async_main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--authenticate",
        action="store_true",
        help="Perform one login and read-only status API checks using ZTEPWD.",
    )
    args = parser.parse_args()
    base_url, password, fingerprint = router_settings(
        require_password=args.authenticate
    )
    if urlsplit(base_url).scheme != "https" and not base_url.startswith("http://"):
        raise SystemExit("ZTE_ROUTER_URL must be an http(s) origin.")

    report: dict[str, object] = {
        "discovery": await async_discover(base_url, fingerprint)
    }
    if args.authenticate:
        try:
            report["authenticated_api_summary"] = await async_authenticated_discovery(
                base_url, password, fingerprint
            )
        except Exception as err:
            report["authenticated_api_summary"] = {
                "ok": False,
                "error_type": type(err).__name__,
            }
            print_json(report)
            return 1
    print_json(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(async_main()))
