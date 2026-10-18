from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
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
from app.services.roster_parser import find_roster_entries
from app.utils.dates import parse_date
from app.utils.names import names_prefix_match, normalize_name


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
    assessment_group: str = ""


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


def _assessment_group(assessment_type: AssessmentType) -> str:
    return "clinical" if assessment_type in {"MiniCeX", "Med Recon"} else "prescription"


def _can_accept(
    load: AssessorLoad,
    assessment_type: AssessmentType,
    availability_type: GlfAvailabilityType = "",
) -> bool:
    daily_limit = 2 if availability_type == "Half day GLF" else 4
    if load.assessment_group and load.assessment_group != _assessment_group(assessment_type):
        return False
    if load.total >= daily_limit:
        return False
    if assessment_type == "MiniCeX" and load.minicex >= 2:
        return False
    return True


def _is_same_person(first_name: str, second_name: str) -> bool:
    first = normalize_name(first_name)
    second = normalize_name(second_name)
    return bool(
        first
        and second
        and (first == second or names_prefix_match(first_name, second_name) or names_prefix_match(second_name, first_name))
    )


def _is_glf_assessee(candidate_name: str, glf_assessee_names: Tuple[str, ...]) -> bool:
    return any(_is_same_person(candidate_name, assessee_name) for assessee_name in glf_assessee_names)


def _select_assessor(
    assessors: List[str],
    date_text: str,
    assessment_type: AssessmentType,
    loads: Dict[str, Dict[str, AssessorLoad]],
    last_used: Dict[Tuple[str, str], int],
    roster: RosterData,
) -> Optional[str]:
    candidates = []
    for assessor in assessors:
        key = normalize_name(assessor)
        load = loads[date_text][key]
        if _can_accept(load, assessment_type, _availability_type_for_assessor(roster, date_text, assessor)):
            candidates.append(assessor)
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda name: (
            loads[date_text][normalize_name(name)].assessment_group != _assessment_group(assessment_type),
            loads[date_text][normalize_name(name)].total,
            last_used.get((date_text, normalize_name(name)), -1),
            normalize_name(name),
        ),
    )[0]


def _prefer_same_day_assessee_assessor(
    candidates: List[str],
    date_text: str,
    assessee_name: str,
    current_run_assignees: Dict[Tuple[str, str], List[str]],
) -> List[str]:
    same_assessee_key = (date_text, normalize_name(assessee_name))
    previous_assessors = current_run_assignees.get(same_assessee_key, [])
    if not previous_assessors:
        return candidates

    candidate_keys = {normalize_name(candidate) for candidate in candidates}
    reusable = [
        assessor
        for assessor in previous_assessors
        if normalize_name(assessor) in candidate_keys
    ]
    if reusable:
        return reusable
    return candidates


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


def allocate_assessments(needs: List[GlfAssessmentNeed], roster: RosterData) -> List[AllocationRecord]:
    records: List[AllocationRecord] = []
    loads: DefaultDict[str, DefaultDict[str, AssessorLoad]] = defaultdict(lambda: defaultdict(AssessorLoad))
    last_used: Dict[Tuple[str, str], int] = {}
    current_run_assignees: DefaultDict[Tuple[str, str], List[str]] = defaultdict(list)
    usage_counter = 0
    glf_assessee_names = tuple(sorted({need.assessee_name for need in needs if normalize_name(need.assessee_name)}, key=normalize_name))

    eligible_by_date_location: Dict[Tuple[str, str], List[str]] = {}

    for need in needs:
        if not need.needs_allocation:
            records.append(_skipped_record(need))
            continue

        roster_entries = sorted(find_roster_entries(roster, need.assessee_name), key=lambda entry: parse_date(entry.date))
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
            availability_key = (entry.date, entry.location)
            if availability_key not in eligible_by_date_location:
                eligible_by_date_location[availability_key] = [
                    name for name in _available_assessors_for_entry(roster, entry)
                    if not _is_glf_assessee(name, glf_assessee_names)
                ]
            available = eligible_by_date_location[availability_key]
            if not available:
                continue

            candidates = [
                name
                for name in available
                if not _is_same_person(name, need.assessee_name)
                and _can_accept(
                    loads[entry.date][normalize_name(name)], need.assessment_type,
                    _availability_type_for_assessor(roster, entry.date, name),
                )
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

            preferred = _prefer_same_day_assessee_assessor(
                preferred,
                entry.date,
                need.assessee_name,
                current_run_assignees,
            )
            assessor = _select_assessor(preferred, entry.date, need.assessment_type, loads, last_used, roster)
            if assessor is None:
                continue

            assessor_key = normalize_name(assessor)
            load = loads[entry.date][assessor_key]
            load.assessment_group = _assessment_group(need.assessment_type)
            load.total += 1
            if need.assessment_type == "MiniCeX":
                load.minicex += 1
            usage_counter += 1
            last_used[(entry.date, assessor_key)] = usage_counter
            same_assessee_key = (entry.date, normalize_name(need.assessee_name))
            if assessor not in current_run_assignees[same_assessee_key]:
                current_run_assignees[same_assessee_key].append(assessor)
            reason = "Repeated assessor used because no alternative eligible assessor was available." if repeated_fallback else ""
            allocation = AllocationRecord(
                date=entry.date,
                assessee_name=need.assessee_name,
                glf_section_header=need.glf_section_header,
                assessment_type=need.assessment_type,
                assessee_location=_display_location(entry),
                assigned_assessor=assessor,
                assessor_glf_availability_date=entry.date,
                assessor_glf_availability_type=_availability_type_for_assessor(roster, entry.date, assessor),
                status="Allocated",
                reason=reason,
                original_glf_cell_reference=need.original_glf_cell_reference,
                existing_allocation_history=need.existing_allocation_history,
            )
            break

        if allocation:
            records.append(allocation)
        elif capacity_blocked:
            records.append(_unallocated_record(need, "No eligible assessor remains after daily capacity and same-day assessment group checks.", last_entry))
        else:
            records.append(
                _unallocated_record(
                    need,
                    "No eligible assessor found for this assessee, assessment, date, and location.",
                    last_entry,
                )
            )

    return records
