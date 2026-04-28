from __future__ import annotations

from colorsys import rgb_to_hsv
from typing import Literal

from openpyxl.styles.colors import COLOR_INDEX

LocationType = Literal["Ward", "OPS", "Unknown"]


def _normalise_hex(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    if len(value) == 8:
        value = value[2:]
    if len(value) != 6:
        return None
    try:
        int(value, 16)
    except ValueError:
        return None
    return value.upper()


def fill_rgb(cell) -> str | None:
    fill = getattr(cell, "fill", None)
    if fill is None or fill.fill_type is None:
        return None
    color = fill.fgColor
    if color is None:
        return None
    if color.type == "rgb":
        return _normalise_hex(color.rgb)
    if color.type == "indexed" and color.indexed is not None and color.indexed < len(COLOR_INDEX):
        return _normalise_hex(COLOR_INDEX[color.indexed])
    # Theme colours need the workbook theme to resolve accurately. When openpyxl
    # cannot expose an RGB value, callers fall back to value-based rules.
    return None


def _rgb_tuple(cell) -> tuple[int, int, int] | None:
    rgb = fill_rgb(cell)
    if not rgb:
        return None
    return int(rgb[0:2], 16), int(rgb[2:4], 16), int(rgb[4:6], 16)


def has_no_fill(cell) -> bool:
    fill = getattr(cell, "fill", None)
    return fill is None or fill.fill_type is None or fill_rgb(cell) in (None, "000000")


def is_black_fill(cell) -> bool:
    rgb = _rgb_tuple(cell)
    return bool(rgb and max(rgb) <= 45)


def is_yellow_fill(cell) -> bool:
    rgb = _rgb_tuple(cell)
    if not rgb:
        return False
    red, green, blue = rgb
    return red >= 190 and green >= 175 and blue <= 90


def is_green_fill(cell) -> bool:
    rgb = _rgb_tuple(cell)
    if not rgb:
        return False
    red, green, blue = rgb
    hue, saturation, value = rgb_to_hsv(red / 255, green / 255, blue / 255)
    return 0.20 <= hue <= 0.45 and saturation >= 0.25 and value >= 0.45


def is_red_fill(cell) -> bool:
    rgb = _rgb_tuple(cell)
    if not rgb:
        return False
    red, green, blue = rgb
    return red >= 180 and green <= 90 and blue <= 90


def is_ward_fill(cell) -> bool:
    if has_no_fill(cell):
        return True
    rgb = _rgb_tuple(cell)
    if not rgb:
        return False
    red, green, blue = rgb
    if min(rgb) >= 235:
        return True
    if red >= 185 and green >= 135 and blue >= 185:
        return True
    if red >= 210 and green >= 170 and blue >= 120:
        return True
    if red >= 190 and 80 <= green <= 190 and blue <= 120:
        return True
    return False


def classify_location_from_fill(cell) -> LocationType:
    if is_green_fill(cell):
        return "OPS"
    if is_ward_fill(cell):
        return "Ward"
    return "Unknown"
