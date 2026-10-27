"""Bounded integer-pixel Fit Mode reference model, without rendering or I/O.

The search considers balanced, contiguous shelves in both orientations. It is
deterministic, O(n**2), and deliberately does not claim globally optimal packing.
Reflowable content occupies its interior. Fixed-aspect content is contained,
never cropped; raster dimensions round down by less than one physical pixel.
"""

from dataclasses import dataclass
from fractions import Fraction

MAX_WINDOWS = 64
MAX_DIMENSION = 32768
MAX_COORDINATE = 1048576


def integer(value, name, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{name} must be an integer in [{low}, {high}]")
    return value


def identifier(value, name="identifier"):
    if (not isinstance(value, str) or not 1 <= len(value) <= 64
            or not all(c.isascii() and (c.isalnum() or c in "_.-") for c in value)):
        raise ValueError(f"{name} must contain 1-64 ASCII letters, digits, _, . or -")
    return value


def label(value):
    if (not isinstance(value, str) or len(value) > 120 or not value.strip()
            or any(not c.isprintable() for c in value)):
        raise ValueError("label must contain 1-120 printable characters")
    return value


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    width: int
    height: int

    def __post_init__(self):
        integer(self.x, "x", -MAX_COORDINATE, MAX_COORDINATE)
        integer(self.y, "y", -MAX_COORDINATE, MAX_COORDINATE)
        integer(self.width, "width", 1, MAX_DIMENSION)
        integer(self.height, "height", 1, MAX_DIMENSION)
        if abs(self.right) > MAX_COORDINATE or abs(self.bottom) > MAX_COORDINATE:
            raise ValueError("rectangle endpoints exceed coordinate bounds")

    @property
    def right(self):
        return self.x + self.width

    @property
    def bottom(self):
        return self.y + self.height

    @property
    def area(self):
        return self.width * self.height

    def contains(self, other):
        return (self.x <= other.x and self.y <= other.y
                and self.right >= other.right and self.bottom >= other.bottom)

    def overlaps(self, other):
        return (self.x < other.right and other.x < self.right
                and self.y < other.bottom and other.y < self.bottom)

    def has_point(self, x, y):
        return self.x <= x < self.right and self.y <= y < self.bottom


@dataclass(frozen=True)
class WindowSpec:
    identifier: str
    label: str
    min_width: int = 1
    min_height: int = 1
    aspect: tuple | None = None

    def __post_init__(self):
        identifier(self.identifier, "window identifier")
        label(self.label)
        integer(self.min_width, "minimum content width", 1, MAX_DIMENSION)
        integer(self.min_height, "minimum content height", 1, MAX_DIMENSION)
        if self.aspect is not None:
            if type(self.aspect) is not tuple or len(self.aspect) != 2:
                raise ValueError("aspect must be a (width, height) tuple")
            for part in self.aspect:
                integer(part, "aspect component", 1, MAX_DIMENSION)

    def minimum_interior(self):
        if self.aspect is None:
            return self.min_width, self.min_height
        a, b = self.aspect
        return (max(self.min_width, (self.min_height * a + b - 1) // b),
                max(self.min_height, (self.min_width * b + a - 1) // a))


@dataclass(frozen=True)
class Placement:
    identifier: str
    label: str
    tile: Rect
    interior: Rect
    content: Rect
    # Exact logical content transform; the integer raster box rounds down.
    aspect_scale: Fraction | None

    @property
    def border_pixels(self):
        return self.tile.area - self.interior.area

    @property
    def letterbox_pixels(self):
        return self.interior.area - self.content.area


@dataclass(frozen=True)
class LayoutResult:
    viewport: Rect
    border: int
    feasible: bool
    placements: tuple[Placement, ...]
    reason: str | None = None
    # A failed heuristic search is not a mathematical impossibility proof.
    failure_scope: str | None = None
    search_family: str = "balanced-shelves-v1"

    @property
    def content_pixels(self):
        return sum(p.content.area for p in self.placements)

    @property
    def border_pixels(self):
        return sum(p.border_pixels for p in self.placements)

    @property
    def letterbox_pixels(self):
        return sum(p.letterbox_pixels for p in self.placements)

    @property
    def unassigned_pixels(self):
        return self.viewport.area - sum(p.tile.area for p in self.placements)

    @property
    def unused_content_pixels(self):
        """Everything outside content, including deliberately reserved borders."""
        return self.border_pixels + self.letterbox_pixels + self.unassigned_pixels


def validate_windows(windows):
    if type(windows) not in (list, tuple) or len(windows) > MAX_WINDOWS:
        raise ValueError(f"windows must be a list or tuple of at most {MAX_WINDOWS} items")
    if any(type(w) is not WindowSpec for w in windows):
        raise ValueError("each window must be a WindowSpec")
    if len({w.identifier for w in windows}) != len(windows):
        raise ValueError("window identifiers must be unique")
    return tuple(windows)


def _allocate(total, minima):
    """Distribute surplus pixels equally, with deterministic remainder order."""
    surplus = total - sum(minima)
    if surplus < 0:
        return None
    share, remainder = divmod(surplus, len(minima))
    return [minimum + share + (index < remainder)
            for index, minimum in enumerate(minima)]


def _placement(spec, tile, border):
    interior = Rect(tile.x + border, tile.y + border,
                    tile.width - 2 * border, tile.height - 2 * border)
    scale = None
    content = interior
    if spec.aspect is not None:
        a, b = spec.aspect
        scale = min(Fraction(interior.width, a), Fraction(interior.height, b))
        width, height = int(a * scale), int(b * scale)
        content = Rect(interior.x + (interior.width - width) // 2,
                       interior.y + (interior.height - height) // 2, width, height)
    return Placement(spec.identifier, spec.label, tile, interior, content, scale)


def _candidate(viewport, specs, minima, border, shelves, transposed):
    count, extra = divmod(len(specs), shelves)
    groups = []
    offset = 0
    for shelf in range(shelves):
        size = count + (shelf < extra)
        groups.append(list(range(offset, offset + size)))
        offset += size
    major = viewport.height if transposed else viewport.width
    minor = viewport.width if transposed else viewport.height
    dimension = 1 if transposed else 0
    shelf_minima = [max(minima[i][1 - dimension] for i in group) for group in groups]
    shelf_sizes = _allocate(minor, shelf_minima)
    if shelf_sizes is None:
        return None
    placements = []
    minor_offset = 0
    for group, shelf_size in zip(groups, shelf_sizes):
        sizes = _allocate(major, [minima[i][dimension] for i in group])
        if sizes is None:
            return None
        major_offset = 0
        for i, size in zip(group, sizes):
            if transposed:
                tile = Rect(viewport.x + minor_offset, viewport.y + major_offset,
                            shelf_size, size)
            else:
                tile = Rect(viewport.x + major_offset, viewport.y + minor_offset,
                            size, shelf_size)
            placements.append(_placement(specs[i], tile, border))
            major_offset += size
        minor_offset += shelf_size
    return tuple(placements)


def fit_layout(viewport, windows, border=2):
    """Return a complete layout or an explicit failure; never shrink minima.

    All dimensions are physical pixels. Supplied order is the stable placement
    order. This models one output only and never changes its display mode.
    """
    if type(viewport) is not Rect:
        raise ValueError("viewport must be a Rect")
    integer(border, "physical-pixel border", 2, 3)
    specs = validate_windows(windows)
    if not specs:
        return LayoutResult(viewport, border, True, ())
    minima = [(w + border * 2, h + border * 2)
              for w, h in (spec.minimum_interior() for spec in specs)]
    if any(w > viewport.width or h > viewport.height for w, h in minima):
        return LayoutResult(viewport, border, False, (),
                            "A window minimum plus borders exceeds the output.",
                            "proven-constraints")
    if sum(w * h for w, h in minima) > viewport.area:
        return LayoutResult(viewport, border, False, (),
                            "The sum of minimum tile areas exceeds the output.",
                            "proven-constraints")
    best, best_score = None, None
    for shelves in range(1, len(specs) + 1):
        for transposed in (False, True):
            candidate = _candidate(viewport, specs, minima, border, shelves, transposed)
            if candidate is None:
                continue
            result = LayoutResult(viewport, border, True, candidate)
            areas = [p.content.area for p in candidate]
            score = (result.unused_content_pixels, Fraction(max(areas), min(areas)),
                     shelves, transposed)
            if best_score is None or score < best_score:
                best, best_score = result, score
    if best is not None:
        return best
    return LayoutResult(viewport, border, False, (),
                        "No supported balanced-shelf layout satisfies every minimum.",
                        "search-family-only")
