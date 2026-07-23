import { apiRequestBlob, apiRequest } from "@/api/client";
import type { ReportResponse } from "@/types/api";

export function generateReport(assessmentId: string): Promise<ReportResponse> {
  return apiRequest<ReportResponse>(`/api/v1/assessments/${assessmentId}/report`, {
    method: "POST",
  });
}

export function listReports(childId: string): Promise<ReportResponse[]> {
  return apiRequest<ReportResponse[]>(`/api/v1/children/${childId}/reports`);
}

export function getReport(reportId: string): Promise<ReportResponse> {
  return apiRequest<ReportResponse>(`/api/v1/reports/${reportId}`);
}

export function getReportPdf(reportId: string): Promise<Blob> {
  return apiRequestBlob(`/api/v1/reports/${reportId}/pdf`);
}
