from typing import Dict, List

from app.models.allocation import AllocationRecord, GlfAssessmentNeed, RosterData, RosterEntry
from app.services.allocation_service import allocate_assessments, sort_records_for_preview, summarize_records


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


def test_same_group_preference_fills_an_assessor_before_round_robin_moves_on() -> None:
    entries = [RosterEntry(f"P{i}", "15/04/26", "Ward") for i in range(1, 6)]
    roster = roster_for(entries, {"15/04/26": ["Assessor B", "Assessor A"]})
    records = allocate_assessments([make_need(f"P{i}", "Rx Check", f"G{i}") for i in range(1, 6)], roster)
    assert [record.assigned_assessor for record in records] == ["Assessor A"] * 4 + ["Assessor B"]


def test_half_day_assessors_keep_assessment_groups_apart() -> None:
    entries = [RosterEntry(f"P{i}", "15/04/26", "Ward") for i in range(1, 4)]
    roster = RosterData(
        {"15/04/26": ["Assessor A", "Assessor B"]},
        {entry.assessee_name.casefold(): [entry] for entry in entries},
        assessor_availability_type_by_date={"15/04/26": {"assessor a": "Half day GLF", "assessor b": "Half day GLF"}},
    )
    records = allocate_assessments(
        [make_need("P1", "Rx Check", "G2"), make_need("P2", "MiniCeX", "J3"), make_need("P3", "Med Recon", "I4")],
        roster,
    )
    assert [record.assigned_assessor for record in records] == ["Assessor A", "Assessor B", "Assessor B"]


def mixed_group_needs() -> List[GlfAssessmentNeed]:
    return [make_need("P1", "Dispensing", "H2"), make_need("P2", "Med Recon", "I3"), make_need("P3", "MiniCeX", "J4")]


def mixed_group_roster(availability_type: str) -> RosterData:
    entries = [RosterEntry("P1", "15/04/26", "OPS"), RosterEntry("P2", "15/04/26", "Ward"), RosterEntry("P3", "15/04/26", "Ward")]
    return RosterData(
        {"15/04/26": ["Assessor A"]},
        {entry.assessee_name.casefold(): [entry] for entry in entries},
        assessor_availability_type_by_date={"15/04/26": {"assessor a": availability_type}},
    )


def test_half_day_assessor_never_mixes_minicex_med_recon_with_rx_check_dispensing() -> None:
    records = allocate_assessments(mixed_group_needs(), mixed_group_roster("Half day GLF"))
    # Whole-day solving picks the group that allocates the most: Med Recon + MiniCeX (2) over Dispensing (1).
    assert [record.status for record in records] == ["Unallocated", "Allocated", "Allocated"]
    assert [record.assigned_assessor for record in records[1:]] == ["Assessor A", "Assessor A"]
    assert "different assessment group" in records[0].reason


def test_full_day_assessor_may_mix_assessment_groups() -> None:
    records = allocate_assessments(mixed_group_needs(), mixed_group_roster("Full day GLF"))
    assert [record.assigned_assessor for record in records] == ["Assessor A"] * 3


def test_half_day_glf_assessor_takes_at_most_two_assessments() -> None:
    entries = [RosterEntry(f"P{i}", "15/04/26", "Ward") for i in range(1, 5)]
    roster = RosterData(
        {"15/04/26": ["Assessor A"]},
        {entry.assessee_name.casefold(): [entry] for entry in entries},
        assessor_availability_type_by_date={"15/04/26": {"assessor a": "Half day GLF"}},
    )
    records = allocate_assessments([make_need(f"P{i}", "Rx Check", f"G{i}") for i in range(1, 5)], roster)
    assert [record.status for record in records] == ["Allocated", "Allocated", "Unallocated", "Unallocated"]


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


def test_current_run_assignments_can_repeat_for_same_assessee_when_capacity_allows() -> None:
    roster = roster_for(
        [RosterEntry("Person", "15/04/26", "OPS")],
        {"15/04/26": ["Assessor A"]},
    )
    records = allocate_assessments(
        [
            make_need("Person", "Rx Check", "G2"),
            make_need("Person", "Dispensing", "H2"),
        ],
        roster,
    )
    assert [record.assigned_assessor for record in records] == ["Assessor A", "Assessor A"]
    assert all(record.reason == "" for record in records)


def test_same_day_same_assessee_prefers_current_run_assessor_before_round_robin() -> None:
    roster = roster_for(
        [RosterEntry("Jerald Tan", "15/04/26", "OPS", ops_shift="ICT")],
        {"15/04/26": ["Genevieve Subur", "Khoo Sher Ri"]},
    )
    records = allocate_assessments(
        [
            make_need("Jerald Tan", "Rx Check", "G36"),
            make_need("Jerald Tan", "Dispensing", "H36"),
        ],
        roster,
    )
    assert [record.assigned_assessor for record in records] == ["Genevieve Subur", "Genevieve Subur"]


def test_same_day_same_assessee_reuse_still_requires_location_eligible_assessor() -> None:
    roster = RosterData(
        available_assessors_by_date={"15/04/26": ["OPS Assessor", "Ward Assessor"]},
        assessee_entries_by_name={
            "person": [
                RosterEntry("Person", "15/04/26", "OPS", ops_shift="C1"),
                RosterEntry("Person", "15/04/26", "Ward", ward_location="7A"),
            ],
        },
        available_assessors_by_date_location={
            "15/04/26": {
                "OPS": ["OPS Assessor"],
                "Ward": ["Ward Assessor"],
            }
        },
    )
    records = allocate_assessments(
        [
            make_need("Person", "Rx Check", "G2"),
            make_need("Person", "MiniCeX", "J2"),
        ],
        roster,
    )
    assert [record.assigned_assessor for record in records] == ["OPS Assessor", "Ward Assessor"]


def test_existing_assessor_avoidance_applies_to_rx_check_and_dispensing() -> None:
    roster = roster_for(
        [RosterEntry("Person", "15/04/26", "OPS")],
        {"15/04/26": ["Assessor A", "Assessor B"]},
    )
    records = allocate_assessments(
        [
            make_need("Person", "Rx Check", "G2", existing=("Assessor A",)),
            make_need("Person", "Dispensing", "H2", existing=("Assessor A",)),
        ],
        roster,
    )
    assert [record.assigned_assessor for record in records] == ["Assessor B", "Assessor B"]


def test_repeat_assessor_fallback_marks_reason_when_no_alternative_exists() -> None:
    roster = roster_for(
        [RosterEntry("Person", "15/04/26", "Ward")],
        {"15/04/26": ["Assessor A"]},
    )
    records = allocate_assessments(
        [
            make_need("Person", "Med Recon", "I2", existing=("Assessor A",)),
        ],
        roster,
    )
    assert records[0].assigned_assessor == "Assessor A"
    assert records[0].reason == "Repeated assessor used because no alternative eligible assessor was available."


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


def test_ward_allocation_uses_another_same_day_ward_assessor_not_the_assessee() -> None:
    roster = RosterData(
        available_assessors_by_date={"15/04/26": ["Amanda Chua", "Fiona Yeo"]},
        assessee_entries_by_name={
            "amanda chua": [RosterEntry("Amanda Chua", "15/04/26", "Ward", source_cell="B3", ward_location="42A")],
        },
        available_assessors_by_date_location={
            "15/04/26": {"Ward": ["Amanda Chua", "Fiona Yeo"]},
        },
        ward_assessors_by_source_cell={"B3": ["Amanda Chua"]},
    )

    record = allocate_assessments([make_need("Amanda Chua Jing Yi", "MiniCeX")], roster)[0]

    assert record.status == "Allocated"
    assert record.assigned_assessor == "Fiona Yeo"


def test_glf_assessees_are_never_selected_as_assessors_for_other_people() -> None:
    roster = RosterData(
        available_assessors_by_date={"15/04/26": ["Amanda Chua", "Fiona Yeo"]},
        assessee_entries_by_name={
            "target": [RosterEntry("Target", "15/04/26", "Ward", ward_location="42A")],
        },
        available_assessors_by_date_location={
            "15/04/26": {"Ward": ["Amanda Chua", "Fiona Yeo"]},
        },
    )
    glf_assessee = GlfAssessmentNeed(
        assessee_name="Amanda Chua Jing Yi",
        assessment_type="Rx Check",
        original_glf_cell_reference="G3",
        needs_allocation=False,
        status="Skipped - Already Allocated",
    )

    record = allocate_assessments([make_need("Target", "MiniCeX"), glf_assessee], roster)[0]

    assert record.status == "Allocated"
    assert record.assigned_assessor == "Fiona Yeo"


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


def test_ops_allocation_displays_shift_label() -> None:
    roster = roster_for(
        [RosterEntry("Person", "15/04/26", "OPS", ops_shift="C1")],
        {"15/04/26": ["Assessor A"]},
    )
    records = allocate_assessments([make_need("Person", "Dispensing")], roster)
    assert records[0].status == "Allocated"
    assert records[0].assessee_location == "OPS (C1)"


def test_allocation_records_assessor_glf_availability_type() -> None:
    roster = RosterData(
        available_assessors_by_date={"15/04/26": ["Assessor A"]},
        assessee_entries_by_name={
            "person": [RosterEntry("Person", "15/04/26", "OPS")],
        },
        assessor_availability_type_by_date={"15/04/26": {"assessor a": "Half day GLF"}},
    )
    records = allocate_assessments([make_need("Person", "Dispensing")], roster)
    assert records[0].status == "Allocated"
    assert records[0].assessor_glf_availability_type == "Half day GLF"


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


def test_reordered_glf_name_matches_roster_and_is_never_its_own_assessor() -> None:
    roster = roster_for(
        [RosterEntry("Kelly Ho", "15/04/26", "OPS"), RosterEntry("Charlotte Loh", "16/04/26", "Ward")],
        {"15/04/26": ["Kelly Ho", "Assessor A"], "16/04/26": ["Kelly Ho", "Assessor A"]},
    )
    records = allocate_assessments(
        [make_need("Ho Siang Kin Kelly", "Dispensing", "H2"), make_need("Loh Yen Shan Charlotte", "MiniCeX", "J3")],
        roster,
    )
    assert records[0].status == "Allocated"
    assert records[0].assigned_assessor == "Assessor A"
    assert records[1].status == "Allocated"
    assert records[1].assigned_assessor != "Kelly Ho"


def test_unallocated_reason_distinguishes_missing_from_roster_and_no_usable_days() -> None:
    roster = RosterData(
        {"15/04/26": ["Assessor A"]},
        {"kelly ho": [RosterEntry("Kelly Ho", "15/04/26", "OPS")]},
        roster_names=["Kelly Ho", "Joan Wee"],
    )
    records = allocate_assessments([make_need("Joan Wee (DI/IP)", "Rx Check"), make_need("Tan Elisa", "Rx Check")], roster)
    assert records[0].reason == "Assessee found in roster but has no Ward or OPS days."
    assert records[1].reason == "Assessee not found in roster workbook."


def test_roster_days_are_tried_in_real_date_order_not_text_order() -> None:
    roster = roster_for(
        [RosterEntry("P1", "04/05/26", "Ward"), RosterEntry("P1", "13/04/26", "Ward")],
        {"04/05/26": ["Assessor A"], "13/04/26": ["Assessor A"]},
    )
    records = allocate_assessments([make_need("P1", "MiniCeX", "J2")], roster)
    assert records[0].date == "13/04/26"


def test_preview_records_are_sorted_by_date_then_assessee() -> None:
    def record(date_text: str, name: str) -> AllocationRecord:
        return AllocationRecord(
            date=date_text,
            assessee_name=name,
            assessment_type="Rx Check",
            assessee_location="",
            assigned_assessor="",
            assessor_glf_availability_date="",
            status="Allocated" if date_text else "Unallocated",
            reason="",
            original_glf_cell_reference="",
            existing_allocation_history="",
        )

    records = [
        record("04/05/26", "Zoe"),
        record("", "Unmatched"),
        record("13/04/26", "Bob"),
        record("04/05/26", "Amy"),
        record("", "Another"),
    ]
    assert [(r.date, r.assessee_name) for r in sort_records_for_preview(records)] == [
        ("13/04/26", "Bob"),
        ("04/05/26", "Amy"),
        ("04/05/26", "Zoe"),
        ("", "Unmatched"),
        ("", "Another"),
    ]


def test_full_day_assessor_already_working_is_reused_before_a_new_assessor() -> None:
    entries = [RosterEntry(name, "13/04/26", "Ward") for name in ("P1", "P2", "P3")]
    roster = roster_for(entries, {"13/04/26": ["Assessor A", "Assessor B"]})
    records = allocate_assessments(
        [
            make_need("P1", "Rx Check", "G2"),
            make_need("P2", "Rx Check", "G3"),
            make_need("P3", "Med Recon", "I4"),
            make_need("P3", "MiniCeX", "J4"),
        ],
        roster,
    )
    assert [record.assigned_assessor for record in records] == ["Assessor A"] * 4


def test_new_assessor_for_a_day_is_the_one_who_can_cover_later_assessees() -> None:
    roster = roster_for(
        [RosterEntry("Jerald", "15/04/26", "OPS"), RosterEntry("Kristy", "15/04/26", "OPS")],
        {"15/04/26": ["Genevieve", "Khoo"]},
    )
    records = allocate_assessments(
        [
            make_need("Jerald", "Rx Check", "G36"),
            make_need("Jerald", "Dispensing", "H36"),
            make_need("Kristy", "Rx Check", "G47", existing=("Gen",)),
        ],
        roster,
    )
    assert [record.assigned_assessor for record in records] == ["Khoo", "Khoo", "Khoo"]


def test_assessment_that_does_not_fit_moves_to_the_assessees_next_roster_day() -> None:
    # P1 is first in the GLF sheet but is the only one with a later roster day,
    # so P1 is the assessment moved when 13/04 is full.
    entries = [RosterEntry("P1", "13/04/26", "Ward"), RosterEntry("P1", "14/04/26", "Ward")]
    entries += [RosterEntry(f"P{i}", "13/04/26", "Ward") for i in range(2, 6)]
    roster = roster_for(entries, {"13/04/26": ["Assessor A"], "14/04/26": ["Assessor B"]})
    records = allocate_assessments([make_need(f"P{i}", "Rx Check", f"G{i}") for i in range(1, 6)], roster)
    assert (records[0].date, records[0].assigned_assessor) == ("14/04/26", "Assessor B")
    assert [record.assigned_assessor for record in records[1:]] == ["Assessor A"] * 4
