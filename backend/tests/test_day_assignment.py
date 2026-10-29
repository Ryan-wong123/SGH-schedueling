from app.services.day_assignment import DayTask, solve_day


def full_day(_name: str) -> str:
    return "Full day GLF"


def test_uses_one_assessor_when_one_can_cover_the_whole_day() -> None:
    tasks = [
        DayTask(1, "Rx Check", ("Assessor A", "Assessor B")),
        DayTask(2, "Rx Check", ("Assessor B", "Assessor C")),
        DayTask(3, "Dispensing", ("Assessor B",)),
    ]
    assert solve_day(tasks, full_day) == {1: "Assessor B", 2: "Assessor B", 3: "Assessor B"}


def test_avoiding_a_repeat_assessor_comes_before_using_fewer_assessors() -> None:
    tasks = [
        DayTask(1, "Rx Check", ("Assessor A", "Assessor B"), repeat_assessors=frozenset({"Assessor A"})),
        DayTask(2, "Rx Check", ("Assessor A",)),
    ]
    assert solve_day(tasks, full_day) == {1: "Assessor B", 2: "Assessor A"}


def test_daily_limits_are_respected_and_the_rest_left_for_another_day() -> None:
    tasks = [DayTask(index, "MiniCeX", ("Assessor A",)) for index in range(1, 4)]
    assert solve_day(tasks, full_day) == {1: "Assessor A", 2: "Assessor A"}

    tasks = [DayTask(index, "Rx Check", ("Assessor A",)) for index in range(1, 6)]
    assert len(solve_day(tasks, full_day)) == 4


def test_half_day_assessor_gets_at_most_two_from_one_group() -> None:
    tasks = [
        DayTask(1, "Rx Check", ("Assessor A",)),
        DayTask(2, "Med Recon", ("Assessor A",)),
        DayTask(3, "MiniCeX", ("Assessor A",)),
    ]
    assert solve_day(tasks, lambda _name: "Half day GLF") == {2: "Assessor A", 3: "Assessor A"}


def test_full_day_assessor_prefers_one_group_when_assessor_count_is_equal() -> None:
    tasks = [
        DayTask(1, "Rx Check", ("Assessor A", "Assessor B")),
        DayTask(2, "Med Recon", ("Assessor A", "Assessor B")),
        DayTask(3, "Dispensing", ("Assessor A", "Assessor B")),
        DayTask(4, "MiniCeX", ("Assessor A", "Assessor B")),
        DayTask(5, "Rx Check", ("Assessor A", "Assessor B")),
    ]
    result = solve_day(tasks, full_day)
    assert len(result) == 5
    assert len(set(result.values())) == 2
    groups_by_assessor = {}
    for key, assessor in result.items():
        group = "ward" if tasks[key - 1].assessment_type in ("Med Recon", "MiniCeX") else "rx"
        groups_by_assessor.setdefault(assessor, set()).add(group)
    assert sum(1 for groups in groups_by_assessor.values() if len(groups) > 1) <= 1


def test_search_stops_at_node_limit_and_still_returns_an_arrangement() -> None:
    assessors = tuple(f"Assessor {letter}" for letter in "ABCDEFGHIJ")
    tasks = [DayTask(index, "Rx Check", assessors[index % 10:] + assessors[: index % 10]) for index in range(30)]
    result = solve_day(tasks, full_day, node_limit=500)
    assert len(result) == 30
