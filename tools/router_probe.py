"""Probe unauthenticated HTTP/HTTPS reachability, status codes, and redirects.

The probe never sends a password or login token. For a self-signed router
certificate, set ZTE_TLS_FINGERPRINT to its independently verified SHA-256
fingerprint. The fingerprint from the supplied router certificate is suitable
for this router only; do not reuse it for another device.

Example:
    $env:ZTE_TLS_FINGERPRINT = "<64-character SHA-256 fingerprint>"
    python tools/router_probe.py
"""

from __future__ import annotations

import asyncio
import os
from urllib.parse import urlsplit

import aiohttp

try:
    from .router_test_support import make_ssl_argument, print_json, router_settings
except ImportError:
    from router_test_support import make_ssl_argument, print_json, router_settings


async def probe_scheme(base_url: str, fingerprint: str | None) -> dict[str, object]:
    parsed = urlsplit(base_url)
    url = f"{parsed.scheme}://{parsed.netloc}/"
    ssl_arg = make_ssl_argument(url, fingerprint)
    timeout = aiohttp.ClientTimeout(total=12)
    try:
        async with aiohttp.ClientSession(
            timeout=timeout, trust_env=False
        ) as session:
            async with session.get(
                url,
                allow_redirects=True,
                max_redirects=5,
                ssl=ssl_arg,
            ) as response:
                await response.read()
                return {
                    "scheme": parsed.scheme,
                    "ok": 200 <= response.status < 400,
                    "status": response.status,
                    "redirect_statuses": [item.status for item in response.history],
                    "redirect_count": len(response.history),
                    "final_scheme": response.url.scheme,
                    "content_type": response.content_type,
                }
    except Exception as err:
        return {
            "scheme": parsed.scheme,
            "ok": False,
            "error_type": type(err).__name__,
        }


async def async_main() -> int:
    base_url, _, fingerprint = router_settings()
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise SystemExit("ZTE_ROUTER_URL must be an http(s) origin.")
    host = parsed.hostname
    http_origin = os.environ.get("ZTE_HTTP_URL", f"http://{host}").rstrip("/")
    https_origin = os.environ.get(
        "ZTE_HTTPS_URL",
        base_url if parsed.scheme == "https" else f"https://{host}",
    ).rstrip("/")
    results = await asyncio.gather(
        probe_scheme(http_origin, None),
        probe_scheme(https_origin, fingerprint),
    )
    print_json(
        {
            "router_host": host,
            "checks": results,
            "tls_mode": "sha256_fingerprint" if fingerprint else "system_ca_validation",
        }
    )
    return 0 if all(item["ok"] for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(async_main()))
