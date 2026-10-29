from __future__ import annotations

import heapq
from collections import defaultdict
from datetime import date
from typing import DefaultDict, Dict, List, Optional, Set, Tuple

from app.models.allocation import (
    AllocationRecord,
    AssessmentType,
    GlfAvailabilityType,
    GlfAssessmentNeed,
    LocationType,
    REPEAT_AVOIDANCE_ASSESSMENTS,
    RosterData,
    RosterEntry,
)
from app.services.day_assignment import ASSESSMENT_GROUPS, DayTask, solve_day
from app.services.roster_parser import find_roster_entries, is_listed_in_roster
from app.utils.dates import parse_date
from app.utils.names import names_token_match, normalize_name


ASSESSMENT_LOCATIONS: Dict[AssessmentType, Set[LocationType]] = {
    "Rx Check": {"Ward", "OPS"},
    "Dispensing": {"OPS"},
    "Med Recon": {"Ward"},
    "MiniCeX": {"Ward"},
}


def _date_sort_key(date_text: str) -> Tuple[int, date, str]:
    # Roster dates are dd/mm/yy text, so sort by the real date, not the string.
    parsed = parse_date(date_text)
    return (0, parsed, date_text) if parsed else (1, date.max, date_text)


def sort_records_for_preview(records: List[AllocationRecord]) -> List[AllocationRecord]:
    """Order records by date, then assessee; records without a date go last in GLF order."""
    def key(record: AllocationRecord) -> Tuple[int, date, str]:
        parsed = parse_date(record.date)
        if parsed is None:
            return (1, date.max, "")
        return (0, parsed, normalize_name(record.assessee_name))

    return sorted(records, key=key)


def summarize_records(records: List[AllocationRecord]) -> Dict[str, int]:
    allocated = sum(1 for record in records if record.status == "Allocated")
    unallocated = sum(1 for record in records if record.status == "Unallocated")
    skipped = len(records) - allocated - unallocated
    return {"allocated": allocated, "unallocated": unallocated, "skipped": skipped}


def is_location_compatible(assessment_type: AssessmentType, location: LocationType) -> bool:
    return location in ASSESSMENT_LOCATIONS[assessment_type]


def _existing_matches_assessor(existing: Tuple[str, ...], assessor_name: str) -> bool:
    assessor = normalize_name(assessor_name)
    for existing_name in existing:
        item = normalize_name(existing_name)
        if not item:
            continue
        if item in assessor or assessor in item:
            return True
        if len(item) >= 3 and assessor.startswith(item):
            return True
    return False


def _is_same_person(first_name: str, second_name: str) -> bool:
    first = normalize_name(first_name)
    second = normalize_name(second_name)
    return bool(
        first
        and second
        and (first == second or names_token_match(first_name, second_name) or names_token_match(second_name, first_name))
    )


def _is_glf_assessee(candidate_name: str, glf_assessee_names: Tuple[str, ...]) -> bool:
    return any(_is_same_person(candidate_name, assessee_name) for assessee_name in glf_assessee_names)


def _available_assessors_for_entry(roster: RosterData, entry: RosterEntry) -> List[str]:
    by_location = roster.available_assessors_by_date_location.get(entry.date, {})
    if by_location:
        return by_location.get(entry.location, [])
    return roster.available_assessors_by_date.get(entry.date, [])


def _display_location(entry: Optional[RosterEntry]) -> str:
    if entry is None:
        return ""
    if entry.location == "Ward" and entry.ward_location:
        return f"Ward ({entry.ward_location})"
    if entry.location == "OPS" and entry.ops_shift:
        return f"OPS ({entry.ops_shift})"
    return entry.location


def _availability_type_for_assessor(roster: RosterData, date_text: str, assessor_name: str) -> GlfAvailabilityType:
    return roster.assessor_availability_type_by_date.get(date_text, {}).get(normalize_name(assessor_name), "")


def _skipped_record(need: GlfAssessmentNeed) -> AllocationRecord:
    return AllocationRecord(
        date="",
        assessee_name=need.assessee_name,
        glf_section_header=need.glf_section_header,
        assessment_type=need.assessment_type,
        assessee_location="",
        assigned_assessor="",
        assessor_glf_availability_date="",
        status=need.status or "Skipped - Not Applicable",
        reason=need.reason,
        original_glf_cell_reference=need.original_glf_cell_reference,
        existing_allocation_history=need.existing_allocation_history,
    )


def _unallocated_record(need: GlfAssessmentNeed, reason: str, entry: Optional[RosterEntry] = None) -> AllocationRecord:
    return AllocationRecord(
        date=entry.date if entry else "",
        assessee_name=need.assessee_name,
        glf_section_header=need.glf_section_header,
        assessment_type=need.assessment_type,
        assessee_location=_display_location(entry),
        assigned_assessor="",
        assessor_glf_availability_date="",
        status="Unallocated",
        reason=reason,
        original_glf_cell_reference=need.original_glf_cell_reference,
        existing_allocation_history=need.existing_allocation_history,
    )


CAPACITY_REASON = (
    "All eligible assessors reached daily capacity, or are half-day assessors on a different assessment group that day."
)
NO_ASSESSOR_REASON = "No eligible assessor found for this assessee, assessment, date, and location."
REPEAT_REASON = "Repeated assessor used because no alternative eligible assessor was available."


def _eligible_assessors(
    roster: RosterData,
    entry: RosterEntry,
    assessee_name: str,
    glf_assessee_names: Tuple[str, ...],
) -> Tuple[str, ...]:
    return tuple(
        name
        for name in _available_assessors_for_entry(roster, entry)
        if not _is_same_person(name, assessee_name) and not _is_glf_assessee(name, glf_assessee_names)
    )


def _repeat_assessors(need: GlfAssessmentNeed, eligible: Tuple[str, ...]) -> frozenset:
    if need.assessment_type not in REPEAT_AVOIDANCE_ASSESSMENTS:
        return frozenset()
    return frozenset(name for name in eligible if _existing_matches_assessor(need.existing_assessors_for_row, name))


def allocate_assessments(needs: List[GlfAssessmentNeed], roster: RosterData) -> List[AllocationRecord]:
    """Allocate assessors in two steps.

    1. Each assessment starts on its earliest roster day that has an eligible assessor.
    2. Each day is solved as a whole (`solve_day`), so all of that day's assessments are
       known when assessors are chosen and the fewest assessors are used. Assessments that
       do not fit move to the assessee's next roster day, which is solved later.
    """
    records: Dict[int, AllocationRecord] = {}
    glf_assessee_names = tuple(sorted({need.assessee_name for need in needs if normalize_name(need.assessee_name)}, key=normalize_name))
    # For each assessment: its remaining (entry, eligible assessors) options in date order.
    options_by_need: Dict[int, List[Tuple[RosterEntry, Tuple[str, ...]]]] = {}
    last_entry_by_need: Dict[int, RosterEntry] = {}
    pending_by_date: DefaultDict[str, List[int]] = defaultdict(list)
    date_queue: List[Tuple[Tuple[int, date, str], str]] = []

    def schedule(index: int) -> bool:
        options = options_by_need[index]
        if not options:
            return False
        date_text = options[0][0].date
        if not pending_by_date[date_text]:
            heapq.heappush(date_queue, (_date_sort_key(date_text), date_text))
        pending_by_date[date_text].append(index)
        return True

    for index, need in enumerate(needs):
        if not need.needs_allocation:
            records[index] = _skipped_record(need)
            continue

        roster_entries = sorted(find_roster_entries(roster, need.assessee_name), key=lambda entry: _date_sort_key(entry.date))
        if not roster_entries:
            reason = (
                "Assessee found in roster but has no Ward or OPS days."
                if is_listed_in_roster(roster, need.assessee_name)
                else "Assessee not found in roster workbook."
            )
            records[index] = _unallocated_record(need, reason)
            continue

        compatible_entries = [
            entry for entry in roster_entries if is_location_compatible(need.assessment_type, entry.location)
        ]
        if not compatible_entries:
            records[index] = _unallocated_record(
                need,
                f"No roster entry with {need.assessment_type}-compatible location.",
                roster_entries[0],
            )
            continue

        last_entry_by_need[index] = compatible_entries[-1]
        options_by_need[index] = [
            (entry, eligible)
            for entry in compatible_entries
            if (eligible := _eligible_assessors(roster, entry, need.assessee_name, glf_assessee_names))
        ]
        if not schedule(index):
            records[index] = _unallocated_record(need, NO_ASSESSOR_REASON, compatible_entries[-1])

    while date_queue:
        _, date_text = heapq.heappop(date_queue)
        indexes = pending_by_date.pop(date_text, [])
        if not indexes:
            continue
        entry_by_index = {index: options_by_need[index][0][0] for index in indexes}
        tasks = [
            DayTask(
                key=index,
                assessment_type=needs[index].assessment_type,
                eligible=options_by_need[index][0][1],
                repeat_assessors=_repeat_assessors(needs[index], options_by_need[index][0][1]),
                has_later_day=len(options_by_need[index]) > 1,
            )
            for index in indexes
        ]
        assignment = solve_day(
            tasks,
            lambda name: _availability_type_for_assessor(roster, date_text, name),
        )

        for task in tasks:
            index = task.key
            need = needs[index]
            entry = entry_by_index[index]
            assessor = assignment.get(index)
            if assessor is None:
                # No room today: try the assessee's next roster day.
                options_by_need[index].pop(0)
                if not schedule(index):
                    records[index] = _unallocated_record(need, CAPACITY_REASON, entry)
                continue
            records[index] = AllocationRecord(
                date=entry.date,
                assessee_name=need.assessee_name,
                glf_section_header=need.glf_section_header,
                assessment_type=need.assessment_type,
                assessee_location=_display_location(entry),
                assigned_assessor=assessor,
                assessor_glf_availability_date=entry.date,
                assessor_glf_availability_type=_availability_type_for_assessor(roster, entry.date, assessor),
                status="Allocated",
                reason=REPEAT_REASON if assessor in task.repeat_assessors else "",
                original_glf_cell_reference=need.original_glf_cell_reference,
                existing_allocation_history=need.existing_allocation_history,
            )

    return [records[index] for index in range(len(needs))]
