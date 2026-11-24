"""Close the remaining coverage gaps in the dependency-free identity module."""

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "zte_5g_router"
spec = importlib.util.spec_from_file_location("zte_identity_coverage_test", ROOT / "identity.py")
identity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(identity)


class NormalizeMacCoverageTests(unittest.TestCase):
    def test_canonicalizes_and_rejects_macs(self):
        self.assertEqual(identity.normalize_mac("AA-BB-CC-DD-EE-FF"), "aa:bb:cc:dd:ee:ff")
        for value in ("", "not-a-mac", "aa:bb:cc:dd:ee", None, 123):
            with self.subTest(value=value):
                self.assertIsNone(identity.normalize_mac(value))


class NormalizeIdentifierCoverageTests(unittest.TestCase):
    def test_rejects_non_strings_and_placeholders(self):
        for value in (None, 123, "", "  ", "unknown", "N/A"):
            with self.subTest(value=value):
                self.assertIsNone(identity.normalize_identifier(value))

    def test_accepts_mac_and_plain_opaque_id(self):
        self.assertEqual(identity.normalize_identifier(" A0:B1:C2:D3:E4:F5 "), "a0:b1:c2:d3:e4:f5")
        self.assertEqual(identity.normalize_identifier(" ZTE123 "), "ZTE123")

    def test_rejects_overlong_identifier(self):
        self.assertIsNone(identity.normalize_identifier("A" * 65))

    def test_rejects_identifier_with_embedded_whitespace(self):
        for value in ("ABC 123", "ABC\t123", "ABC\n123"):
            with self.subTest(value=value):
                self.assertIsNone(identity.normalize_identifier(value))

    def test_uuid_like_identifier_is_lowercased(self):
        value = "123E4567-E89B-12D3-A456-426614174000"
        self.assertEqual(identity.normalize_identifier(value), value.lower())


class DeviceIdentifierCoverageTests(unittest.TestCase):
    def test_payload_only_accepts_dicts_and_known_keys(self):
        self.assertIsNone(identity.device_identifier_from_payload(None))
        self.assertIsNone(identity.device_identifier_from_payload({"other": "AA:BB:CC:DD:EE:FF"}))
        self.assertEqual(
            identity.device_identifier_from_payload({"mac": "AA:BB:CC:DD:EE:FF"}),
            "aa:bb:cc:dd:ee:ff",
        )

    def test_data_sections_and_top_level_fallback(self):
        self.assertIsNone(identity.device_identifier_from_data(None))
        self.assertEqual(
            identity.device_identifier_from_data({"wan": {"device_mac": "001122AABBCC"}}),
            "00:11:22:aa:bb:cc",
        )
        self.assertEqual(identity.device_identifier_from_data({"sn": "SN123"}), "SN123")
        self.assertIsNone(identity.device_identifier_from_data({"sim_info": {}}))


class UniqueIdCoverageTests(unittest.TestCase):
    def test_entry_id_is_stable(self):
        self.assertEqual(
            identity.entry_unique_id("aa:bb:cc:dd:ee:ff"), "zte_5g_router_aa:bb:cc:dd:ee:ff"
        )

    def test_non_prefixed_id_is_not_migrated(self):
        self.assertFalse(
            identity.should_migrate_unique_id("https://192.0.2.1", "aa:bb:cc:dd:ee:ff")
        )

    def test_already_migrated_and_mac_ids_are_not_migrated(self):
        mac = "aa:bb:cc:dd:ee:ff"
        self.assertFalse(identity.should_migrate_unique_id(None, mac))
        self.assertFalse(identity.should_migrate_unique_id(identity.entry_unique_id(mac), mac))
        self.assertFalse(
            identity.should_migrate_unique_id(identity.entry_unique_id("11:22:33:44:55:66"), mac)
        )

    def test_missing_or_non_prefixed_id_is_not_other_router(self):
        mac = "aa:bb:cc:dd:ee:ff"
        for unique_id in (None, "https://192.0.2.1", ""):
            with self.subTest(unique_id=unique_id):
                self.assertFalse(identity.is_other_router(unique_id, mac))

    def test_other_router_guard_for_mac_and_opaque_ids(self):
        mac = "aa:bb:cc:dd:ee:ff"
        self.assertTrue(
            identity.is_other_router(identity.entry_unique_id(mac), "11:22:33:44:55:66")
        )
        self.assertFalse(identity.is_other_router(identity.entry_unique_id(mac), mac))
        self.assertFalse(identity.is_other_router(identity.entry_unique_id("ZTE123"), mac))


if __name__ == "__main__":
    unittest.main()
