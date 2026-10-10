from copy import deepcopy
from dataclasses import replace
import unittest

from mimamori_breach.hibp import Breach
from mimamori_breach.model import apply_success


EMAIL = "synthetic@example.com"
FIRST = "2026-10-10T00:00:00+00:00"
SECOND = "2026-10-11T00:00:00+00:00"
BREACH = Breach("Example", "Example Service", "example.com", "2020-01-01",
                "2020-02-01T12:00:00Z", ["Email addresses", "Passwords"])


class StateTests(unittest.TestCase):
    def test_first_check_surfaces_historical_matches(self):
        state, alerts = apply_success({}, " SYNTHETIC@EXAMPLE.COM ", [BREACH], FIRST)
        self.assertEqual(alerts, [BREACH])
        self.assertEqual(state["account"], EMAIL)
        self.assertEqual(state["last_success"], FIRST)
        self.assertFalse(state["items"]["Example"]["acknowledged"])
        self.assertEqual(state["items"]["Example"]["first_seen"], FIRST)

    def test_repeated_result_does_not_alert_even_if_not_acknowledged(self):
        first, _ = apply_success({}, EMAIL, [BREACH], FIRST)
        later, alerts = apply_success(first, EMAIL, [BREACH], SECOND)
        self.assertEqual(alerts, [])
        self.assertFalse(later["items"]["Example"]["acknowledged"])
        self.assertEqual(later["last_success"], SECOND)
        self.assertEqual(later["items"]["Example"]["first_seen"], FIRST)

    def test_acknowledgment_survives_same_result_and_title_changes(self):
        first, _ = apply_success({}, EMAIL, [BREACH], FIRST)
        first["items"]["Example"]["acknowledged"] = True
        revised = replace(BREACH, title="Example Service (2020)", data_classes=list(reversed(BREACH.data_classes)))
        later, alerts = apply_success(first, EMAIL, [revised], SECOND)
        self.assertEqual(alerts, [])
        self.assertTrue(later["items"]["Example"]["acknowledged"])
        self.assertEqual(later["items"]["Example"]["breach"]["title"], revised.title)

    def test_material_changes_reset_acknowledgment_and_alert_once(self):
        first, _ = apply_success({}, EMAIL, [BREACH], FIRST)
        first["items"]["Example"]["acknowledged"] = True
        changes = [
            {"data_classes": ["Email addresses", "Passwords", "Phone numbers"]},
            {"domain": "other.example"}, {"breach_date": "2020-01-02"},
            {"added_date": "2020-02-02T12:00:00Z"},
        ]
        for change in changes:
            with self.subTest(change=change):
                updated = replace(BREACH, **change)
                later, alerts = apply_success(first, EMAIL, [updated], SECOND)
                self.assertEqual(alerts, [updated])
                self.assertFalse(later["items"]["Example"]["acknowledged"])
                self.assertEqual(later["items"]["Example"]["first_seen"], FIRST)
                _, repeated = apply_success(later, EMAIL, [updated], SECOND)
                self.assertEqual(repeated, [])

    def test_absent_result_keeps_history_and_acknowledgment(self):
        first, _ = apply_success({}, EMAIL, [BREACH], FIRST)
        first["items"]["Example"]["acknowledged"] = True
        later, alerts = apply_success(first, EMAIL, [], SECOND)
        self.assertEqual(alerts, [])
        self.assertEqual(later["items"], first["items"])
        _, restored = apply_success(later, EMAIL, [BREACH], SECOND)
        self.assertEqual(restored, [])

    def test_changed_email_starts_separate_history(self):
        first, _ = apply_success({}, EMAIL, [BREACH], FIRST)
        later, alerts = apply_success(first, "different@example.com", [], SECOND)
        self.assertEqual(later["items"], {})
        self.assertEqual(alerts, [])
        later, alerts = apply_success(first, "different@example.com", [BREACH], SECOND)
        self.assertEqual(alerts, [BREACH])
        self.assertEqual(later["items"]["Example"]["first_seen"], SECOND)

    def test_inputs_and_returned_state_do_not_share_mutable_history(self):
        original, _ = apply_success({}, EMAIL, [BREACH], FIRST)
        snapshot = deepcopy(original)
        later, _ = apply_success(original, EMAIL, [BREACH], SECOND)
        self.assertEqual(original, snapshot)
        later["items"]["Example"]["breach"]["data_classes"].append("Synthetic category")
        self.assertEqual(original, snapshot)
        self.assertNotIn("Synthetic category", BREACH.data_classes)

    def test_new_match_appears_alongside_old_history(self):
        first, _ = apply_success({}, EMAIL, [BREACH], FIRST)
        new = replace(BREACH, name="Another", title="Another service")
        later, alerts = apply_success(first, EMAIL, [BREACH, new], SECOND)
        self.assertEqual(alerts, [new])
        self.assertEqual(set(later["items"]), {"Example", "Another"})
        self.assertEqual(later["items"]["Another"]["first_seen"], SECOND)

    def test_duplicate_input_records_emit_one_notification(self):
        state, alerts = apply_success({}, EMAIL, [BREACH, BREACH], FIRST)
        self.assertEqual(alerts, [BREACH])
        self.assertEqual(len(state["items"]), 1)


if __name__ == "__main__":
    unittest.main()
