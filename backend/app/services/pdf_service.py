"""Portable, Arabic-aware PDF rendering for assessment reports.

The packaged Tajawal font is embedded into every PDF. Arabic text is cleaned,
wrapped in logical order, reshaped, and converted to visual RTL order before
being drawn by ReportLab's canvas API. The layout deliberately avoids Unicode
symbols that some PDF viewers render as empty boxes.
"""
from __future__ import annotations

import unicodedata
from io import BytesIO
from pathlib import Path

import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

from app.core.config import Settings
from app.core.logging import get_logger
from app.schemas.report import ReportResponse

logger = get_logger(__name__)

_ARABIC_FONT_NAME = "ReportArabicFont"
_PACKAGED_ARABIC_FONT_PATH = (
    Path(__file__).resolve().parents[2] / "assets" / "fonts" / "Tajawal-Regular.ttf"
)
_PAGE_WIDTH, _PAGE_HEIGHT = A4
_MARGIN_X = 42
_MARGIN_TOP = 46
_MARGIN_BOTTOM = 44
_TEXT_WIDTH = _PAGE_WIDTH - (2 * _MARGIN_X)
_PRIMARY = colors.HexColor("#3F3D8F")
_PRIMARY_LIGHT = colors.HexColor("#F0EFFF")
_TEXT = colors.HexColor("#20233A")
_MUTED = colors.HexColor("#676B7A")
_BORDER = colors.HexColor("#DDDDF0")


def _sanitize_text(text: str) -> str:
    """Remove invisible/control characters and normalize risky punctuation."""
    replacements = {
        "—": "-",
        "–": "-",
        "•": "-",
        "●": "-",
        "▪": "-",
        "…": "...",
        "\u00a0": " ",
    }
    cleaned = "".join(replacements.get(char, char) for char in str(text))
    return "".join(
        char
        for char in cleaned
        if char in "\n\t" or unicodedata.category(char) not in {"Cc", "Cf", "Cs"}
    ).strip()


def _shape(text: str) -> str:
    """Return connected Arabic glyph forms in visual RTL order."""
    safe = _sanitize_text(text)
    return get_display(arabic_reshaper.reshape(safe))


def _resolve_font_path(settings: Settings) -> Path:
    if settings.pdf_arabic_font_path:
        configured = Path(settings.pdf_arabic_font_path)
        if configured.is_file():
            return configured
        logger.warning(
            "pdf_arabic_font_override_missing",
            configured_path=str(configured),
        )
    if not _PACKAGED_ARABIC_FONT_PATH.is_file():
        raise RuntimeError(
            "The packaged Arabic PDF font is missing; PDF generation cannot "
            "safely fall back to a font without Arabic glyph coverage."
        )
    return _PACKAGED_ARABIC_FONT_PATH


def _resolve_font(settings: Settings) -> str:
    font_path = _resolve_font_path(settings)
    if _ARABIC_FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(_ARABIC_FONT_NAME, str(font_path)))
    return _ARABIC_FONT_NAME


def _wrap_rtl_text(
    text: str,
    *,
    font_name: str,
    font_size: float,
    width: float = _TEXT_WIDTH,
) -> list[str]:
    """Wrap logical-order text before shaping each line for RTL drawing."""
    words = _sanitize_text(text).split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if pdfmetrics.stringWidth(_shape(candidate), font_name, font_size) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


class _ReportPdfWriter:
    def __init__(self, canvas: Canvas, font_name: str, report_number: str) -> None:
        self._canvas = canvas
        self._font_name = font_name
        self._report_number = report_number
        self._page_number = 0
        self._y = 0.0
        self._new_page()

    def _new_page(self) -> None:
        if self._page_number:
            self._canvas.showPage()
        self._page_number += 1
        self._canvas.setFillColor(_PRIMARY)
        self._canvas.rect(0, _PAGE_HEIGHT - 12, _PAGE_WIDTH, 12, fill=1, stroke=0)
        self._canvas.setFillColor(_MUTED)
        self._canvas.setFont(self._font_name, 8.5)
        self._canvas.drawString(_MARGIN_X, 24, self._report_number)
        self._canvas.drawRightString(
            _PAGE_WIDTH - _MARGIN_X,
            24,
            _shape(f"الصفحة {self._page_number}"),
        )
        self._canvas.setStrokeColor(_BORDER)
        self._canvas.line(_MARGIN_X, 34, _PAGE_WIDTH - _MARGIN_X, 34)
        self._y = _PAGE_HEIGHT - _MARGIN_TOP

    def _ensure_space(self, needed: float) -> None:
        if self._y - needed < _MARGIN_BOTTOM:
            self._new_page()

    def _draw_rtl(
        self,
        text: str,
        *,
        font_size: float,
        leading: float,
        color: colors.Color = _TEXT,
        indent: float = 0,
    ) -> None:
        width = _TEXT_WIDTH - indent
        lines = _wrap_rtl_text(
            text,
            font_name=self._font_name,
            font_size=font_size,
            width=width,
        )
        self._ensure_space(len(lines) * leading)
        self._canvas.setFillColor(color)
        self._canvas.setFont(self._font_name, font_size)
        right = _PAGE_WIDTH - _MARGIN_X - indent
        for line in lines:
            self._canvas.drawRightString(right, self._y, _shape(line))
            self._y -= leading

    def title(self, text: str) -> None:
        self._ensure_space(46)
        self._canvas.setFillColor(_PRIMARY)
        self._canvas.setFont(self._font_name, 18)
        self._canvas.drawRightString(_PAGE_WIDTH - _MARGIN_X, self._y, _shape(text))
        self._y -= 27
        self._canvas.setStrokeColor(_PRIMARY)
        self._canvas.setLineWidth(1.2)
        self._canvas.line(_MARGIN_X, self._y, _PAGE_WIDTH - _MARGIN_X, self._y)
        self._y -= 16

    def metadata(self, label: str, value: str) -> None:
        self._draw_rtl(f"{label}: {value}", font_size=10.5, leading=16, color=_MUTED)

    def section(self, text: str) -> None:
        self._ensure_space(34)
        self._y -= 6
        self._canvas.setFillColor(_PRIMARY_LIGHT)
        self._canvas.roundRect(
            _MARGIN_X,
            self._y - 20,
            _TEXT_WIDTH,
            26,
            6,
            fill=1,
            stroke=0,
        )
        self._canvas.setFillColor(_PRIMARY)
        self._canvas.setFont(self._font_name, 12.5)
        self._canvas.drawRightString(
            _PAGE_WIDTH - _MARGIN_X - 10,
            self._y - 13,
            _shape(text),
        )
        self._y -= 34

    def paragraph(self, text: str, *, color: colors.Color = _TEXT) -> None:
        self._draw_rtl(text, font_size=10.5, leading=17, color=color)
        self._y -= 4

    def bullet_list(self, items: list[str]) -> None:
        for item in items:
            self._draw_rtl(
                f"- {item}",
                font_size=10.5,
                leading=17,
                color=_TEXT,
                indent=8,
            )
        self._y -= 4

    def domain_row(self, title: str, result: str, recommendation: str) -> None:
        lines = _wrap_rtl_text(
            recommendation,
            font_name=self._font_name,
            font_size=9.5,
            width=_TEXT_WIDTH - 28,
        )
        height = 43 + max(0, len(lines) - 1) * 15
        self._ensure_space(height + 8)
        y_bottom = self._y - height
        self._canvas.setStrokeColor(_BORDER)
        self._canvas.setFillColor(colors.white)
        self._canvas.roundRect(
            _MARGIN_X,
            y_bottom,
            _TEXT_WIDTH,
            height,
            6,
            fill=1,
            stroke=1,
        )
        self._canvas.setFillColor(_PRIMARY)
        self._canvas.setFont(self._font_name, 11)
        self._canvas.drawRightString(
            _PAGE_WIDTH - _MARGIN_X - 10,
            self._y - 16,
            _shape(title),
        )
        self._canvas.setFillColor(_TEXT)
        self._canvas.setFont(self._font_name, 10)
        self._canvas.drawString(_MARGIN_X + 10, self._y - 16, _sanitize_text(result))
        current_y = self._y - 34
        self._canvas.setFillColor(_MUTED)
        self._canvas.setFont(self._font_name, 9.5)
        for line in lines:
            self._canvas.drawRightString(
                _PAGE_WIDTH - _MARGIN_X - 10,
                current_y,
                _shape(line),
            )
            current_y -= 15
        self._y = y_bottom - 8


def render_report_pdf(report: ReportResponse, settings: Settings) -> bytes:
    buffer = BytesIO()
    canvas = Canvas(buffer, pagesize=A4)
    canvas.setTitle(report.report_number)
    canvas.setAuthor("Smart Guide for Children’s Language Delay")
    font_name = _resolve_font(settings)
    writer = _ReportPdfWriter(canvas, font_name, report.report_number)

    writer.title("تقرير التقييم الأولي للتأخر اللغوي")
    writer.metadata("رقم التقرير", report.report_number)
    writer.metadata("اسم الطفل", report.child_name)
    writer.metadata("العمر", f"{report.child_age_years} سنوات")
    writer.metadata("التاريخ", report.generated_at.date().isoformat())
    writer.metadata("النتيجة العامة", report.overall_severity.value)

    writer.section("الملخص")
    writer.paragraph(report.summary_text)

    writer.section("النتائج حسب المجال")
    for domain_summary in report.domain_summaries:
        writer.domain_row(
            domain_summary.domain.value,
            f"{domain_summary.score_percent:.0f}% - {domain_summary.severity.value}",
            domain_summary.recommendation,
        )

    if report.strengths:
        writer.section("نقاط القوة")
        writer.bullet_list(report.strengths)

    if report.support_needs:
        writer.section("الجوانب التي تحتاج دعمًا")
        writer.bullet_list(report.support_needs)

    writer.section("هدف الأسبوع")
    writer.paragraph(report.weekly_goal)

    writer.section("المتابعة")
    writer.paragraph(report.next_reassessment)

    if report.referral_recommended:
        writer.section("الإحالة إلى أخصائي")
        writer.paragraph("يُنصح بالتواصل مع أخصائي تخاطب مؤهل لمتابعة النتائج.")

    writer.section("إخلاء المسؤولية")
    writer.paragraph(report.disclaimer, color=_MUTED)

    canvas.save()
    return buffer.getvalue()
