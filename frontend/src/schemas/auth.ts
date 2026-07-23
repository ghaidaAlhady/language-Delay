import { z } from "zod";

// Mirrors backend/app/schemas/auth.py exactly (EmailStr, password 8-128, display_name 1-255).
export const registerSchema = z
  .object({
    email: z.string().min(1, "البريد الإلكتروني مطلوب.").email("صيغة البريد الإلكتروني غير صحيحة."),
    password: z
      .string()
      .min(8, "كلمة المرور يجب أن تتكون من 8 أحرف على الأقل.")
      .max(128, "كلمة المرور طويلة جدًا."),
    confirmPassword: z.string().min(1, "تأكيد كلمة المرور مطلوب."),
    displayName: z
      .string()
      .min(1, "الاسم مطلوب.")
      .max(255, "الاسم طويل جدًا."),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "كلمتا المرور غير متطابقتين.",
    path: ["confirmPassword"],
  });

export type RegisterFormValues = z.infer<typeof registerSchema>;

export const loginSchema = z.object({
  email: z.string().min(1, "البريد الإلكتروني مطلوب.").email("صيغة البريد الإلكتروني غير صحيحة."),
  password: z.string().min(1, "كلمة المرور مطلوبة."),
});

export type LoginFormValues = z.infer<typeof loginSchema>;
