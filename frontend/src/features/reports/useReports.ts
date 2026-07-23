import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as reportsApi from "@/api/reports";
import { queryKeys } from "@/api/queryKeys";

export function useReportsForChild(childId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.reports.forChild(childId ?? ""),
    queryFn: () => reportsApi.listReports(childId as string),
    enabled: Boolean(childId),
  });
}

export function useReport(reportId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.reports.detail(reportId ?? ""),
    queryFn: () => reportsApi.getReport(reportId as string),
    enabled: Boolean(reportId),
  });
}

export function useGenerateReport() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (assessmentId: string) => reportsApi.generateReport(assessmentId),
    onSuccess: (report) => {
      queryClient.setQueryData(queryKeys.reports.detail(report.id), report);
      void queryClient.invalidateQueries({ queryKey: queryKeys.reports.forChild(report.child_id) });
    },
  });
}

export function useDownloadReportPdf() {
  return useMutation({
    mutationFn: (reportId: string) => reportsApi.getReportPdf(reportId),
  });
}
