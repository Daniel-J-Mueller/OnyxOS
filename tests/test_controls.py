import random
import unittest

from prototype.controls import Control, DirectionalControls
from prototype.fit import Rect


class DirectionalControlTests(unittest.TestCase):
    def test_approach_expands_instantly_and_stationary_samples_stay_stable(self):
        controller = DirectionalControls(Rect(0, 0, 400, 200),
                                         [Control("close", "Close", Rect(140, 20, 8, 8))])
        self.assertIsNone(controller.move(70, 24).active_identifier)
        state = controller.move(100, 24)
        self.assertEqual(state.active_identifier, "close")
        self.assertGreater(state.expanded_rect.area, 64)
        for _ in range(10):
            self.assertEqual(controller.move(100, 24), state)
        self.assertIsNone(controller.move(70, 24).active_identifier)

    def test_moving_away_does_not_activate(self):
        controller = DirectionalControls(Rect(0, 0, 400, 200),
                                         [Control("close", "Close", Rect(140, 20, 8, 8))])
        controller.move(120, 24)
        self.assertIsNone(controller.move(100, 24).active_identifier)

    def test_expansion_preserves_neighbor_hit_ownership(self):
        controls = [Control("left", "Left", Rect(30, 20, 8, 8)),
                    Control("right", "Right", Rect(44, 20, 8, 8))]
        controller = DirectionalControls(Rect(0, 0, 100, 100), controls)
        state = controller.move(32, 24)
        self.assertFalse(state.expanded_rect.overlaps(controls[1].base))
        self.assertEqual(controller.hit_test(46, 24), "right")
        self.assertEqual(controller.move(46, 24).active_identifier, "right")
        self.assertEqual(controller.hit_test(32, 24), "left")

    def test_small_jitter_inside_expanded_target_keeps_identity(self):
        controller = DirectionalControls(Rect(0, 0, 100, 100),
                                         [Control("menu", "Menu", Rect(40, 40, 8, 8))])
        controller.move(43, 43)
        for x, y in ((39, 43), (38, 42), (39, 44), (40, 43), (37, 42)):
            self.assertEqual(controller.move(x, y).active_identifier, "menu")
            self.assertEqual(controller.hit_test(x, y), "menu")

    def test_expansion_clamps_to_output_edges(self):
        viewport = Rect(0, 0, 100, 100)
        controller = DirectionalControls(viewport, [Control("edge", "Edge", Rect(0, 0, 8, 8))])
        state = controller.move(2, 2)
        self.assertTrue(viewport.contains(state.expanded_rect))
        self.assertEqual(state.expanded_rect.x, 0)
        self.assertEqual(state.expanded_rect.y, 0)

    def test_seeded_pointer_traces_preserve_target_identity_and_bounds(self):
        viewport = Rect(0, 0, 240, 240)
        controls = [Control(f"c{i}", f"Control {i}", Rect(20 + (i % 4) * 55, 20 + (i // 4) * 55, 8, 8))
                    for i in range(16)]
        controller = DirectionalControls(viewport, controls, expansion=32)
        by_id = {c.identifier: c for c in controls}
        rng = random.Random(84)
        for _ in range(600):
            x, y = rng.randrange(240), rng.randrange(240)
            state = controller.move(x, y)
            self.assertEqual(controller.move(x, y), state)
            if state.active_identifier is not None:
                active = by_id[state.active_identifier]
                self.assertTrue(viewport.contains(state.expanded_rect))
                self.assertTrue(state.expanded_rect.contains(active.base))
                for control in controls:
                    self.assertEqual(controller.hit_test(control.base.x, control.base.y), control.identifier)
                    if control != active:
                        self.assertFalse(state.expanded_rect.overlaps(control.base))

    def test_invalid_input_rejected(self):
        viewport = Rect(0, 0, 100, 100)
        control = Control("a", "A", Rect(20, 20, 10, 10))
        for controls in ([control, control], [control, Control("b", "B", Rect(25, 25, 10, 10))],
                         [Control("c", "C", Rect(-1, 0, 10, 10))], ["bad"]):
            with self.assertRaises(ValueError):
                DirectionalControls(viewport, controls)
        controller = DirectionalControls(viewport, [control])
        for point in ((True, 1), (100, 1), (-1, 1), (1, 0.5)):
            with self.assertRaises(ValueError):
                controller.move(*point)


if __name__ == "__main__":
    unittest.main()
