"""Shared helpers for safe real-router checks."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys
import types
from typing import Any
from urllib.parse import urlsplit

import aiohttp


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROUTER_URL = "https://192.168.0.1"


def router_settings(*, require_password: bool = False) -> tuple[str, str, str | None]:
    """Read router settings without ever displaying the password."""
    base_url = os.environ.get("ZTE_ROUTER_URL", DEFAULT_ROUTER_URL).rstrip("/")
    parsed = urlsplit(base_url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        raise RuntimeError("ZTE_ROUTER_URL must be an origin-only http(s) URL.")
    password = os.environ.get("ZTEPWD", "")
    fingerprint = os.environ.get("ZTE_TLS_FINGERPRINT", "").strip()
    if require_password and not password:
        raise RuntimeError("Set the router password in the ZTEPWD environment variable.")
    if fingerprint:
        fingerprint = fingerprint.replace(":", "").lower()
        if len(fingerprint) != 64 or any(
            character not in "0123456789abcdef" for character in fingerprint
        ):
            raise RuntimeError("ZTE_TLS_FINGERPRINT must be a SHA-256 hex fingerprint.")
    return base_url, password, fingerprint or None


def load_api_class() -> type:
    """Load the integration API for standalone tools without requiring HA Core."""
    try:
        import homeassistant.core  # noqa: F401
    except ModuleNotFoundError:
        core = types.ModuleType("homeassistant.core")
        core.HomeAssistant = object
        homeassistant = types.ModuleType("homeassistant")
        homeassistant.core = core
        sys.modules["homeassistant"] = homeassistant
        sys.modules["homeassistant.core"] = core

    api_path = ROOT / "custom_components" / "zte_5g_router" / "zte_api.py"
    spec = importlib.util.spec_from_file_location("zte_5g_router_hardware_api", api_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load the integration API module.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.ZteRouterApi


def make_ssl_argument(
    url: str, fingerprint: str | None
) -> bool | aiohttp.Fingerprint | None:
    """Keep normal TLS checks enabled, or verify the exact supplied certificate."""
    if not url.lower().startswith("https://"):
        return None
    if fingerprint:
        return aiohttp.Fingerprint(bytes.fromhex(fingerprint))
    return True


def safe_api(api: Any) -> dict[str, Any]:
    """Summarize live API payloads without exposing router-provided data."""
    slow = api.get("slow_data") or {}
    fast = api.get("fast_data") or {}
    common = slow.get("common_config") or {}
    device = slow.get("device") or {}
    wan = slow.get("wan") or {}
    netinfo = slow.get("netinfo") or {}

    def present(mapping: Any, keys: tuple[str, ...]) -> bool:
        return isinstance(mapping, dict) and any(mapping.get(key) is not None for key in keys)

    def first_value(mapping: Any, keys: tuple[str, ...]) -> str | None:
        if not isinstance(mapping, dict):
            return None
        return next(
            (str(mapping[key]) for key in keys if mapping.get(key) is not None),
            None,
        )

    return {
        "login_method": api.get("login_method"),
        "session_established": api.get("session_established", False),
        "model": first_value(common, ("model", "model_name", "product_name")),
        "firmware_version": first_value(
            common, ("wa_inner_version", "wa_version", "firmware_version")
        ),
        "firmware_detected": present(
            common, ("wa_inner_version", "wa_version", "hardware_version")
        ),
        "device_info_received": bool(device),
        "wan_status_received": bool(wan or fast.get("wan")),
        "network_data_received": bool(netinfo),
        "signal_data_received": present(
            netinfo, ("rsrp", "RSRP", "sinr", "SINR", "rssi", "RSSI")
        ),
        "statistics_received": bool(slow.get("wwandst") or fast.get("wwandst")),
        "response_sections": sorted(
            key
            for key, value in slow.items()
            if value is not None and key not in {"sms", "network_clients"}
        ),
    }


def track_api_batches(api: Any) -> list[dict[str, Any]]:
    """Capture only per-method success and safe RPC/HTTP failure codes."""
    batches: list[dict[str, Any]] = []
    original = api.async_call_ubus_batch

    async def tracked(calls: list[dict[str, Any]], *args: Any, **kwargs: Any) -> Any:
        results = await original(calls, *args, **kwargs)
        name = kwargs.get("batch_name", "unnamed")
        summary = []
        if isinstance(results, list):
            for call, result in zip(calls, results, strict=False):
                error = result.get("error") if isinstance(result, dict) else None
                failure_code = None
                if isinstance(error, dict):
                    code = error.get("code")
                    failure_code = (
                        f"HTTP {error['status']}"
                        if isinstance(error.get("status"), int)
                        else f"RPC {code}"
                        if isinstance(code, int)
                        else "transport"
                        if error.get("kind") == "transport"
                        else "router_error_without_code"
                        if "message" in error
                        else "unknown_error"
                    )
                summary.append(
                    {
                        "method": f"{call.get('service')}.{call.get('method')}",
                        "ok": bool(isinstance(result, dict) and result.get("success")),
                        "failure_code": failure_code,
                    }
                )
        batches.append({"name": name, "calls": summary})
        return results

    api.async_call_ubus_batch = tracked
    return batches


def print_json(result: dict[str, Any]) -> None:
    """Print a stable, JSON-safe report with no router response bodies."""
    import json

    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
