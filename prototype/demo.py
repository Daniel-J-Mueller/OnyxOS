"""Run `python -m prototype.demo` for a deterministic, JSON-only host demo."""

import argparse
import json
from dataclasses import asdict

from .controls import Control, DirectionalControls
from .fit import Rect, WindowSpec
from .session import DesktopPreset, DesktopSession


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--border", type=int, choices=(2, 3), default=2)
    args = parser.parse_args()
    try:
        viewport = Rect(0, 0, args.width, args.height)
        windows = (WindowSpec("editor", "Source editor", 240, 160),
                   WindowSpec("terminal", "Build terminal", 160, 100),
                   WindowSpec("image", "Reference image", 160, 90, (16, 9)))
        standard = {"editor": Rect(80, 60, 900, 680),
                    "terminal": Rect(260, 180, 680, 420),
                    "image": Rect(620, 80, 960, 540)}
        session = DesktopSession(viewport, windows, standard,
                                 (DesktopPreset("onyx", "Onyx"),
                                  DesktopPreset("workbench", "Workbench"),
                                  DesktopPreset("compact", "Compact")), args.border)
        result = session.toggle_fit()
        layout = result.layout
        placements = []
        for placement in layout.placements:
            item = asdict(placement)
            scale = placement.aspect_scale
            item["aspect_scale"] = ({"numerator": scale.numerator, "denominator": scale.denominator}
                                    if scale is not None else None)
            placements.append(item)
        session.cycle_preset(1)
        preset = session.current_preset.identifier
        fit_after_preset = session.fit_active
        if session.fit_active:
            session.toggle_fit()
        pointer = None
        if viewport.width >= 160 and viewport.height >= 60:
            controller = DirectionalControls(viewport, [Control("close", "Close", Rect(140, 20, 8, 8))])
            first = controller.move(70, 24)
            approaching = controller.move(100, 24)
            pointer = {"before": asdict(first), "approaching": asdict(approaching)}
        output = {
            "model": "host-side-reference-only", "display_mode_changed": False,
            "feasible": layout.feasible, "failure_scope": layout.failure_scope,
            "reason": layout.reason, "search_family": layout.search_family,
            "viewport": asdict(viewport), "physical_pixel_border": layout.border,
            "placements": placements,
            "pixel_accounting": {"output": viewport.area, "content": layout.content_pixels,
                                 "reserved_borders": layout.border_pixels,
                                 "letterbox": layout.letterbox_pixels,
                                 "unassigned": layout.unassigned_pixels,
                                 "unused_content": layout.unused_content_pixels},
            "preset_after_cycle": preset, "fit_active_after_preset_cycle": fit_after_preset,
            "standard_geometry_restored_exactly": session.geometries == standard,
            "directional_control": pointer,
        }
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
