from __future__ import annotations

from collections import defaultdict
import re
from typing import DefaultDict, Dict, List, Tuple

from app.models.allocation import GlfAvailabilityType, LocationType, RosterData, RosterEntry
from app.utils.colours import is_green_fill, is_white_fill, is_yellow_fill
from app.utils.dates import format_date, parse_date
from app.utils.errors import AppError
from app.utils.names import names_prefix_match, normalize_name


SKIP_ROSTER_VALUES = {"", "glf", "x", "off", "al", "mc", "leave", "hl", "ops", "floater"}
# A ward value is a two-digit ward number followed by a letter or bracket, e.g. 11B,
# 45A, 58 ISO, 63(12-14), 68ICU. Single digits (NICU-1, MSF (2-5)) and times (10am)
# are not ward numbers.
WARD_VALUE_PATTERN = re.compile(r"(?<![A-Za-z0-9-])\d{2}(?!\d)(?!\s*[ap]\.?m\b)\s?[A-Za-z(]", re.IGNORECASE)
OPS_SHIFT_PATTERN = re.compile(r"\b([A-F](?:[12]|\+)?)\b|\(([A-F](?:[12]|\+)?)\)|(\?)", re.IGNORECASE)


def _find_date_columns(ws) -> Tuple[int, Dict[int, str]]:
    best_row = 0
    best_dates: Dict[int, str] = {}
    for row_index in range(1, min(ws.max_row, 15) + 1):
        dates = {
            col: format_date(ws.cell(row_index, col).value)
            for col in range(2, ws.max_column + 1)
            if parse_date(ws.cell(row_index, col).value)
        }
        if len(dates) > len(best_dates):
            best_row = row_index
            best_dates = dates
    if not best_dates:
        raise AppError("Unable to identify roster date columns.")
    return best_row, best_dates


def _is_schedule_value(value: object) -> bool:
    text = str(value).replace("\xa0", " ").strip().casefold() if value is not None else ""
    marker = re.sub(r"[^a-z0-9]+", "", text)
    if text in SKIP_ROSTER_VALUES or marker in SKIP_ROSTER_VALUES or "floater" in marker:
        return False
    return bool(text)


def _add_entry(entries: Dict[str, List[RosterEntry]], name: str, entry: RosterEntry) -> None:
    entries[normalize_name(name)].append(entry)


def _strip_braces(text: str) -> str:
    # Braces are only markers; the text inside is classified like any other value.
    return text.replace("{", " ").replace("}", " ")


def _ward_location_text(value: object) -> str:
    if value is None:
        return ""
    # Excel can store carriage returns as the literal escape "_x000D_".
    return " ".join(str(value).replace("_x000D_", " ").replace("\xa0", " ").split())


def _ops_shift_text(value: object) -> str:
    if value is None:
        return ""
    text = " ".join(str(value).replace("\xa0", " ").split())
    for match in OPS_SHIFT_PATTERN.finditer(text):
        shift = next((group for group in match.groups() if group), "")
        if shift:
            return shift.upper()
    return text


def _has_ward_value(value: object) -> bool:
    if value is None:
        return False
    return bool(WARD_VALUE_PATTERN.search(_strip_braces(str(value).replace("\xa0", " "))))


def _add_available(
    available: Dict[str, List[str]],
    available_by_location: Dict[str, Dict[LocationType, List[str]]],
    availability_type_by_date: Dict[str, Dict[str, GlfAvailabilityType]],
    date_text: str,
    location: LocationType,
    assessor_name: str,
    availability_type: GlfAvailabilityType = "Full day GLF",
) -> None:
    available[date_text].append(assessor_name)
    available_by_location[date_text][location].append(assessor_name)
    assessor_key = normalize_name(assessor_name)
    current = availability_type_by_date[date_text].get(assessor_key)
    if current != "Half day GLF":
        availability_type_by_date[date_text][assessor_key] = availability_type


def _glf_availability_type(value: object) -> GlfAvailabilityType:
    text = str(value).replace("\xa0", " ").strip().casefold() if value is not None else ""
    if text == "/glf":
        return "Half day GLF"
    if text == "glf":
        return "Full day GLF"
    return ""


def _parse_primary_roster_sheet(
    ws,
    available: Dict[str, List[str]],
    available_by_location: Dict[str, Dict[LocationType, List[str]]],
    availability_type_by_date: Dict[str, Dict[str, GlfAvailabilityType]],
    entries: Dict[str, List[RosterEntry]],
    ward_assessors_by_source_cell: Dict[str, List[str]],
) -> None:
    date_row, date_columns = _find_date_columns(ws)
    for row_index in range(date_row + 1, ws.max_row + 1):
        name_value = ws.cell(row_index, 1).value
        if name_value is None:
            continue
        name = str(name_value).strip()
        if not name:
            continue

        for col, date_text in date_columns.items():
            cell = ws.cell(row_index, col)
            value = cell.value
            text = str(value).strip() if value is not None else ""
            availability_type = _glf_availability_type(text)
            if availability_type and is_yellow_fill(cell):
                _add_available(
                    available,
                    available_by_location,
                    availability_type_by_date,
                    date_text,
                    "OPS",
                    name,
                    availability_type,
                )
                continue
            if not _is_schedule_value(value):
                continue
            if is_white_fill(cell):
                _add_ward_cell(
                    cell, name, date_text, available, available_by_location, availability_type_by_date, entries,
                    ward_assessors_by_source_cell,
                )
                continue
            if not is_green_fill(cell):
                continue
            _add_entry(
                entries,
                name,
                RosterEntry(
                    assessee_name=name,
                    date=date_text,
                    location="OPS",
                    source_cell=cell.coordinate,
                    ops_shift=_ops_shift_text(value),
                ),
            )


def _add_ward_cell(
    cell,
    name: str,
    date_text: str,
    available: Dict[str, List[str]],
    available_by_location: Dict[str, Dict[LocationType, List[str]]],
    availability_type_by_date: Dict[str, Dict[str, GlfAvailabilityType]],
    entries: Dict[str, List[RosterEntry]],
    ward_assessors_by_source_cell: Dict[str, List[str]],
) -> None:
    text = str(cell.value)
    if not _has_ward_value(text):
        return
    ward_assessors_by_source_cell[cell.coordinate] = [name]
    _add_available(available, available_by_location, availability_type_by_date, date_text, "Ward", name)
    _add_entry(
        entries,
        name,
        RosterEntry(
            assessee_name=name,
            date=date_text,
            location="Ward",
            source_cell=cell.coordinate,
            ward_location=_ward_location_text(text),
        ),
    )


def parse_roster(workbook) -> RosterData:
    if not workbook.worksheets:
        raise AppError("The roster workbook must contain at least one worksheet.")
    available: DefaultDict[str, List[str]] = defaultdict(list)
    available_by_location: DefaultDict[str, DefaultDict[LocationType, List[str]]] = defaultdict(
        lambda: defaultdict(list)
    )
    availability_type_by_date: DefaultDict[str, Dict[str, GlfAvailabilityType]] = defaultdict(dict)
    entries: DefaultDict[str, List[RosterEntry]] = defaultdict(list)
    ward_assessors_by_source_cell: Dict[str, List[str]] = {}

    _parse_primary_roster_sheet(
        workbook.worksheets[0],
        available,
        available_by_location,
        availability_type_by_date,
        entries,
        ward_assessors_by_source_cell,
    )

    for date_text in list(available):
        available[date_text] = sorted(set(available[date_text]), key=normalize_name)
    location_availability = {
        date_text: {
            location: sorted(set(assessors), key=normalize_name)
            for location, assessors in locations.items()
        }
        for date_text, locations in available_by_location.items()
    }

    if not available:
        raise AppError("Unable to detect GLF availability in the roster workbook.")
    if not entries:
        raise AppError("Unable to detect assessee locations in the roster workbook.")
    all_assessors = sorted(
        {assessor for assessors in available.values() for assessor in assessors},
        key=normalize_name,
    )
    return RosterData(
        dict(available),
        dict(entries),
        location_availability,
        ward_assessors_by_source_cell,
        all_assessors,
        {date_text: dict(types) for date_text, types in availability_type_by_date.items()},
    )


def find_roster_entries(roster: RosterData, assessee_name: str) -> List[RosterEntry]:
    normalized = normalize_name(assessee_name)
    exact = roster.assessee_entries_by_name.get(normalized)
    if exact:
        return exact
    candidates: List[List[RosterEntry]] = []
    for roster_name, entries in roster.assessee_entries_by_name.items():
        if names_prefix_match(assessee_name, roster_name):
            candidates.append(entries)
    if len(candidates) == 1:
        return candidates[0]
    return []
