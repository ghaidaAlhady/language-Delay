from __future__ import annotations

from app.core.config import Settings
from app.rag.schemas import Domain, ReferralGuidance, Severity
from app.schemas.report import ReportDomainSummary, ReportResponse
from app.services.pdf_service import render_report_pdf


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
        next_reassessment="إعادة التقييم بعد 3 أشهر",
        disclaimer="هذا التطبيق أداة داعمة ولا يغني عن التقييم المتخصص.",
    )


def test_render_report_pdf_without_configured_font_produces_valid_pdf(
    settings: Settings,
) -> None:
    assert settings.pdf_arabic_font_path == ""
    pdf_bytes = render_report_pdf(_sample_report(), settings)
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 500


def test_render_report_pdf_with_missing_configured_font_falls_back(
    settings: Settings,
) -> None:
    broken_settings = settings.model_copy(update={"pdf_arabic_font_path": "/no/such/font.ttf"})
    pdf_bytes = render_report_pdf(_sample_report(), broken_settings)
    assert pdf_bytes.startswith(b"%PDF-")
