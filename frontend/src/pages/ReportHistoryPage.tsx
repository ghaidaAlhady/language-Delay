import { Link, useParams } from "react-router-dom";

import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { SeverityBadge } from "@/components/SeverityBadge";
import { SkeletonCard } from "@/components/Skeleton";
import { useReportsForChild } from "@/features/reports/useReports";
import { getArabicErrorMessage } from "@/utils/errorMessages";
import { formatArabicDate } from "@/utils/formatArabic";

export function ReportHistoryPage() {
  const { childId } = useParams<{ childId: string }>();
  const reportsQuery = useReportsForChild(childId);

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold text-primary-900">التقارير</h1>

      {reportsQuery.isPending && <SkeletonCard />}
      {reportsQuery.isError && (
        <ErrorState message={getArabicErrorMessage(reportsQuery.error)} onRetry={() => void reportsQuery.refetch()} />
      )}
      {reportsQuery.data && reportsQuery.data.length === 0 && (
        <EmptyState title="لا توجد تقارير بعد" description="أكمل تقييمًا أولاً لعرض التقارير." />
      )}

      <div className="flex flex-col gap-3">
        {reportsQuery.data?.map((report) => (
          <Link key={report.id} to={`/reports/${report.id}`}>
            <Card className="flex flex-wrap items-center justify-between gap-3 transition-shadow hover:shadow-md">
              <div>
                <p className="text-sm text-gray-500">{formatArabicDate(report.generated_at)}</p>
                <p className="font-medium text-primary-900">{report.report_number}</p>
              </div>
              <SeverityBadge severity={report.overall_severity} />
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
