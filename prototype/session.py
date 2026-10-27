"""Reversible fit geometry and independent desktop-preset state machines.

Preset IDs represent proposed shell profiles, not installed desktop environments.
No keyboard, display server, hardware mode switch, or application is controlled.
"""

from dataclasses import dataclass

from .fit import Rect, fit_layout, identifier, integer, label, validate_windows


@dataclass(frozen=True)
class DesktopPreset:
    identifier: str
    label: str

    def __post_init__(self):
        identifier(self.identifier, "preset identifier")
        label(self.label)


@dataclass(frozen=True)
class ToggleOutcome:
    active: bool
    changed: bool
    layout: object = None


class DesktopSession:
    def __init__(self, viewport, windows, standard_geometries, presets, border=2):
        if type(viewport) is not Rect:
            raise ValueError("viewport must be a Rect")
        self._windows = validate_windows(windows)
        integer(border, "physical-pixel border", 2, 3)
        if type(standard_geometries) is not dict:
            raise ValueError("standard geometries must be a dictionary")
        if len(standard_geometries) != len(self._windows):
            raise ValueError("standard geometries must match the window count")
        if set(standard_geometries) != {w.identifier for w in self._windows}:
            raise ValueError("standard geometries must match window identifiers exactly")
        if any(type(r) is not Rect for r in standard_geometries.values()):
            raise ValueError("standard geometries must contain Rect values")
        if type(presets) not in (list, tuple) or not 1 <= len(presets) <= 16:
            raise ValueError("provide 1-16 desktop presets")
        if any(type(p) is not DesktopPreset for p in presets):
            raise ValueError("each preset must be a DesktopPreset")
        if len({p.identifier for p in presets}) != len(presets):
            raise ValueError("preset identifiers must be unique")
        self._viewport = viewport
        self._border = border
        self._geometries = dict(standard_geometries)
        self._saved_standard = None
        self._presets = tuple(presets)
        self._preset_index = 0

    @property
    def fit_active(self):
        return self._saved_standard is not None

    @property
    def geometries(self):
        return dict(self._geometries)

    @property
    def current_preset(self):
        return self._presets[self._preset_index]

    def toggle_fit(self):
        if self.fit_active:
            self._geometries = self._saved_standard
            self._saved_standard = None
            return ToggleOutcome(False, True)
        layout = fit_layout(self._viewport, self._windows, self._border)
        if not layout.feasible:
            return ToggleOutcome(False, False, layout)
        self._saved_standard = dict(self._geometries)
        self._geometries = {p.identifier: p.tile for p in layout.placements}
        return ToggleOutcome(True, True, layout)

    def set_standard_geometry(self, window_id, rect):
        if self.fit_active:
            raise ValueError("standard geometry may only change outside Fit Mode")
        identifier(window_id, "window identifier")
        if window_id not in self._geometries or type(rect) is not Rect:
            raise ValueError("provide an existing window identifier and Rect")
        self._geometries[window_id] = rect

    def cycle_preset(self, direction):
        integer(direction, "preset direction", -1, 1)
        if direction == 0:
            raise ValueError("preset direction must be -1 or +1")
        self._preset_index = (self._preset_index + direction) % len(self._presets)
        return self.current_preset

    def select_preset(self, preset_id):
        """Direct selection supports a visible picker, independent of keybinds."""
        identifier(preset_id, "preset identifier")
        for index, preset in enumerate(self._presets):
            if preset.identifier == preset_id:
                self._preset_index = index
                return preset
        raise ValueError("unknown desktop preset")
