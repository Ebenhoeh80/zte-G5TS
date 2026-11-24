"""Stale client trackers leave the registry after the grace period."""

import unittest
from unittest.mock import patch

from test_device_tracker import MAC, Registry, snapshot, trackers

STALE_SECONDS = trackers.STALE_CLIENT_REMOVAL_DAYS * 86400
UNIQUE_ID = "entry_wifi_021234567890"


class StaleRegistry(Registry):
    """Registry stub that resolves one known tracker entity."""

    def __init__(self, entries):
        super().__init__(entries)
        self.entity_id = "device_tracker.phone"

    def async_get_entity_id(self, domain, platform, unique_id):
        return self.entity_id if unique_id == UNIQUE_ID else None


class TrackerStaleTests(unittest.IsolatedAsyncioTestCase):
    def test_tracking_marks_long_absent_client_stale(self):
        tracking = trackers.NetworkClientTracking(consider_home=0)
        tracking.update(snapshot(0, True), now=0)
        tracking.update(snapshot(1, False), now=1)
        self.assertFalse(tracking.clients[MAC].stale)
        tracking.update(snapshot(2, False), now=STALE_SECONDS + 1)
        self.assertTrue(tracking.clients[MAC].stale)

    async def _setup(self, registry):
        listeners = []

        def listen(listener):
            listeners.append(listener)
            return lambda: listeners.remove(listener)

        coordinator = type("Coordinator", (), {})()
        coordinator.data = {"network_clients": snapshot(0, True)}
        coordinator.last_update_success = True
        coordinator.async_add_listener = listen
        store = type("Store", (), {})()
        store.coordinator = coordinator
        store.name = "Router"
        store.reset_client_absence = None
        hass = type("Hass", (), {})()
        hass.registry = registry
        entry = type("Entry", (), {})()
        entry.entry_id = "entry"
        entry.data = {}
        entry.options = {"track_wifi_clients": True}
        entry.runtime_data = store
        entry.async_on_unload = lambda callback: None
        entities = []
        await trackers.async_setup_entry(hass, entry, entities.extend)
        return coordinator, listeners, entities

    async def test_stale_tracker_is_removed_from_registry(self):
        registry_entry = type("Entity", (), {})()
        registry_entry.domain = "device_tracker"
        registry_entry.platform = "zte_5g_router"
        registry_entry.unique_id = UNIQUE_ID
        registry = StaleRegistry([registry_entry])
        coordinator, listeners, entities = await self._setup(registry)
        self.assertEqual(len(entities), 1)

        coordinator.data = {"network_clients": snapshot(1, False)}
        with patch.object(trackers.time, "monotonic", side_effect=[0, 0]):
            listeners[0]()
        self.assertEqual(registry.removed, [])

        coordinator.data = {"network_clients": snapshot(2, False)}
        with patch.object(trackers.time, "monotonic", return_value=STALE_SECONDS + 1):
            listeners[0]()
        self.assertEqual(registry.removed, ["device_tracker.phone"])
        self.assertNotIn(MAC, entities[0]._tracking.clients)


if __name__ == "__main__":
    unittest.main()
