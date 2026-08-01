import { Link } from "react-router-dom";

import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { SkeletonCard } from "@/components/Skeleton";
import { useChildrenList } from "@/features/children/useChildren";
import { getArabicErrorMessage } from "@/utils/errorMessages";
import { formatChildAge } from "@/utils/formatArabic";

export function ChildrenListPage() {
  const childrenQuery = useChildrenList();

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-primary-900">أطفالي</h1>
        <Link to="/children/new">
          <Button>إضافة طفل جديد</Button>
        </Link>
      </div>

      {childrenQuery.isPending && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      )}

      {childrenQuery.isError && (
        <ErrorState
          message={getArabicErrorMessage(childrenQuery.error)}
          onRetry={() => void childrenQuery.refetch()}
        />
      )}

      {childrenQuery.data && childrenQuery.data.length === 0 && (
        <EmptyState
          title="لا يوجد أطفال بعد"
          description="أضف طفلك الأول للبدء بالتقييم."
          action={
            <Link to="/children/new">
              <Button>إضافة طفل</Button>
            </Link>
          }
        />
      )}

      {childrenQuery.data && childrenQuery.data.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {childrenQuery.data.map((child) => (
            <Link key={child.id} to={`/children/${child.id}`}>
              <Card className="h-full transition-shadow hover:shadow-md">
                <p className="font-semibold text-primary-900">{child.name}</p>
                <p className="text-sm text-gray-600">{formatChildAge(child.age_years)}</p>
                {!child.is_assessment_age_eligible && (
                  <p className="mt-2 text-xs text-warning-600">خارج نطاق عمر التقييم حاليًا</p>
                )}
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
