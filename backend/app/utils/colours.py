from __future__ import annotations

from colorsys import rgb_to_hsv
from functools import lru_cache
from xml.etree import ElementTree

from openpyxl.writer.theme import theme_xml
from typing import Literal, Optional, Tuple

from openpyxl.styles.colors import COLOR_INDEX

LocationType = Literal["Ward", "OPS", "Unknown"]


def _normalise_hex(value: Optional[str]) -> Optional[str]:
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


@lru_cache(maxsize=16)
def _theme_palette(theme: str) -> Tuple[Optional[str], ...]:
    try:
        root = ElementTree.fromstring(theme)
        scheme = root.find(".//{http://schemas.openxmlformats.org/drawingml/2006/main}clrScheme")
        if scheme is None:
            return ()
        colours = {node.tag.rsplit("}", 1)[-1]: next(iter(node), None) for node in scheme}
        palette = []
        for key in ("lt1", "dk1", "lt2", "dk2", "accent1", "accent2", "accent3", "accent4", "accent5", "accent6", "hlink", "folHlink"):
            node = colours.get(key)
            palette.append(_normalise_hex(node.get("lastClr") or node.get("val")) if node is not None else None)
        return tuple(palette)
    except (ElementTree.ParseError, TypeError):
        return ()


def fill_rgb(cell) -> Optional[str]:
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
    if color.type == "theme":
        workbook = cell.parent.parent
        palette = _theme_palette(workbook.loaded_theme or theme_xml)
        if 0 <= color.theme < len(palette) and palette[color.theme]:
            rgb = palette[color.theme]
            channels = [int(rgb[i:i + 2], 16) for i in (0, 2, 4)]
            tint = color.tint
            channels = [round(c * (1 + tint) if tint < 0 else c * (1 - tint) + 255 * tint) for c in channels]
            return "".join(f"{c:02X}" for c in channels)
    return None


def _rgb_tuple(cell) -> Optional[Tuple[int, int, int]]:
    rgb = fill_rgb(cell)
    if not rgb:
        return None
    return int(rgb[0:2], 16), int(rgb[2:4], 16), int(rgb[4:6], 16)


def has_no_fill(cell) -> bool:
    fill = getattr(cell, "fill", None)
    return fill is None or fill.fill_type is None or fill_rgb(cell) in (None, "000000")


def is_white_fill(cell) -> bool:
    fill = getattr(cell, "fill", None)
    if fill is None or fill.fill_type is None:
        return True
    rgb = _rgb_tuple(cell)
    return bool(rgb and min(rgb) >= 245)


def is_black_fill(cell) -> bool:
    fill = getattr(cell, "fill", None)
    if fill is None or fill.fill_type is None:
        return False
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
    return is_white_fill(cell)


def classify_location_from_fill(cell) -> LocationType:
    if is_green_fill(cell):
        return "OPS"
    if is_ward_fill(cell):
        return "Ward"
    return "Unknown"
