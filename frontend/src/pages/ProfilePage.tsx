import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { useToast } from "@/components/ToastContext";
import { useAuth } from "@/features/auth/useAuth";
import { getArabicErrorMessage } from "@/utils/errorMessages";
import { formatArabicDate } from "@/utils/formatArabic";

export function ProfilePage() {
  const { user, logout, deleteAccount } = useAuth();
  const { showToast } = useToast();
  const navigate = useNavigate();
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  async function handleLogout(): Promise<void> {
    await logout();
    navigate("/login", { replace: true });
  }

  async function handleDeleteAccount(): Promise<void> {
    setIsDeleting(true);
    try {
      await deleteAccount();
      navigate("/", { replace: true });
    } catch (error) {
      showToast(getArabicErrorMessage(error), "error");
      setConfirmingDelete(false);
    } finally {
      setIsDeleting(false);
    }
  }

  if (!user) return null;

  return (
    <div className="mx-auto flex max-w-lg flex-col gap-6">
      <h1 className="text-2xl font-bold text-primary-900">الحساب</h1>

      <Card className="flex flex-col gap-3">
        <div>
          <p className="text-xs text-gray-500">الاسم</p>
          <p className="font-medium text-primary-900">{user.display_name}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">البريد الإلكتروني</p>
          <p className="font-medium text-primary-900">{user.email}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">تاريخ إنشاء الحساب</p>
          <p className="font-medium text-primary-900">{formatArabicDate(user.created_at)}</p>
        </div>
      </Card>

      <Card className="flex flex-col gap-3">
        <h2 className="font-semibold text-primary-900">اللغة</h2>
        <p className="text-sm text-gray-600">العربية (مفعّلة)</p>
      </Card>

      <div className="flex flex-col gap-3">
        <Button variant="outline" onClick={() => void handleLogout()}>
          تسجيل الخروج
        </Button>
        <Button variant="danger" onClick={() => setConfirmingDelete(true)}>
          حذف الحساب
        </Button>
      </div>

      <ConfirmDialog
        open={confirmingDelete}
        title="حذف الحساب"
        description="سيؤدي حذف حسابك إلى حذف جميع بيانات الأطفال والتقييمات والتقارير والخطط المرتبطة به نهائيًا. هذا الإجراء لا يمكن التراجع عنه."
        confirmLabel="حذف نهائي"
        isDangerous
        isConfirming={isDeleting}
        onConfirm={() => void handleDeleteAccount()}
        onCancel={() => setConfirmingDelete(false)}
      />
    </div>
  );
}
