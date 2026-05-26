from openpyxl import Workbook
from openpyxl.styles import PatternFill

from app.services.roster_parser import find_roster_entries, parse_roster


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
    assert roster.available_assessors_by_date == {"15/04/26": ["Fiona Yeo", "Genevieve Subur"]}
    assert roster.available_assessors_by_date_location == {
        "15/04/26": {
            "OPS": ["Genevieve Subur"],
            "Ward": ["Fiona Yeo"],
        }
    }
    entries = find_roster_entries(roster, "Amanda Chua Jing Yi")
    assert sorted((entry.date, entry.location) for entry in entries) == [
        ("15/04/26", "Ward"),
        ("16/04/26", "OPS"),
    ]
    ward_entries = [entry for entry in entries if entry.location == "Ward"]
    assert ward_entries[0].ward_location == "42A (1-8) RS-2"
