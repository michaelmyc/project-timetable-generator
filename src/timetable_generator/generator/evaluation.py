"""Evaluation report generator — Markdown report from judge scores."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from timetable_generator.generator.judge import JudgeScore


@dataclass
class CaseResult:
    """Result of running one evaluation case."""

    case_id: str
    description: str
    score: JudgeScore
    actual_hours: int
    target_hours: int


def generate_eval_report(
    results: list[CaseResult],
    output_path: Path,
    title: str = "Generator Core 评估报告",
) -> Path:
    """Generate a Markdown evaluation report.

    Args:
        results: List of case results with judge scores.
        output_path: Where to write the report.
        title: Report title.

    Returns:
        Path to the generated report.
    """
    total = len(results)
    hard_pass_count = sum(1 for r in results if r.score.hard_constraint_pass)
    avg_ratio_accuracy = sum(r.score.ratio_accuracy for r in results) / total if total else 0
    avg_retry = sum(r.score.retry_count for r in results) / total if total else 0
    avg_overall = sum(r.score.overall_score for r in results) / total if total else 0

    lines = [
        f"# {title}",
        "",
        "## 汇总",
        "",
        f"- 硬约束通过率：{hard_pass_count}/{total} ({hard_pass_count / total * 100:.0f}%)"
        if total
        else "- 硬约束通过率：N/A",
        f"- 平均比例达成度：{avg_ratio_accuracy:.1%}",
        f"- 平均重试次数：{avg_retry:.1f}",
        f"- 平均综合分：{avg_overall:.2f}",
        "",
        "## 各 Test Case 详情",
        "",
        "| Case | 描述 | 比例达成 | 硬约束 | 满载率 | 自然度 | 重试 | 综合分 |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for r in results:
        lines.append(
            f"| {r.case_id} | {r.description} | "
            f"{r.score.ratio_accuracy:.1%} | "
            f"{'✅' if r.score.hard_constraint_pass else '❌'} | "
            f"{r.score.full_load_ratio:.1%} | "
            f"{r.score.jitter_naturalness:.2f} | "
            f"{r.score.retry_count} | "
            f"{r.score.overall_score:.2f} |"
        )

    lines.extend(
        [
            "",
            "### 结论",
            f"- 硬约束：{'全通过 ✅' if hard_pass_count == total else '有违反 ❌'}",
            f"- 比例精度：平均 {avg_ratio_accuracy:.1%}",
            f"- 自然度：平均综合分 {avg_overall:.2f}",
            f"- 是否可进入下一步：{'是 ✅' if hard_pass_count == total and avg_ratio_accuracy > 0.95 else '否 ❌'}",
            "",
        ]
    )

    output_path = Path(output_path)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path
