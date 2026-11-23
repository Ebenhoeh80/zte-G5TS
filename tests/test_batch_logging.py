"""Tests for ubus batch failure logging classification."""

from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
import sys
import types
from unittest.mock import patch


def load_api():
    aiohttp = types.ModuleType("aiohttp")
    aiohttp.ClientError = Exception
    aiohttp.ClientSession = object
    aiohttp.CookieJar = object
    core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = object
    path = Path(__file__).resolve().parents[1] / "custom_components/zte_5g_router/zte_api.py"
    spec = importlib.util.spec_from_file_location("zte_batch_logging_test_api", path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"aiohttp": aiohttp, "homeassistant.core": core}):
        spec.loader.exec_module(module)
    return module.ZteRouterApi


ZteRouterApi = load_api()


def api():
    result = ZteRouterApi(session=object())
    result._seen_optional_core_failures = set()
    return result


def _call(service: str, method: str, params: dict | None = None) -> dict:
    call = {"service": service, "method": method}
    if params is not None:
        call["params"] = params
    return call


def test_optional_core_nonzero_result_is_info_once(caplog):
    calls = [
        _call("uci", "get", {"config": "zwrt_common_info", "section": "common_config"}),
        _call("zwrt_led", "get_ODU_switch_state", {}),
        _call("uci", "get", {"config": "wireless", "section": "main_2g"}),
        _call("uci", "get", {"config": "wireless", "section": "main_5g"}),
    ]
    results = [
        {"success": False, "data": None, "error": {"message": "nonzero_result", "ubus_status": 4}},
        {"success": False, "data": None, "error": {"message": "nonzero_result", "ubus_status": 4}},
        {"success": False, "data": None, "error": {"message": "nonzero_result", "ubus_status": 4}},
        {"success": False, "data": None, "error": {"message": "nonzero_result", "ubus_status": 4}},
    ]
    router_api = api()

    with caplog.at_level(logging.DEBUG, logger="zte_batch_logging_test_api"):
        router_api._log_batch_failures("core", calls, results)
        router_api._log_batch_failures("core", calls, results)

    warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
    infos = [r for r in caplog.records if r.levelno == logging.INFO and "optional unsupported or unavailable calls" in r.getMessage()]
    assert not warnings
    assert len(infos) == 1
    assert "uci.get (ubus 4)" in infos[0].getMessage()
    assert "zwrt_led.get_ODU_switch_state (ubus 4)" in infos[0].getMessage()


def test_non_optional_core_failure_stays_warning(caplog):
    calls = [_call("zte_nwinfo_api", "nwinfo_get_netinfo")]
    results = [{"success": False, "data": None, "error": {"message": "nonzero_result"}}]

    with caplog.at_level(logging.DEBUG, logger="zte_batch_logging_test_api"):
        api()._log_batch_failures("core", calls, results)

    warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert len(warnings) == 1
    assert "ubus batch 'core' had failed calls" in warnings[0].getMessage()
    assert "zte_nwinfo_api.nwinfo_get_netinfo" in warnings[0].getMessage()


def test_optional_core_transport_failure_stays_warning(caplog):
    calls = [_call("uci", "get", {"config": "wireless", "section": "main_2g"})]
    results = [
        {
            "success": False,
            "data": None,
            "error": {"message": "timeout", "kind": "transport"},
        }
    ]

    with caplog.at_level(logging.DEBUG, logger="zte_batch_logging_test_api"):
        api()._log_batch_failures("core", calls, results)

    warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert len(warnings) == 1
    assert "transport error" in warnings[0].getMessage()


def test_optional_core_rpc_code_failure_stays_warning(caplog):
    calls = [_call("zwrt_led", "get_ODU_switch_state", {})]
    results = [{"success": False, "data": None, "error": {"code": -32002}}]

    with caplog.at_level(logging.DEBUG, logger="zte_batch_logging_test_api"):
        api()._log_batch_failures("core", calls, results)

    warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert len(warnings) == 1
    assert "RPC -32002" in warnings[0].getMessage()


def test_optional_classification_not_applied_outside_core(caplog):
    calls = [_call("uci", "get", {"config": "wireless", "section": "main_2g"})]
    results = [{"success": False, "data": None, "error": {"message": "nonzero_result"}}]

    with caplog.at_level(logging.DEBUG, logger="zte_batch_logging_test_api"):
        api()._log_batch_failures("sms", calls, results)

    warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert len(warnings) == 1
    assert "ubus batch 'sms' had failed calls" in warnings[0].getMessage()


def test_optional_core_failure_with_unhashable_params_does_not_raise(caplog):
    calls = [_call("uci", "get", {"config": "wireless", "section": "main_2g", "extra": [1, 2]})]
    results = [{"success": False, "data": None, "error": {"message": "nonzero_result"}}]

    with caplog.at_level(logging.DEBUG, logger="zte_batch_logging_test_api"):
        api()._log_batch_failures("core", calls, results)

    assert [r for r in caplog.records if r.levelno >= logging.WARNING]


def test_mixed_optional_and_non_optional_core_failures(caplog):
    calls = [
        _call("uci", "get", {"config": "wireless", "section": "main_2g"}),
        _call("zte_nwinfo_api", "nwinfo_get_netinfo"),
    ]
    results = [
        {"success": False, "data": None, "error": {"message": "nonzero_result"}},
        {"success": False, "data": None, "error": {"message": "nonzero_result"}},
    ]

    with caplog.at_level(logging.DEBUG, logger="zte_batch_logging_test_api"):
        api()._log_batch_failures("core", calls, results)

    warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
    infos = [r for r in caplog.records if r.levelno == logging.INFO]
    assert len(warnings) == 1
    assert "zte_nwinfo_api.nwinfo_get_netinfo" in warnings[0].getMessage()
    assert "uci.get" not in warnings[0].getMessage()
    assert len(infos) == 1
    assert "uci.get" in infos[0].getMessage()


def test_optional_core_error_none_stays_warning(caplog):
    calls = [_call("uci", "get", {"config": "wireless", "section": "main_2g"})]
    results = [{"success": False, "data": None, "error": None}]

    with caplog.at_level(logging.DEBUG, logger="zte_batch_logging_test_api"):
        api()._log_batch_failures("core", calls, results)

    warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert len(warnings) == 1
    assert "unknown error" in warnings[0].getMessage()
