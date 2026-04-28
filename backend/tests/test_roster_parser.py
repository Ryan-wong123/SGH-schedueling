from openpyxl import Workbook
from openpyxl.styles import PatternFill

from app.services.roster_parser import find_roster_entries, parse_roster


def build_roster_workbook() -> Workbook:
    wb = Workbook()
    ws = wb.active
    ws.title = "Roster First"
    wb.create_sheet("Ignored Ward Sheet")
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
    ignored = wb["Ignored Ward Sheet"]
    ignored["A1"] = "Should not matter"
    ignored["B4"] = "17/04/26"
    return wb


def test_roster_parser_uses_first_sheet_only() -> None:
    roster = parse_roster(build_roster_workbook())
    assert roster.available_assessors_by_date == {"15/04/26": ["Genevieve Subur"]}
    entries = find_roster_entries(roster, "Amanda Chua Jing Yi")
    assert [entry.location for entry in entries] == ["Ward", "OPS"]
    assert all(entry.date != "17/04/26" for entry in entries)
