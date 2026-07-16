"""Test cases for generator evaluation."""

from dataclasses import dataclass
from datetime import date

from timetable_generator.models.project import Project
from timetable_generator.models.staff_state import GlobalSpan, StaffState


@dataclass
class EvalCase:
    """A single evaluation test case."""

    id: str
    description: str
    global_span: GlobalSpan
    staff: list[StaffState]
    projects: list[Project]
    holidays: set[date]
    expected_target_hours: dict[str, int]  # project_id → expected total hours


def _make_staff(span: GlobalSpan, ids: list[str]) -> list[StaffState]:
    return [StaffState.from_changes(pid, [], span) for pid in ids]


# Standard test cases for generator core evaluation
CORE_TEST_CASES: list[EvalCase] = [
    EvalCase(
        id="tc_single_full",
        description="单人全比例",
        global_span=GlobalSpan(date(2026, 3, 2), date(2026, 3, 13)),  # 2 weeks
        staff=_make_staff(GlobalSpan(date(2026, 3, 2), date(2026, 3, 13)), ["u1"]),
        projects=[Project(
            id="p1", name="A", start_date=date(2026, 3, 2), end_date=date(2026, 3, 13),
            target_ratio=1.0, required_job_types=["研发人员"], associated_person_ids=["u1"],
        )],
        holidays=set(),
        expected_target_hours={"p1": 80},  # 10 workdays × 8h
    ),
    EvalCase(
        id="tc_single_half",
        description="单人半比例",
        global_span=GlobalSpan(date(2026, 3, 2), date(2026, 3, 13)),
        staff=_make_staff(GlobalSpan(date(2026, 3, 2), date(2026, 3, 13)), ["u1"]),
        projects=[Project(
            id="p1", name="A", start_date=date(2026, 3, 2), end_date=date(2026, 3, 13),
            target_ratio=0.5, required_job_types=["研发人员"], associated_person_ids=["u1"],
        )],
        holidays=set(),
        expected_target_hours={"p1": 40},  # 80 × 0.5
    ),
    EvalCase(
        id="tc_single_small",
        description="小规模高精度",
        global_span=GlobalSpan(date(2026, 3, 2), date(2026, 3, 6)),  # 5 workdays
        staff=_make_staff(GlobalSpan(date(2026, 3, 2), date(2026, 3, 6)), ["u1"]),
        projects=[Project(
            id="p1", name="A", start_date=date(2026, 3, 2), end_date=date(2026, 3, 6),
            target_ratio=0.3, required_job_types=["研发人员"], associated_person_ids=["u1"],
        )],
        holidays=set(),
        expected_target_hours={"p1": 12},  # 40 × 0.3
    ),
    EvalCase(
        id="tc_single_sparse",
        description="低比例稀疏",
        global_span=GlobalSpan(date(2026, 3, 2), date(2026, 3, 27)),  # 4 weeks
        staff=_make_staff(GlobalSpan(date(2026, 3, 2), date(2026, 3, 27)), ["u1"]),
        projects=[Project(
            id="p1", name="A", start_date=date(2026, 3, 2), end_date=date(2026, 3, 27),
            target_ratio=0.1, required_job_types=["研发人员"], associated_person_ids=["u1"],
        )],
        holidays=set(),
        expected_target_hours={"p1": 16},  # 20 workdays × 8 × 0.1 = 16
    ),
    EvalCase(
        id="tc_single_jitter",
        description="自然抖动",
        global_span=GlobalSpan(date(2026, 3, 2), date(2026, 4, 10)),  # ~6 weeks
        staff=_make_staff(GlobalSpan(date(2026, 3, 2), date(2026, 4, 10)), ["u1"]),
        projects=[Project(
            id="p1", name="A", start_date=date(2026, 3, 2), end_date=date(2026, 4, 10),
            target_ratio=0.6, required_job_types=["研发人员"], associated_person_ids=["u1"],
        )],
        holidays=set(),
        expected_target_hours={"p1": 144},  # 30 workdays × 8 × 0.6 = 144
    ),
]
