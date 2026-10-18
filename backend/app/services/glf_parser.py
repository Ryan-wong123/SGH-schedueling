from __future__ import annotations

import re
from typing import Dict, List, Tuple

from openpyxl.utils import get_column_letter

from app.models.allocation import ASSESSMENT_TYPES, GlfAssessmentNeed
from app.utils.colours import is_black_fill, is_red_fill
from app.utils.errors import AppError
from app.utils.names import normalize_name


HEADER_ALIASES = {
    "rxcheck": "Rx Check",
    "dispensing": "Dispensing",
    "medrecon": "Med Recon",
    "minicex": "MiniCeX",
}
SECTION_HEADERS = {"new pre-reg > oprs"}
END_MARKERS = {"legend"}


def _canonical_header(value: object) -> str:
    text = normalize_name(value).replace(" ", "")
    return HEADER_ALIASES.get(text, "")


def _find_assessment_columns(ws) -> Tuple[int, Dict[str, int]]:
    for row in ws.iter_rows(min_row=1, max_row=min(ws.max_row, 30)):
        found: Dict[str, int] = {}
        for cell in row:
            assessment = _canonical_header(cell.value)
            if assessment:
                found[assessment] = cell.column
        if all(assessment in found for assessment in ASSESSMENT_TYPES):
            return row[0].row, found
    missing = ", ".join(ASSESSMENT_TYPES)
    raise AppError(f"Could not find required assessment columns: {missing}.")


def _is_section_header(value: object) -> bool:
    text = normalize_name(value)
    if not text:
        return True
    if text in SECTION_HEADERS:
        return True
    if re.fullmatch(r"y\d+", text):
        return True
    return False


def _is_end_marker(value: object) -> bool:
    return normalize_name(value) in END_MARKERS


def _extract_existing_assessors(text: object) -> Tuple[str, ...]:
    if text is None:
        return ()
    raw = str(text).strip()
    if not raw:
        return ()
    before_date = re.split(r"\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b", raw, maxsplit=1)[0]
    parts = re.split(r"/|,|&|\band\b", before_date)
    names = tuple(part.strip() for part in parts if part.strip())
    return names or (raw,)


def parse_glf_progress(workbook) -> List[GlfAssessmentNeed]:
    if len(workbook.worksheets) < 2:
        raise AppError("The GLF workbook must contain at least two worksheets.")
    ws = workbook.worksheets[1]
    header_row, assessment_columns = _find_assessment_columns(ws)
    needs: List[GlfAssessmentNeed] = []
    current_section_header = ""

    for row_index in range(header_row + 1, ws.max_row + 1):
        name_cell = ws.cell(row_index, 1)
        assessee_name = str(name_cell.value).strip() if name_cell.value is not None else ""
        if _is_end_marker(assessee_name):
            break
        if _is_section_header(assessee_name):
            if assessee_name:
                current_section_header = assessee_name
            continue

        existing_for_row: List[str] = []
        for assessment in ASSESSMENT_TYPES:
            existing_for_row.extend(_extract_existing_assessors(ws.cell(row_index, assessment_columns[assessment]).value))

        for assessment in ASSESSMENT_TYPES:
            column = assessment_columns[assessment]
            cell = ws.cell(row_index, column)
            cell_ref = f"{get_column_letter(column)}{row_index}"
            value = cell.value
            existing_history = "" if value is None else str(value).strip()

            if is_black_fill(cell):
                needs.append(
                    GlfAssessmentNeed(
                        assessee_name=assessee_name,
                        assessment_type=assessment,
                        original_glf_cell_reference=cell_ref,
                        needs_allocation=False,
                        glf_section_header=current_section_header,
                        status="Skipped - Already Passed",
                        reason="Black-filled cell",
                        existing_assessors_for_row=tuple(existing_for_row),
                    )
                )
            elif existing_history:
                needs.append(
                    GlfAssessmentNeed(
                        assessee_name=assessee_name,
                        assessment_type=assessment,
                        original_glf_cell_reference=cell_ref,
                        needs_allocation=False,
                        glf_section_header=current_section_header,
                        status="Skipped - Already Allocated",
                        reason="Existing allocation found",
                        existing_allocation_history=existing_history,
                        existing_assessors_for_row=tuple(existing_for_row),
                    )
                )
            elif is_red_fill(cell):
                needs.append(
                    GlfAssessmentNeed(
                        assessee_name=assessee_name,
                        assessment_type=assessment,
                        original_glf_cell_reference=cell_ref,
                        needs_allocation=False,
                        glf_section_header=current_section_header,
                        status="Skipped - Unsupported Cell State",
                        reason="Blank red-filled assessment cell is not automatically allocatable",
                        existing_assessors_for_row=tuple(existing_for_row),
                    )
                )
            else:
                needs.append(
                    GlfAssessmentNeed(
                        assessee_name=assessee_name,
                        assessment_type=assessment,
                        original_glf_cell_reference=cell_ref,
                        needs_allocation=True,
                        glf_section_header=current_section_header,
                        existing_assessors_for_row=tuple(existing_for_row),
                    )
                )
    return needs
