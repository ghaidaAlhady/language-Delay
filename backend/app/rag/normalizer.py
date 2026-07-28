"""Converts raw validated sheet rows into typed KB record models."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from app.rag.exceptions import KnowledgeBaseLoadError
from app.rag.parsing import parse_id_list, parse_score_threshold
from app.rag.schemas import (
    ActivityRecord,
    DecisionRuleRecord,
    Domain,
    Importance,
    MilestoneRecord,
    NarrativeTemplate,
    QuestionRecord,
    ReferenceRecord,
    ReferralGuidance,
    ReportStatus,
    ReportTemplateField,
    Severity,
    WeeklyFollowupQuestionRecord,
    WeeklyPlanTemplateDay,
)


def _build_records(
    model_cls: type,
    source_file: str,
    source_sheet: str,
    rows: list[dict[str, Any]],
    field_builder: Callable[[dict[str, Any]], dict[str, Any]],
) -> list[Any]:
    """Build one record per row, turning any failure — a missing/None cell,
    a bad type coercion, an unrecognized enum value, or a failed parse — into
    a single, clearly-scoped ``KnowledgeBaseLoadError``.
    """
    records = []
    for row in rows:
        try:
            fields = field_builder(row)
            records.append(model_cls(source_file=source_file, source_sheet=source_sheet, **fields))
        except (ValidationError, KeyError, TypeError, ValueError) as exc:
            raise KnowledgeBaseLoadError(
                f"{source_file}::{source_sheet} row failed validation: {exc}"
            ) from exc
    return records


def normalize_kb01(
    sheets: dict[str, list[dict[str, Any]]], source_file: str
) -> tuple[list[MilestoneRecord], list[ReferenceRecord]]:
    milestones: list[MilestoneRecord] = []
    for sheet_name, rows in sheets.items():
        if sheet_name == "References":
            continue
        age = int(sheet_name.removeprefix("Age ").strip())

        def build_fields(row: dict[str, Any], age: int = age) -> dict[str, Any]:
            return {
                "id": row["ID"],
                "age": age,
                "domain": row["المجال"],
                "skill": row["المهارة"],
                "criterion_description": row["وصف المعيار"],
                "assessment_question": row["Assessment Question"],
                "expected_development": row["Expected Development"],
                "importance": row["Importance"],
                "reference": row["Reference"],
            }

        milestones.extend(
            _build_records(MilestoneRecord, source_file, sheet_name, rows, build_fields)
        )

    references = _build_records(
        ReferenceRecord,
        source_file,
        "References",
        sheets.get("References", []),
        lambda row: {"code": row["Reference"], "description": row["وصف المعيار"]},
    )

    return milestones, references


def normalize_kb02(
    sheets: dict[str, list[dict[str, Any]]], source_file: str
) -> list[ActivityRecord]:
    sheet_name = "Activities"
    return _build_records(
        ActivityRecord,
        source_file,
        sheet_name,
        sheets[sheet_name],
        lambda row: {
            "id": row["معرف النشاط"],
            "name": row["اسم النشاط"],
            "age": int(row["العمر"]),
            "domain": row["المجال"],
            "target_skill": row["المهارة المستهدفة"],
            "goal": row["الهدف"],
            "description": row["وصف النشاط"],
            "tools": row["الأدوات"],
            "duration": row["المدة"],
            "frequency": row["التكرار"],
            "difficulty": row["مستوى الصعوبة"],
            "parent_instructions": row["تعليمات لولي الأمر"],
            "expected_outcome": row["النتيجة المتوقعة"],
            "reference": row["المرجع"],
        },
    )


def normalize_kb03(
    sheets: dict[str, list[dict[str, Any]]], source_file: str
) -> list[DecisionRuleRecord]:
    sheet_name = "Decision_Rules"

    def build_fields(row: dict[str, Any]) -> dict[str, Any]:
        condition = row["شرط التقييم"]
        return {
            "id": row["معرف القاعدة"],
            "age": int(row["العمر"]),
            "domain": row["المجال"],
            "score_condition": condition,
            "score_threshold": parse_score_threshold(condition),
            "severity": row["مستوى الشدة"],
            "ai_recommendation": row["توصية الذكاء الاصطناعي"],
            "suggested_activity_ids": parse_id_list(row["الأنشطة المقترحة"]),
            "follow_up": row["المتابعة"],
            "referral": row["الإحالة إلى أخصائي"],
            "reference": row["المرجع"],
        }

    return _build_records(
        DecisionRuleRecord, source_file, sheet_name, sheets[sheet_name], build_fields
    )


def normalize_kb04(
    sheets: dict[str, list[dict[str, Any]]], source_file: str
) -> dict[str, list[Any]]:
    def key_value_fields(sheet_name: str) -> list[ReportTemplateField]:
        return _build_records(
            ReportTemplateField,
            source_file,
            sheet_name,
            sheets[sheet_name],
            lambda row: {
                "field_name": row["الحقل"],
                "value_description": row["القيمة / الوصف"],
            },
        )

    weekly_plan_template = _build_records(
        WeeklyPlanTemplateDay,
        source_file,
        "الخطة_الأسبوعية",
        sheets["الخطة_الأسبوعية"],
        lambda row: {
            "day": row["اليوم"],
            "activity_slot": str(row["رقم النشاط"]),
            "activity_name": row["اسم النشاط"],
            "duration": row["المدة"],
            "goal": row["الهدف"],
        },
    )

    narrative_templates = _build_records(
        NarrativeTemplate,
        source_file,
        "قوالب_النصوص",
        sheets["قوالب_النصوص"],
        lambda row: {
            "template_id": row["رقم القالب"],
            "status": row["الحالة"],
            "text": row["النص"],
        },
    )

    return {
        "initial_report_fields": key_value_fields("التقرير_الأولي"),
        "progress_report_fields": key_value_fields("تقرير_التقدم"),
        "referral_report_fields": key_value_fields("تقرير_الإحالة"),
        "weekly_plan_template": weekly_plan_template,
        "narrative_templates": narrative_templates,
    }


def normalize_kb05(
    sheets: dict[str, list[dict[str, Any]]], source_file: str
) -> list[QuestionRecord]:
    sheet_name = "Assessment_Questions"
    return _build_records(
        QuestionRecord,
        source_file,
        sheet_name,
        sheets[sheet_name],
        lambda row: {
            "id": row["معرف السؤال"],
            "age": int(row["العمر"]),
            "domain": row["المجال"],
            "question": row["السؤال"],
            "answer_type": row["نوع الإجابة"],
            "yes_score": float(row["الدرجة (نعم)"]),
            "no_score": float(row["الدرجة (لا)"]),
            "linked_milestone_id": row["مرتبط بالمعيار"],
            "linked_rule_ids": parse_id_list(row["مرتبط بقاعدة القرار"]),
            "notes": row["ملاحظات"],
        },
    )


def normalize_kb06(
    rows: list[dict[str, Any]], source_file: str
) -> list[WeeklyFollowupQuestionRecord]:
    source_sheet = "WeeklyFollowupQuestions"
    return _build_records(
        WeeklyFollowupQuestionRecord,
        source_file,
        source_sheet,
        rows,
        lambda row: {
            "id": row["question_id"],
            "age_min": int(row["age_min"]),
            "age_max": int(row["age_max"]),
            "domain": row.get("domain"),
            "weekly_goal_key": row["weekly_goal_key"],
            "skill_key": row["skill_key"],
            "applicable_activity_ids": list(row["applicable_activity_ids"]),
            "question_text_ar": row["question_text_ar"],
            "response_type": row["response_type"],
            "required": bool(row["required"]),
            "progress_weight": float(row["progress_weight"]),
            "active": bool(row["active"]),
            "is_generic_fallback": bool(row.get("is_generic_fallback", False)),
            "reference_note": row["reference_note"],
        },
    )


__all__ = [
    "normalize_kb01",
    "normalize_kb02",
    "normalize_kb03",
    "normalize_kb04",
    "normalize_kb05",
    "normalize_kb06",
    "Domain",
    "Importance",
    "Severity",
    "ReferralGuidance",
    "ReportStatus",
]
