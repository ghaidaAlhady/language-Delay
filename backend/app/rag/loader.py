"""Reads and structurally validates the KB01-KB05 Excel workbooks and KB06 JSON.

This module only deals with raw sheet/column validation and produces plain
``dict`` rows per sheet. Typed, semantically validated records are built from
these rows in :mod:`app.rag.normalizer`.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from app.rag.exceptions import KnowledgeBaseLoadError

#: Required sheet -> required column set, per workbook filename.
REQUIRED_SHEET_COLUMNS: dict[str, dict[str, set[str]]] = {
    "KB01.xlsx": {
        **{
            f"Age {age}": {
                "ID",
                "المجال",
                "المهارة",
                "وصف المعيار",
                "Assessment Question",
                "Expected Development",
                "Importance",
                "Reference",
            }
            for age in range(2, 6)
        },
        "References": {"Reference", "وصف المعيار"},
    },
    "KB02.xlsx": {
        "Activities": {
            "معرف النشاط",
            "اسم النشاط",
            "العمر",
            "المجال",
            "المهارة المستهدفة",
            "الهدف",
            "وصف النشاط",
            "الأدوات",
            "المدة",
            "التكرار",
            "مستوى الصعوبة",
            "تعليمات لولي الأمر",
            "النتيجة المتوقعة",
            "المرجع",
        },
    },
    "KB03.xlsx": {
        "Decision_Rules": {
            "معرف القاعدة",
            "العمر",
            "المجال",
            "شرط التقييم",
            "مستوى الشدة",
            "توصية الذكاء الاصطناعي",
            "الأنشطة المقترحة",
            "المتابعة",
            "الإحالة إلى أخصائي",
            "المرجع",
        },
    },
    "KB04.xlsx": {
        "التقرير_الأولي": {"الحقل", "القيمة / الوصف"},
        "الخطة_الأسبوعية": {"اليوم", "رقم النشاط", "اسم النشاط", "المدة", "الهدف"},
        "تقرير_التقدم": {"الحقل", "القيمة / الوصف"},
        "تقرير_الإحالة": {"الحقل", "القيمة / الوصف"},
        "قوالب_النصوص": {"رقم القالب", "الحالة", "النص"},
    },
    "KB05.xlsx": {
        "Assessment_Questions": {
            "معرف السؤال",
            "العمر",
            "المجال",
            "السؤال",
            "نوع الإجابة",
            "الدرجة (نعم)",
            "الدرجة (لا)",
            "مرتبط بالمعيار",
            "مرتبط بقاعدة القرار",
            "ملاحظات",
        },
    },
}

REQUIRED_WORKBOOKS: tuple[str, ...] = tuple(REQUIRED_SHEET_COLUMNS)


def load_workbook_sheets(kb_dir: Path, filename: str) -> dict[str, list[dict[str, Any]]]:
    """Load and structurally validate every required sheet of one workbook."""
    path = kb_dir / filename
    if not path.exists():
        raise KnowledgeBaseLoadError(f"Knowledge-base file not found: {path}")

    try:
        sheets = pd.read_excel(path, sheet_name=None, engine="openpyxl")
    except Exception as exc:  # pragma: no cover - depends on corrupt input
        raise KnowledgeBaseLoadError(f"Failed to read {filename}: {exc}") from exc

    required = REQUIRED_SHEET_COLUMNS.get(filename)
    if required is None:
        raise KnowledgeBaseLoadError(f"No validation schema registered for {filename}")

    missing_sheets = set(required) - set(sheets)
    if missing_sheets:
        raise KnowledgeBaseLoadError(
            f"{filename} is missing required sheet(s): {sorted(missing_sheets)}"
        )

    normalized: dict[str, list[dict[str, Any]]] = {}
    for sheet_name, required_columns in required.items():
        frame = sheets[sheet_name]
        missing_columns = required_columns - set(frame.columns)
        if missing_columns:
            raise KnowledgeBaseLoadError(
                f"{filename}::{sheet_name} is missing required column(s): "
                f"{sorted(missing_columns)}"
            )
        records = frame.to_dict("records")
        normalized[sheet_name] = [
            {str(key): (None if pd.isna(value) else value) for key, value in record.items()}
            for record in records
        ]

    return normalized


def load_all_workbooks(kb_dir: Path) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Load and validate all five required workbooks from ``kb_dir``."""
    if not kb_dir.exists():
        raise KnowledgeBaseLoadError(f"Knowledge-base directory not found: {kb_dir}")

    return {filename: load_workbook_sheets(kb_dir, filename) for filename in REQUIRED_WORKBOOKS}


def load_kb06_records(kb_dir: Path) -> list[dict[str, Any]]:
    """Load the deterministic weekly-follow-up templates from ``KB06.json``."""
    path = kb_dir / "KB06.json"
    if not path.exists():
        raise KnowledgeBaseLoadError(f"Knowledge-base file not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise KnowledgeBaseLoadError(f"Failed to read KB06.json: {exc}") from exc
    if not isinstance(payload, list):
        raise KnowledgeBaseLoadError("KB06.json must contain a top-level list.")
    if not all(isinstance(item, dict) for item in payload):
        raise KnowledgeBaseLoadError("Every KB06.json entry must be an object.")
    return payload
