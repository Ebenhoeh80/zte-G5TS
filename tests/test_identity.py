"""Stable device identity must be normalized, private and migration-safe."""

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "zte_5g_router"
spec = importlib.util.spec_from_file_location("zte_identity_test", ROOT / "identity.py")
identity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(identity)


class NormalizeMacTests(unittest.TestCase):
    def test_common_mac_formats(self):
        for value in (
            "AA:BB:CC:DD:EE:FF",
            "aa-bb-cc-dd-ee-ff",
            "aabb.ccdd.eeff",
            "AABBCCDDEEFF",
        ):
            with self.subTest(value=value):
                self.assertEqual(identity.normalize_mac(value), "aa:bb:cc:dd:ee:ff")

    def test_non_mac_is_rejected(self):
        for value in ("", "not-a-mac", "aa:bb:cc:dd:ee", None, 123):
            with self.subTest(value=value):
                self.assertIsNone(identity.normalize_mac(value))


class DeviceIdentifierTests(unittest.TestCase):
    def test_wlan_mac_from_sim_info_is_preferred(self):
        data = {
            "sim_info": {
                "wlan_mac_address": "A0:B1:C2:D3:E4:F5",
                "imei": "123456789012345",
            },
            "device": {"mac_address": "00:11:22:33:44:55"},
        }
        self.assertEqual(
            identity.device_identifier_from_data(data), "a0:b1:c2:d3:e4:f5"
        )

    def test_fallback_to_serial_on_firmwares_without_mac(self):
        self.assertEqual(
            identity.device_identifier_from_data({"device": {"serial_number": "ZTE123"}}),
            "ZTE123",
        )

    def test_placeholders_and_missing_values_are_ignored(self):
        for data in (
            {"sim_info": {"wlan_mac_address": "unknown"}},
            {"sim_info": {"wlan_mac_address": "unavailable"}},
            {},
            None,
        ):
            with self.subTest(data=data):
                self.assertIsNone(identity.device_identifier_from_data(data))

    def test_only_legacy_url_ids_are_migrated(self):
        mac = "aa:bb:cc:dd:ee:ff"
        self.assertTrue(
            identity.should_migrate_unique_id("zte_5g_router_https://192.0.2.1", mac)
        )
        self.assertFalse(
            identity.should_migrate_unique_id(identity.entry_unique_id(mac), mac)
        )
        self.assertFalse(
            identity.should_migrate_unique_id(
                identity.entry_unique_id("11:22:33:44:55:66"), mac
            )
        )
        self.assertFalse(identity.should_migrate_unique_id(None, mac))

    def test_other_router_guard_only_applies_to_mac_based_ids(self):
        mac = "aa:bb:cc:dd:ee:ff"
        self.assertTrue(identity.is_other_router(identity.entry_unique_id(mac), "11:22:33:44:55:66"))
        self.assertFalse(identity.is_other_router(identity.entry_unique_id(mac), mac))
        self.assertFalse(identity.is_other_router("zte_5g_router_https://192.0.2.1", mac))


if __name__ == "__main__":
    unittest.main()
