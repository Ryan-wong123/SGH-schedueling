from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Tuple

AssessmentType = Literal["Rx Check", "Dispensing", "Med Recon", "MiniCeX"]
LocationType = Literal["Ward", "OPS", "Unknown"]
GlfAvailabilityType = Literal["Full day GLF", "Half day GLF", ""]
AllocationStatus = Literal[
    "Allocated",
    "Unallocated",
    "Skipped - Already Passed",
    "Skipped - Already Allocated",
    "Skipped - Not Applicable",
    "Skipped - Unsupported Cell State",
]

ASSESSMENT_TYPES: Tuple[AssessmentType, ...] = ("Rx Check", "Dispensing", "Med Recon", "MiniCeX")
REPEAT_AVOIDANCE_ASSESSMENTS = set(ASSESSMENT_TYPES)


@dataclass(frozen=True)
class GlfAssessmentNeed:
    assessee_name: str
    assessment_type: AssessmentType
    original_glf_cell_reference: str
    needs_allocation: bool
    glf_section_header: str = ""
    status: Optional[AllocationStatus] = None
    reason: str = ""
    existing_allocation_history: str = ""
    existing_assessors_for_row: Tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RosterEntry:
    assessee_name: str
    date: str
    location: LocationType
    source_cell: str = ""
    ward_location: str = ""
    ops_shift: str = ""


@dataclass(frozen=True)
class RosterData:
    available_assessors_by_date: Dict[str, List[str]]
    assessee_entries_by_name: Dict[str, List[RosterEntry]]
    available_assessors_by_date_location: Dict[str, Dict[LocationType, List[str]]] = field(default_factory=dict)
    ward_assessors_by_source_cell: Dict[str, List[str]] = field(default_factory=dict)
    all_assessors: List[str] = field(default_factory=list)
    assessor_availability_type_by_date: Dict[str, Dict[str, GlfAvailabilityType]] = field(default_factory=dict)


@dataclass
class AllocationRecord:
    date: str
    assessee_name: str
    assessment_type: str
    assessee_location: str
    assigned_assessor: str
    assessor_glf_availability_date: str
    status: AllocationStatus
    reason: str
    original_glf_cell_reference: str
    existing_allocation_history: str
    assessor_glf_availability_type: GlfAvailabilityType = ""
    glf_section_header: str = ""

    def to_api_dict(self) -> Dict[str, str]:
        return {
            "date": self.date,
            "assesseeName": self.assessee_name,
            "glfSectionHeader": self.glf_section_header,
            "assessmentType": self.assessment_type,
            "assesseeLocation": self.assessee_location,
            "assignedAssessor": self.assigned_assessor,
            "assessorGlfAvailabilityDate": self.assessor_glf_availability_date,
            "assessorGlfAvailabilityType": self.assessor_glf_availability_type,
            "status": self.status,
            "reason": self.reason,
            "originalGlfCellReference": self.original_glf_cell_reference,
            "existingAllocationHistory": self.existing_allocation_history,
        }

    def row_values(self) -> List[str]:
        return [
            self.date,
            self.assessee_name,
            self.glf_section_header,
            self.assessment_type,
            self.assessee_location,
            self.assigned_assessor,
            self.assessor_glf_availability_date,
            self.assessor_glf_availability_type,
            self.status,
            self.reason,
            self.original_glf_cell_reference,
            self.existing_allocation_history,
        ]
