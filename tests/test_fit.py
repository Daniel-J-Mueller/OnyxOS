import random
import unittest
from fractions import Fraction

from prototype.fit import MAX_WINDOWS, Rect, WindowSpec, fit_layout


class FitLayoutTests(unittest.TestCase):
    def assert_layout_contract(self, viewport, specs, result):
        self.assertTrue(result.feasible)
        self.assertEqual([p.identifier for p in result.placements], [w.identifier for w in specs])
        by_id = {w.identifier: w for w in specs}
        for index, placement in enumerate(result.placements):
            spec = by_id[placement.identifier]
            self.assertTrue(viewport.contains(placement.tile))
            self.assertTrue(placement.tile.contains(placement.interior))
            self.assertTrue(placement.interior.contains(placement.content))
            self.assertEqual(placement.interior.x - placement.tile.x, result.border)
            self.assertEqual(placement.tile.right - placement.interior.right, result.border)
            self.assertEqual(placement.interior.y - placement.tile.y, result.border)
            self.assertEqual(placement.tile.bottom - placement.interior.bottom, result.border)
            self.assertGreaterEqual(placement.content.width, spec.min_width)
            self.assertGreaterEqual(placement.content.height, spec.min_height)
            for other in result.placements[:index]:
                self.assertFalse(placement.tile.overlaps(other.tile))
            if spec.aspect is not None:
                a, b = spec.aspect
                scale = placement.aspect_scale
                self.assertLessEqual(a * scale, placement.interior.width)
                self.assertLessEqual(b * scale, placement.interior.height)
                self.assertGreaterEqual(a * scale - placement.content.width, 0)
                self.assertLess(a * scale - placement.content.width, 1)
                self.assertGreaterEqual(b * scale - placement.content.height, 0)
                self.assertLess(b * scale - placement.content.height, 1)
        self.assertEqual(result.unassigned_pixels, 0 if specs else viewport.area)
        self.assertEqual(viewport.area, result.content_pixels + result.border_pixels
                         + result.letterbox_pixels + result.unassigned_pixels)
        self.assertEqual(result.unused_content_pixels, viewport.area - result.content_pixels)

    def test_odd_dimensions_and_exact_area(self):
        viewport = Rect(-100, 20, 1919, 1079)
        specs = [WindowSpec(str(i), f"Window {i}", 80, 60) for i in range(7)]
        for border in (2, 3):
            self.assert_layout_contract(viewport, specs, fit_layout(viewport, specs, border))

    def test_fixed_aspect_is_contained_and_unused_pixels_are_honest(self):
        viewport = Rect(0, 0, 104, 104)
        specs = [WindowSpec("image", "Image", 1, 1, (16, 9))]
        result = fit_layout(viewport, specs)
        self.assert_layout_contract(viewport, specs, result)
        placement = result.placements[0]
        self.assertEqual(placement.content, Rect(2, 24, 100, 56))
        self.assertEqual(placement.aspect_scale, Fraction(25, 4))
        self.assertEqual(result.letterbox_pixels, 4400)
        self.assertEqual(result.border_pixels, 816)

    def test_aspect_minimum_is_checked_after_containment(self):
        result = fit_layout(Rect(0, 0, 100, 100),
                            [WindowSpec("wide", "Wide image", 50, 50, (16, 9))])
        self.assertTrue(result.feasible)
        self.assertGreaterEqual(result.placements[0].content.height, 50)
        failure = fit_layout(Rect(0, 0, 80, 100),
                             [WindowSpec("wide", "Wide image", 50, 50, (16, 9))])
        self.assertFalse(failure.feasible)
        self.assertEqual(failure.failure_scope, "proven-constraints")

    def test_minimum_failure_has_no_silently_shrunken_placements(self):
        specs = [WindowSpec("a", "A", 98, 20)]
        result = fit_layout(Rect(0, 0, 100, 100), specs)
        self.assertFalse(result.feasible)
        self.assertEqual(result.placements, ())
        self.assertEqual(result.unassigned_pixels, 10000)
        self.assertEqual(result.failure_scope, "proven-constraints")

    def test_total_minimum_area_failure(self):
        result = fit_layout(Rect(0, 0, 100, 100),
                            [WindowSpec("a", "A", 76, 76), WindowSpec("b", "B", 76, 76)])
        self.assertFalse(result.feasible)
        self.assertIn("sum", result.reason)

    def test_empty_output_is_fully_accounted(self):
        viewport = Rect(0, 0, 1, 1)
        self.assert_layout_contract(viewport, [], fit_layout(viewport, []))

    def test_seeded_random_layout_invariants(self):
        rng = random.Random(0x0A17)
        for case in range(240):
            viewport = Rect(rng.randint(-200, 200), rng.randint(-200, 200),
                            rng.randint(100, 1600), rng.randint(100, 1200))
            specs = [WindowSpec(f"window_{i}", f"Window {i}", rng.randint(1, 120),
                                rng.randint(1, 90),
                                (rng.randint(1, 20), rng.randint(1, 20)) if rng.randrange(3) == 0 else None)
                     for i in range(rng.randint(1, 14))]
            border = rng.choice((2, 3))
            with self.subTest(case=case):
                result = fit_layout(viewport, specs, border)
                self.assertEqual(result, fit_layout(viewport, specs, border))
                if result.feasible:
                    self.assert_layout_contract(viewport, specs, result)
                else:
                    self.assertEqual(result.placements, ())
                    self.assertIn(result.failure_scope, ("proven-constraints", "search-family-only"))
                    self.assertEqual(result.unused_content_pixels, viewport.area)

    def test_bounded_maximum_window_count(self):
        specs = [WindowSpec(str(i), str(i)) for i in range(MAX_WINDOWS)]
        viewport = Rect(0, 0, 4096, 2160)
        self.assert_layout_contract(viewport, specs, fit_layout(viewport, specs))

    def test_invalid_arguments_are_rejected(self):
        viewport = Rect(0, 0, 100, 100)
        spec = WindowSpec("a", "A")
        calls = [lambda: Rect(0, 0, True, 100), lambda: Rect(0, 0, 0, 100),
                 lambda: Rect(0, 0, 32769, 100), lambda: Rect(1048576, 0, 1, 1),
                 lambda: WindowSpec("bad id", "A"), lambda: WindowSpec("a", "\n"),
                 lambda: WindowSpec("a", "x" * 121),
                 lambda: WindowSpec("a", "A", 0), lambda: WindowSpec("a", "A", aspect=(0, 1)),
                 lambda: WindowSpec("a", "A", aspect=[1, 1]),
                 lambda: fit_layout(viewport, [spec, spec]),
                 lambda: fit_layout(viewport, [spec] * (MAX_WINDOWS + 1)),
                 lambda: fit_layout(viewport, iter([spec])),
                 lambda: fit_layout(viewport, ["invalid"]),
                 lambda: fit_layout(viewport, [spec], 1),
                 lambda: fit_layout(viewport, [spec], True)]
        for call in calls:
            with self.subTest(call=call), self.assertRaises(ValueError):
                call()


if __name__ == "__main__":
    unittest.main()
