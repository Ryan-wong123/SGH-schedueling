from openpyxl import Workbook
from openpyxl.styles import PatternFill

from app.services.roster_parser import _ops_shift_text, find_roster_entries, parse_roster


def build_roster_workbook() -> Workbook:
    wb = Workbook()
    ws = wb.active
    ws.title = "Roster First"
    ward = wb.create_sheet("Ward Sheet")
    ws["B4"] = "15/04/26"
    ws["C4"] = "16/04/26"
    ws["A5"] = "Genevieve Subur"
    ws["B5"] = "GLF"
    ws["B5"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF00")
    ws["A7"] = "Khoo Sher Ri"
    ws["C7"] = "/GLF"
    ws["C7"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF00")
    ws["A6"] = "Amanda Chua"
    ws["B6"] = "42A"
    ws["B6"].fill = PatternFill(fill_type="solid", fgColor="FFFBE2D5")
    ws["C6"] = "Clinic-1"
    ws["C6"].fill = PatternFill(fill_type="solid", fgColor="FF92D050")
    ward["B2"] = "15/04/26"
    ward["C2"] = "17/04/26"
    ward["B3"] = "Fiona Yeo\n*floater*\n{Amanda Chua}"
    ward["B3"].fill = PatternFill(fill_type="solid", fgColor="FFFFFFFF")
    ward["A3"] = "42A (1-8)\nRS-2"
    ward["C3"] = "Amanda Chua"
    ward["C3"].fill = PatternFill(fill_type="solid", fgColor="FFFBE2D5")
    return wb


def test_roster_parser_uses_second_sheet_white_cells_for_ward_assessors_and_assessees() -> None:
    roster = parse_roster(build_roster_workbook())
    assert roster.available_assessors_by_date == {
        "15/04/26": ["Genevieve Subur"],
        "16/04/26": ["Khoo Sher Ri"],
    }
    assert roster.all_assessors == ["Genevieve Subur", "Khoo Sher Ri"]
    assert roster.assessor_availability_type_by_date == {
        "15/04/26": {"genevieve subur": "Full day GLF"},
        "16/04/26": {"khoo sher ri": "Half day GLF"},
    }
    assert roster.available_assessors_by_date_location == {
        "15/04/26": {
            "OPS": ["Genevieve Subur"],
        },
        "16/04/26": {
            "OPS": ["Khoo Sher Ri"],
        },
    }
    assert roster.ward_assessors_by_source_cell["B3"] == []
    entries = find_roster_entries(roster, "Amanda Chua Jing Yi")
    assert sorted((entry.date, entry.location) for entry in entries) == [
        ("16/04/26", "OPS"),
    ]
    assert entries[0].ops_shift == "Clinic-1"


def test_braced_ward_cell_is_fully_ignored_for_automatic_allocation() -> None:
    roster = parse_roster(build_roster_workbook())
    assert "Fiona Yeo" not in roster.available_assessors_by_date.get("15/04/26", [])
    entries = find_roster_entries(roster, "Amanda Chua Jing Yi")
    assert all(entry.source_cell != "B3" for entry in entries)


def test_ops_shift_text_extracts_shift_code_or_preserves_label() -> None:
    assert _ops_shift_text("X(C1)") == "C1"
    assert _ops_shift_text("C1") == "C1"
    assert _ops_shift_text("D") == "D"
    assert _ops_shift_text("ICT") == "ICT"
