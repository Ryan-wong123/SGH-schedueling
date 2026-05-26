from typing import Dict, List

from app.models.allocation import GlfAssessmentNeed, RosterData, RosterEntry
from app.services.allocation_service import allocate_assessments, summarize_records


def make_need(name: str, assessment: str, cell: str = "G2", existing=()) -> GlfAssessmentNeed:
    return GlfAssessmentNeed(
        assessee_name=name,
        assessment_type=assessment,
        original_glf_cell_reference=cell,
        needs_allocation=True,
        existing_assessors_for_row=tuple(existing),
    )


def roster_for(entries: List[RosterEntry], assessors_by_date: Dict[str, List[str]]) -> RosterData:
    by_name: Dict[str, List[RosterEntry]] = {}
    for entry in entries:
        by_name.setdefault(entry.assessee_name.casefold(), []).append(entry)
    return RosterData(assessors_by_date, by_name)


def test_location_compatibility_for_dispensing_and_minicex() -> None:
    roster = roster_for(
        [
            RosterEntry("Person", "15/04/26", "Ward"),
            RosterEntry("Other", "15/04/26", "OPS"),
        ],
        {"15/04/26": ["Assessor A"]},
    )
    records = allocate_assessments([make_need("Person", "Dispensing"), make_need("Other", "MiniCeX")], roster)
    assert records[0].status == "Unallocated"
    assert records[1].status == "Unallocated"


def test_round_robin_picks_fewest_loaded_assessor() -> None:
    roster = roster_for(
        [
            RosterEntry("P1", "15/04/26", "Ward"),
            RosterEntry("P2", "15/04/26", "Ward"),
            RosterEntry("P3", "15/04/26", "Ward"),
        ],
        {"15/04/26": ["Assessor A", "Assessor B"]},
    )
    records = allocate_assessments(
        [make_need("P1", "Rx Check", "G2"), make_need("P2", "Rx Check", "G3"), make_need("P3", "Rx Check", "G4")],
        roster,
    )
    assert [record.assigned_assessor for record in records] == ["Assessor A", "Assessor B", "Assessor A"]


def test_capacity_and_minicex_limits_are_enforced() -> None:
    entries = [RosterEntry(f"P{i}", "15/04/26", "Ward") for i in range(1, 7)]
    roster = roster_for(entries, {"15/04/26": ["Assessor A"]})
    records = allocate_assessments([make_need(f"P{i}", "MiniCeX", f"J{i}") for i in range(1, 7)], roster)
    assert sum(1 for record in records if record.status == "Allocated") == 2
    assert records[2].status == "Unallocated"

    records = allocate_assessments([make_need(f"P{i}", "Rx Check", f"G{i}") for i in range(1, 7)], roster)
    assert sum(1 for record in records if record.status == "Allocated") == 4
    assert records[4].status == "Unallocated"


def test_repeat_assessor_avoidance_for_med_recon() -> None:
    roster = roster_for(
        [RosterEntry("Person", "15/04/26", "Ward")],
        {"15/04/26": ["Genevieve Subur", "Melissa Wu"]},
    )
    records = allocate_assessments([make_need("Person", "Med Recon", "I2", existing=("Gen",))], roster)
    assert records[0].assigned_assessor == "Melissa Wu"


def test_ward_allocation_uses_ward_assessors_for_same_date() -> None:
    roster = RosterData(
        available_assessors_by_date={"15/04/26": ["OPS Assessor", "Ward Assessor"]},
        assessee_entries_by_name={
            "person": [RosterEntry("Person", "15/04/26", "Ward", ward_location="42A (1-8) RS-2")],
        },
        available_assessors_by_date_location={
            "15/04/26": {
                "OPS": ["OPS Assessor"],
                "Ward": ["Ward Assessor"],
            }
        },
    )
    records = allocate_assessments([make_need("Person", "MiniCeX")], roster)
    assert records[0].status == "Allocated"
    assert records[0].assigned_assessor == "Ward Assessor"
    assert records[0].assessee_location == "Ward (42A (1-8) RS-2)"


def test_ops_allocation_does_not_use_ward_assessors() -> None:
    roster = RosterData(
        available_assessors_by_date={"15/04/26": ["Ward Assessor"]},
        assessee_entries_by_name={
            "person": [RosterEntry("Person", "15/04/26", "OPS")],
        },
        available_assessors_by_date_location={
            "15/04/26": {
                "Ward": ["Ward Assessor"],
            }
        },
    )
    records = allocate_assessments([make_need("Person", "Dispensing")], roster)
    assert records[0].status == "Unallocated"


def test_summary_counts_skipped() -> None:
    skipped = GlfAssessmentNeed(
        assessee_name="Person",
        assessment_type="Rx Check",
        original_glf_cell_reference="G2",
        needs_allocation=False,
        status="Skipped - Already Passed",
    )
    roster = roster_for([], {})
    records = allocate_assessments([skipped], roster)
    assert summarize_records(records) == {"allocated": 0, "unallocated": 0, "skipped": 1}
