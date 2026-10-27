import random
import unittest

from prototype.fit import Rect, WindowSpec
from prototype.session import DesktopPreset, DesktopSession


class DesktopSessionTests(unittest.TestCase):
    def make_session(self, viewport=None):
        windows = [WindowSpec("editor", "Editor", 120, 80), WindowSpec("shell", "Shell", 80, 60)]
        original = {"editor": Rect(-30, 17, 640, 480), "shell": Rect(150, 100, 400, 300)}
        presets = [DesktopPreset("onyx", "Onyx"), DesktopPreset("compact", "Compact"),
                   DesktopPreset("workbench", "Workbench")]
        return DesktopSession(viewport or Rect(0, 0, 1200, 800), windows, original, presets), original

    def test_same_action_restores_exact_geometry_after_preset_changes(self):
        session, original = self.make_session()
        first = session.toggle_fit()
        self.assertTrue(first.changed)
        self.assertTrue(session.fit_active)
        self.assertNotEqual(session.geometries, original)
        fitted = session.geometries
        session.cycle_preset(1)
        session.cycle_preset(-1)
        session.select_preset("workbench")
        self.assertEqual(session.geometries, fitted)
        self.assertTrue(session.fit_active)
        second = session.toggle_fit()
        self.assertFalse(second.active)
        self.assertEqual(session.geometries, original)
        self.assertEqual(session.current_preset.identifier, "workbench")

    def test_failed_fit_does_not_mutate_standard_state(self):
        session, original = self.make_session(Rect(0, 0, 100, 50))
        outcome = session.toggle_fit()
        self.assertFalse(outcome.active)
        self.assertFalse(outcome.changed)
        self.assertFalse(outcome.layout.feasible)
        self.assertEqual(session.geometries, original)
        self.assertFalse(session.fit_active)

    def test_snapshot_cannot_be_modified_through_caller_dictionary(self):
        session, original = self.make_session()
        expected = dict(original)
        original["editor"] = Rect(0, 0, 10, 10)
        session.toggle_fit()
        exposed = session.geometries
        exposed.clear()
        session.toggle_fit()
        self.assertEqual(session.geometries, expected)

    def test_standard_update_changes_next_restore_snapshot(self):
        session, original = self.make_session()
        rect = Rect(30, 40, 500, 600)
        session.set_standard_geometry("editor", rect)
        session.toggle_fit()
        with self.assertRaises(ValueError):
            session.set_standard_geometry("editor", original["editor"])
        session.toggle_fit()
        self.assertEqual(session.geometries["editor"], rect)

    def test_preset_cycles_wrap_and_have_no_geometry_effect(self):
        session, original = self.make_session()
        self.assertEqual(session.cycle_preset(-1).identifier, "workbench")
        self.assertEqual(session.cycle_preset(1).identifier, "onyx")
        self.assertFalse(session.fit_active)
        self.assertEqual(session.geometries, original)

    def test_seeded_repeated_toggles_restore_exact_state(self):
        session, expected = self.make_session()
        rng = random.Random(357)
        for step in range(300):
            if rng.randrange(4) == 0:
                session.cycle_preset(rng.choice((-1, 1)))
            else:
                session.toggle_fit()
            if not session.fit_active:
                self.assertEqual(session.geometries, expected)
        if session.fit_active:
            session.toggle_fit()
        self.assertEqual(session.geometries, expected)

    def test_empty_session_toggles_and_restores(self):
        session = DesktopSession(Rect(0, 0, 100, 100), [], {}, [DesktopPreset("empty", "Empty")])
        self.assertTrue(session.toggle_fit().active)
        self.assertFalse(session.toggle_fit().active)
        self.assertEqual(session.geometries, {})

    def test_invalid_preset_direction_and_unknown_ids(self):
        session, _ = self.make_session()
        for direction in (0, 2, True, "1"):
            with self.assertRaises(ValueError):
                session.cycle_preset(direction)
        with self.assertRaises(ValueError):
            session.select_preset("missing")
        with self.assertRaises(ValueError):
            session.set_standard_geometry("missing", Rect(0, 0, 10, 10))

    def test_oversized_standard_geometry_map_is_rejected(self):
        geometries = {f"extra_{i}": Rect(0, 0, 10, 10) for i in range(65)}
        with self.assertRaises(ValueError):
            DesktopSession(Rect(0, 0, 100, 100), [], geometries,
                           [DesktopPreset("standard", "Standard")])


if __name__ == "__main__":
    unittest.main()
