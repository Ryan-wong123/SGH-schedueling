from __future__ import annotations

from io import BytesIO
from typing import List

from openpyxl.styles import PatternFill

from app.models.allocation import AllocationRecord
from app.utils.colours import is_black_fill

ALLOCATED_CELL_FILL = PatternFill(fill_type="solid", fgColor="FF00B0F0")


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


def save_workbook_to_bytes(workbook) -> bytes:
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()
