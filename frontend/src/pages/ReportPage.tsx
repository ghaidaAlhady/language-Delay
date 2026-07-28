import { useParams } from "react-router-dom";

import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { ErrorState } from "@/components/ErrorState";
import { SeverityBadge } from "@/components/SeverityBadge";
import { SkeletonCard } from "@/components/Skeleton";
import { useToast } from "@/components/ToastContext";
import { useDownloadReportPdf, useReport } from "@/features/reports/useReports";
import { getArabicErrorMessage } from "@/utils/errorMessages";
import { formatArabicDate, formatArabicPercent } from "@/utils/formatArabic";

export function ReportPage() {
  const { reportId } = useParams<{ reportId: string }>();
  const { showToast } = useToast();
  const reportQuery = useReport(reportId);
  const downloadPdf = useDownloadReportPdf();

  if (reportQuery.isPending) return <SkeletonCard />;
  if (reportQuery.isError) {
    return <ErrorState message={getArabicErrorMessage(reportQuery.error)} onRetry={() => void reportQuery.refetch()} />;
  }

  const report = reportQuery.data;
  if (!report) return null;

  function handleDownload(): void {
    downloadPdf.mutate(report!.id, {
      onSuccess: (blob) => {
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `${report!.report_number}.pdf`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
      },
      onError: (error) => showToast(getArabicErrorMessage(error), "error"),
    });
  }

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm text-gray-500">تقرير التقييم الأولي</p>
          <h1 className="text-xl font-bold text-primary-900">{report.report_number}</h1>
          <p className="text-sm text-gray-600">
            {report.child_name} • {formatArabicDate(report.generated_at)}
          </p>
        </div>
        <Button isLoading={downloadPdf.isPending} onClick={handleDownload}>
          تحميل PDF
        </Button>
      </div>

      <Card className="flex flex-wrap items-center justify-between gap-3">
        <SeverityBadge severity={report.overall_severity} />
        <p className="text-sm text-gray-600">
          درجة الثقة: {formatArabicPercent(report.confidence_score * 100)}
        </p>
      </Card>

      <Card>
        <h2 className="mb-2 font-semibold text-primary-900">ملخص التقييم</h2>
        <p className="leading-relaxed text-gray-700">{report.summary_text}</p>
      </Card>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Card>
          <h2 className="mb-2 font-semibold text-success-600">نقاط القوة</h2>
          <ul className="flex flex-col gap-1 text-sm text-gray-700">
            {report.strengths.length === 0 && <li className="text-gray-500">لا يوجد.</li>}
            {report.strengths.map((s) => (
              <li key={s}>• {s}</li>
            ))}
          </ul>
        </Card>
        <Card>
          <h2 className="mb-2 font-semibold text-warning-600">المهارات التي تحتاج دعمًا</h2>
          <ul className="flex flex-col gap-1 text-sm text-gray-700">
            {report.support_needs.length === 0 && <li className="text-gray-500">لا يوجد.</li>}
            {report.support_needs.map((s) => (
              <li key={s}>• {s}</li>
            ))}
          </ul>
        </Card>
      </div>

      <Card>
        <h2 className="mb-3 font-semibold text-primary-900">النتيجة حسب المجال</h2>
        <div className="flex flex-col gap-3">
          {report.domain_summaries.map((domain) => (
            <div key={domain.domain} className="flex flex-wrap items-center justify-between gap-2 border-b border-primary-50 pb-2 last:border-0">
              <p className="text-sm font-medium text-primary-900">{domain.domain}</p>
              <p className="text-sm text-gray-600">{formatArabicPercent(domain.score_percent)}</p>
              <SeverityBadge severity={domain.severity} />
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <h2 className="mb-1 font-semibold text-primary-900">الهدف الأسبوعي</h2>
        <p className="text-sm text-gray-700">{report.weekly_goal}</p>
        <p className="mt-3 text-sm text-gray-600">المتابعة: {report.next_reassessment}</p>
      </Card>

      <Card className="border-2 border-primary-200 bg-primary-50 text-sm text-primary-900">
        {report.disclaimer}
      </Card>
    </div>
  );
}
