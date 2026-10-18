from io import BytesIO

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Color, PatternFill

from app.services.excel_reader import WRONG_PASSWORD_MESSAGE, load_glf_workbook_from_bytes
from app.services.glf_parser import parse_glf_progress
from app.utils.errors import AppError


def build_glf_workbook() -> Workbook:
    wb = Workbook()
    wb.active.title = "Criteria"
    ws = wb.create_sheet("Progress")
    ws.append(
        [
            "GLF Assessment",
            "Mentor",
            "Appraiser",
            "Preceptor",
            "MM/YY joined",
            "MM/YY first registered",
            "Rx check",
            "Dispensing",
            "Med recon",
            "MiniCEX",
            "CBD",
            "PA",
        ]
    )
    ws.append(["Y1"])
    ws.append(["Person One", "M", "A", "P", None, "2024", None, "Assessor 10/03/26", None, None, None, None])
    ws["I3"].fill = PatternFill(fill_type="solid", fgColor="FF000000")
    ws["J3"].fill = PatternFill(fill_type="solid", fgColor="FFE9B2FA")
    return wb


def workbook_bytes(wb: Workbook) -> bytes:
    stream = BytesIO()
    wb.save(stream)
    return stream.getvalue()


def test_glf_parser_uses_second_sheet_and_classifies_cells() -> None:
    needs = parse_glf_progress(build_glf_workbook())
    by_cell = {need.original_glf_cell_reference: need for need in needs}
    assert by_cell["G3"].needs_allocation
    assert by_cell["G3"].glf_section_header == "Y1"
    assert by_cell["H3"].status == "Skipped - Already Allocated"
    assert by_cell["I3"].status == "Skipped - Already Passed"
    assert by_cell["J3"].needs_allocation
    assert all(need.assessment_type not in {"CBD", "PA"} for need in needs)


def test_glf_parser_extracts_existing_assessors_from_all_allocated_assessment_cells() -> None:
    wb = build_glf_workbook()
    ws = wb["Progress"]
    ws["G3"] = "Rx Assessor 10/03/26"
    ws["H3"] = "Disp Assessor 11/03/26"
    ws["I3"] = "Med Assessor 12/03/26"
    ws["I3"].fill = PatternFill()

    needs = parse_glf_progress(wb)
    minicex_need = next(need for need in needs if need.original_glf_cell_reference == "J3")

    assert minicex_need.needs_allocation
    assert minicex_need.existing_assessors_for_row == ("Rx Assessor", "Disp Assessor", "Med Assessor")


def test_glf_parser_treats_theme_dark_cells_as_already_passed() -> None:
    wb = build_glf_workbook()
    ws = wb["Progress"]
    ws["G3"].fill = PatternFill(fill_type="solid", fgColor=Color(theme=1, tint=0))

    needs = parse_glf_progress(wb)
    by_cell = {need.original_glf_cell_reference: need for need in needs}

    assert by_cell["G3"].status == "Skipped - Already Passed"
    assert not by_cell["G3"].needs_allocation


def test_glf_parser_stops_before_legend_block() -> None:
    wb = build_glf_workbook()
    ws = wb["Progress"]
    ws.append(["Legend"])
    ws.append(["arrange for CBD in cycle 1", None, None, None, None, None, None, None, None, None, "note", None])
    ws.append(["rotation in IP first", None, None, None, None, None, None, None, None, None, None, "note"])

    needs = parse_glf_progress(wb)

    assert {need.assessee_name for need in needs} == {"Person One"}


def test_unencrypted_glf_workbook_can_load_when_password_supplied() -> None:
    loaded = load_glf_workbook_from_bytes(workbook_bytes(build_glf_workbook()), "anything")
    assert loaded.sheetnames[1] == "Progress"


def test_invalid_glf_workbook_raises_clear_error() -> None:
    try:
        load_glf_workbook_from_bytes(b"not excel", "wrong")
    except AppError as exc:
        assert exc.message in {WRONG_PASSWORD_MESSAGE, "Invalid Excel file."}
    else:
        raise AssertionError("Expected AppError")
