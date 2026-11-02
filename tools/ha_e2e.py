"""Exercise the renamed integration inside a running Home Assistant instance.

Required environment: HA_URL, HA_TOKEN, and ZTEPWD. The tool creates the
integration entry if none exists, otherwise verifies the sole existing entry.
The integration must already be installed in Home Assistant. The tool never
prints credentials or router/HA response bodies. Home Assistant is restarted
only when --restart and HA_ALLOW_RESTART=1 are both supplied.
"""

from __future__ import annotations

import argparse
import asyncio
import os
from urllib.parse import urlsplit, urlunsplit

import aiohttp

try:
    from .router_test_support import print_json, router_settings
except ImportError:
    from router_test_support import print_json, router_settings


INTEGRATION_DOMAIN = "zte_5g_router"
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=20)


class HomeAssistantE2E:
    """Authenticated HA API client that keeps access tokens out of reports."""

    def __init__(self, base_url: str, token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.session = aiohttp.ClientSession(
            timeout=REQUEST_TIMEOUT,
            trust_env=False,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )

    async def close(self) -> None:
        await self.session.close()

    async def rest(
        self,
        method: str,
        path: str,
        *,
        payload: dict | None = None,
    ):
        async with self.session.request(
            method,
            f"{self.base_url}{path}",
            json=payload,
            allow_redirects=False,
        ) as response:
            if response.status >= 400:
                raise RuntimeError(f"Home Assistant REST returned HTTP {response.status}")
            if response.status == 204:
                return None
            try:
                return await response.json(content_type=None)
            except (aiohttp.ContentTypeError, ValueError) as err:
                raise RuntimeError("Home Assistant returned an invalid JSON response") from err

    async def websocket_result(self, command: dict):
        parsed = urlsplit(self.base_url)
        ws_url = urlunsplit(
            ("wss" if parsed.scheme == "https" else "ws", parsed.netloc, "/api/websocket", "", "")
        )
        async with self.session.ws_connect(ws_url, heartbeat=30) as ws:
            required = await ws.receive_json()
            if required.get("type") != "auth_required":
                raise RuntimeError("Home Assistant WebSocket auth handshake failed")
            await ws.send_json({"type": "auth", "access_token": self.token})
            authenticated = await ws.receive_json()
            if authenticated.get("type") != "auth_ok":
                raise RuntimeError("Home Assistant WebSocket authentication failed")
            await ws.send_json({"id": 1, **command})
            result = await ws.receive_json()
            if result.get("id") != 1 or not result.get("success", True):
                error = result.get("error")
                code = error.get("code") if isinstance(error, dict) else None
                raise RuntimeError(
                    f"Home Assistant WebSocket command failed: {code or 'unknown'}"
                )
            return result.get("result")


async def get_domain_entries(client: HomeAssistantE2E) -> list[dict]:
    result = await client.rest(
        "GET", f"/api/config/config_entries/entry?domain={INTEGRATION_DOMAIN}"
    )
    if not isinstance(result, list):
        raise RuntimeError("Home Assistant returned an invalid config-entry list")
    return [entry for entry in result if isinstance(entry, dict)]


async def create_entry(
    client: HomeAssistantE2E,
    router_url: str,
    password: str,
    fingerprint: str | None,
) -> str:
    try:
        flow = await client.rest(
            "POST",
            "/api/config/config_entries/flow",
            payload={"handler": INTEGRATION_DOMAIN},
        )
    except RuntimeError as err:
        if "HTTP 404" in str(err):
            raise RuntimeError(
                "Home Assistant could not find this integration's config flow; "
                "install the integration and restart Home Assistant before retrying"
            ) from err
        raise
    if not isinstance(flow, dict) or flow.get("type") != "form":
        raise RuntimeError("Home Assistant did not start the integration config flow")
    flow_id = flow.get("flow_id")
    if not isinstance(flow_id, str):
        raise RuntimeError("Home Assistant config flow returned no flow identifier")

    result = await client.rest(
        "POST",
        f"/api/config/config_entries/flow/{flow_id}",
        payload={
            "name": "ZTE 5G Router E2E",
            "host": router_url,
            "password": password,
            "verify_tls": True,
            "tls_fingerprint": fingerprint or "",
            "allow_insecure_http": False,
            "scan_interval": 60,
            "fast_scan_interval": 5,
            "track_wifi_clients": False,
            "client_consider_home": 180,
        },
    )
    if not isinstance(result, dict):
        raise RuntimeError("Home Assistant returned an invalid config-flow result")
    if result.get("type") != "create_entry":
        errors = result.get("errors")
        error_codes = sorted(str(key) for key in errors) if isinstance(errors, dict) else []
        raise RuntimeError(
            "Home Assistant config flow did not create an entry"
            + (f" (error codes: {', '.join(error_codes)})" if error_codes else "")
        )
    entry = result.get("result")
    entry_id = entry.get("entry_id") if isinstance(entry, dict) else None
    if not isinstance(entry_id, str):
        raise RuntimeError("Home Assistant created no config-entry identifier")
    return entry_id


async def wait_for_loaded_entry(
    client: HomeAssistantE2E, entry_id: str, *, timeout: float = 240
) -> dict:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        for entry in await get_domain_entries(client):
            if entry.get("entry_id") == entry_id:
                if entry.get("state") == "loaded":
                    return entry
                if entry.get("state") in {"setup_error", "failed_unload"}:
                    raise RuntimeError(
                        f"Home Assistant integration setup ended in {entry['state']}"
                    )
        await asyncio.sleep(3)
    raise TimeoutError("Timed out waiting for the integration entry to load")


async def integration_entities(
    client: HomeAssistantE2E, entry_id: str
) -> list[dict]:
    result = await client.websocket_result({"type": "config/entity_registry/list"})
    if not isinstance(result, list):
        raise RuntimeError("Home Assistant returned an invalid entity registry")
    return [
        item
        for item in result
        if isinstance(item, dict)
        and item.get("config_entry_id") == entry_id
        and item.get("platform") == INTEGRATION_DOMAIN
        and isinstance(item.get("entity_id"), str)
    ]


async def available_entity_count(
    client: HomeAssistantE2E, entities: list[dict]
) -> int:
    states = await client.rest("GET", "/api/states")
    if not isinstance(states, list):
        raise RuntimeError("Home Assistant returned an invalid entity state list")
    states_by_id = {
        state.get("entity_id"): state
        for state in states
        if isinstance(state, dict) and isinstance(state.get("entity_id"), str)
    }
    return sum(
        1
        for entity in entities
        if (state := states_by_id.get(entity["entity_id"])) is not None
        and state.get("state") != "unavailable"
    )


async def wait_for_api(client: HomeAssistantE2E, *, timeout: float = 300) -> None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    last_error: str | None = None
    while loop.time() < deadline:
        try:
            response = await client.rest("GET", "/api/")
            if isinstance(response, dict) and response.get("message") == "API running.":
                return
        except (aiohttp.ClientError, RuntimeError) as err:
            last_error = type(err).__name__
        await asyncio.sleep(5)
    raise TimeoutError(
        "Home Assistant did not return after restart"
        + (f" (last error type: {last_error})" if last_error else "")
    )


async def async_main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--restart",
        action="store_true",
        help="Restart Home Assistant after initial validation; requires HA_ALLOW_RESTART=1.",
    )
    args = parser.parse_args()

    base_url = os.environ.get("HA_URL", "").rstrip("/")
    token = os.environ.get("HA_TOKEN", "")
    if not base_url or not token:
        parser.error("Set HA_URL and HA_TOKEN in the environment; do not pass tokens as arguments.")
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
        parser.error("HA_URL must be an origin-only http(s) URL without credentials.")
    if parsed.scheme == "http" and os.environ.get("HA_ALLOW_INSECURE_HTTP") != "1":
        parser.error("HA_URL must use HTTPS unless HA_ALLOW_INSECURE_HTTP=1 is explicitly set.")
    if args.restart and os.environ.get("HA_ALLOW_RESTART") != "1":
        parser.error("Set HA_ALLOW_RESTART=1 to authorize a Home Assistant restart.")

    router_url, password, fingerprint = router_settings(require_password=False)
    client = HomeAssistantE2E(base_url, token)
    try:
        health = await client.rest("GET", "/api/")
        if not isinstance(health, dict) or health.get("message") != "API running.":
            raise RuntimeError("Home Assistant API health check failed")

        entries = await get_domain_entries(client)
        if len(entries) > 1:
            raise RuntimeError("Multiple renamed integration entries found; refusing to choose.")
        if entries:
            entry_id = entries[0].get("entry_id")
            if not isinstance(entry_id, str):
                raise RuntimeError("Existing config entry has no identifier")
            created = False
        else:
            if not password:
                raise RuntimeError("Set ZTEPWD to create the config entry.")
            entry_id = await create_entry(client, router_url, password, fingerprint)
            created = True

        entry = await wait_for_loaded_entry(client, entry_id)
        entities = await integration_entities(client, entry_id)
        if not entities:
            raise RuntimeError("No entities were registered for the integration")
        available = await available_entity_count(client, entities)
        if available < 1:
            raise RuntimeError("No integration entities have an available state")

        restarted = False
        if args.restart:
            await client.rest(
                "POST",
                "/api/services/homeassistant/restart",
                payload={},
            )
            await wait_for_api(client)
            entry = await wait_for_loaded_entry(client, entry_id)
            entities = await integration_entities(client, entry_id)
            available = await available_entity_count(client, entities)
            if not entities or available < 1:
                raise RuntimeError("Integration did not recover after Home Assistant restart")
            restarted = True

        print_json(
            {
                "ok": True,
                "domain": INTEGRATION_DOMAIN,
                "config_entry_created": created,
                "config_entry_state": entry.get("state"),
                "entity_count": len(entities),
                "available_entity_count": available,
                "initial_coordinator_refresh": entry.get("state") == "loaded",
                "home_assistant_restart_recovery": restarted,
            }
        )
        return 0
    finally:
        await client.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(async_main()))
