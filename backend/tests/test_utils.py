from datetime import datetime

import pytest
from openpyxl import Workbook
from openpyxl.styles import PatternFill

from app.utils.colours import classify_location_from_fill, is_black_fill, is_yellow_fill
from app.utils.dates import format_date, parse_date
from app.utils.names import names_match, names_token_match, normalize_name


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


@pytest.mark.parametrize(
    ("glf_name", "roster_name"),
    [
        ("Amanda Chua Jing Yi", "Amanda Chua"),
        ("Ho Siang Kin Kelly", "Kelly Ho"),
        ("Loh Yen Shan Charlotte", "Charlotte Loh"),
        ("Chan Xiao Ting, Kristy", "Kristy Chan"),
        ("Joan Wee (DI/IP)", "Joan Wee"),
        ("Lee Jun Yin", "Lee Jun Yin*"),
        ("Goh Jia Ying", "Goh Jia Ying (Megan)"),
    ],
)
def test_names_token_match_ignores_word_order_commas_and_brackets(glf_name: str, roster_name: str) -> None:
    assert names_token_match(glf_name, roster_name)


@pytest.mark.parametrize(
    ("glf_name", "roster_name"),
    [
        ("Tan Elisa", "Eda Tan"),
        ("Tham Yat Tinn Nicole", "Vivien Tham"),
        ("Kelly", "Kelly Ho"),
        ("", "Kelly Ho"),
    ],
)
def test_names_token_match_needs_every_roster_word(glf_name: str, roster_name: str) -> None:
    assert not names_token_match(glf_name, roster_name)
