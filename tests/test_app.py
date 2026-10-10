from copy import deepcopy
from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import Mock

from mimamori_breach.app import App, DAY, demo_breaches, seconds_until_due
from mimamori_breach.model import apply_success
from mimamori_breach.storage import StorageError


class SchedulingTests(unittest.TestCase):
    def test_restart_respects_last_success(self):
        now = datetime(2026, 10, 10, tzinfo=timezone.utc)
        self.assertEqual(seconds_until_due((now - timedelta(hours=4)).isoformat(), now), 20 * 3600)
        self.assertEqual(seconds_until_due((now - timedelta(days=2)).isoformat(), now), 0)
        self.assertEqual(seconds_until_due((now + timedelta(days=2)).isoformat(), now), DAY)
        for invalid in (None, "bad", "2026-01-01T00:00:00"):
            self.assertEqual(seconds_until_due(invalid, now), 0)


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.app = App.__new__(App)
        self.app.payload = {"config": {"email": "test@example.test", "api_key": "0" * 32,
                            "enabled": True, "consent": True}, "state": {}}
        self.app.demo = False
        self.app.store = Mock()
        self.app.status = Mock()
        self.app._refresh = Mock()
        self.app._notify = Mock()
        self.app.storage_failed = False
        self.app.last_error = False
        self.app.busy = True
        self.app.generation = 3

    def test_success_persists_and_notifies_only_new_records(self):
        event = ("result", 3, "test@example.test", demo_breaches())
        self.app._handle_result(event)
        self.assertEqual(len(self.app.payload["state"]["items"]), 2)
        self.app.store.save.assert_called_once()
        self.app._notify.assert_called_once()
        self.app._handle_result(event)
        self.app._notify.assert_called_once()

    def test_old_settings_response_is_discarded(self):
        original = deepcopy(self.app.payload)
        self.app._handle_result(("result", 2, "old@example.test", demo_breaches()))
        self.app.store.save.assert_not_called()
        self.assertEqual(self.app.payload, original)
        self.assertFalse(self.app.busy)

    def test_failure_preserves_history_and_auth_stops_auto_retry(self):
        state, _ = apply_success({}, "test@example.test", demo_breaches(), "2026-10-10T00:00:00+00:00")
        self.app.payload["state"] = state
        original = deepcopy(state)
        self.app._handle_result(("error", 3, "auth", 300))
        self.assertEqual(self.app.payload["state"], original)
        self.app.store.save.assert_not_called()
        self.assertEqual(self.app.next_check, float("inf"))
        self.assertTrue(self.app.last_error)
        self.app._notify.assert_called_once()
        self.app._handle_result(("error", 3, "auth", 300))
        self.app._notify.assert_called_once()

    def test_failed_storage_never_replaces_in_memory_state_or_keeps_monitoring(self):
        self.app.store.save.side_effect = StorageError("unavailable")
        original = deepcopy(self.app.payload)
        self.app._handle_result(("result", 3, "test@example.test", demo_breaches()))
        self.assertEqual(self.app.payload, original)
        self.assertTrue(self.app.storage_failed)
        self.assertEqual(self.app.next_check, float("inf"))
        self.app._notify.assert_called_once()

    def test_disabled_monitor_never_schedules_after_manual_success_or_error(self):
        self.app.payload["config"]["enabled"] = False
        self.app._handle_result(("result", 3, "test@example.test", []))
        self.assertEqual(self.app.next_check, float("inf"))
        self.app._handle_result(("error", 3, "network", 300))
        self.assertEqual(self.app.next_check, float("inf"))

    def test_persisted_history_missing_required_field_is_rejected(self):
        state, _ = apply_success({}, "test@example.test", demo_breaches(), "2026-10-10T00:00:00+00:00")
        self.app.payload["state"] = state
        App._validate_payload(self.app.payload)
        del state["items"]["ExampleGarden"]["first_seen"]
        with self.assertRaises(ValueError):
            App._validate_payload(self.app.payload)


if __name__ == "__main__":
    unittest.main()
