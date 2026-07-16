"""Multi-project evaluation test cases."""

from dataclasses import dataclass
from datetime import date

from timetable_generator.models.project import Project
from timetable_generator.models.staff_state import GlobalSpan, StaffState

from tests.test_generator.cases import EvalCase


def _staff(span: GlobalSpan, ids: list[str]) -> list[StaffState]:
    return [StaffState.from_changes(pid, [], span) for pid in ids]


MULTI_TEST_CASES: list[EvalCase] = [
    EvalCase(
        id="tc_multi_2p_half",
        description="2项目各50%",
        global_span=GlobalSpan(date(2026, 3, 2), date(2026, 3, 13)),
        staff=_staff(GlobalSpan(date(2026, 3, 2), date(2026, 3, 13)), ["u1"]),
        projects=[
            Project("p1", "A", date(2026, 3, 2), date(2026, 3, 13), 0.5, ["研发人员"], ["u1"]),
            Project("p2", "B", date(2026, 3, 2), date(2026, 3, 13), 0.5, ["研发人员"], ["u1"]),
        ],
        holidays=set(),
        expected_target_hours={"p1": 40, "p2": 40},
    ),
    EvalCase(
        id="tc_multi_3p_split",
        description="3项目拆分",
        global_span=GlobalSpan(date(2026, 3, 2), date(2026, 3, 27)),
        staff=_staff(GlobalSpan(date(2026, 3, 2), date(2026, 3, 27)), ["u1"]),
        projects=[
            Project("p1", "A", date(2026, 3, 2), date(2026, 3, 27), 0.5, ["研发人员"], ["u1"]),
            Project("p2", "B", date(2026, 3, 2), date(2026, 3, 27), 0.3, ["研发人员"], ["u1"]),
            Project("p3", "C", date(2026, 3, 2), date(2026, 3, 27), 0.2, ["研发人员"], ["u1"]),
        ],
        holidays=set(),
        expected_target_hours={"p1": 80, "p2": 48, "p3": 32},
    ),
    EvalCase(
        id="tc_multi_2p_2person",
        description="2项目2人",
        global_span=GlobalSpan(date(2026, 3, 2), date(2026, 3, 13)),
        staff=_staff(GlobalSpan(date(2026, 3, 2), date(2026, 3, 13)), ["u1", "u2"]),
        projects=[
            Project("p1", "A", date(2026, 3, 2), date(2026, 3, 13), 0.4, ["研发人员"], ["u1", "u2"]),
            Project("p2", "B", date(2026, 3, 2), date(2026, 3, 13), 0.3, ["研发人员"], ["u1", "u2"]),
        ],
        holidays=set(),
        expected_target_hours={"p1": 64, "p2": 48},  # capacity=160, 0.4*160=64, 0.3*160=48
    ),
    EvalCase(
        id="tc_multi_continuity",
        description="持续性验证",
        global_span=GlobalSpan(date(2026, 3, 2), date(2026, 4, 10)),
        staff=_staff(GlobalSpan(date(2026, 3, 2), date(2026, 4, 10)), ["u1"]),
        projects=[
            Project("p1", "A", date(2026, 3, 2), date(2026, 4, 10), 0.6, ["研发人员"], ["u1"]),
            Project("p2", "B", date(2026, 3, 2), date(2026, 4, 10), 0.4, ["研发人员"], ["u1"]),
        ],
        holidays=set(),
        expected_target_hours={"p1": 144, "p2": 96},  # 30 workdays × 8 × 0.6/0.4
    ),
    EvalCase(
        id="tc_multi_precision",
        description="小规模精度",
        global_span=GlobalSpan(date(2026, 3, 2), date(2026, 3, 6)),
        staff=_staff(GlobalSpan(date(2026, 3, 2), date(2026, 3, 6)), ["u1"]),
        projects=[
            Project("p1", "A", date(2026, 3, 2), date(2026, 3, 6), 0.3, ["研发人员"], ["u1"]),
            Project("p2", "B", date(2026, 3, 2), date(2026, 3, 6), 0.5, ["研发人员"], ["u1"]),
        ],
        holidays=set(),
        expected_target_hours={"p1": 12, "p2": 20},  # 40h capacity, 0.3*40=12, 0.5*40=20
    ),
]
