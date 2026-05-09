from openpyxl import Workbook
from openpyxl.styles import PatternFill

from app.models.allocation import AllocationRecord
from app.services.workbook_writer import add_generated_allocation_sheet, save_workbook_to_bytes


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
    assert wb["Generated Allocation"]["G2"].fill.fgColor.rgb == "FFE9B2FA"
    assert save_workbook_to_bytes(wb).startswith(b"PK")


def test_generated_sheet_name_increments() -> None:
    wb = Workbook()
    wb.active.title = "First"
    wb.create_sheet("Original Progress")
    wb.create_sheet("Generated Allocation")
    sheet_name = add_generated_allocation_sheet(wb, [])
    assert sheet_name == "Generated Allocation 2"
    assert wb.sheetnames[1] == "Generated Allocation 2"
