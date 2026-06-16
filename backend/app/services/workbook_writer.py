from __future__ import annotations

from io import BytesIO
from typing import Iterable, List, Sequence, Tuple

from openpyxl import Workbook
from openpyxl.styles import PatternFill
from openpyxl.worksheet.worksheet import Worksheet

from app.models.allocation import AllocationRecord
from app.utils.colours import is_black_fill

ALLOCATED_CELL_FILL = PatternFill(fill_type="solid", fgColor="FF00B0F0")
PREVIEW_HEADERS: Tuple[str, ...] = (
    "Date",
    "Assessee",
    "Header",
    "Assessment",
    "Location",
    "Assessor",
    "GLF Type",
    "Status",
    "Reason",
    "Cell",
)


def unique_generated_sheet_name(workbook) -> str:
    base = "Generated Allocation"
    if base not in workbook.sheetnames:
        return base
    counter = 2
    while f"{base} {counter}" in workbook.sheetnames:
        counter += 1
    return f"{base} {counter}"


def _move_sheet_to_index(workbook, worksheet, index: int) -> None:
    workbook._sheets.remove(worksheet)
    workbook._sheets.insert(index, worksheet)


def _allocation_cell_text(record: AllocationRecord) -> str:
    if record.date:
        return f"{record.assigned_assessor} {record.date}"
    return record.assigned_assessor


def add_generated_allocation_sheet(workbook, records: List[AllocationRecord]) -> str:
    template = workbook.worksheets[1]
    sheet_name = unique_generated_sheet_name(workbook)
    ws = workbook.copy_worksheet(template)
    ws.title = sheet_name
    _move_sheet_to_index(workbook, ws, 1)

    for record in records:
        if not record.original_glf_cell_reference:
            continue
        cell = ws[record.original_glf_cell_reference]
        if record.status == "Skipped - Already Passed" or is_black_fill(cell):
            cell.value = None
            continue
        if record.status == "Allocated":
            cell.value = _allocation_cell_text(record)
            cell.fill = ALLOCATED_CELL_FILL
    return sheet_name


def _preview_row(record: AllocationRecord) -> Sequence[str]:
    return (
        record.date,
        record.assessee_name,
        record.glf_section_header,
        record.assessment_type,
        record.assessee_location,
        record.assigned_assessor,
        record.assessor_glf_availability_type,
        record.status,
        record.reason or record.existing_allocation_history,
        record.original_glf_cell_reference,
    )


def _autosize_columns(worksheet: Worksheet) -> None:
    for column_cells in worksheet.columns:
        column_letter = column_cells[0].column_letter
        max_length = max(len(str(cell.value or "")) for cell in column_cells)
        worksheet.column_dimensions[column_letter].width = min(max(max_length + 2, 10), 42)


def create_preview_allocation_workbook(records: Iterable[AllocationRecord]) -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "New Allocation"
    worksheet.append(PREVIEW_HEADERS)

    for record in records:
        if record.status == "Allocated":
            worksheet.append(_preview_row(record))

    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = worksheet.dimensions
    _autosize_columns(worksheet)
    return save_workbook_to_bytes(workbook)


def save_workbook_to_bytes(workbook) -> bytes:
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()
