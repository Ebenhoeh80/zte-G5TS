"""Probe ZTE router login challenges without exposing secrets.

Run on the Home Assistant host for the most useful network-path diagnosis:
python tests/diagnose_login.py

Pass --login to also make one UBUS login attempt using the ztepwd environment
variable. This may invalidate an existing WebUI session.

For legacy routers that expose only HTTP or use an untrusted HTTPS certificate,
pass --insecure explicitly. Credentials and session traffic may then be exposed.
"""

from __future__ import annotations

import argparse
import hashlib
import http.cookiejar
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


def _read_json(response: Any) -> tuple[Any, bytes]:
    body = response.read()
    try:
        return json.loads(body), body
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, body


def _rpc(
    opener: urllib.request.OpenerDirector,
    base_url: str,
    method: str,
    params: dict[str, str],
) -> Any:
    body = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "call",
            "params": ["0" * 32, "zwrt_web", method, params],
        }
    ]
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
        "User-Agent": "Mozilla/5.0 (Home Assistant; ZTE NG Router)",
        "Origin": base_url,
        "Referer": base_url + "/",
        "Z-Mode": "0",
        "Z-Tag": method,
        "X-Requested-With": "XMLHttpRequest",
    }
    request = urllib.request.Request(
        base_url + "/ubus/?t=1",
        data=json.dumps(body, separators=(",", ":")).encode(),
        headers=headers,
        method="POST",
    )
    with opener.open(request, timeout=10) as response:
        value, _ = _read_json(response)
    return value


def _rpc_payload(value: Any) -> tuple[dict[str, Any] | None, Any]:
    if not isinstance(value, list) or not value or not isinstance(value[0], dict):
        return None, None
    result = value[0].get("result")
    if isinstance(result, list) and len(result) > 1 and result[0] == 0:
        payload = result[1]
        return (payload if isinstance(payload, dict) else None), result[0]
    return None, result[0] if isinstance(result, list) and result else None


def _print_result(stage: str, details: dict[str, Any]) -> None:
    print(json.dumps({"stage": stage, **details}, ensure_ascii=True))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="https://192.168.0.1", help="Router HTTPS origin")
    parser.add_argument(
        "--verify-tls",
        action="store_true",
        default=True,
        help="Verify HTTPS certificates (the secure default)",
    )
    parser.add_argument(
        "--insecure",
        dest="verify_tls",
        action="store_false",
        help="Allow HTTP or disable HTTPS certificate verification; unsafe",
    )
    parser.add_argument(
        "--login",
        action="store_true",
        help="Attempt one UBUS login using ztepwd; may invalidate the WebUI session",
    )
    args = parser.parse_args()
    base_url = args.host.rstrip("/")
    parsed_host = urllib.parse.urlsplit(base_url)
    if (
        parsed_host.scheme not in {"http", "https"}
        or not parsed_host.hostname
        or parsed_host.username is not None
        or parsed_host.password is not None
        or parsed_host.path
        or parsed_host.query
        or parsed_host.fragment
    ):
        parser.error("host must be an origin-only http:// or https:// URL without credentials")
    if parsed_host.scheme == "http" and args.verify_tls:
        parser.error("HTTP is unencrypted; pass --insecure only if this risk is acceptable")
    if not args.verify_tls:
        print(
            "WARNING: insecure transport or unverified TLS is enabled; credentials and sessions may be exposed.",
            file=sys.stderr,
        )
    ssl_context = (
        ssl.create_default_context()
        if args.verify_tls
        else ssl._create_unverified_context()
    )
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cookie_jar),
        urllib.request.HTTPSHandler(context=ssl_context),
    )

    try:
        request = urllib.request.Request(
            base_url + "/index.html",
            headers={"User-Agent": "Mozilla/5.0 (Home Assistant; ZTE NG Router)"},
        )
        with opener.open(request, timeout=10) as response:
            _, body = _read_json(response)
            _print_result(
                "index",
                {
                    "status": response.status,
                    "final_url": response.geturl(),
                    "content_type": response.headers.get("Content-Type"),
                    "bytes": len(body),
                    "cookie_count": len(cookie_jar),
                },
            )
    except Exception as exc:
        _print_result("index", {"ok": False, "error_type": type(exc).__name__, "error": str(exc)})

    try:
        challenge = _rpc(opener, base_url, "web_login_info", {})
        payload, result_code = _rpc_payload(challenge)
        _print_result(
            "UBUS web_login_info",
            {
                "ok": bool(payload and payload.get("zte_web_sault")),
                "result_code": result_code,
                "response_type": type(challenge).__name__,
                "data_keys": sorted(payload) if payload else [],
                "has_salt": bool(payload and payload.get("zte_web_sault")),
            },
        )
    except Exception as exc:
        payload = None
        _print_result(
            "UBUS web_login_info",
            {"ok": False, "error_type": type(exc).__name__, "error": str(exc)},
        )

    try:
        query = urllib.parse.urlencode(
            {"isTest": "false", "cmd": "LD", "multi_data": "1", "_": "1"}
        )
        request = urllib.request.Request(
            base_url + "/goform/goform_get_cmd_process?" + query,
            headers={
                "Referer": base_url + "/index.html",
                "X-Requested-With": "XMLHttpRequest",
            },
        )
        with opener.open(request, timeout=10) as response:
            value, body = _read_json(response)
            is_json_object = isinstance(value, dict)
            _print_result(
                "GoForm LD",
                {
                    "ok": bool(is_json_object and value.get("LD")),
                    "status": response.status,
                    "final_url": response.geturl(),
                    "content_type": response.headers.get("Content-Type"),
                    "response_type": type(value).__name__ if value is not None else "non-JSON",
                    "has_LD": bool(is_json_object and value.get("LD")),
                    "LD_length": len(str(value.get("LD") or "")) if is_json_object else 0,
                    "bytes": len(body),
                },
            )
    except Exception as exc:
        _print_result(
            "GoForm LD",
            {"ok": False, "error_type": type(exc).__name__, "error": str(exc)},
        )

    if not args.login:
        return 0
    password = os.environ.get("ztepwd")
    if not password:
        _print_result("UBUS login", {"ok": False, "error": "environment variable ztepwd is not set"})
        return 2
    if not payload or not payload.get("zte_web_sault"):
        _print_result("UBUS login", {"ok": False, "error": "no login salt; see challenge result above"})
        return 1

    password_hash = hashlib.sha256(password.encode("utf-8")).hexdigest().upper()
    final_hash = hashlib.sha256(
        (password_hash + payload["zte_web_sault"]).encode("utf-8")
    ).hexdigest().upper()
    try:
        response = _rpc(opener, base_url, "web_login", {"password": final_hash})
        login_data, result_code = _rpc_payload(response)
        logged_in = bool(login_data and login_data.get("ubus_rpc_session"))
        _print_result(
            "UBUS login",
            {
                "ok": logged_in,
                "result_code": result_code,
                "data_keys": sorted(login_data) if login_data else [],
                "session_created": logged_in,
            },
        )
        return 0 if logged_in else 1
    except Exception as exc:
        _print_result("UBUS login", {"ok": False, "error_type": type(exc).__name__, "error": str(exc)})
        return 1


if __name__ == "__main__":
    sys.exit(main())
