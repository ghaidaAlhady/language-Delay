"""Portable Arabic-aware PDF rendering for assessment reports.

The packaged Tajawal TTF supplies Arabic Unicode glyphs and is embedded by
ReportLab. ``arabic_reshaper`` joins contextual letter forms and
``python-bidi`` converts logical RTL text to the visual order expected by
ReportLab's canvas API.
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path

import arabic_reshaper
from bidi.algorithm import get_display
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
_MARGIN = 40
_TEXT_WIDTH = _PAGE_WIDTH - (2 * _MARGIN)


def _shape(text: str) -> str:
    """Return connected Arabic glyph forms in visual RTL order."""
    return get_display(arabic_reshaper.reshape(text))


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


def _wrap_rtl_text(text: str, *, font_name: str, font_size: float) -> list[str]:
    """Wrap logical-order text before shaping each line for RTL drawing."""
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        shaped_candidate = _shape(candidate)
        if pdfmetrics.stringWidth(shaped_candidate, font_name, font_size) <= _TEXT_WIDTH:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


class _ReportPdfWriter:
    def __init__(self, canvas: Canvas, font_name: str) -> None:
        self._canvas = canvas
        self._font_name = font_name
        self._y = _PAGE_HEIGHT - _MARGIN

    def _ensure_space(self, needed: float) -> None:
        if self._y - needed < _MARGIN:
            self._canvas.showPage()
            self._y = _PAGE_HEIGHT - _MARGIN

    def _draw_rtl(self, text: str, *, font_size: float, leading: float) -> None:
        lines = _wrap_rtl_text(
            text, font_name=self._font_name, font_size=font_size
        )
        for line in lines:
            self._ensure_space(leading)
            self._canvas.setFont(self._font_name, font_size)
            self._canvas.drawRightString(
                _PAGE_WIDTH - _MARGIN, self._y, _shape(line)
            )
            self._y -= leading

    def heading(self, text: str) -> None:
        self._draw_rtl(text, font_size=16, leading=28)

    def subheading(self, text: str) -> None:
        self._draw_rtl(text, font_size=13, leading=20)

    def paragraph(self, text: str) -> None:
        self._draw_rtl(text, font_size=11, leading=16)

    def spacer(self, height: float = 10) -> None:
        self._y -= height


def render_report_pdf(report: ReportResponse, settings: Settings) -> bytes:
    buffer = BytesIO()
    canvas = Canvas(buffer, pagesize=A4)
    canvas.setTitle(report.report_number)
    font_name = _resolve_font(settings)
    writer = _ReportPdfWriter(canvas, font_name)

    writer.heading(report.report_number)
    writer.paragraph(f"{report.child_name} — {report.child_age_years}")
    writer.spacer()

    writer.subheading("الملخص")
    writer.paragraph(report.summary_text)
    writer.spacer()

    writer.subheading("النتائج حسب المجال")
    for domain_summary in report.domain_summaries:
        writer.paragraph(
            f"{domain_summary.domain.value}: {domain_summary.score_percent:.0f}% "
            f"— {domain_summary.severity.value}"
        )
    writer.spacer()

    if report.strengths:
        writer.subheading("نقاط القوة")
        writer.paragraph("، ".join(report.strengths))
        writer.spacer()

    if report.support_needs:
        writer.subheading("الجوانب التي تحتاج دعمًا")
        writer.paragraph("، ".join(report.support_needs))
        writer.spacer()

    writer.subheading("هدف الأسبوع")
    writer.paragraph(report.weekly_goal)
    writer.spacer()

    writer.subheading("المتابعة")
    writer.paragraph(report.next_reassessment)
    writer.spacer()

    if report.referral_recommended:
        writer.subheading("الإحالة إلى أخصائي")
        writer.paragraph("يُنصح بالتواصل مع أخصائي تخاطب لمتابعة النتائج.")
        writer.spacer()

    writer.subheading("إخلاء المسؤولية")
    writer.paragraph(report.disclaimer)

    canvas.save()
    return buffer.getvalue()
