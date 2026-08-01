import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";

import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { TextField } from "@/components/TextField";
import { useAuth } from "@/features/auth/useAuth";
import { registerSchema, type RegisterFormValues } from "@/schemas/auth";
import { getArabicErrorMessage } from "@/utils/errorMessages";

export function RegisterPage() {
  const { register: registerParent } = useAuth();
  const navigate = useNavigate();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormValues>({ resolver: zodResolver(registerSchema) });

  async function onSubmit(values: RegisterFormValues): Promise<void> {
    setServerError(null);
    try {
      await registerParent(values.email, values.password, values.displayName);
      navigate("/dashboard", { replace: true });
    } catch (error) {
      setServerError(getArabicErrorMessage(error, "register"));
    }
  }

  return (
    <div className="mx-auto flex max-w-md flex-col gap-6 px-4 py-12">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-primary-900">إنشاء حساب</h1>
        <p className="mt-1 text-sm text-gray-600">سجّل للبدء</p>
      </div>

      <Card>
        <form className="flex flex-col gap-4" onSubmit={(e) => void handleSubmit(onSubmit)(e)} noValidate>
          <TextField
            label="الاسم"
            autoComplete="name"
            error={errors.displayName?.message}
            {...register("displayName")}
          />
          <TextField
            label="البريد الإلكتروني"
            type="email"
            autoComplete="email"
            error={errors.email?.message}
            {...register("email")}
          />
          <TextField
            label="كلمة المرور"
            type="password"
            autoComplete="new-password"
            hint="8 أحرف على الأقل"
            error={errors.password?.message}
            {...register("password")}
          />
          <TextField
            label="تأكيد كلمة المرور"
            type="password"
            autoComplete="new-password"
            error={errors.confirmPassword?.message}
            {...register("confirmPassword")}
          />

          {serverError && (
            <p role="alert" className="text-sm text-danger-600">
              {serverError}
            </p>
          )}

          <Button type="submit" isLoading={isSubmitting} className="mt-2">
            إنشاء حساب
          </Button>
        </form>
      </Card>

      <p className="text-center text-sm text-gray-600">
        لديك حساب بالفعل؟{" "}
        <Link to="/login" className="font-medium text-primary-600 hover:underline">
          تسجيل الدخول
        </Link>
      </p>
    </div>
  );
}
