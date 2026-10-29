"""Choose assessors for all of one day's assessments at once.

The allocation service first decides which date each assessment falls on, then
calls `solve_day` with every assessment for that date. Because the whole day is
known, the search can find the arrangement that uses the fewest assessors
instead of deciding one assessment at a time.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, FrozenSet, List, Optional, Set, Tuple

from app.models.allocation import AssessmentType, GlfAvailabilityType

# On a Half day GLF an assessor's day is either MiniCeX/Med Recon or Rx Check/Dispensing,
# never both. Full day GLF assessors may mix the groups.
ASSESSMENT_GROUPS: Dict[AssessmentType, str] = {
    "MiniCeX": "MiniCeX/Med Recon",
    "Med Recon": "MiniCeX/Med Recon",
    "Rx Check": "Rx Check/Dispensing",
    "Dispensing": "Rx Check/Dispensing",
}
FULL_DAY_LIMIT = 4
HALF_DAY_LIMIT = 2
MINICEX_LIMIT = 2
# Upper bound on search steps for one day. Real rosters finish far below this;
# if a very large day hits it, the best arrangement found so far is used.
DEFAULT_NODE_LIMIT = 200_000


@dataclass
class AssessorLoad:
    total: int = 0
    minicex: int = 0
    groups: Set[str] = field(default_factory=set)


@dataclass(frozen=True)
class DayTask:
    key: int
    assessment_type: AssessmentType
    eligible: Tuple[str, ...]
    # Eligible assessors who already assessed this assessee; used only when unavoidable.
    repeat_assessors: FrozenSet[str] = frozenset()
    # True when the assessee has another roster day this assessment could move to.
    has_later_day: bool = False


def can_accept(
    load: AssessorLoad,
    assessment_type: AssessmentType,
    availability_type: GlfAvailabilityType = "Full day GLF",
) -> bool:
    half_day = availability_type == "Half day GLF"
    if load.total >= (HALF_DAY_LIMIT if half_day else FULL_DAY_LIMIT):
        return False
    if assessment_type == "MiniCeX" and load.minicex >= MINICEX_LIMIT:
        return False
    if half_day and load.groups and ASSESSMENT_GROUPS[assessment_type] not in load.groups:
        return False
    return True


# Score is compared lexicographically and lower is better:
# (-assessments assigned, assessments left with no later day, repeated assessors used,
#  assessors used, assessors mixing groups).
Score = Tuple[int, int, int, int, int]


def solve_day(
    tasks: List[DayTask],
    availability_type: Callable[[str], GlfAvailabilityType],
    node_limit: int = DEFAULT_NODE_LIMIT,
) -> Dict[int, str]:
    """Return {task key: assessor} for the best arrangement; unassigned tasks are omitted."""
    if not tasks:
        return {}
    # Most constrained assessments first so dead ends are found early.
    ordered = sorted(tasks, key=lambda task: (len(task.eligible), task.key))
    count = len(ordered)
    eligible_from: List[Dict[str, Tuple[FrozenSet[int], FrozenSet[int]]]] = []
    for start in range(count):
        signature: Dict[str, Tuple[Set[int], Set[int]]] = {}
        for index in range(start, count):
            task = ordered[index]
            for name in task.eligible:
                usable, repeats = signature.setdefault(name, (set(), set()))
                usable.add(index)
                if name in task.repeat_assessors:
                    repeats.add(index)
        eligible_from.append({name: (frozenset(u), frozenset(r)) for name, (u, r) in signature.items()})

    loads: Dict[str, AssessorLoad] = {}
    choice: List[Optional[str]] = [None] * count
    best: Dict[str, object] = {"score": None, "choice": None}
    nodes = [0]

    def search(index: int, assigned: int, stranded: int, repeats: int, used: int, mixed: int) -> None:
        nodes[0] += 1
        if nodes[0] > node_limit and best["score"] is not None:
            return
        optimistic = (-(assigned + count - index), stranded, repeats, used, mixed)
        if best["score"] is not None and optimistic >= best["score"]:
            return
        if index == count:
            best["score"] = (-assigned, stranded, repeats, used, mixed)
            best["choice"] = list(choice)
            return

        task = ordered[index]
        group = ASSESSMENT_GROUPS[task.assessment_type]
        options = [
            name
            for name in task.eligible
            if can_accept(loads.setdefault(name, AssessorLoad()), task.assessment_type, availability_type(name))
        ]
        # Try assessors already working today first, then non-repeats, then by name.
        options.sort(key=lambda name: (loads[name].total == 0, name in task.repeat_assessors, name.casefold()))

        tried_new_signatures: Set[Tuple[GlfAvailabilityType, FrozenSet[int], FrozenSet[int]]] = set()
        for name in options:
            load = loads[name]
            is_new = load.total == 0
            if is_new:
                # Two unused assessors who can do exactly the same remaining work are
                # interchangeable, so only one of them needs to be tried.
                usable, repeat_set = eligible_from[index][name]
                signature = (availability_type(name), usable, repeat_set)
                if signature in tried_new_signatures:
                    continue
                tried_new_signatures.add(signature)
            adds_group = bool(load.groups) and group not in load.groups
            newly_mixed = adds_group and len(load.groups) == 1
            had_group = group in load.groups

            load.total += 1
            if task.assessment_type == "MiniCeX":
                load.minicex += 1
            load.groups.add(group)
            choice[index] = name
            search(
                index + 1,
                assigned + 1,
                stranded,
                repeats + (1 if name in task.repeat_assessors else 0),
                used + (1 if is_new else 0),
                mixed + (1 if newly_mixed else 0),
            )
            choice[index] = None
            if not had_group:
                load.groups.discard(group)
            if task.assessment_type == "MiniCeX":
                load.minicex -= 1
            load.total -= 1

        # Leaving this assessment for a later date is always an option; prefer leaving
        # ones that have a later roster day over ones that would go unallocated.
        search(index + 1, assigned, stranded + (0 if task.has_later_day else 1), repeats, used, mixed)

    search(0, 0, 0, 0, 0, 0)
    chosen = best["choice"] or [None] * count
    return {ordered[index].key: name for index, name in enumerate(chosen) if name is not None}
