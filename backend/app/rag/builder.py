"""Top-level factory that loads, validates, and normalizes KB01-KB05."""
from __future__ import annotations

from pathlib import Path

from app.rag.loader import load_all_workbooks
from app.rag.normalizer import (
    normalize_kb01,
    normalize_kb02,
    normalize_kb03,
    normalize_kb04,
    normalize_kb05,
)
from app.rag.schemas import KnowledgeBase


def build_knowledge_base(kb_dir: Path) -> KnowledgeBase:
    """Load every KB workbook from ``kb_dir`` into a validated ``KnowledgeBase``."""
    raw = load_all_workbooks(kb_dir)

    milestones, references = normalize_kb01(raw["KB01.xlsx"], "KB01.xlsx")
    activities = normalize_kb02(raw["KB02.xlsx"], "KB02.xlsx")
    decision_rules = normalize_kb03(raw["KB03.xlsx"], "KB03.xlsx")
    kb04 = normalize_kb04(raw["KB04.xlsx"], "KB04.xlsx")
    questions = normalize_kb05(raw["KB05.xlsx"], "KB05.xlsx")

    return KnowledgeBase(
        milestones=milestones,
        references=references,
        activities=activities,
        decision_rules=decision_rules,
        questions=questions,
        initial_report_fields=kb04["initial_report_fields"],
        progress_report_fields=kb04["progress_report_fields"],
        referral_report_fields=kb04["referral_report_fields"],
        weekly_plan_template=kb04["weekly_plan_template"],
        narrative_templates=kb04["narrative_templates"],
    )
