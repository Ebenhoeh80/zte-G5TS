"""Extra offline coverage for device-tracker registry and restore edge cases."""

from datetime import datetime
import types
import unittest

from test_device_tracker import MAC, START, Registry, snapshot, trackers


def make_tracker(metadata=None, last_seen=None):
    tracking = trackers.NetworkClientTracking(180)
    client = trackers.NetworkClient(MAC, metadata=dict(metadata or {}), last_seen=last_seen)
    tracking.clients[MAC] = client
    coordinator = types.SimpleNamespace(last_update_success=True)
    entity = trackers.ZteNetworkClientTracker(coordinator, tracking, MAC, "entry", "Router")
    return entity, client


class RegistryCleanupTests(unittest.IsolatedAsyncioTestCase):
    async def test_foreign_registry_entries_are_ignored(self):
        entries = [
            types.SimpleNamespace(
                domain="sensor", platform="zte_5g_router", unique_id="entry_wifi_021234567890"
            ),
            types.SimpleNamespace(
                domain="device_tracker",
                platform="other_integration",
                unique_id="entry_wifi_021234567890",
            ),
            types.SimpleNamespace(
                domain="device_tracker",
                platform="zte_5g_router",
                unique_id="entry_lan_021234567890",
            ),
            types.SimpleNamespace(
                domain="device_tracker",
                platform="zte_5g_router",
                unique_id="entry_wifi_021234567890",
            ),
        ]
        coordinator = types.SimpleNamespace(
            data={"network_clients": snapshot()},
            last_update_success=True,
            async_add_listener=lambda listener: lambda: None,
        )
        store = types.SimpleNamespace(
            coordinator=coordinator, name="Router", reset_client_absence=None
        )
        hass = types.SimpleNamespace(registry=Registry(entries))
        entry = types.SimpleNamespace(
            entry_id="entry",
            data={},
            options={"track_wifi_clients": True},
            runtime_data=store,
            async_on_unload=lambda callback: None,
        )
        entities = []
        await trackers.async_setup_entry(hass, entry, entities.extend)
        self.assertEqual(len(entities), 1)
        self.assertEqual(entities[0].mac_address, MAC)


class TrackerPropertyTests(unittest.TestCase):
    def test_name_falls_back_to_mac_without_hostname(self):
        entity, _ = make_tracker()
        self.assertIsNone(entity.hostname)
        self.assertEqual(entity.name, f"Router {MAC}")
        entity, _ = make_tracker({"hostname": "Phone"})
        self.assertEqual(entity.name, "Router Phone")


class RestoreEdgeCaseTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_state_and_existing_sighting_skip_restore(self):
        for restored_state in (
            None,
            types.SimpleNamespace(
                state="home",
                attributes={
                    "host_name": "Old name",
                    "last_seen": START.isoformat(),
                },
            ),
        ):
            with self.subTest(restored_state=restored_state):
                entity, client = make_tracker({"hostname": "Live"}, START)
                entity.restored_state = restored_state
                await entity.async_added_to_hass()
                self.assertEqual(client.metadata, {"hostname": "Live"})
                self.assertEqual(client.last_seen, START)

    async def test_invalid_last_seen_restores_metadata_but_not_presence(self):
        for invalid in ("not-a-date", "", START, datetime(2026, 1, 1), 123):
            with self.subTest(last_seen=invalid):
                entity, client = make_tracker()
                entity.restored_state = types.SimpleNamespace(
                    state="home",
                    attributes={
                        "host_name": "Old name",
                        "ip": "192.0.2.5",
                        "last_seen": invalid,
                    },
                )
                await entity.async_added_to_hass()
                self.assertEqual(client.metadata["hostname"], "Old name")
                self.assertEqual(client.metadata["ip_address"], "192.0.2.5")
                self.assertIsNone(client.last_seen)
                self.assertIsNone(client.connected)


if __name__ == "__main__":
    unittest.main()
