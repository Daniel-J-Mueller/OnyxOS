"""Immediate directional target expansion with stable, nonoverlapping hit areas.

This geometric model has no timers, animations, event injection, or click action.
The fixed base target keeps its identity and ownership when another one expands.
"""

from dataclasses import dataclass

from .fit import MAX_COORDINATE, Rect, identifier, integer, label


@dataclass(frozen=True)
class Control:
    identifier: str
    label: str
    base: Rect

    def __post_init__(self):
        identifier(self.identifier, "control identifier")
        label(self.label)
        if type(self.base) is not Rect:
            raise ValueError("control base must be a Rect")


@dataclass(frozen=True)
class ControlState:
    active_identifier: str | None
    expanded_rect: Rect | None


class DirectionalControls:
    def __init__(self, viewport, controls, approach_distance=64, expansion=12):
        if type(viewport) is not Rect:
            raise ValueError("viewport must be a Rect")
        if type(controls) not in (list, tuple) or len(controls) > 64:
            raise ValueError("controls must be a list or tuple of at most 64 items")
        if any(type(c) is not Control for c in controls):
            raise ValueError("each control must be a Control")
        if len({c.identifier for c in controls}) != len(controls):
            raise ValueError("control identifiers must be unique")
        for index, control in enumerate(controls):
            if not viewport.contains(control.base):
                raise ValueError("controls must be inside the viewport")
            if any(control.base.overlaps(other.base) for other in controls[:index]):
                raise ValueError("base control targets must not overlap")
        integer(approach_distance, "approach distance", 1, 256)
        integer(expansion, "expansion", 1, 64)
        self._viewport = viewport
        self._controls = tuple(controls)
        self._distance = approach_distance
        self._expansion = expansion
        self._previous = None
        self._active = None

    @property
    def state(self):
        if self._active is None:
            return ControlState(None, None)
        return ControlState(self._active.identifier, self._expanded(self._active))

    def _expanded(self, control):
        base = control.base
        left = max(self._viewport.x, base.x - self._expansion)
        top = max(self._viewport.y, base.y - self._expansion)
        right = min(self._viewport.right, base.right + self._expansion)
        bottom = min(self._viewport.bottom, base.bottom + self._expansion)
        for other in self._controls:
            if other.identifier == control.identifier:
                continue
            # Preserve a separating axis from each other fixed target.
            if base.right <= other.base.x:
                right = min(right, other.base.x)
            elif other.base.right <= base.x:
                left = max(left, other.base.right)
            elif base.bottom <= other.base.y:
                bottom = min(bottom, other.base.y)
            else:
                top = max(top, other.base.bottom)
        return Rect(left, top, right - left, bottom - top)

    @staticmethod
    def _distance_squared(rect, x, y):
        dx = max(rect.x - x, 0, x - (rect.right - 1))
        dy = max(rect.y - y, 0, y - (rect.bottom - 1))
        return dx * dx + dy * dy

    def move(self, x, y):
        """Apply one physical-pixel pointer sample; repeated samples are stable."""
        integer(x, "pointer x", -MAX_COORDINATE, MAX_COORDINATE)
        integer(y, "pointer y", -MAX_COORDINATE, MAX_COORDINATE)
        if not self._viewport.has_point(x, y):
            raise ValueError("pointer must be inside the modeled viewport")
        if self._previous == (x, y):
            return self.state
        previous = self._previous
        self._previous = (x, y)
        # A base target always owns its original area, independent of history.
        for control in self._controls:
            if control.base.has_point(x, y):
                self._active = control
                return self.state
        if self._active is not None and self._expanded(self._active).has_point(x, y):
            return self.state
        candidates = []
        if previous is not None:
            dx, dy = x - previous[0], y - previous[1]
            for control in self._controls:
                rect = control.base
                distance = self._distance_squared(rect, x, y)
                if distance > self._distance * self._distance:
                    continue
                # Doubled centers avoid floating-point boundaries. Motion must
                # approach the target within a 45-degree directional cone.
                vx, vy = 2 * rect.x + rect.width - 2 * x, 2 * rect.y + rect.height - 2 * y
                dot = dx * vx + dy * vy
                if (dot > 0 and 2 * dot * dot >= (dx * dx + dy * dy) * (vx * vx + vy * vy)
                        and distance < self._distance_squared(rect, *previous)):
                    candidates.append((distance, control.identifier, control))
        self._active = min(candidates, key=lambda item: item[:2])[2] if candidates else None
        return self.state

    def hit_test(self, x, y):
        integer(x, "pointer x", -MAX_COORDINATE, MAX_COORDINATE)
        integer(y, "pointer y", -MAX_COORDINATE, MAX_COORDINATE)
        for control in self._controls:
            if control.base.has_point(x, y):
                return control.identifier
        if self._active is not None and self._expanded(self._active).has_point(x, y):
            return self._active.identifier
        return None
