from __future__ import annotations

from io import BytesIO

from app.models.allocation import AllocationRecord


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


def add_generated_allocation_sheet(workbook, records: list[AllocationRecord]) -> str:
    template = workbook.worksheets[1]
    sheet_name = unique_generated_sheet_name(workbook)
    ws = workbook.copy_worksheet(template)
    ws.title = sheet_name
    _move_sheet_to_index(workbook, ws, 1)

    for record in records:
        if record.status == "Allocated" and record.original_glf_cell_reference:
            ws[record.original_glf_cell_reference].value = _allocation_cell_text(record)
    return sheet_name


def save_workbook_to_bytes(workbook) -> bytes:
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()
