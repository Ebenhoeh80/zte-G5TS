"""Offline coverage tests for the low-level ZTE router API.

No Home Assistant instance, no network and no real router are involved. The
module is loaded under a private name so the tests never clash with the other
suites that stub aiohttp/homeassistant in ``sys.modules``.
"""

import asyncio
import base64
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import types
import unittest
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "zte_5g_router"


def _load_api():
    core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = object
    spec = importlib.util.spec_from_file_location("zte_api_coverage_private", _ROOT / "zte_api.py")
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"homeassistant.core": core}):
        spec.loader.exec_module(module)
    return module


api_module = _load_api()
ZteRouterApi = api_module.ZteRouterApi

KEY = "12" * 32
OTHER_KEY = "34" * 32


def seal(value: str, key: str = KEY) -> str:
    iv = bytes(range(12))
    encrypted = AESGCM(bytes.fromhex(key)).encrypt(iv, value.encode(), None)
    return base64.b64encode(iv + encrypted[-16:] + encrypted[:-16]).decode()


class FakeResponse:
    """Minimal async context manager mimicking aiohttp's request response."""

    def __init__(
        self,
        *,
        status=200,
        payload=None,
        text="",
        content_type="application/json",
        status_error=None,
        read_error=None,
    ):
        self.status = status
        self._payload = {} if payload is None else payload
        self._text = text
        self.content_type = content_type
        self._status_error = status_error
        self._read_error = read_error

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    def raise_for_status(self):
        if self._status_error is not None:
            raise self._status_error

    async def json(self, content_type=None):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload

    async def text(self):
        if isinstance(self._text, Exception):
            raise self._text
        return self._text

    async def read(self):
        if self._read_error is not None:
            raise self._read_error
        return b"<html>router</html>"


def fake_session(*, post=None, get=None, closed=False):
    session = Mock()
    session.closed = closed
    session.post = Mock(return_value=FakeResponse() if post is None else post)
    session.get = Mock(return_value=FakeResponse() if get is None else get)
    session.close = AsyncMock()
    return session


def make_router(**kwargs):
    kwargs.setdefault("base_url", "https://192.0.2.1")
    kwargs.setdefault("password", "secret")
    kwargs.setdefault("session", fake_session())
    return ZteRouterApi(**kwargs)


def logged_in_router(**kwargs):
    router = make_router(**kwargs)
    router._logged_in = True
    router._session_id = "session-id"
    return router


def ok(data=None):
    return {"success": True, "data": data if data is not None else {}}


def batch_ok(*payloads):
    return [ok(payload) for payload in payloads]


class ConstructionTests(unittest.IsolatedAsyncioTestCase):
    async def test_owned_session_uses_router_connector_and_unsafe_cookie_jar(self):
        with (
            patch.object(aiohttp, "TCPConnector") as connector,
            patch.object(api_module, "CookieJar") as jar,
            patch.object(aiohttp, "ClientSession") as session_cls,
        ):
            router = ZteRouterApi(base_url="https://192.0.2.1")
            self.assertTrue(router._owns_session)
            connector.assert_called_once()
            jar.assert_called_once_with(unsafe=True)
            self.assertEqual(jar.call_args.kwargs["unsafe"], True)
            session_cls.assert_called_once_with(
                connector=connector.return_value, cookie_jar=jar.return_value
            )
        self.assertIs(router._session, session_cls.return_value)
        self.assertEqual(router._base_headers["Origin"], "https://192.0.2.1")
        self.assertEqual(router._base_headers["Referer"], "https://192.0.2.1/")

    async def test_injected_session_is_not_owned_and_not_closed(self):
        session = fake_session(closed=False)
        router = make_router(session=session)
        self.assertFalse(router._owns_session)
        await router.async_close()
        session.close.assert_not_awaited()

    async def test_async_close_closes_owned_session_and_goform_session(self):
        session = fake_session()
        router = ZteRouterApi(base_url="https://192.0.2.1", session=None)
        # Close the real owned session before swapping in the fake, otherwise
        # it is only finalized by the garbage collector (ResourceWarning).
        await router._session.close()
        router._session = session
        goform = fake_session()
        router._goform_session = goform
        await router.async_close()
        goform.close.assert_awaited_once()
        session.close.assert_awaited_once()
        self.assertIsNone(router._goform_session)

    async def test_async_close_skips_already_closed_sessions(self):
        session = fake_session(closed=True)
        router = make_router(session=session)
        router._owns_session = True
        goform = fake_session(closed=True)
        router._goform_session = goform
        await router.async_close()
        session.close.assert_not_awaited()
        goform.close.assert_not_awaited()

    async def test_real_owned_session_is_created_and_closed(self):
        router = ZteRouterApi(base_url="https://192.0.2.1")
        self.assertIsInstance(router._session, aiohttp.ClientSession)
        await router.async_close()
        self.assertTrue(router._session.closed)

    async def test_tls_fingerprint_is_normalized_and_drives_connector(self):
        fingerprint = "AA:BB:CC" + ":DD" * 29
        with patch.object(aiohttp, "TCPConnector") as connector:
            router = ZteRouterApi(base_url="https://192.0.2.1", tls_fingerprint=fingerprint)
            pin = connector.call_args.kwargs["ssl"]
        self.assertIsInstance(pin, aiohttp.Fingerprint)
        self.assertEqual(pin.fingerprint, bytes.fromhex("aabbcc" + "dd" * 29))
        self.assertEqual(router.tls_fingerprint, "aabbcc" + "dd" * 29)
        self.assertEqual(router._tls_validation().fingerprint, pin.fingerprint)
        await router.async_close()

    async def test_invalid_fingerprint_is_rejected(self):
        for value in ("abc", "zz" * 32, "aa" * 31 + "gg", "aa" * 63):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "TLS fingerprint"):
                ZteRouterApi(base_url="https://192.0.2.1", tls_fingerprint=value)

    async def test_tls_validation_falls_back_to_verify_flag(self):
        self.assertIs(make_router(verify_tls=True)._tls_validation(), True)
        self.assertIs(make_router(verify_tls=False)._tls_validation(), False)

    async def test_connection_scheme_warnings(self):
        with self.assertLogs(api_module.__name__, level="WARNING") as captured:
            make_router(base_url="http://192.0.2.1/", allow_insecure_http=True)
        self.assertIn("unencrypted HTTP", "\n".join(captured.output))
        with self.assertLogs(api_module.__name__, level="WARNING") as captured:
            make_router(verify_tls=False, tls_fingerprint="")
        self.assertIn("verification is disabled", "\n".join(captured.output))
        with self.assertLogs(api_module.__name__, level="INFO") as captured:
            make_router(tls_fingerprint="ab" * 32)
        self.assertIn("pinned", "\n".join(captured.output))

    async def test_url_userinfo_is_stripped_for_browser_headers(self):
        cases = {
            "https://user:pw@192.0.2.1": "https://192.0.2.1",
            "http://user@192.0.2.1:8080/path/": "http://192.0.2.1:8080/path",
            "https://user@[2001:db8::1]:8443/": "https://[2001:db8::1]:8443",
            "https://192.0.2.1": "https://192.0.2.1",
            "": "",
        }
        for source, expected in cases.items():
            with self.subTest(source=source):
                self.assertEqual(ZteRouterApi._strip_url_userinfo(source), expected)

    async def test_ubus_url_rpc_ids_and_login_properties(self):
        router = logged_in_router(base_url="https://192.0.2.1/")
        with patch.object(api_module.time, "time", return_value=1.5):
            self.assertEqual(router._ubus_url(), "https://192.0.2.1/ubus/?t=1500")
        self.assertEqual([router._next_rpc_id() for _ in range(3)], [1, 2, 3])
        self.assertTrue(router.is_logged_in)
        self.assertEqual(router.login_method, "ubus")
        router._logged_in = False
        self.assertIsNone(router.login_method)
        self.assertFalse(router.is_logged_in)

    async def test_build_ubus_call_and_mark_session_stale(self):
        router = logged_in_router()
        router._http_encryption_key = KEY
        router._goform_field_cache["hardware_version"] = "x"
        router._seen_optional_core_failures.add(("a", "b", ()))
        self.assertEqual(
            router.build_ubus_call("svc", "method", {"p": 1}),
            {"service": "svc", "method": "method", "params": {"p": 1}},
        )
        self.assertEqual(
            router.build_ubus_call("svc", "method"),
            {"service": "svc", "method": "method", "params": {}},
        )
        router._mark_session_stale()
        self.assertFalse(router._logged_in)
        self.assertIsNone(router._session_id)
        self.assertIsNone(router._http_encryption_key)
        self.assertEqual(router._goform_field_cache, {})
        self.assertEqual(router._seen_optional_core_failures, set())
        router._seen_optional_core_failures = "not a set"
        router._mark_session_stale()

    async def test_invalidate_session_with_and_without_hass(self):
        goform = fake_session()
        router = logged_in_router()
        router._goform_session = goform
        router.invalidate_session()
        self.assertFalse(router._logged_in)
        self.assertIsNone(router._goform_session)
        await asyncio.sleep(0)
        goform.close.assert_awaited_once()

        hass = Mock()
        hass.async_create_task = Mock(side_effect=lambda coro: coro.close())
        goform2 = fake_session()
        router2 = logged_in_router(hass=hass)
        router2._goform_session = goform2
        router2.invalidate_session()
        hass.async_create_task.assert_called_once()
        goform2.close.assert_not_awaited()
        router2._goform_session = fake_session(closed=True)
        router2.invalidate_session()

    async def test_normalize_pem(self):
        body = "A" * 100 + "\n" + "B" * 50
        compact = f"-----BEGIN PUBLIC KEY-----{body}-----END PUBLIC KEY-----"
        normalized = ZteRouterApi._normalize_pem(compact)
        self.assertIn("\n", normalized)
        self.assertTrue(normalized.endswith("\n"))
        self.assertEqual(ZteRouterApi._normalize_pem("  plain  "), "plain")
        self.assertEqual(ZteRouterApi._normalize_pem(None), "")

    async def test_sha256_and_next_rpc_id(self):
        self.assertEqual(
            ZteRouterApi.sha256("abc"),
            hashlib.sha256(b"abc").hexdigest().upper(),
        )


class ErrorSummaryTests(unittest.TestCase):
    def test_safe_exception_summary_variants(self):
        cases = [
            (TimeoutError(), "timed out"),
            (type("CertificateVerifyError", (Exception,), {})(), "TLS certificate"),
            (RuntimeError("ssl CERTIFICATE_VERIFY_FAILED failed"), "TLS certificate"),
            (type("HttpError", (Exception,), {})(), "during router request"),
        ]
        http_error = type("HttpError", (Exception,), {})()
        http_error.status = 503
        cases.append((http_error, "HTTP 503"))
        for exc, expected in cases:
            with self.subTest(exc=type(exc).__name__):
                self.assertIn(expected, ZteRouterApi._safe_exception_summary(exc))
        for name in ("ClientConnectorError", "ClientConnectionError"):
            exc = type(name, (Exception,), {})()
            self.assertEqual(
                ZteRouterApi._safe_exception_summary(exc), "could not connect to router"
            )
        self.assertEqual(
            ZteRouterApi._safe_exception_summary(json.JSONDecodeError("bad", "", 0)),
            "router returned invalid JSON",
        )

    def test_safe_error_summary_keeps_known_errors(self):
        for exc in (
            api_module.UnsupportedLoginProtocol("unsupported"),
            api_module.RouterResponseError("bad response"),
            RuntimeError("UBUS login rejected"),
            RuntimeError("GoForm GET LD failed"),
            RuntimeError("Login failed: nope"),
        ):
            with self.subTest(exc=str(exc)):
                self.assertEqual(ZteRouterApi.safe_error_summary(exc), str(exc))
        self.assertEqual(
            ZteRouterApi.safe_error_summary(RuntimeError("password=secret")),
            "RuntimeError during router request",
        )
        self.assertTrue(issubclass(api_module.ZteAuthError, RuntimeError))
        self.assertTrue(issubclass(api_module.RouterResponseError, RuntimeError))

    def test_describe_rpc_failure(self):
        self.assertEqual(ZteRouterApi._describe_rpc_failure("x"), "invalid UBUS error response")
        self.assertEqual(
            ZteRouterApi._describe_rpc_failure({"kind": "transport", "message": "refused"}),
            "refused",
        )
        self.assertEqual(
            ZteRouterApi._describe_rpc_failure({"kind": "transport"}), "transport request failed"
        )
        self.assertEqual(ZteRouterApi._describe_rpc_failure({"status": 404}), "HTTP 404")
        self.assertEqual(ZteRouterApi._describe_rpc_failure({"code": -32002}), "RPC error -32002")
        self.assertEqual(
            ZteRouterApi._describe_rpc_failure({"message": "oops"}),
            "router returned an error without a code",
        )

    def test_connreset_detection_follows_exception_chain(self):
        direct = ConnectionResetError(104, "reset")
        self.assertTrue(ZteRouterApi._is_conn_reset_104(direct))
        self.assertTrue(ZteRouterApi._is_conn_reset_104(OSError(104, "reset")))
        self.assertFalse(ZteRouterApi._is_conn_reset_104(ConnectionResetError(99, "other")))
        inner = OSError(104, "reset")
        outer = RuntimeError("wrapper")
        outer.__cause__ = inner
        self.assertTrue(ZteRouterApi._is_conn_reset_104(outer))
        contextual = RuntimeError("context")
        contextual.__context__ = inner
        self.assertTrue(ZteRouterApi._is_conn_reset_104(contextual))
        a = RuntimeError("a")
        b = RuntimeError("b")
        a.__cause__ = b
        b.__cause__ = a
        self.assertFalse(ZteRouterApi._is_conn_reset_104(a))
        self.assertFalse(ZteRouterApi._is_conn_reset_104(None))


class SmsHelperTests(unittest.TestCase):
    def test_decode_sms_content(self):
        self.assertEqual(ZteRouterApi._decode_sms_content(None), "")
        self.assertEqual(ZteRouterApi._decode_sms_content("  "), "")
        self.assertEqual(ZteRouterApi._decode_sms_content("hello"), "hello")
        self.assertEqual(ZteRouterApi._decode_sms_content("00480069"), "Hi")
        self.assertEqual(ZteRouterApi._decode_sms_content(b"00480069"), "b'00480069'")
        self.assertEqual(ZteRouterApi._decode_sms_content("48656c6c6f"), "Hello")
        self.assertEqual(ZteRouterApi._decode_sms_content("00FF00"), "\xff")
        self.assertEqual(ZteRouterApi._decode_sms_content("004800690000000A"), "Hi")

    def test_decode_sms_number(self):
        for value in (None, "", "1234", "004812", "00GG", "+48123", "Orange"):
            with self.subTest(value=value):
                self.assertEqual(ZteRouterApi._decode_sms_number(value), str(value or ""))
        self.assertEqual(ZteRouterApi._decode_sms_number("004F00720061006E00670065"), "Orange")
        self.assertEqual(ZteRouterApi._decode_sms_number("0001"), "0001")
        self.assertEqual(ZteRouterApi._decode_sms_number("D800"), "D800")

    def test_normalize_sms_capacity_variants(self):
        self.assertEqual(ZteRouterApi._normalize_sms_capacity(None), {})
        self.assertEqual(ZteRouterApi._normalize_sms_capacity("invalid"), {})
        raw = {"sms_nv_rev_total": "2", "sms_nv_send_total": 3, "sms_nv_draftbox_total": "4"}
        self.assertEqual(ZteRouterApi._normalize_sms_capacity(raw)["sms_nvused_total"], 9)
        self.assertEqual(raw.get("sms_nvused_total", 0), 0)
        negative = {"sms_nv_rev_total": -1, "sms_nv_send_total": 2, "sms_nv_draftbox_total": 1}
        self.assertEqual(ZteRouterApi._normalize_sms_capacity(negative), negative)
        for bad in (
            {},
            {"sms_nv_rev_total": "x"},
            {"sms_nv_rev_total": None},
            {"sms_nv_rev_total": 10**400},
        ):
            with self.subTest(bad=bad):
                self.assertEqual(ZteRouterApi._normalize_sms_capacity(bad), bad)

    def test_parse_sms_compose_input(self):
        self.assertEqual(
            ZteRouterApi.parse_sms_compose_input(" +48 123 456 , Hello "), ("+48123456", "Hello")
        )
        self.assertEqual(ZteRouterApi.parse_sms_compose_input("123,Hi"), ("123", "Hi"))
        for value, message in (
            ("", "Expected format"),
            ("123", "Expected format"),
            (",Hi", "Missing destination"),
            ("12a,Hi", "only '+' and digits"),
            ("+1+2,Hi", "'+' placement"),
            ("1+2,Hi", "'+' placement"),
            ("123, ", "must not be empty"),
        ):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, re.escape(message)):
                ZteRouterApi.parse_sms_compose_input(value)

    def test_build_sms_time_string_offsets(self):
        cases = [
            (timezone(timedelta(hours=2)), "+2"),
            (timezone(timedelta(hours=-3)), "-3"),
            (timezone(timedelta(hours=5, minutes=30)), "+5.5"),
            (timezone(timedelta(hours=-4, minutes=-30)), "-4.5"),
            (None, "+0"),
        ]
        for tzinfo, expected in cases:
            with self.subTest(tzinfo=tzinfo):
                moment = datetime(2026, 11, 24, 13, 45, 6, tzinfo=tzinfo)
                clock = Mock()
                clock.now.return_value.astimezone.return_value = moment
                with patch.object(api_module, "datetime", clock):
                    value = ZteRouterApi._build_sms_time_string()
                self.assertTrue(value.endswith(";" + expected), value)
                self.assertTrue(value.startswith("26;11;24;13;45;06;"), value)

    def test_sms_encode_type_and_message_encoding(self):
        self.assertEqual(ZteRouterApi._get_sms_encode_type("Hello 123"), "GSM7_default")
        self.assertEqual(ZteRouterApi._get_sms_encode_type("Hallo {\u20ac}"), "GSM7_default")
        self.assertEqual(ZteRouterApi._get_sms_encode_type("Hello \U0001f600"), "UNICODE")
        self.assertEqual(ZteRouterApi._get_sms_encode_type("\u0141"), "UNICODE")
        self.assertEqual(ZteRouterApi._encode_sms_message("Hi!"), "00480069 0021".replace(" ", ""))
        self.assertEqual(ZteRouterApi._encode_sms_message("\U0001f600"), "1F600")

    def test_decrypt_sms_field_defensive_branches(self):
        router = make_router()
        self.assertEqual(router._decrypt_sms_field("x"), "x")
        router._http_encryption_key = KEY
        self.assertEqual(router._decrypt_sms_field(None), None)
        self.assertEqual(router._decrypt_sms_field("short"), "short")
        for invalid in ("not base64!", base64.b64encode(b"short").decode(), seal("x", OTHER_KEY)):
            with self.subTest(invalid=invalid[:20]):
                self.assertEqual(router._decrypt_sms_field(invalid), invalid)
        tampered = bytearray(base64.b64decode(seal("hello")))
        tampered[-1] ^= 1
        self.assertEqual(
            router._decrypt_sms_field(base64.b64encode(tampered).decode()),
            base64.b64encode(tampered).decode(),
        )
        binary = base64.b64encode(b"\x00" * 12 + b"\x00" * 16 + b"\xff\xfe").decode()
        self.assertEqual(router._decrypt_sms_field(binary), binary)
        self.assertEqual(router._decrypt_sms_field(seal("00480069")), "00480069")

    def test_parse_sms_message_fields_and_format_detection(self):
        router = make_router()
        parsed = router._parse_sms_message(
            {
                "id": 7,
                "number": "+48123",
                "date": "26,11,24",
                "tag": "1",
                "mem_store": "nv",
                "content": "00480069",
            }
        )
        self.assertEqual(
            parsed,
            {
                "id": 7,
                "number": "+48123",
                "date": "26,11,24",
                "tag": "1",
                "mem_store": "nv",
                "content_raw": "00480069",
                "content_decoded": "Hi",
            },
        )
        self.assertEqual(router._sms_encryption, "plain")
        router._sms_encryption = None
        router._parse_sms_message({"content": "not hex"})
        self.assertIsNone(router._sms_encryption)
        router._parse_sms_message({"content": "0001"})
        self.assertIsNone(router._sms_encryption)
        router._http_encryption_key = KEY
        router._parse_sms_message({"content": seal("00480069")})
        self.assertEqual(router._sms_encryption, "aes_gcm")

    def test_encryption_profile_detection_and_field_encryption(self):
        router = make_router()
        router._update_sms_encryption_from_device({"model": "G51F"})
        self.assertEqual(router._sms_encryption, "aes_gcm")
        router._http_encryption_key = KEY
        first, second = router._encrypt_sms_field("+48123"), router._encrypt_sms_field("+48123")
        self.assertNotEqual(first, second)
        self.assertEqual(router._decrypt_sms_field(first), "+48123")
        router._http_encryption_key = None
        with self.assertRaisesRegex(ValueError, "session key"):
            router._encrypt_sms_field("+48123")
        plain = make_router()
        plain._sms_encryption = None
        with self.assertRaisesRegex(ValueError, "no SMS sent"):
            plain._encrypt_sms_field("+48123")
        plain._update_sms_encryption_from_device(
            {"hardware_version": "BD_G5TCV1.0", "model_name": "G5TC"}, {"wa_inner_version": "x"}
        )
        self.assertEqual(plain._sms_encryption, "plain")
        self.assertEqual(plain._encrypt_sms_field("+48123"), "+48123")
        for identity in ("G5 MAX", "G5 ULTRA", "MC8830", "G5TS", "G5C"):
            fresh = make_router()
            fresh._update_sms_encryption_from_device({"model": identity})
            self.assertEqual(fresh._sms_encryption, "plain", identity)
        for identity in ("MC7510", "G51F"):
            fresh = make_router()
            fresh._update_sms_encryption_from_device({"model": identity})
            self.assertEqual(fresh._sms_encryption, "aes_gcm", identity)
        for identity in ("", "unknown", "XXG51FXX", "G51F0"):
            fresh = make_router()
            fresh._update_sms_encryption_from_device({"model": identity})
            self.assertIsNone(fresh._sms_encryption, identity)
        router._decrypt_sms_field(first)
        self.assertEqual(router._sms_encryption, "aes_gcm")


class BandHelperTests(unittest.TestCase):
    def test_lte_earfcn_mapping(self):
        self.assertIsNone(ZteRouterApi._convert_lte_earfcn_to_band(None))
        for earfcn, band in (
            (0, 1),
            (599, 1),
            (1200, 3),
            (1950, 4),
            (2400, 5),
            (2750, 7),
            (3450, 8),
            (6150, 20),
            (9210, 28),
            (9920, 32),
            (37750, 38),
            (38650, 40),
            (41590, 42),
            (43590, 43),
        ):
            with self.subTest(earfcn=earfcn):
                self.assertEqual(ZteRouterApi._convert_lte_earfcn_to_band(earfcn), band)
        self.assertIsNone(ZteRouterApi._convert_lte_earfcn_to_band(999999))

    def test_nr_arfcn_mapping(self):
        self.assertIsNone(ZteRouterApi._convert_nr_arfcn_to_band(None))
        for arfcn, band in (
            (422000, 1),
            (361000, 3),
            (173800, 5),
            (524000, 7),
            (185000, 8),
            (151600, 28),
            (460000, 40),
            (499200, 41),
            (286400, 75),
            (620000, 78),
            (693334, 79),
        ):
            with self.subTest(arfcn=arfcn):
                self.assertEqual(ZteRouterApi._convert_nr_arfcn_to_band(arfcn), band)
        self.assertIsNone(ZteRouterApi._convert_nr_arfcn_to_band(42))

    def test_compute_bands_and_bandwidth(self):
        router = make_router()
        self.assertEqual(router._compute_bands_and_bw({}), ("-", 0.0))
        for bad in ("abc", None, ""):
            with self.subTest(bad=bad):
                self.assertEqual(
                    router._compute_bands_and_bw(
                        {
                            "lte_action_channel": bad,
                            "lte_bandwidth": bad,
                            "nr5g_action_channel": bad,
                            "nr5g_bandwidth": bad,
                        }
                    ),
                    ("-", 0.0),
                )
        self.assertEqual(
            router._compute_bands_and_bw(
                {
                    "lte_action_channel": "100",
                    "lte_bandwidth": "20",
                    "nr5g_action_channel": "620000",
                    "nr5g_bandwidth": "100",
                }
            ),
            ("B1 + n78", 120.0),
        )
        self.assertEqual(
            router._compute_bands_and_bw(
                {
                    "lte_action_channel": "100",
                    "lte_bandwidth": 20,
                    "nr5g_action_channel": "620000",
                    "nr5g_bandwidth": 100,
                }
            ),
            ("B1 + n78", 120.0),
        )
        self.assertEqual(
            router._compute_bands_and_bw(
                {
                    "lte_action_channel": "100",
                    "lte_bandwidth": "0",
                    "nr5g_action_channel": "999999",
                    "nr5g_bandwidth": "5",
                }
            ),
            ("-", 5.0),
        )


class CellLockTests(unittest.IsolatedAsyncioTestCase):
    def test_normalize_and_read_lock_values(self):
        self.assertEqual(ZteRouterApi._norm_cell_lock_str(None), "")
        self.assertEqual(ZteRouterApi._norm_cell_lock_str(" 12,1300;; "), "12,1300")
        self.assertEqual(ZteRouterApi.get_4g_cell_lock_value(None), "0,0")
        self.assertEqual(ZteRouterApi.get_4g_cell_lock_value({}), "0,0")
        self.assertEqual(ZteRouterApi.get_4g_cell_lock_value({"lock_lte_cell": "1,2"}), "1,2")
        self.assertEqual(ZteRouterApi.get_5g_cell_lock_value(None), "0,0,0")
        self.assertEqual(ZteRouterApi.get_5g_cell_lock_value({"lock_nr_cell": "1,2,78"}), "1,2,78")
        self.assertFalse(ZteRouterApi.is_4g_cell_lock_active(None))
        self.assertFalse(ZteRouterApi.is_4g_cell_lock_active({}))
        self.assertTrue(ZteRouterApi.is_4g_cell_lock_active({"lock_lte_cell": "1,2"}))
        self.assertFalse(ZteRouterApi.is_5g_cell_lock_active(None))
        self.assertFalse(ZteRouterApi.is_5g_cell_lock_active({"lock_nr_cell": ";0,0,0;"}))
        self.assertTrue(ZteRouterApi.is_5g_cell_lock_active({"lock_nr_cell": "1,2,78"}))

    def test_suggest_lock_texts(self):
        self.assertEqual(ZteRouterApi.suggest_4g_cell_lock_text(None), "")
        self.assertEqual(ZteRouterApi.suggest_4g_cell_lock_text({}), "")
        self.assertEqual(ZteRouterApi.suggest_4g_cell_lock_text({"lock_lte_cell": "7,8"}), "7,8")
        self.assertEqual(
            ZteRouterApi.suggest_4g_cell_lock_text({"lte_pci": 12, "lte_action_channel": "1300"}),
            "12,1300",
        )
        for info in (
            {"lte_pci": "x", "lte_action_channel": 1},
            {"lte_pci": 1, "lte_action_channel": "y"},
            {"lte_pci": 1},
        ):
            with self.subTest(info=info):
                self.assertEqual(ZteRouterApi.suggest_4g_cell_lock_text(info), "")

        self.assertEqual(ZteRouterApi.suggest_5g_cell_lock_text(None), "")
        self.assertEqual(ZteRouterApi.suggest_5g_cell_lock_text({}), "")
        self.assertEqual(
            ZteRouterApi.suggest_5g_cell_lock_text({"lock_nr_cell": "1,2,78"}), "1,2,78"
        )
        self.assertEqual(
            ZteRouterApi.suggest_5g_cell_lock_text(
                {
                    "nr5g_pci": 3,
                    "nr5g_action_channel": "620000",
                    "nr5g_action_band": "n78",
                }
            ),
            "3,620000,78",
        )
        self.assertEqual(
            ZteRouterApi.suggest_5g_cell_lock_text(
                {
                    "nr5g_pci": 3,
                    "nr5g_action_channel": "620000",
                    "nr5g_action_band": "oops",
                }
            ),
            "3,620000,78",
        )
        self.assertEqual(
            ZteRouterApi.suggest_5g_cell_lock_text(
                {
                    "nr5g_pci": 3,
                    "nr5g_action_channel": "620000",
                    "nr5g_action_band": None,
                }
            ),
            "3,620000,78",
        )
        for info in (
            {"nr5g_pci": 3, "nr5g_action_channel": "bad"},
            {"nr5g_pci": 1, "nr5g_action_channel": 2, "nr5g_action_band": "bad"},
            {"nr5g_pci": "x", "nr5g_action_channel": 2, "nr5g_action_band": "n78"},
            {"nr5g_pci": 1},
        ):
            with self.subTest(info=info):
                self.assertEqual(ZteRouterApi.suggest_5g_cell_lock_text(info), "")

    def test_parse_cell_lock_inputs(self):
        self.assertEqual(ZteRouterApi.parse_4g_cell_lock_input(" 12 , 1300 "), (12, 1300))
        self.assertEqual(ZteRouterApi.parse_5g_cell_lock_input("3,620000,78"), (3, 620000, 78))
        for text in (None, "1", "1,2,3", "x,2", "1,x", "-1,2", "1,-2", "504,2"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                ZteRouterApi.parse_4g_cell_lock_input(text)
        for text in (
            None,
            "1,2",
            "1,2,3,4",
            "x,2,3",
            "1,x,3",
            "1,2,x",
            "-1,2,3",
            "1,-2,3",
            "1,2,-3",
            "1008,2,3",
        ):
            with self.subTest(text=text), self.assertRaises(ValueError):
                ZteRouterApi.parse_5g_cell_lock_input(text)

    async def test_cell_lock_write_helpers(self):
        router = logged_in_router()
        router.async_execute_ubus_action = AsyncMock(return_value=True)
        self.assertTrue(await router.async_lock_4g_cell("12", 1300))
        self.assertEqual(
            router.async_execute_ubus_action.call_args.args[0],
            {
                "service": "zte_nwinfo_api",
                "method": "nwinfo_lock_lte_cell",
                "params": {"lock_lte_pci": "12", "lock_lte_earfcn": "1300"},
            },
        )
        await router.async_unlock_4g_cell()
        self.assertEqual(
            router.async_execute_ubus_action.call_args.args[0]["params"],
            {"lock_lte_pci": "0", "lock_lte_earfcn": "0"},
        )
        self.assertTrue(await router.async_lock_5g_cell(3, 620000, 78))
        self.assertEqual(
            router.async_execute_ubus_action.call_args.args[0]["params"],
            {"lock_nr_pci": "3", "lock_nr_earfcn": "620000", "lock_nr_cell_band": "78"},
        )
        await router.async_unlock_5g_cell()
        self.assertEqual(
            router.async_execute_ubus_action.call_args.args[0]["params"],
            {"lock_nr_pci": "0", "lock_nr_earfcn": "0", "lock_nr_cell_band": "0"},
        )
        self.assertTrue(await router.async_set_4g_cell_lock_from_text("12,1300"))
        self.assertTrue(await router.async_set_5g_cell_lock_from_text("3,620000,78"))
        self.assertTrue(await router.async_set_4g_cell_lock_enabled(True, value="12,1300"))
        self.assertTrue(await router.async_set_4g_cell_lock_enabled(False))
        self.assertTrue(await router.async_set_5g_cell_lock_enabled(True, value="3,620000,78"))
        self.assertTrue(await router.async_set_5g_cell_lock_enabled(False))
        for method in (
            router.async_set_4g_cell_lock_enabled,
            router.async_set_5g_cell_lock_enabled,
        ):
            with self.assertRaisesRegex(ValueError, "Missing value"):
                await method(True)
            with self.assertRaisesRegex(ValueError, "Missing value"):
                await method(True, value="")


def install_login(router, *, fail=False):
    async def login(*, force=False):
        if fail:
            raise RuntimeError("login unavailable")
        router._logged_in = True
        router._session_id = "new-session"

    router._async_ensure_logged_in = AsyncMock(side_effect=login)
    return router


class AuthTests(unittest.IsolatedAsyncioTestCase):
    async def test_ubus_login_challenge_and_encryption_setup(self):
        router = logged_in_router()
        router._logged_in = False
        router._session_id = None
        router._http_encryption_key = KEY
        responses = [
            ok({"zte_web_sault": "salt"}),
            ok({"ubus_rpc_session": "sid"}),
        ]
        router.async_call_ubus = AsyncMock(side_effect=responses)
        router._async_setup_http_encryption = AsyncMock()
        await router._async_ubus_login()
        challenge, login = router.async_call_ubus.call_args_list
        self.assertEqual(challenge.args[0]["method"], "web_login_info")
        self.assertEqual(challenge.kwargs["session_id"], "0" * 32)
        self.assertFalse(challenge.kwargs["retry_on_access_denied"])
        expected = ZteRouterApi.sha256(ZteRouterApi.sha256("secret") + "salt")
        self.assertEqual(login.args[0]["params"]["password"], expected)
        self.assertEqual(router._session_id, "sid")
        self.assertTrue(router.is_logged_in)
        router._async_setup_http_encryption.assert_awaited_once()

    async def test_ubus_login_accepts_salt_alias(self):
        router = logged_in_router()
        router._logged_in = False
        router.async_call_ubus = AsyncMock(
            side_effect=[
                ok({"salt": "other"}),
                ok({"ubus_rpc_session": "sid"}),
            ]
        )
        router._async_setup_http_encryption = AsyncMock()
        await router._async_ubus_login()
        self.assertEqual(router._session_id, "sid")

    async def test_ubus_login_unsupported_protocol_branches(self):
        for response in (
            {"success": False, "error": {"code": -32601}},
            {"success": False, "error": {"status": 404}},
            {"success": False, "error": {"status": 405}},
            {"success": False, "error": {"status": 501}},
            {"success": True, "data": "invalid"},
            {"success": True, "data": {}},
            {"success": True, "data": {"salt": 123}},
        ):
            with self.subTest(response=response):
                router = logged_in_router()
                router.async_call_ubus = AsyncMock(return_value=response)
                with self.assertRaises(api_module.UnsupportedLoginProtocol):
                    await router._async_ubus_login()

    async def test_ubus_login_errors_and_missing_session_id(self):
        router = logged_in_router()
        router.async_call_ubus = AsyncMock(
            return_value={
                "success": False,
                "error": {"message": "refused", "kind": "transport"},
            }
        )
        with self.assertRaisesRegex(RuntimeError, "refused"):
            await router._async_ubus_login()

        router = logged_in_router()
        router.async_call_ubus = AsyncMock(
            side_effect=[
                ok({"salt": "s"}),
                {"success": False, "error": {"code": -32002, "message": "denied"}},
            ]
        )
        with self.assertRaises(api_module.ZteAuthError):
            await router._async_ubus_login()

        for payload in ({"success": True, "data": {}}, {"success": True, "data": "bad"}):
            router = logged_in_router()
            router.async_call_ubus = AsyncMock(side_effect=[ok({"salt": "s"}), payload])
            with self.assertRaisesRegex(RuntimeError, "ubus_rpc_session"):
                await router._async_ubus_login()

    async def test_async_login_success_and_fallback_branches(self):
        router = logged_in_router()
        router._async_ubus_login = AsyncMock()
        router._async_goform_login = AsyncMock()
        await router.async_login()
        self.assertEqual(router._api_mode, "ubus")
        router._async_goform_login.assert_not_awaited()

        router = logged_in_router()
        router._async_ubus_login = AsyncMock(
            side_effect=api_module.UnsupportedLoginProtocol("unsupported")
        )
        router._async_goform_login = AsyncMock()
        await router.async_login()
        router._async_goform_login.assert_awaited_once()
        self.assertEqual(router._api_mode, "ubus")

        router = logged_in_router()
        router._async_ubus_login = AsyncMock(
            side_effect=api_module.UnsupportedLoginProtocol("unsupported")
        )
        router._async_goform_login = AsyncMock(side_effect=api_module.ZteAuthError("rejected"))
        with self.assertRaises(api_module.ZteAuthError):
            await router.async_login()

        router = logged_in_router()
        router._async_ubus_login = AsyncMock(
            side_effect=api_module.UnsupportedLoginProtocol("unsupported")
        )
        router._async_goform_login = AsyncMock(side_effect=RuntimeError("boom"))
        with self.assertRaisesRegex(RuntimeError, "Login failed: UBUS protocol unsupported"):
            await router.async_login()

        router = logged_in_router()
        router._async_ubus_login = AsyncMock(side_effect=RuntimeError("ubus down"))
        with self.assertRaisesRegex(RuntimeError, "ubus down"):
            await router.async_login()

    async def test_async_ensure_logged_in_branches(self):
        router = make_router()
        router.async_login = AsyncMock()
        await router._async_ensure_logged_in()
        router.async_login.assert_awaited_once()

        router = logged_in_router()
        router.async_login = AsyncMock()
        await router._async_ensure_logged_in()
        router.async_login.assert_not_awaited()

        router._session_id = None
        await router._async_ensure_logged_in()
        router.async_login.assert_awaited_once()

        goform = fake_session()
        router._goform_session = goform
        router._api_mode = "goform"
        goform.close.side_effect = RuntimeError("already closed")
        await router._async_ensure_logged_in(force=True)
        self.assertIsNone(router._goform_session)
        self.assertEqual(router.async_login.await_count, 2)

    async def test_http_encryption_setup_short_circuits(self):
        router = logged_in_router()
        router._session_id = None
        router.async_call_ubus = AsyncMock()
        await router._async_setup_http_encryption()
        router.async_call_ubus.assert_not_awaited()

        router = logged_in_router()
        router.async_call_ubus = AsyncMock(return_value=ok({"result": ""}))
        await router._async_setup_http_encryption()
        self.assertIsNone(router._http_encryption_key)
        router.async_call_ubus.assert_awaited_once()

    async def test_http_encryption_setup_with_public_key_pem(self):
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = (
            private_key.public_key()
            .public_bytes(
                serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
            )
            .decode()
        )
        router = logged_in_router()
        router._http_encryption_key = None
        calls = []

        async def call_ubus(request, **kwargs):
            calls.append((request, kwargs))
            if request["method"] == "web_crt_get":
                return ok({"result": pem})
            encrypted = base64.b64decode(request["params"]["web_enstr"])
            key_hex = private_key.decrypt(encrypted, padding.PKCS1v15()).decode()
            return ok({"result": "success"}) if key_hex else ok({})

        router.async_call_ubus = AsyncMock(side_effect=call_ubus)
        await router._async_setup_http_encryption()
        self.assertIsNotNone(router._http_encryption_key)
        self.assertEqual(len(bytes.fromhex(router._http_encryption_key)), 32)
        self.assertEqual(calls[0][1]["z_mode_override"], "0")
        self.assertFalse(calls[0][1]["retry_on_access_denied"])
        self.assertEqual(calls[1][0]["method"], "web_http_enstr_set")

    async def test_http_encryption_setup_compact_key_certificate_and_failures(self):
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        der = private_key.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        compact = base64.b64encode(der).decode()

        async def run(cert, *, set_response=None, patch_parser=None):
            router = logged_in_router()
            router._http_encryption_key = None

            async def call_ubus(request, **kwargs):
                if request["method"] == "web_crt_get":
                    return ok({"crt": cert})
                return set_response if set_response is not None else ok({"result": "ok"})

            router.async_call_ubus = AsyncMock(side_effect=call_ubus)
            if patch_parser == "x509":
                with patch.object(x509, "load_pem_x509_certificate") as loader:
                    loader.return_value.public_key.return_value = private_key.public_key()
                    await router._async_setup_http_encryption()
            elif patch_parser == "broken":
                with (
                    patch.object(
                        serialization, "load_pem_public_key", side_effect=ValueError("bad")
                    ),
                    patch.object(x509, "load_pem_x509_certificate", side_effect=ValueError("bad")),
                ):
                    await router._async_setup_http_encryption()
            else:
                await router._async_setup_http_encryption()
            return router

        compact_router = await run(compact)
        self.assertIsNotNone(compact_router._http_encryption_key)

        certificate_router = await run(
            "-----BEGIN CERTIFICATE-----\nabc\n-----END CERTIFICATE-----", patch_parser="x509"
        )
        self.assertIsNotNone(certificate_router._http_encryption_key)

        broken = await run(
            "-----BEGIN CERTIFICATE-----\nabc\n-----END CERTIFICATE-----", patch_parser="broken"
        )
        self.assertIsNone(broken._http_encryption_key)

        pem_router = await run(
            private_key.public_key()
            .public_bytes(
                serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
            )
            .decode(),
            set_response={"success": True, "data": {"result": "FAILURE"}},
        )
        self.assertIsNone(pem_router._http_encryption_key)

        no_success = await run(
            private_key.public_key()
            .public_bytes(
                serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
            )
            .decode(),
            set_response={"success": False},
        )
        self.assertIsNone(no_success._http_encryption_key)

        failing = logged_in_router()
        failing.async_call_ubus = AsyncMock(side_effect=RuntimeError("boom"))
        await failing._async_setup_http_encryption()
        self.assertIsNone(failing._http_encryption_key)


class GoFormHttpTests(unittest.IsolatedAsyncioTestCase):
    async def test_goform_session_created_once_and_closed(self):
        with (
            patch.object(aiohttp, "TCPConnector") as connector,
            patch.object(aiohttp, "CookieJar") as jar,
            patch.object(aiohttp, "ClientSession") as session_cls,
        ):
            router = make_router(tls_fingerprint="ab" * 32)
            first = await router._async_get_goform_session()
            second = await router._async_get_goform_session()
        self.assertIs(first, second)
        self.assertIs(first, session_cls.return_value)
        connector.assert_called_once()
        jar.assert_called_once_with(unsafe=True)

    async def test_goform_get_request_and_payload_validation(self):
        session = fake_session(get=FakeResponse(payload={"field": "value"}))
        router = logged_in_router()
        router._async_get_goform_session = AsyncMock(return_value=session)
        self.assertEqual(await router._async_goform_get("field", {"x": "1"}), {"field": "value"})
        request = session.get.call_args
        self.assertEqual(request.args[0], "https://192.0.2.1/goform/goform_get_cmd_process")
        self.assertEqual(request.kwargs["params"]["cmd"], "field")
        self.assertEqual(request.kwargs["params"]["x"], "1")
        self.assertEqual(request.kwargs["params"]["isTest"], "false")
        self.assertEqual(request.kwargs["headers"]["X-Requested-With"], "XMLHttpRequest")
        self.assertEqual(request.kwargs["timeout"].total, 15)

        session.get.return_value = FakeResponse(payload=["not", "a", "dict"])
        with self.assertRaisesRegex(RuntimeError, "GoForm GET field failed"):
            await router._async_goform_get("field", raise_errors=True)

    async def test_goform_get_error_paths(self):
        session = fake_session()
        router = logged_in_router()
        router._async_get_goform_session = AsyncMock(return_value=session)

        session.get.return_value = FakeResponse(
            content_type="text/html", status_error=RuntimeError("403")
        )
        with self.assertRaisesRegex(RuntimeError, "GoForm GET LD failed"):
            await router._async_goform_get("LD", raise_errors=True)
        self.assertEqual(await router._async_goform_get("LD"), {})

        session.get.return_value = FakeResponse(content_type="text/html")
        with self.assertRaises(api_module.RouterResponseError):
            await router._async_goform_get("LD", raise_errors=True)
        self.assertEqual(await router._async_goform_get("LD"), {})

        session.get.side_effect = json.JSONDecodeError("bad", "", 0)
        with self.assertRaisesRegex(
            RuntimeError, "GoForm GET LD failed: router returned invalid JSON"
        ):
            await router._async_goform_get("LD", raise_errors=True)
        self.assertEqual(await router._async_goform_get("LD"), {})

    async def test_goform_set_request_and_error_paths(self):
        session = fake_session(post=FakeResponse(payload={"result": 0}))
        router = logged_in_router()
        router._async_get_goform_session = AsyncMock(return_value=session)
        self.assertEqual(await router._async_goform_set({"goformId": "LOGIN"}), {"result": 0})
        request = session.post.call_args
        self.assertEqual(request.args[0], "https://192.0.2.1/goform/goform_set_cmd_process")
        self.assertEqual(request.kwargs["data"], {"goformId": "LOGIN"})
        self.assertIn("urlencoded", request.kwargs["headers"]["Content-Type"])
        self.assertEqual(request.kwargs["timeout"].total, 15)

        session.post.return_value = FakeResponse(content_type="text/html")
        with self.assertRaises(api_module.RouterResponseError):
            await router._async_goform_set({}, raise_errors=True)
        self.assertEqual(await router._async_goform_set({}), {})

        session.post.return_value = FakeResponse(payload=["x"])
        with self.assertRaisesRegex(RuntimeError, "GoForm POST failed"):
            await router._async_goform_set({}, raise_errors=True)

        session.post.side_effect = TimeoutError()
        with self.assertRaisesRegex(RuntimeError, "GoForm POST failed: request timed out"):
            await router._async_goform_set({}, raise_errors=True)
        self.assertEqual(await router._async_goform_set({}), {})

    async def test_goform_init_session_error_paths(self):
        session = fake_session()
        router = logged_in_router()
        router._async_get_goform_session = AsyncMock(return_value=session)
        await router._async_goform_init_session()
        self.assertEqual(session.get.call_args.args[0], "https://192.0.2.1/index.html")

        session.get.return_value = FakeResponse(status_error=RuntimeError("500"), status=500)
        with self.assertRaisesRegex(RuntimeError, "GoForm session init failed"):
            await router._async_goform_init_session(raise_errors=True)
        await router._async_goform_init_session()

        session.get.side_effect = RuntimeError("offline")
        with self.assertRaisesRegex(RuntimeError, "GoForm session init failed"):
            await router._async_goform_init_session(raise_errors=True)
        await router._async_goform_init_session()

    async def test_goform_login_branches(self):
        router = logged_in_router()
        router._api_mode = "ubus"
        router._logged_in = False
        router._async_goform_init_session = AsyncMock()
        router._async_goform_get = AsyncMock(return_value={"LD": "nonce"})
        router._async_goform_set = AsyncMock(return_value={"result": 0})
        await router._async_goform_login()
        self.assertTrue(router.is_logged_in)
        self.assertEqual(router.login_method, "goform")
        expected = (
            hashlib.sha256((hashlib.sha256(b"secret").hexdigest().upper() + "nonce").encode())
            .hexdigest()
            .upper()
        )
        self.assertEqual(router._async_goform_set.call_args.args[0]["password"], expected)
        router._async_goform_init_session.assert_awaited_once_with(raise_errors=True)

        router._async_goform_get = AsyncMock(return_value={})
        with self.assertRaisesRegex(RuntimeError, "LD nonce is empty"):
            await router._async_goform_login()

        router._async_goform_get = AsyncMock(return_value={"LD": "nonce"})
        router._async_goform_set = AsyncMock(return_value={"result": 1})
        with self.assertRaises(api_module.ZteAuthError):
            await router._async_goform_login()

    async def test_goform_field_helpers(self):
        self.assertTrue(ZteRouterApi._goform_has_usable_payload({"network_type": "5G"}))
        self.assertTrue(
            ZteRouterApi._goform_has_usable_payload(
                {"ppp_status": "-", "wifi_chip1_ssid1_ssid": "wifi"}
            )
        )
        for payload in ({}, {"network_type": ""}, {"network_type": None}, {"network_type": "null"}):
            self.assertFalse(ZteRouterApi._goform_has_usable_payload(payload))

        router = logged_in_router()

        async def get_field(field):
            return {field: field.upper()} if field != "missing" else "bad"

        router._async_goform_get = AsyncMock(side_effect=get_field)
        self.assertEqual(
            await router._async_goform_get_fields(["a", "missing", "b"]),
            {"a": "A", "missing": None, "b": "B"},
        )

    async def test_goform_update_all_maps_payloads(self):
        router = logged_in_router()
        fields = {
            "network_type": "5G",
            "network_signalbar": "4",
            "network_provider_fullname": "Net",
            "network_rmcc": "260",
            "network_rmnc": "01",
            "network_Z5g_CELL_ID": "cell",
            "lte_pci": "12",
            "wan_active_channel": "100",
            "network_lte_ca_pcell_band": "B1",
            "network_lte_ca_pcell_bandwidth": "20",
            "network_lte_rsrp": "-80",
            "lte_rsrq": "-10",
            "lte_snr": "5",
            "lte_rssi": "-60",
            "network_Z5g_PCI": "3",
            "nr5g_action_band": "n78",
            "nr5g_action_channel": "620000",
            "nr5g_nsa_bandwidth": "100",
            "Z5g_rsrp": "-90",
            "Z5g_rsrq": "-11",
            "Z5g_SINR": "7",
            "Z5g_rssi": "-70",
            "wifi_onoff_state": "1",
            "RadioOff": "0",
            "wifi_chip1_ssid1_ssid": "2g",
            "wifi_chip2_ssid1_ssid": "5g",
            "wifi_chip1_ssid1_access_sta_num": "2",
            "wifi_chip2_ssid1_access_sta_num": "bad",
            "mwan_wanlan1_link_state": "up",
            "ppp_status": "connected",
            "flux_realtime_rx_thrpt": "10",
            "flux_realtime_tx_thrpt": "20",
            "flux_realtime_time": "30",
            "flux_monthly_rx_bytes": "40",
            "flux_monthly_tx_bytes": "50",
            "modem_main_state": "online",
            "hardware_version": "hw",
            "wa_inner_version": "fw",
            "device_uptime": "99",
            "cpu_usage": "15",
            "cpuUsage": "16",
            "cpu_load": "17",
            "cpuload": "18",
            "hightemp_datalimit_status": "0",
            "5g_modem_temperature": "40",
            "mwan_wanlan1_ipv6_wan_ipaddr": "2001:db8::1",
        }
        special = {
            "lan_station_list": {"lan_station_list": [{"mac": "x"}]},
            "sms_capacity_info": {
                "sms_nv_total": "100",
                "sms_sim_total": "20",
                "sms_nv_rev_total": "3",
                "sms_nv_send_total": "4",
                "sms_nv_draftbox_total": "5",
                "sms_sim_rev_total": "2",
            },
            "sms_data_total": {
                "messages": [
                    {"id": 1, "number": "+48123", "content": "00480069"},
                    "invalid",
                    {"id": 2, "number": None, "content": None},
                ]
            },
        }

        async def goform_get(field, extra=None, **kwargs):
            if field in special:
                return special[field]
            return {field: fields.get(field)}

        router._async_goform_get = AsyncMock(side_effect=goform_get)
        data = await router._async_goform_update_all()
        self.assertEqual(data["netinfo"]["network_type"], "5G")
        self.assertEqual(data["bands_summary"], "B1 + n78")
        self.assertEqual(data["total_bw_mhz"], 120.0)
        self.assertEqual(data["wlan"]["main2g_ssid"], "2g")
        self.assertEqual(data["user_list_num"], {"lan_num": 1, "wireless_num": 2})
        self.assertEqual(data["wan"]["mwan_wanlan1_ipv6_wan_ipaddr"], "2001:db8::1")
        self.assertEqual(data["common_config"]["hardware_version"], "hw")
        self.assertEqual(data["sms"]["capacity"]["sms_nvused_total"], "12")
        self.assertEqual(data["sms"]["capacity"]["sms_dev_unread_num"], "5")
        self.assertEqual(len(data["sms"]["messages"]), 2)
        self.assertEqual(data["sms"]["latest"]["content_decoded"], "Hi")
        self.assertEqual(router._goform_field_cache["hardware_version"], "hw")
        self.assertEqual(router._goform_field_cache["wa_inner_version"], "fw")

        # Cached static fields are reused; malformed special responses are tolerated.
        router._async_goform_get = AsyncMock(
            side_effect=lambda field, extra=None, **kwargs: (
                {"field": "x"} if field in special else {field: "cached"}
            )
        )
        data2 = await router._async_goform_update_all()
        self.assertEqual(data2["common_config"]["hardware_version"], "hw")
        self.assertEqual(data2["common_config"]["wa_inner_version"], "fw")

    async def test_goform_update_all_rejects_empty_payload(self):
        router = logged_in_router()
        router._async_goform_get = AsyncMock(return_value={})
        with self.assertRaisesRegex(RuntimeError, "no usable payload"):
            await router._async_goform_update_all()

    async def test_goform_update_all_defensive_value_parsing(self):
        router = logged_in_router()
        minimal = {"network_type": "LTE", "network_signalbar": "2"}

        async def goform_get(field, extra=None, **kwargs):
            if field in ("sms_capacity_info", "sms_data_total", "lan_station_list"):
                return {
                    "sms_nv_rev_total": "bad",
                    "sms_nv_send_total": None,
                    "sms_data": "bad",
                    "lan_station_list": "bad",
                }
            return {field: minimal.get(field)}

        router._async_goform_get = AsyncMock(side_effect=goform_get)
        data = await router._async_goform_update_all()
        self.assertEqual(data["user_list_num"], {"lan_num": 0, "wireless_num": 0})
        self.assertEqual(data["sms"]["capacity"]["sms_nvused_total"], "0")
        self.assertEqual(data["sms"]["capacity"]["sms_dev_unread_num"], "0")
        self.assertEqual(data["sms"]["messages"], [])
        self.assertIsNone(data["sms"]["latest"])

    async def test_goform_update_fast(self):
        router = logged_in_router()
        values = {
            "flux_realtime_rx_thrpt": "12",
            "flux_realtime_tx_thrpt": "34",
            "flux_realtime_time": "56",
            "ppp_status": "connected",
            "cpu_usage": "10",
            "cpu_load": "11",
            "cpuload": "12",
        }
        router._async_goform_get = AsyncMock(side_effect=lambda field: {field: values.get(field)})
        data = await router._async_goform_update_fast()
        self.assertEqual(data["wan"]["current_wan_status"], "connected")
        self.assertEqual(data["wwandst"]["real_rx_speed"], "12")
        self.assertEqual(data["device"]["cpu_load"], "11")

        router._async_goform_get = AsyncMock(return_value={})
        with self.assertRaisesRegex(RuntimeError, "no usable values"):
            await router._async_goform_update_fast()


class UbusCallTests(unittest.IsolatedAsyncioTestCase):
    async def test_goform_mode_skips_ubus_calls(self):
        router = logged_in_router()
        router._api_mode = "goform"
        router._session_id = None
        result = await router.async_call_ubus({"service": "x", "method": "y"})
        self.assertEqual(result["error"]["message"], "ubus_unavailable_in_goform_mode")
        router._session.post.assert_not_called()

    async def test_lazy_login_and_request_envelope(self):
        router = make_router()
        install_login(router)
        router._session.post.return_value = FakeResponse(
            payload=[{"id": 1, "result": [0, {"ok": 1}]}]
        )
        result = await router.async_call_ubus({"service": "svc", "method": "m", "params": {"p": 1}})
        self.assertEqual(result, {"success": True, "data": {"ok": 1}})
        router._async_ensure_logged_in.assert_awaited_once()
        request = router._session.post.call_args
        envelope = json.loads(request.kwargs["data"])
        self.assertEqual(envelope[0]["jsonrpc"], "2.0")
        self.assertEqual(envelope[0]["method"], "call")
        self.assertEqual(envelope[0]["params"], ["new-session", "svc", "m", {"p": 1}])
        self.assertTrue(request.args[0].startswith("https://192.0.2.1/ubus/?t="))
        self.assertEqual(request.kwargs["timeout"], 10)
        self.assertEqual(request.kwargs["headers"]["Z-Mode"], "1")
        self.assertEqual(request.kwargs["headers"]["Z-Tag"], "m")
        self.assertEqual(request.kwargs["headers"]["X-Requested-With"], "XMLHttpRequest")

    async def test_header_variants(self):
        router = logged_in_router()
        post = router._session.post
        post.return_value = FakeResponse(payload=[{"id": 1, "result": [0]}])

        await router.async_call_ubus(
            {"service": "uci", "method": "get", "params": {"config": "wireless"}},
            session_id="0" * 32,
        )
        headers = post.call_args.kwargs["headers"]
        self.assertEqual(headers["Z-Mode"], "0")
        self.assertEqual(headers["Z-Tag"], "wireless")

        await router.async_call_ubus(
            {"service": "svc", "method": "m"}, session_id="sid", z_mode_override="0"
        )
        self.assertEqual(post.call_args.kwargs["headers"]["Z-Mode"], "0")

        await router.async_call_ubus({"service": "svc", "method": ""}, session_id="sid")
        self.assertNotIn("Z-Tag", post.call_args.kwargs["headers"])
        self.assertEqual(post.call_args.kwargs["headers"]["Z-Mode"], "1")

        class BadParams(dict):
            def get(self, *_args):
                raise RuntimeError("bad params")

        await router.async_call_ubus(
            {"service": "uci", "method": "get", "params": BadParams({"x": 1})}, session_id="sid"
        )
        self.assertNotIn("Z-Tag", post.call_args.kwargs["headers"])

        router._logged_in = False
        await router.async_call_ubus({"service": "svc", "method": "m"}, session_id="sid")
        self.assertEqual(post.call_args.kwargs["headers"]["Z-Mode"], "0")

    async def test_response_shapes(self):
        router = logged_in_router()
        cases = [
            ([{"id": 1, "result": [0]}], True, None),
            ([{"id": 1, "result": [0, {"data": 1}]}], True, {"data": 1}),
            ([{"id": 1, "result": [1, "no"]}], False, None),
            ([{"id": 1, "result": []}], False, None),
            ([], False, None),
            ({"id": 1, "result": [0]}, False, None),
            (["bad"], False, None),
            ([{"error": {"code": -32000, "message": "oops"}}], False, None),
            ([{"error": "bad"}], False, None),
        ]
        for payload, success, data in cases:
            with self.subTest(payload=payload):
                router._session.post.return_value = FakeResponse(payload=payload)
                result = await router.async_call_ubus(
                    {"service": "svc", "method": "m"}, session_id="sid"
                )
                self.assertEqual(result["success"], success)
                if success:
                    self.assertEqual(result["data"], data)
                self.assertFalse(router._logged_in) if not success and payload in (
                    [],
                    {"id": 1, "result": [0]},
                    ["bad"],
                ) else None

    async def test_access_denied_retry_and_relogin_failure(self):
        router = logged_in_router()
        install_login(router)
        router._session.post.side_effect = [
            FakeResponse(payload=[{"error": {"code": -32002}}]),
            FakeResponse(payload=[{"id": 2, "result": [0, {"ok": True}]}]),
        ]
        result = await router.async_call_ubus({"service": "svc", "method": "m"}, session_id="sid")
        self.assertTrue(result["success"])
        self.assertEqual(router._session.post.call_count, 2)

        router = logged_in_router()
        install_login(router, fail=True)
        router._session.post.return_value = FakeResponse(payload=[{"error": {"code": -32002}}])
        result = await router.async_call_ubus({"service": "svc", "method": "m"}, session_id="sid")
        self.assertFalse(result["success"])
        self.assertEqual(result["error"]["kind"], "transport")
        self.assertEqual(result["error"]["message"], "RuntimeError during router request")

        router = logged_in_router()
        router._session.post.return_value = FakeResponse(payload=[{"error": {"code": -32002}}])
        result = await router.async_call_ubus(
            {"service": "svc", "method": "m"},
            session_id="sid",
            retry_on_access_denied=False,
        )
        self.assertEqual(result["error"]["code"], -32002)

    async def test_connreset_retry_and_transport_errors(self):
        router = logged_in_router()
        install_login(router)
        router._session.post.side_effect = [
            ConnectionResetError(104, "reset"),
            FakeResponse(payload=[{"id": 2, "result": [0, {"ok": 1}]}]),
        ]
        result = await router.async_call_ubus({"service": "svc", "method": "m"}, session_id="sid")
        self.assertTrue(result["success"])

        router = logged_in_router()
        install_login(router, fail=True)
        router._session.post.side_effect = ConnectionResetError(104, "reset")
        result = await router.async_call_ubus({"service": "svc", "method": "m"}, session_id="sid")
        self.assertEqual(result["error"]["kind"], "transport")

        router = logged_in_router()
        router._session.post.side_effect = TimeoutError()
        result = await router.async_call_ubus({"service": "svc", "method": "m"}, session_id="sid")
        self.assertEqual(result["error"]["message"], "request timed out")
        self.assertFalse(router._logged_in)

        error = RuntimeError("http")
        error.status = 503
        router = logged_in_router()
        router._session.post.side_effect = error
        result = await router.async_call_ubus({"service": "svc", "method": "m"}, session_id="sid")
        self.assertEqual(result["error"]["status"], 503)

    async def test_batch_response_mapping(self):
        router = logged_in_router()
        calls = [{"service": f"s{i}", "method": "m"} for i in range(7)]
        payload = [
            {"id": 1, "result": [0, {"x": 1}]},
            {"id": 2, "error": {"code": -1}},
            {"id": 999, "result": [0]},
            "bad",
            {"id": 5, "result": [5, "no"]},
            {"id": 6, "result": [0]},
            {"id": 7, "result": ["x"]},
        ]
        router._session.post.return_value = FakeResponse(text=json.dumps(payload))
        out = await router.async_call_ubus_batch(
            calls, batch_name="test", z_mode_override="0", retry_on_access_denied=False
        )
        self.assertEqual(len(out), 7)
        self.assertEqual(out[0], {"success": True, "data": {"x": 1}, "error": None})
        self.assertEqual(out[1]["error"], {"code": -1})
        self.assertEqual(out[2], {"success": False, "data": None, "error": None})
        self.assertEqual(out[4]["error"]["ubus_status"], 5)
        self.assertEqual(out[5], {"success": True, "data": None, "error": None})
        self.assertEqual(out[6]["error"], {"message": "nonzero_result"})
        headers = router._session.post.call_args.kwargs["headers"]
        self.assertEqual(headers["Z-Mode"], "0")
        self.assertIn(
            "session-id", json.loads(router._session.post.call_args.kwargs["data"])[0]["params"]
        )

    async def test_batch_retries_and_errors(self):
        router = logged_in_router()
        install_login(router)
        router._session.post.side_effect = [
            FakeResponse(text=json.dumps([{"id": 1, "error": {"code": -32002}}])),
            FakeResponse(text=json.dumps([{"id": 2, "result": [0, {"ok": 1}]}])),
        ]
        out = await router.async_call_ubus_batch(
            [{"service": "s", "method": "m"}], batch_name="test"
        )
        self.assertEqual(out[0]["data"], {"ok": 1})

        router = logged_in_router()
        install_login(router)
        router._session.post.side_effect = [
            ConnectionResetError(104, "reset"),
            FakeResponse(text=json.dumps([{"id": 2, "result": [0, {"ok": 2}]}])),
        ]
        out = await router.async_call_ubus_batch([{"service": "s", "method": "m"}])
        self.assertEqual(out[0]["data"], {"ok": 2})

        router = logged_in_router()
        install_login(router, fail=True)
        router._session.post.side_effect = ConnectionResetError(104, "reset")
        out = await router.async_call_ubus_batch([{"service": "s", "method": "m"}])
        self.assertEqual(out[0]["error"]["kind"], "transport")

        router = logged_in_router()
        router._session.post.side_effect = TimeoutError()
        out = await router.async_call_ubus_batch([{"service": "s", "method": "m"}])
        self.assertEqual(out[0]["error"]["message"], "request timed out")

        router = logged_in_router()
        router._session.post.return_value = FakeResponse(text=json.dumps({"not": "a list"}))
        out = await router.async_call_ubus_batch([{"service": "s", "method": "m"}])
        self.assertEqual(out[0]["error"]["message"], "invalid_json")

    async def test_batch_lazy_login(self):
        router = make_router()
        install_login(router)
        router._session.post.return_value = FakeResponse(text=json.dumps([]))
        await router.async_call_ubus_batch([{"service": "s", "method": "m"}])
        router._async_ensure_logged_in.assert_awaited_once()
        self.assertIn(
            "new-session", json.loads(router._session.post.call_args.kwargs["data"])[0]["params"]
        )


class BatchLoggingTests(unittest.TestCase):
    def test_failure_key_variants(self):
        self.assertEqual(ZteRouterApi._batch_failure_key({}), ("None", "None", ()))
        self.assertEqual(
            ZteRouterApi._batch_failure_key(
                {
                    "service": "uci",
                    "method": "get",
                    "params": {"config": "wireless", "section": "main_2g"},
                }
            ),
            ("uci", "get", (("config", "wireless"), ("section", "main_2g"))),
        )
        unhashable = ZteRouterApi._batch_failure_key({"params": {"a": [1, 2]}})
        self.assertEqual(unhashable[2], (("a", "[1, 2]"),))
        self.assertEqual(
            ZteRouterApi._batch_failure_key({"params": ["x"]}),
            ("None", "None", (("__params__", "['x']"),)),
        )
        self.assertEqual(
            ZteRouterApi._batch_failure_key({"params": "scalar"}),
            ("None", "None", (("__params__", "scalar"),)),
        )

    def test_optional_failure_detection(self):
        optional = {
            "service": "uci",
            "method": "get",
            "params": {"config": "wireless", "section": "main_2g"},
        }
        error = {"ubus_status": 1, "message": "nonzero_result"}
        self.assertTrue(ZteRouterApi._is_optional_batch_failure("core", optional, error))
        self.assertFalse(ZteRouterApi._is_optional_batch_failure("monthly", optional, error))
        self.assertFalse(ZteRouterApi._is_optional_batch_failure("core", optional, "bad"))
        for bad_error in (
            {"ubus_status": 1, "kind": "transport"},
            {"ubus_status": 1, "status": 500},
            {"ubus_status": 1, "code": -32000},
            {"ubus_status": 99},
        ):
            self.assertFalse(ZteRouterApi._is_optional_batch_failure("core", optional, bad_error))
        self.assertFalse(
            ZteRouterApi._is_optional_batch_failure(
                "core", {"service": "other", "method": "get", "params": {}}, error
            )
        )
        with patch.object(ZteRouterApi, "_batch_failure_key", return_value=None):
            self.assertFalse(ZteRouterApi._is_optional_batch_failure("core", optional, error))

    def test_log_batch_failures(self):
        router = make_router()
        optional = {
            "service": "uci",
            "method": "get",
            "params": {"config": "wireless", "section": "main_2g"},
        }
        calls = [
            optional,
            {"service": "a", "method": "b"},
            {"service": "c", "method": "d"},
            {"service": "e", "method": "f"},
            {"service": "g", "method": "h"},
            {"service": "i", "method": "j"},
            {"service": "k", "method": "l"},
        ]
        results = [
            {"success": False, "error": {"ubus_status": 1}},
            {"success": False, "error": {"status": 503}},
            {"success": False, "error": {"code": -32000}},
            {"success": False, "error": {"kind": "transport"}},
            {"success": False, "error": {"ubus_status": 2}},
            {"success": False, "error": {"message": "no code"}},
            {"success": False, "error": "bad"},
        ]
        with self.assertLogs(api_module.__name__, level="INFO") as captured:
            router._log_batch_failures("core", calls, results)
        output = "\n".join(captured.output)
        self.assertIn("optional unsupported", output)
        self.assertIn("HTTP 503", output)
        self.assertIn("RPC -32000", output)
        self.assertIn("transport error", output)
        self.assertIn("ubus 2", output)
        self.assertIn("router error without code", output)
        self.assertIn("unknown error", output)
        self.assertEqual(len(router._seen_optional_core_failures), 1)
        # Duplicates are logged once; a second identical failure stays silent.
        router._log_batch_failures("core", calls[:1], results[:1])
        router._seen_optional_core_failures = "invalid"
        router._log_batch_failures("core", calls[:1], results[:1])
        with patch.object(ZteRouterApi, "_batch_failure_key", return_value=None):
            router._log_batch_failures("core", calls[:1], results[:1])


class ActionTests(unittest.IsolatedAsyncioTestCase):
    async def test_execute_ubus_action_branches(self):
        router = logged_in_router()
        router.async_call_ubus = AsyncMock(return_value={"success": False, "error": {"code": -1}})
        self.assertFalse(await router.async_execute_ubus_action({"service": "s", "method": "m"}))

        router.async_call_ubus = AsyncMock(return_value=ok({"result": "FAILURE"}))
        self.assertFalse(await router.async_execute_ubus_action({"service": "s", "method": "m"}))
        router.async_call_ubus = AsyncMock(return_value=ok({"result": "success"}))
        self.assertTrue(await router.async_execute_ubus_action({"service": "s", "method": "m"}))
        router.async_call_ubus = AsyncMock(return_value=ok({"other": 1}))
        self.assertTrue(await router.async_execute_ubus_action({"service": "s", "method": "m"}))

        router.async_call_ubus = AsyncMock(return_value=ok({"result": 1}))
        self.assertTrue(
            await router.async_execute_ubus_action(
                {"service": "s", "method": "m"}, success_key="result"
            )
        )
        router.async_call_ubus = AsyncMock(return_value=ok({}))
        self.assertFalse(
            await router.async_execute_ubus_action(
                {"service": "s", "method": "m"}, success_key="result"
            )
        )
        router.async_call_ubus = AsyncMock(return_value=ok({"result": "ready"}))
        self.assertTrue(
            await router.async_execute_ubus_action(
                {"service": "s", "method": "m"}, success_key="result", success_values={"ready"}
            )
        )
        self.assertFalse(
            await router.async_execute_ubus_action(
                {"service": "s", "method": "m"}, success_key="result", success_values={"other"}
            )
        )
        self.assertEqual(router.async_call_ubus.call_args.kwargs["z_mode_override"], None)

    async def test_execute_action_def_branches(self):
        router = logged_in_router()
        self.assertFalse(await router.async_execute_action_def({}))
        self.assertFalse(await router.async_execute_action_def({"service": "s"}))
        self.assertFalse(
            await router.async_execute_action_def({"service": "s", "method": "m", "params": "bad"})
        )
        router.async_call_ubus = AsyncMock(return_value=ok({"result": "done"}))
        self.assertTrue(
            await router.async_execute_action_def(
                {
                    "service": "s",
                    "method": "m",
                    "params": {"p": 1},
                    "success_key": "result",
                    "success_values": ["done", "ok"],
                    "z_mode_override": "0",
                }
            )
        )
        self.assertEqual(router.async_call_ubus.call_args.kwargs["z_mode_override"], "0")
        self.assertTrue(
            await router.async_execute_action_def(
                {
                    "service": "s",
                    "method": "m",
                    "success_values": "done",
                }
            )
        )

        install_login(router, fail=True)
        self.assertFalse(
            await router.async_execute_action_def(
                {
                    "service": "s",
                    "method": "m",
                    "force_relogin": True,
                }
            )
        )
        install_login(router)
        self.assertTrue(
            await router.async_execute_action_def(
                {
                    "service": "s",
                    "method": "m",
                    "force_relogin": True,
                }
            )
        )
        router._async_ensure_logged_in.assert_awaited_once_with(force=True)

    async def test_firmware_update_action_choices(self):
        self.assertEqual(
            ZteRouterApi.firmware_update_action({"current_upgrade_state": "download_completed"}),
            {
                "service": "zwrt_fota_res.api",
                "method": "start_update",
                "params": {"moduleName": "zte_web"},
            },
        )
        for state in ("", "idle", "fota_idle", "upgrade_pack_redownload"):
            with self.subTest(state=state):
                self.assertEqual(
                    ZteRouterApi.firmware_update_action(
                        {
                            "new_version_state": "version_has_new_optional_software",
                            "current_upgrade_state": state,
                        }
                    ),
                    {"service": "zwrt_zte_dm", "method": "confirm_download", "params": {}},
                )
        for info in (
            {},
            {"new_version_state": "1", "current_upgrade_state": "upgrading"},
            {
                "new_version_state": "version_has_new_critical_software",
                "current_upgrade_state": "x",
            },
        ):
            with self.subTest(info=info):
                self.assertIsNone(ZteRouterApi.firmware_update_action(info))

    async def test_firmware_commands_and_mode_guards(self):
        router = logged_in_router()
        install_login(router)
        router.async_call_ubus = AsyncMock(return_value=ok({"result": "SUCCESS"}))
        self.assertTrue(await router.async_check_firmware_update())
        self.assertFalse(router.async_call_ubus.call_args.kwargs["retry_on_connreset_104"])
        router.async_call_ubus = AsyncMock(return_value=ok({"result": "failure"}))
        self.assertFalse(await router.async_check_firmware_update())
        router.async_call_ubus = AsyncMock(return_value={"success": False})
        self.assertFalse(await router.async_check_firmware_update())
        router.async_call_ubus = AsyncMock(return_value=ok(None))
        self.assertTrue(await router.async_check_firmware_update())
        router.async_call_ubus = AsyncMock(return_value=ok("unexpected"))
        self.assertFalse(await router.async_check_firmware_update())

        router._api_mode = "goform"
        with self.assertRaises(ValueError):
            await router.async_check_firmware_update()
        with self.assertRaises(ValueError):
            await router.async_start_firmware_update()

        router._api_mode = "ubus"
        router.async_call_ubus = AsyncMock(return_value={"success": False})
        with self.assertRaisesRegex(ValueError, "Cannot verify"):
            await router.async_start_firmware_update()
        router.async_call_ubus = AsyncMock(
            side_effect=[
                ok({"new_version_state": "1", "current_upgrade_state": "fota_idle"}),
                ok({"result": "0"}),
            ]
        )
        self.assertTrue(await router.async_start_firmware_update())
        router.async_call_ubus = AsyncMock(return_value=ok({"current_upgrade_state": "fota_idle"}))
        with self.assertRaisesRegex(ValueError, "No firmware update is ready"):
            await router.async_start_firmware_update()

    async def test_update_all_locked_ensures_login(self):
        router = make_router()
        router._async_ensure_logged_in = AsyncMock()
        router._api_mode = "goform"
        router._async_goform_update_all = AsyncMock(return_value={"ok": 1})
        self.assertEqual(await router._async_update_all_locked(), {"ok": 1})
        router._async_ensure_logged_in.assert_awaited_once()

    async def test_update_fast_and_update_all_goform_retry(self):
        router = logged_in_router()
        router._logged_in = False
        install_login(router)
        router.async_call_ubus_batch = AsyncMock(
            return_value=[
                ok({"a": 1}),
                ok({"b": 2}),
                ok({"c": 3}),
            ]
        )
        data = await router.async_update_fast()
        self.assertEqual(data["wan"], {"a": 1})
        calls = router.async_call_ubus_batch.call_args.args[0]
        self.assertEqual(
            [c["method"] for c in calls],
            [
                "router_get_status",
                "get_wwandst",
                "get_device_info",
            ],
        )
        router.async_call_ubus_batch = AsyncMock(return_value=[])
        self.assertIsNone(await router.async_update_fast())

        router = logged_in_router()
        router._api_mode = "goform"
        install_login(router)
        router._async_goform_update_fast = AsyncMock(side_effect=[RuntimeError("bad"), {"ok": 1}])
        self.assertEqual(await router.async_update_fast(), {"ok": 1})
        router._async_goform_update_all = AsyncMock(side_effect=[RuntimeError("bad"), {"all": 1}])
        self.assertEqual(await router.async_update_all(), {"all": 1})

    async def test_update_all_ubus_mapping_and_client_tracking(self):
        router = logged_in_router(track_clients=True)
        counts = {"access_total_num": 2, "wireless_num": 1, "lan_num": 1}

        async def batch(calls, **kwargs):
            name = kwargs.get("batch_name")
            if name == "core":
                payloads = [
                    {"lte_action_channel": 100, "lte_bandwidth": 20},
                    {"ap": 1},
                    {"values": {"model": "G5TC"}},
                    {"temp": 40},
                    {"model": "G5TC"},
                    {"imsi": 1},
                    {"ip": "1.2.3.4"},
                    counts,
                    {"values": {"model": "G5TC"}},
                    {"led": 1},
                    {},
                    {},
                    {"rx": 1},
                    {"iface": 1},
                ]
            elif name == "monthly":
                payloads = [{"month": 1}, {"enable": 0}, {"clearday": 1}]
            elif name == "firmware_gnss":
                payloads = [{"current_upgrade_state": "fota_idle"}, {"values": {"LAT": "1"}}]
            elif name == "sms":
                payloads = [
                    {"messages": [{"id": 1, "content": "00480069"}, "invalid"]},
                    {"sms_nv_rev_total": 1},
                ]
            else:
                payloads = [
                    {
                        "wireless_access_list_info": [
                            {
                                "mac_address": "aa:bb:cc:dd:ee:ff",
                                "hostname": "phone",
                                "ip_address": "192.168.1.2",
                                "interface_type": 1,
                            },
                        ]
                    },
                    {
                        "lan_access_list_info": [
                            {
                                "mac_address": "aa:bb:cc:dd:ee:ff",
                                "hostname": "phone",
                                "ipv6_address": "2001:db8::2",
                                "interface_type": "wifi",
                            },
                        ]
                    },
                    counts,
                ]
            return [ok(payload) for payload in payloads]

        router.async_call_ubus_batch = AsyncMock(side_effect=batch)
        data = await router.async_update_all()
        self.assertEqual(data["wan"], {"ip": "1.2.3.4"})
        self.assertEqual(data["data_limit"], {"enable": 0})
        self.assertEqual(data["traffic_reset"], {"clearday": 1})
        self.assertEqual(data["firmware"], {"current_upgrade_state": "fota_idle"})
        self.assertEqual(data["gnss"], {"LAT": "1"})
        self.assertEqual(data["sms"]["latest"]["content_decoded"], "Hi")
        clients = data["network_clients"]["clients"]
        self.assertEqual(clients["aa:bb:cc:dd:ee:ff"]["connection_type"], "wifi+lan")
        self.assertEqual(clients["aa:bb:cc:dd:ee:ff"]["ipv6_address"], "2001:db8::2")
        self.assertTrue(data["network_clients"]["complete"])
        self.assertTrue(router._client_snapshot_ok)

        router.track_clients = True
        router._client_snapshot_ok = True
        router._async_read_network_clients_locked = AsyncMock(side_effect=RuntimeError("bad"))
        with self.assertLogs(api_module.__name__, level="WARNING"):
            data = await router.async_update_all()
        self.assertIsNone(data["network_clients"])
        self.assertFalse(router._client_snapshot_ok)

        router._client_snapshot_ok = True
        router._async_read_network_clients_locked = AsyncMock(
            return_value={"clients": {}, "complete": False}
        )
        with self.assertLogs(api_module.__name__, level="WARNING"):
            await router.async_update_all()
        router._client_snapshot_ok = False
        router._async_read_network_clients_locked = AsyncMock(
            return_value={"clients": {}, "complete": True}
        )
        with self.assertLogs(api_module.__name__, level="INFO"):
            await router.async_update_all()


class NetworkClientTests(unittest.IsolatedAsyncioTestCase):
    def test_normalize_client_mac(self):
        for value in ("AA:BB:CC:DD:EE:FF", "aa-bb-cc-dd-ee-ff", "aabb.ccdd.eeff", " aabbccddeeff "):
            with self.subTest(value=value):
                self.assertEqual(ZteRouterApi.normalize_client_mac(value), "aa:bb:cc:dd:ee:ff")
        for value in (
            None,
            123,
            "aa:bb",
            "gg:bb:cc:dd:ee:ff",
            "00:00:00:00:00:00",
            "01:bb:cc:dd:ee:ff",
            "aa:bb:cc:dd:ee:ff:00",
        ):
            with self.subTest(value=value):
                self.assertIsNone(ZteRouterApi.normalize_client_mac(value))

    def test_normalize_network_client(self):
        self.assertIsNone(ZteRouterApi._normalize_network_client(None))
        self.assertIsNone(ZteRouterApi._normalize_network_client({"mac_address": "bad"}))
        row = {
            "mac_address": "AA-BB-CC-DD-EE-FF",
            "hostname": "  phone  ",
            "ip_address": "192.168.1.2",
            "ipv6_address": "2001:db8::1",
            "interface_type": 7,
        }
        self.assertEqual(
            ZteRouterApi._normalize_network_client(row),
            {
                "mac_address": "aa:bb:cc:dd:ee:ff",
                "hostname": "phone",
                "ip_address": "192.168.1.2",
                "ipv6_address": "2001:db8::1",
                "interface_type": "7",
            },
        )
        odd = {
            "mac_address": "aa:bb:cc:dd:ee:ff",
            "hostname": "x" * 300,
            "ip_address": "2001:db8::1",
            "ipv6_address": "192.168.1.1",
            "interface_type": "lan",
        }
        normalized = ZteRouterApi._normalize_network_client(odd)
        self.assertEqual(len(normalized["hostname"]), 255)
        self.assertIsNone(normalized["ip_address"])
        self.assertIsNone(normalized["ipv6_address"])
        self.assertEqual(normalized["interface_type"], "lan")
        unspecified = ZteRouterApi._normalize_network_client(
            {
                "mac_address": "aa:bb:cc:dd:ee:ff",
                "ip_address": "0.0.0.0",
                "ipv6_address": "::",
                "hostname": 5,
            }
        )
        self.assertIsNone(unspecified["ip_address"])
        self.assertIsNone(unspecified["ipv6_address"])
        self.assertIsNone(unspecified["hostname"])
        self.assertIsNone(unspecified["interface_type"])

    def test_network_client_counts(self):
        self.assertIsNone(ZteRouterApi._network_client_counts(None))
        counts = {"access_total_num": "2", "wireless_num": 1, "lan_num": 1}
        self.assertEqual(ZteRouterApi._network_client_counts(counts), (2, 1, 1))
        for bad in (
            {"access_total_num": True, "wireless_num": 1, "lan_num": 1},
            {"access_total_num": "x", "wireless_num": 1, "lan_num": 1},
            {"access_total_num": 1, "wireless_num": 2, "lan_num": 0},
            {"access_total_num": 3000, "wireless_num": 3000, "lan_num": 0},
            {"access_total_num": 2},
        ):
            with self.subTest(bad=bad):
                self.assertIsNone(ZteRouterApi._network_client_counts(bad))

    async def test_read_network_clients_locked_defensive_paths(self):
        router = logged_in_router()
        router._api_mode = "goform"
        self.assertIsNone(await router._async_read_network_clients_locked({"access_total_num": 1}))
        router._api_mode = "ubus"
        self.assertIsNone(await router._async_read_network_clients_locked(None))

        counts = {"access_total_num": 1, "wireless_num": 0, "lan_num": 1}
        router.async_call_ubus_batch = AsyncMock(return_value=[])
        self.assertIsNone(await router._async_read_network_clients_locked(counts))

        router.async_call_ubus_batch = AsyncMock(return_value=[ok(counts), ok({})])
        self.assertIsNone(await router._async_read_network_clients_locked(counts))

        bad_counts = {"access_total_num": 2, "wireless_num": 2, "lan_num": 0}
        router.async_call_ubus_batch = AsyncMock(
            return_value=[
                ok(
                    {
                        "wireless_access_list_info": [
                            {"mac_address": "aa:bb:cc:dd:ee:ff"},
                            {"mac_address": "11:22:33:44:55:66"},
                        ]
                    }
                ),
                ok(counts),
            ]
        )
        self.assertIsNone(await router._async_read_network_clients_locked(bad_counts))

        router.async_call_ubus_batch = AsyncMock(
            return_value=[
                ok({"lan_access_list_info": [{"mac_address": "bad"}]}),
                ok(counts),
            ]
        )
        snapshot = await router._async_read_network_clients_locked(counts)
        self.assertFalse(snapshot["complete"])
        self.assertEqual(snapshot["clients"], {})

        router.async_call_ubus_batch = AsyncMock(
            return_value=[
                ok({"lan_access_list_info": [{"mac_address": "aa:bb:cc:dd:ee:ff"}]}),
                ok(counts),
            ]
        )
        snapshot = await router._async_read_network_clients_locked(counts)
        self.assertTrue(snapshot["complete"])
        self.assertEqual(snapshot["clients"]["aa:bb:cc:dd:ee:ff"]["connection_type"], "lan")

        router.async_call_ubus_batch = AsyncMock(
            return_value=[
                {"success": False, "data": None},
                ok(counts),
            ]
        )
        self.assertFalse((await router._async_read_network_clients_locked(counts))["complete"])

        router.async_call_ubus_batch = AsyncMock(
            return_value=[
                ok({"lan_access_list_info": [{"mac_address": "aa:bb:cc:dd:ee:ff"}] * 2049}),
                ok(counts),
            ]
        )
        self.assertFalse((await router._async_read_network_clients_locked(counts))["complete"])


class SmsSendExtraTests(unittest.IsolatedAsyncioTestCase):
    async def test_send_rebuilds_payload_and_stops_after_timeout(self):
        router = logged_in_router()
        router._http_encryption_key = KEY
        router._sms_encryption = "plain"
        router._async_ensure_logged_in = AsyncMock()

        async def login(*, force=False):
            if force:
                router._http_encryption_key = OTHER_KEY

        router._async_ensure_logged_in = AsyncMock(side_effect=login)
        router.async_call_ubus = AsyncMock(
            side_effect=[
                {"success": False, "error": {"code": -32002}},
                ok(),
                ok({"sms_cmd_status_result": "2"}),
            ]
        )
        with patch("asyncio.sleep", new_callable=AsyncMock):
            self.assertFalse(await router.async_send_sms("+48123", "Hi"))
        self.assertEqual(router.async_call_ubus.await_count, 3)
        self.assertEqual(router._async_ensure_logged_in.await_count, 3)
        router._async_ensure_logged_in.assert_any_call(force=True)

        router = logged_in_router()
        router._sms_encryption = "plain"
        router._async_ensure_logged_in = AsyncMock()
        router.async_call_ubus = AsyncMock(side_effect=[ok(), ok({})] + [ok({})] * 19)
        with patch("asyncio.sleep", new_callable=AsyncMock):
            self.assertFalse(await router.async_send_sms("+48123", "Hi"))
        self.assertEqual(router.async_call_ubus.await_count, 21)

    async def test_access_denied_without_retry_flag_stops(self):
        router = logged_in_router()
        router._sms_encryption = "plain"
        router._async_ensure_logged_in = AsyncMock()
        router.async_call_ubus = AsyncMock(
            return_value={"success": False, "error": {"code": -32002}}
        )
        self.assertFalse(await router.async_send_sms("+48123", "Hi"))
        self.assertEqual(router.async_call_ubus.await_count, 2)


if __name__ == "__main__":
    unittest.main()
