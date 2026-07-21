"""Arabic-aware PDF rendering for reports.

Arabic script must be reshaped (letters joined into their contextual forms)
and reordered for visual (right-to-left) display before drawing — plain
Unicode text draws each letter in its isolated form, left to right, which is
unreadable. ``arabic_reshaper`` + ``python-bidi`` handle that.

Rendering Arabic glyphs at all requires a Unicode TTF font; none is
committed to this repository (licensing — see CLAUDE_CODE_PROMPT.md). If the
deployment does not configure ``PDF_ARABIC_FONT_PATH``, this still produces a
real, valid PDF — it just falls back to a base font with no Arabic glyphs, so
Arabic text will not render legibly until a font is configured.
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
_FALLBACK_FONT_NAME = "Helvetica"
_PAGE_WIDTH, _PAGE_HEIGHT = A4
_MARGIN = 40


def _shape(text: str) -> str:
    return get_display(arabic_reshaper.reshape(text))


def _resolve_font(settings: Settings) -> str:
    font_path = settings.pdf_arabic_font_path
    if not font_path:
        logger.warning("pdf_arabic_font_not_configured")
        return _FALLBACK_FONT_NAME
    if not Path(font_path).is_file():
        logger.warning("pdf_arabic_font_missing", path=font_path)
        return _FALLBACK_FONT_NAME
    if _ARABIC_FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(_ARABIC_FONT_NAME, font_path))
    return _ARABIC_FONT_NAME


class _ReportPdfWriter:
    def __init__(self, canvas: Canvas, font_name: str) -> None:
        self._canvas = canvas
        self._font_name = font_name
        self._y = _PAGE_HEIGHT - _MARGIN

    def _ensure_space(self, needed: float) -> None:
        if self._y - needed < _MARGIN:
            self._canvas.showPage()
            self._canvas.setFont(self._font_name, 11)
            self._y = _PAGE_HEIGHT - _MARGIN

    def heading(self, text: str) -> None:
        self._ensure_space(28)
        self._canvas.setFont(self._font_name, 16)
        self._canvas.drawRightString(_PAGE_WIDTH - _MARGIN, self._y, _shape(text))
        self._y -= 28

    def subheading(self, text: str) -> None:
        self._ensure_space(20)
        self._canvas.setFont(self._font_name, 13)
        self._canvas.drawRightString(_PAGE_WIDTH - _MARGIN, self._y, _shape(text))
        self._y -= 20

    def paragraph(self, text: str) -> None:
        self._ensure_space(16)
        self._canvas.setFont(self._font_name, 11)
        self._canvas.drawRightString(_PAGE_WIDTH - _MARGIN, self._y, _shape(text))
        self._y -= 16

    def spacer(self, height: float = 10) -> None:
        self._y -= height


def render_report_pdf(report: ReportResponse, settings: Settings) -> bytes:
    buffer = BytesIO()
    canvas = Canvas(buffer, pagesize=A4)
    font_name = _resolve_font(settings)
    writer = _ReportPdfWriter(canvas, font_name)

    writer.heading(f"{report.report_number}")
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

    writer.subheading("موعد إعادة التقييم")
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
