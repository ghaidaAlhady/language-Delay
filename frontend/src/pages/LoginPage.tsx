import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useLocation, useNavigate, type Location } from "react-router-dom";

import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { TextField } from "@/components/TextField";
import { useAuth } from "@/features/auth/useAuth";
import { loginSchema, type LoginFormValues } from "@/schemas/auth";
import { getArabicErrorMessage } from "@/utils/errorMessages";

interface LocationState {
  from?: Location;
}

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({ resolver: zodResolver(loginSchema) });

  async function onSubmit(values: LoginFormValues): Promise<void> {
    setServerError(null);
    try {
      await login(values.email, values.password);
      const state = location.state as LocationState | null;
      navigate(state?.from?.pathname ?? "/dashboard", { replace: true });
    } catch (error) {
      setServerError(getArabicErrorMessage(error, "login"));
    }
  }

  return (
    <div className="mx-auto flex max-w-md flex-col gap-6 px-4 py-12">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-primary-900">تسجيل الدخول</h1>
        <p className="mt-1 text-sm text-gray-600">قم بتسجيل الدخول إلى حسابك</p>
      </div>

      <Card>
        <form className="flex flex-col gap-4" onSubmit={(e) => void handleSubmit(onSubmit)(e)} noValidate>
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
            autoComplete="current-password"
            error={errors.password?.message}
            {...register("password")}
          />

          {serverError && (
            <p role="alert" className="text-sm text-danger-600">
              {serverError}
            </p>
          )}

          <Button type="submit" isLoading={isSubmitting} className="mt-2">
            تسجيل الدخول
          </Button>
        </form>
      </Card>

      <p className="text-center text-sm text-gray-600">
        ليس لديك حساب؟{" "}
        <Link to="/register" className="font-medium text-primary-600 hover:underline">
          إنشاء حساب
        </Link>
      </p>
    </div>
  );
}
