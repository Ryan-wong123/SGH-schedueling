from __future__ import annotations

from collections import defaultdict
from typing import DefaultDict, Dict, List, Tuple

from app.models.allocation import RosterData, RosterEntry
from app.utils.colours import classify_location_from_fill, is_green_fill, is_white_fill, is_yellow_fill
from app.utils.dates import format_date, parse_date
from app.utils.errors import AppError
from app.utils.names import names_prefix_match, normalize_name


SKIP_ROSTER_VALUES = {"", "glf", "x", "off", "al", "mc", "leave", "hl", "ops"}


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
    if text in SKIP_ROSTER_VALUES:
        return False
    return bool(text)


def _add_entry(entries: Dict[str, List[RosterEntry]], name: str, entry: RosterEntry) -> None:
    entries[normalize_name(name)].append(entry)


def _extract_ward_names(value: object) -> List[str]:
    if value is None:
        return []
    text = str(value).replace("\xa0", " ").strip()
    names: List[str] = []
    for part in text.replace("{", "\n").replace("}", "\n").splitlines():
        name = part.strip()
        if _is_schedule_value(name):
            names.append(name)
    return names


def _parse_primary_roster_sheet(ws, available: Dict[str, List[str]], entries: Dict[str, List[RosterEntry]]) -> None:
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
            if text.casefold() == "glf" and is_yellow_fill(cell):
                available[date_text].append(name)
                continue
            if not _is_schedule_value(value) or not is_green_fill(cell):
                continue
            _add_entry(
                entries,
                name,
                RosterEntry(
                    assessee_name=name,
                    date=date_text,
                    location="OPS",
                    source_cell=cell.coordinate,
                ),
            )


def _parse_ward_roster_sheet(ws, entries: Dict[str, List[RosterEntry]]) -> None:
    date_row, date_columns = _find_date_columns(ws)
    for row_index in range(date_row + 1, ws.max_row + 1):
        for col, date_text in date_columns.items():
            cell = ws.cell(row_index, col)
            if not is_white_fill(cell):
                continue
            if classify_location_from_fill(cell) != "Ward":
                continue
            for name in _extract_ward_names(cell.value):
                _add_entry(
                    entries,
                    name,
                    RosterEntry(
                        assessee_name=name,
                        date=date_text,
                        location="Ward",
                        source_cell=cell.coordinate,
                    ),
                )


def parse_roster(workbook) -> RosterData:
    if len(workbook.worksheets) < 2:
        raise AppError("The roster workbook must contain at least two worksheets.")
    available: DefaultDict[str, List[str]] = defaultdict(list)
    entries: DefaultDict[str, List[RosterEntry]] = defaultdict(list)

    _parse_primary_roster_sheet(workbook.worksheets[0], available, entries)
    _parse_ward_roster_sheet(workbook.worksheets[1], entries)

    for date_text in list(available):
        available[date_text] = sorted(set(available[date_text]), key=normalize_name)

    if not available:
        raise AppError("Unable to detect GLF availability in the roster workbook.")
    if not entries:
        raise AppError("Unable to detect assessee locations in the roster workbook.")
    return RosterData(dict(available), dict(entries))


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
