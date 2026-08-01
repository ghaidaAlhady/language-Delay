from __future__ import annotations

from reportlab.pdfbase.ttfonts import TTFont

from app.core.config import Settings
from app.rag.schemas import Domain, ReferralGuidance, Severity
from app.schemas.report import ReportDomainSummary, ReportResponse
from app.services.pdf_service import (
    _resolve_font_path,
    _sanitize_text,
    _shape,
    render_report_pdf,
)


def _sample_report() -> ReportResponse:
    return ReportResponse(
        id="r1",
        report_number="REP-0001",
        language="ar",
        child_id="c1",
        child_name="ليلى",
        child_age_years=3,
        assessment_id="a1",
        generated_at="2026-01-01T00:00:00Z",
        overall_severity=Severity.NORMAL,
        overall_referral=ReferralGuidance.NO,
        referral_recommended=False,
        confidence_score=0.8,
        domain_summaries=[
            ReportDomainSummary(
                domain=Domain.RECEPTIVE_LANGUAGE,
                score_percent=100.0,
                severity=Severity.NORMAL,
                recommendation="استمر في الأنشطة اليومية.",
            )
        ],
        strengths=["الاستجابة للاسم"],
        support_needs=[],
        summary_text="أظهر التقييم أداءً طبيعيًا.",
        weekly_goal="التركيز على مهارات اللغة الاستقبالية.",
        recommended_activity_ids=["A001", "A002"],
        next_reassessment="إعادة التقييم بعد أسبوع وتحديث الخطة",
        disclaimer="هذا التطبيق أداة داعمة ولا يغني عن التقييم المتخصص.",
    )


def test_packaged_font_covers_arabic_and_shaping_uses_connected_forms(
    settings: Settings,
) -> None:
    assert settings.pdf_arabic_font_path == ""
    font_path = _resolve_font_path(settings)
    font = TTFont("ArabicCoverageRegression", str(font_path))
    shaped = _shape("التقرير العربي")

    assert font_path.name == "Tajawal-Regular.ttf"
    assert ord("ا") in font.face.charWidths
    assert ord("ل") in font.face.charWidths
    assert shaped != "التقرير العربي"
    assert "\ufffd" not in shaped
    assert any(0xFB50 <= ord(character) <= 0xFEFF for character in shaped)


def test_render_real_arabic_report_embeds_font_and_preserves_structure(
    settings: Settings,
) -> None:
    pdf_bytes = render_report_pdf(_sample_report(), settings)

    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 500
    assert b"/FontFile2" in pdf_bytes
    assert b"REP-0001" in pdf_bytes
    assert b"\xef\xbf\xbd" not in pdf_bytes


def test_missing_configured_font_uses_packaged_arabic_font(
    settings: Settings,
) -> None:
    broken_settings = settings.model_copy(update={"pdf_arabic_font_path": "/no/such/font.ttf"})
    pdf_bytes = render_report_pdf(_sample_report(), broken_settings)
    assert pdf_bytes.startswith(b"%PDF-")


def test_pdf_text_sanitizer_removes_direction_controls_and_risky_symbols() -> None:
    cleaned = _sanitize_text("نتيجة‏ — دعم • مستمر")
    assert "\u200f" not in cleaned
    assert "—" not in cleaned
    assert "•" not in cleaned
    assert cleaned == "نتيجة - دعم - مستمر"
