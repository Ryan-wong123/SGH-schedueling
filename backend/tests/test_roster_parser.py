import pytest
from openpyxl import Workbook
from openpyxl.styles import PatternFill

from app.services.roster_parser import _has_ward_value, _ops_shift_text, find_roster_entries, parse_roster


WHITE = PatternFill(fill_type="solid", fgColor="FFFFFFFF")


def build_roster_workbook() -> Workbook:
    wb = Workbook()
    ws = wb.active
    ws.title = "Roster First"
    ws["B4"] = "15/04/26"
    ws["C4"] = "16/04/26"
    ws["D4"] = "17/04/26"
    ws["A5"] = "Genevieve Subur"
    ws["B5"] = "GLF"
    ws["B5"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF00")
    ws["A6"] = "Amanda Chua"
    ws["B6"] = "{ACC1}\n42A"
    ws["B6"].fill = WHITE
    ws["C6"] = "Clinic-1"
    ws["C6"].fill = PatternFill(fill_type="solid", fgColor="FF92D050")
    ws["D6"] = "45A\nMICA"
    ws["D6"].fill = WHITE
    ws["A7"] = "Khoo Sher Ri"
    ws["C7"] = "/GLF"
    ws["C7"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF00")
    ws["D7"] = "MICU\nBurns"
    ws["D7"].fill = WHITE
    ws["A8"] = "Fiona Yeo"
    ws["B8"] = "*floater*"
    ws["B8"].fill = WHITE
    ws["C8"] = "CTS"
    ws["C8"].fill = WHITE
    ws["D8"] = "42B"
    ws["D8"].fill = PatternFill(fill_type="solid", fgColor="FFFBE2D5")
    ignored = wb.create_sheet("Ignored Ward Sheet")
    ignored["B2"] = "15/04/26"
    ignored["B3"] = "Fiona Yeo"
    ignored["B3"].fill = WHITE
    return wb


def test_roster_parser_uses_first_sheet_white_ward_cells_for_assessors_and_assessee_locations() -> None:
    roster = parse_roster(build_roster_workbook())
    assert roster.available_assessors_by_date == {
        "15/04/26": ["Amanda Chua", "Genevieve Subur"],
        "16/04/26": ["Khoo Sher Ri"],
        "17/04/26": ["Amanda Chua"],
    }
    assert roster.all_assessors == ["Amanda Chua", "Genevieve Subur", "Khoo Sher Ri"]
    assert roster.assessor_availability_type_by_date == {
        "15/04/26": {"genevieve subur": "Full day GLF", "amanda chua": "Full day GLF"},
        "16/04/26": {"khoo sher ri": "Half day GLF"},
        "17/04/26": {"amanda chua": "Full day GLF"},
    }
    assert roster.available_assessors_by_date_location == {
        "15/04/26": {"OPS": ["Genevieve Subur"], "Ward": ["Amanda Chua"]},
        "16/04/26": {"OPS": ["Khoo Sher Ri"]},
        "17/04/26": {"Ward": ["Amanda Chua"]},
    }
    assert roster.ward_assessors_by_source_cell == {"B6": ["Amanda Chua"], "D6": ["Amanda Chua"]}
    entries = find_roster_entries(roster, "Amanda Chua Jing Yi")
    assert sorted((entry.date, entry.location) for entry in entries) == [
        ("15/04/26", "Ward"),
        ("16/04/26", "OPS"),
        ("17/04/26", "Ward"),
    ]
    assert next(entry for entry in entries if entry.location == "OPS").ops_shift == "Clinic-1"
    ward_entry = next(entry for entry in entries if entry.source_cell == "D6")
    assert ward_entry.ward_location == "45A MICA"


def test_braces_are_removed_and_inner_text_is_classified_normally() -> None:
    wb = build_roster_workbook()
    ws = wb.worksheets[0]
    ws["A9"] = "Lim Rou Wei"
    ws["B9"] = "{45A}"
    ws["B9"].fill = WHITE
    ws["C9"] = "{CICU}"
    ws["C9"].fill = WHITE
    roster = parse_roster(wb)

    mixed_entry = next(entry for entry in find_roster_entries(roster, "Amanda Chua Jing Yi") if entry.source_cell == "B6")
    assert mixed_entry.location == "Ward"
    assert mixed_entry.ward_location == "{ACC1} 42A"

    entries = find_roster_entries(roster, "Lim Rou Wei")
    assert [(entry.source_cell, entry.ward_location) for entry in entries] == [("B9", "{45A}")]
    assert "C9" not in roster.ward_assessors_by_source_cell


def test_white_cells_with_only_non_ward_values_are_excluded() -> None:
    roster = parse_roster(build_roster_workbook())
    assert find_roster_entries(roster, "Khoo Sher Ri") == []
    assert find_roster_entries(roster, "Fiona Yeo") == []
    assert "D7" not in roster.ward_assessors_by_source_cell
    assert "C8" not in roster.ward_assessors_by_source_cell


@pytest.mark.parametrize(
    "value",
    [
        "11B",
        "45A\nMICA",
        "45AMICA",
        "75B/C\nSB",
        "58 ISO",
        "58(ISO)",
        "SICU\n68ICU\nCCU",
        "63(12-14)\n75C",
        "44A, 22",
        "MIC2\n76A",
        "{ACC1}\n64(15-18)",
        "45A\n{NICU-1}",
        "67A\n{CICU}",
        "{45A}",
        "MICU\n{58B}",
        "DD\n76A/C",
        "11B\n/oc",
    ],
)
def test_has_ward_value_accepts_cells_with_a_ward_number(value: str) -> None:
    assert _has_ward_value(value)


@pytest.mark.parametrize(
    "value",
    [
        "Admin",
        "MICU",
        "MICU\nBurns",
        "CTS\nMICA",
        "DI",
        "HDL",
        "INF",
        "MIC",
        "IPAS/IDD\nMSF (2-5)",
        "SGH@Home Command Centre",
        "WR - IM",
        "Clinic-1",
        "Clinic-2/RTxC",
        "NICU-1\nNICU-2\nCCU",
        "10am - 7pm",
        "{CICU}",
        "{ACC1}\nMICU",
    ],
)
def test_has_ward_value_rejects_cells_with_only_non_ward_values(value: str) -> None:
    assert not _has_ward_value(value)


def test_ops_shift_text_extracts_shift_code_or_preserves_label() -> None:
    assert _ops_shift_text("X(C1)") == "C1"
    assert _ops_shift_text("C1") == "C1"
    assert _ops_shift_text("D") == "D"
    assert _ops_shift_text("ICT") == "ICT"


@pytest.mark.parametrize("value", ["45", "MICA45A", "MICU68ICU", "45A75B", "{45}A", "MICA_x000D_45A"])
def test_ward_detection_does_not_require_separators_or_suffix(value):
    assert _has_ward_value(value)


@pytest.mark.parametrize("marker", ["/GLF", "GLF/"])
def test_single_sheet_roster_accepts_both_half_day_markers(marker):
    from io import BytesIO
    from app.services.excel_reader import load_roster_workbook_from_bytes

    wb = build_roster_workbook()
    del wb["Ignored Ward Sheet"]
    wb.active["C7"] = marker
    stream = BytesIO()
    wb.save(stream)
    roster = parse_roster(load_roster_workbook_from_bytes(stream.getvalue()))
    assert roster.assessor_availability_type_by_date["16/04/26"]["khoo sher ri"] == "Half day GLF"
    assert find_roster_entries(roster, "Amanda Chua")[0].ward_location == "{ACC1} 42A"


def test_floater_row_is_not_an_assessor_or_assessee():
    wb = build_roster_workbook()
    wb.active["A9"] = "*floater*"
    wb.active["B9"] = "45A"
    wb.active["B9"].fill = WHITE
    roster = parse_roster(wb)
    assert "*floater*" not in roster.all_assessors
    assert find_roster_entries(roster, "*floater*") == []
