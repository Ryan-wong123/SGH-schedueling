from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import PatternFill

from app.utils.colours import classify_location_from_fill, is_black_fill, is_yellow_fill
from app.utils.dates import format_date, parse_date
from app.utils.names import names_match, normalize_name


def cell_with_fill(rgb: str):
    wb = Workbook()
    ws = wb.active
    ws["A1"].fill = PatternFill(fill_type="solid", fgColor=rgb)
    return ws["A1"]


def test_name_normalization() -> None:
    assert normalize_name("  Chan   Xiao Ting, Kristy ") == "chan xiao ting, kristy"
    assert names_match("Amanda Chua", " amanda  chua ")


def test_date_formatting() -> None:
    assert format_date("10/3/26") == "10/03/26"
    assert format_date(datetime(2026, 4, 22)) == "22/04/26"
    assert parse_date("22/04/2026").year == 2026


def test_colour_classification() -> None:
    assert is_black_fill(cell_with_fill("FF000000"))
    assert is_yellow_fill(cell_with_fill("FFFFFF00"))
    assert classify_location_from_fill(cell_with_fill("FF92D050")) == "OPS"
    assert classify_location_from_fill(cell_with_fill("FFFFFFFF")) == "Ward"
    assert classify_location_from_fill(cell_with_fill("FFFBE2D5")) == "Unknown"


def test_theme_and_indexed_colours_resolve_for_roster_and_glf():
    from openpyxl.styles import Color
    from openpyxl.writer.theme import theme_xml
    from app.utils.colours import is_green_fill, is_white_fill

    wb = Workbook()
    wb.loaded_theme = theme_xml.replace('val="4F81BD"', 'val="92D050"').replace('val="C0504D"', 'val="FFFF00"').encode()
    cell = wb.active["A1"]
    for colour, check in [(Color(theme=4), is_green_fill), (Color(theme=5), is_yellow_fill),
                          (Color(theme=0), is_white_fill), (Color(theme=1), is_black_fill),
                          (Color(indexed=3), is_green_fill), (Color(indexed=5), is_yellow_fill)]:
        cell.fill = PatternFill(fill_type="solid", fgColor=colour)
        assert check(cell)
    cell.fill = PatternFill(fill_type="solid", fgColor=Color(theme=1, tint=0.98))
    assert is_white_fill(cell)
    assert not is_black_fill(cell)
