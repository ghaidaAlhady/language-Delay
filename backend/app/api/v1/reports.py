"""Report generation and retrieval endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.api.deps import (
    get_assessment_service,
    get_child_service,
    get_current_user,
    get_report_service,
    get_settings_dep,
)
from app.core.config import Settings
from app.core.rate_limit import limiter
from app.models.user import User
from app.schemas.report import ReportResponse
from app.services.assessment_service import AssessmentService
from app.services.child_service import ChildService
from app.services.pdf_service import render_report_pdf
from app.services.report_service import ReportService

router = APIRouter(tags=["reports"])


@router.post(
    "/assessments/{assessment_id}/report",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("20/minute")
async def generate_report(
    request: Request,
    assessment_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    assessment_service: Annotated[AssessmentService, Depends(get_assessment_service)],
    report_service: Annotated[ReportService, Depends(get_report_service)],
) -> ReportResponse:
    assessment = await assessment_service.get_owned(
        assessment_id=assessment_id, user_id=current_user.id
    )
    report = await report_service.generate(assessment)
    return await report_service.build_response(report)


@router.get("/children/{child_id}/reports", response_model=list[ReportResponse])
async def list_reports(
    child_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    child_service: Annotated[ChildService, Depends(get_child_service)],
    report_service: Annotated[ReportService, Depends(get_report_service)],
) -> list[ReportResponse]:
    child = await child_service.get_owned(child_id=child_id, user_id=current_user.id)
    reports = await report_service.list_for_child(child.id)
    return [await report_service.build_response(r) for r in reports]


@router.get("/reports/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    report_service: Annotated[ReportService, Depends(get_report_service)],
) -> ReportResponse:
    report = await report_service.get_owned(report_id=report_id, user_id=current_user.id)
    return await report_service.build_response(report)


@router.get("/reports/{report_id}/pdf")
async def download_report_pdf(
    report_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    report_service: Annotated[ReportService, Depends(get_report_service)],
    settings: Annotated[Settings, Depends(get_settings_dep)],
) -> Response:
    report = await report_service.get_owned(report_id=report_id, user_id=current_user.id)
    response = await report_service.build_response(report)
    pdf_bytes = render_report_pdf(response, settings)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{report.report_number}.pdf"'
        },
    )
