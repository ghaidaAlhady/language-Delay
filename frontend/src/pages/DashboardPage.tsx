import { Link } from "react-router-dom";

import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { ErrorState } from "@/components/ErrorState";
import { SkeletonCard } from "@/components/Skeleton";
import { useAuth } from "@/features/auth/useAuth";
import { useChildrenList } from "@/features/children/useChildren";
import { getArabicErrorMessage } from "@/utils/errorMessages";
import { formatChildAge } from "@/utils/formatArabic";

export function DashboardPage() {
  const { user } = useAuth();
  const childrenQuery = useChildrenList();

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-primary-900">مرحبًا، {user?.display_name} 👋</h1>
        <p className="mt-1 text-gray-600">
          ابدأ بتقييم مهارات طفلك اللغوية واحصل على خطة أنشطة مخصصة.
        </p>
      </div>

      <div className="flex flex-wrap gap-3">
        <Link to="/children/new">
          <Button>إضافة طفل</Button>
        </Link>
        <Link to="/children">
          <Button variant="outline">أطفالي</Button>
        </Link>
      </div>

      <section>
        <h2 className="mb-3 text-lg font-semibold text-primary-900">أطفالي</h2>
        {childrenQuery.isPending && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
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
          <Card className="text-center text-gray-600">
            لا يوجد أطفال بعد. أضف طفلك الأول للبدء بالتقييم.
          </Card>
        )}
        {childrenQuery.data && childrenQuery.data.length > 0 && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {childrenQuery.data.map((child) => (
              <Link key={child.id} to={`/children/${child.id}`}>
                <Card className="transition-shadow hover:shadow-md">
                  <p className="font-semibold text-primary-900">{child.name}</p>
                  <p className="text-sm text-gray-600">{formatChildAge(child.age_years)}</p>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
