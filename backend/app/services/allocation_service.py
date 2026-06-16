from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import DefaultDict, Dict, List, Optional, Set, Tuple

from app.models.allocation import (
    AllocationRecord,
    AssessmentType,
    GlfAssessmentNeed,
    LocationType,
    REPEAT_AVOIDANCE_ASSESSMENTS,
    RosterData,
    RosterEntry,
)
from app.services.roster_parser import find_roster_entries
from app.utils.names import normalize_name


ASSESSMENT_LOCATIONS: Dict[AssessmentType, Set[LocationType]] = {
    "Rx Check": {"Ward", "OPS"},
    "Dispensing": {"OPS"},
    "Med Recon": {"Ward"},
    "MiniCeX": {"Ward"},
}


@dataclass
class AssessorLoad:
    total: int = 0
    minicex: int = 0


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


def _can_accept(load: AssessorLoad, assessment_type: AssessmentType) -> bool:
    if load.total >= 4:
        return False
    if assessment_type == "MiniCeX" and load.minicex >= 2:
        return False
    return True


def _select_assessor(
    assessors: List[str],
    date_text: str,
    assessment_type: AssessmentType,
    loads: Dict[str, Dict[str, AssessorLoad]],
    last_used: Dict[Tuple[str, str], int],
) -> Optional[str]:
    candidates = []
    for assessor in assessors:
        key = normalize_name(assessor)
        load = loads[date_text][key]
        if _can_accept(load, assessment_type):
            candidates.append(assessor)
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda name: (
            loads[date_text][normalize_name(name)].total,
            last_used.get((date_text, normalize_name(name)), -1),
            normalize_name(name),
        ),
    )[0]


def _available_assessors_for_entry(roster: RosterData, entry: RosterEntry) -> List[str]:
    if entry.location == "Ward" and entry.source_cell in roster.ward_assessors_by_source_cell:
        return roster.ward_assessors_by_source_cell[entry.source_cell]
    by_location = roster.available_assessors_by_date_location.get(entry.date, {})
    if by_location:
        return by_location.get(entry.location, [])
    assessors = by_location.get(entry.location)
    if assessors is not None:
        return assessors
    return roster.available_assessors_by_date.get(entry.date, [])


def _display_location(entry: Optional[RosterEntry]) -> str:
    if entry is None:
        return ""
    if entry.location == "Ward" and entry.ward_location:
        return f"Ward ({entry.ward_location})"
    if entry.location == "OPS" and entry.ops_shift:
        return f"OPS ({entry.ops_shift})"
    return entry.location


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


def allocate_assessments(needs: List[GlfAssessmentNeed], roster: RosterData) -> List[AllocationRecord]:
    records: List[AllocationRecord] = []
    loads: DefaultDict[str, DefaultDict[str, AssessorLoad]] = defaultdict(lambda: defaultdict(AssessorLoad))
    last_used: Dict[Tuple[str, str], int] = {}
    usage_counter = 0

    for need in needs:
        if not need.needs_allocation:
            records.append(_skipped_record(need))
            continue

        roster_entries = sorted(find_roster_entries(roster, need.assessee_name), key=lambda entry: entry.date)
        if not roster_entries:
            records.append(_unallocated_record(need, "Assessee not found in roster workbook."))
            continue

        compatible_entries = [
            entry for entry in roster_entries if is_location_compatible(need.assessment_type, entry.location)
        ]
        if not compatible_entries:
            records.append(
                _unallocated_record(
                    need,
                    f"No roster entry with {need.assessment_type}-compatible location.",
                    roster_entries[0],
                )
            )
            continue

        allocation: Optional[AllocationRecord] = None
        last_entry = compatible_entries[0]
        capacity_blocked = False

        for entry in compatible_entries:
            last_entry = entry
            available = _available_assessors_for_entry(roster, entry)
            if not available:
                continue

            candidates = [
                name
                for name in available
                if _can_accept(loads[entry.date][normalize_name(name)], need.assessment_type)
            ]
            if not candidates:
                capacity_blocked = True
                continue

            preferred = candidates
            repeated_fallback = False
            if need.assessment_type in REPEAT_AVOIDANCE_ASSESSMENTS:
                non_repeated = [
                    name
                    for name in candidates
                    if not _existing_matches_assessor(need.existing_assessors_for_row, name)
                ]
                if non_repeated:
                    preferred = non_repeated
                elif need.existing_assessors_for_row:
                    repeated_fallback = True

            assessor = _select_assessor(preferred, entry.date, need.assessment_type, loads, last_used)
            if assessor is None:
                continue

            assessor_key = normalize_name(assessor)
            load = loads[entry.date][assessor_key]
            load.total += 1
            if need.assessment_type == "MiniCeX":
                load.minicex += 1
            usage_counter += 1
            last_used[(entry.date, assessor_key)] = usage_counter
            reason = "Repeated assessor used because no alternative eligible assessor was available." if repeated_fallback else ""
            allocation = AllocationRecord(
                date=entry.date,
                assessee_name=need.assessee_name,
                glf_section_header=need.glf_section_header,
                assessment_type=need.assessment_type,
                assessee_location=_display_location(entry),
                assigned_assessor=assessor,
                assessor_glf_availability_date=entry.date,
                status="Allocated",
                reason=reason,
                original_glf_cell_reference=need.original_glf_cell_reference,
                existing_allocation_history=need.existing_allocation_history,
            )
            break

        if allocation:
            records.append(allocation)
        elif capacity_blocked:
            records.append(_unallocated_record(need, "All eligible assessors reached daily capacity.", last_entry))
        else:
            records.append(
                _unallocated_record(
                    need,
                    "No eligible assessor found for this assessee, assessment, date, and location.",
                    last_entry,
                )
            )

    return records
