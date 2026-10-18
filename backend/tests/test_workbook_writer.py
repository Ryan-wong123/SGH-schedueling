from io import BytesIO

from openpyxl import Workbook
from openpyxl import load_workbook
from openpyxl.styles import Color, PatternFill

from app.models.allocation import AllocationRecord
from app.services.workbook_writer import (
    ALLOCATED_CELL_FILL,
    PREVIEW_HEADERS,
    add_generated_allocation_sheet,
    create_preview_allocation_workbook,
    save_workbook_to_bytes,
)


def test_generated_sheet_copies_progress_format_and_writes_allocations() -> None:
    wb = Workbook()
    wb.active.title = "First"
    progress = wb.create_sheet("Original Progress")
    progress["A1"] = "GLF Assessment 2026 Cycle 1"
    progress["G1"] = "Rx check"
    progress["A2"] = "Person"
    progress["G2"].fill = PatternFill(fill_type="solid", fgColor="FFE9B2FA")
    wb.create_sheet("Later")
    records = [
        AllocationRecord(
            date="15/04/26",
            assessee_name="Person",
            assessment_type="Rx Check",
            assessee_location="Ward",
            assigned_assessor="Assessor",
            assessor_glf_availability_date="15/04/26",
            assessor_glf_availability_type="Half day GLF",
            status="Allocated",
            reason="",
            original_glf_cell_reference="G2",
            existing_allocation_history="",
        )
    ]
    sheet_name = add_generated_allocation_sheet(wb, records)
    assert sheet_name == "Generated Allocation"
    assert wb.sheetnames[:3] == ["First", "Generated Allocation", "Original Progress"]
    assert wb["Original Progress"]["G2"].value is None
    assert wb["Generated Allocation"]["A1"].value == "GLF Assessment 2026 Cycle 1"
    assert wb["Generated Allocation"]["G2"].value == "Assessor 15/04/26"
    assert wb["Generated Allocation"]["G2"].fill.fgColor.rgb == ALLOCATED_CELL_FILL.fgColor.rgb
    assert save_workbook_to_bytes(wb).startswith(b"PK")


def test_generated_sheet_clears_black_passed_cells_and_does_not_write_allocations_to_them() -> None:
    wb = Workbook()
    wb.active.title = "First"
    progress = wb.create_sheet("Original Progress")
    progress["A1"] = "GLF Assessment 2026 Cycle 1"
    progress["G1"] = "Rx check"
    progress["A2"] = "Person"
    progress["G2"] = "Old Assessor 01/01/26"
    progress["G2"].fill = PatternFill(fill_type="solid", fgColor="FF000000")
    progress["H2"].fill = PatternFill(fill_type="solid", fgColor="FF000000")

    records = [
        AllocationRecord(
            date="",
            assessee_name="Person",
            assessment_type="Rx Check",
            assessee_location="",
            assigned_assessor="",
            assessor_glf_availability_date="",
            status="Skipped - Already Passed",
            reason="Black-filled cell",
            original_glf_cell_reference="G2",
            existing_allocation_history="",
        ),
        AllocationRecord(
            date="15/04/26",
            assessee_name="Person",
            assessment_type="Dispensing",
            assessee_location="OPS",
            assigned_assessor="Assessor",
            assessor_glf_availability_date="15/04/26",
            status="Allocated",
            reason="",
            original_glf_cell_reference="H2",
            existing_allocation_history="",
        ),
    ]

    add_generated_allocation_sheet(wb, records)

    generated = wb["Generated Allocation"]
    assert generated["G2"].value is None
    assert generated["H2"].value is None
    assert generated["G2"].fill.fgColor.rgb == "FF000000"
    assert generated["H2"].fill.fgColor.rgb == "FF000000"


def test_generated_sheet_does_not_write_allocations_to_theme_black_cells() -> None:
    wb = Workbook()
    wb.active.title = "First"
    progress = wb.create_sheet("Original Progress")
    progress["A1"] = "GLF Assessment 2026 Cycle 1"
    progress["G1"] = "Rx check"
    progress["A2"] = "Person"
    progress["G2"].fill = PatternFill(fill_type="solid", fgColor=Color(theme=1, tint=0))

    records = [
        AllocationRecord(
            date="15/04/26",
            assessee_name="Person",
            assessment_type="Rx Check",
            assessee_location="Ward",
            assigned_assessor="Assessor",
            assessor_glf_availability_date="15/04/26",
            status="Allocated",
            reason="",
            original_glf_cell_reference="G2",
            existing_allocation_history="",
        )
    ]

    add_generated_allocation_sheet(wb, records)

    assert wb["Generated Allocation"]["G2"].value is None


def test_generated_sheet_name_increments() -> None:
    wb = Workbook()
    wb.active.title = "First"
    wb.create_sheet("Original Progress")
    wb.create_sheet("Generated Allocation")
    sheet_name = add_generated_allocation_sheet(wb, [])
    assert sheet_name == "Generated Allocation 2"
    assert wb.sheetnames[1] == "Generated Allocation 2"


def test_preview_allocation_workbook_matches_website_output_columns() -> None:
    records = [
        AllocationRecord(
            date="15/04/26",
            assessee_name="Person",
            assessment_type="MiniCeX",
            assessee_location="Ward (7A)",
            assigned_assessor="Assessor",
            assessor_glf_availability_date="15/04/26",
            assessor_glf_availability_type="Half day GLF",
            status="Allocated",
            reason="",
            original_glf_cell_reference="J2",
            existing_allocation_history="",
            glf_section_header="Y10",
        ),
        AllocationRecord(
            date="",
            assessee_name="Other Person",
            assessment_type="Dispensing",
            assessee_location="OPS",
            assigned_assessor="",
            assessor_glf_availability_date="",
            status="Unallocated",
            reason="No eligible assessor found",
            original_glf_cell_reference="H3",
            existing_allocation_history="",
            glf_section_header="Y7",
        ),
    ]

    workbook_bytes = create_preview_allocation_workbook(records)
    wb = load_workbook(BytesIO(workbook_bytes))
    ws = wb["New Allocation"]

    assert [cell.value for cell in ws[1]] == list(PREVIEW_HEADERS)
    assert [cell.value for cell in ws[2]] == [
        "15/04/26",
        "Person",
        "Y10",
        "MiniCeX",
        "Ward (7A)",
        "Assessor",
        "Half day GLF",
        "Allocated",
        None,
        "J2",
    ]
    assert ws.max_row == 2
