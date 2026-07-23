import { ApiError, NetworkError, TimeoutError } from "@/api/ApiError";

/**
 * Maps a caught error to a safe, supportive Arabic message for display.
 * Never surfaces the backend's raw (English) message or any stack trace —
 * every branch here is our own wording, chosen per HTTP status/code.
 *
 * `context` disambiguates statuses that mean different things in different
 * flows (e.g. a 401 on `/auth/login` is "wrong password", while a 401
 * anywhere else after a failed silent refresh is "your session expired").
 */
export type ErrorContext =
  | "login"
  | "register"
  | "generic"
  | "assessment-complete"
  | "assessment-age";

export function getArabicErrorMessage(error: unknown, context: ErrorContext = "generic"): string {
  // Checked first regardless of error type: a genuinely offline browser can
  // either fail a fetch immediately (-> NetworkError) or, depending on the
  // browser/network stack, leave it hanging until our own client-side
  // timeout fires (-> TimeoutError). Either way, "you're offline" is the
  // more accurate and actionable message than a generic timeout notice.
  if (
    (error instanceof NetworkError || error instanceof TimeoutError) &&
    typeof navigator !== "undefined" &&
    !navigator.onLine
  ) {
    return "يبدو أنك غير متصل بالإنترنت. يرجى التحقق من الاتصال والمحاولة مرة أخرى.";
  }

  if (error instanceof TimeoutError) {
    return "استغرق الطلب وقتًا أطول من المتوقع. يرجى المحاولة مرة أخرى.";
  }

  if (error instanceof NetworkError) {
    return "تعذر الاتصال بالخادم. يرجى المحاولة مرة أخرى.";
  }

  if (!(error instanceof ApiError)) {
    return "حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.";
  }

  switch (error.status) {
    case 400:
      if (context === "assessment-complete") {
        return "يجب الإجابة عن جميع الأسئلة قبل إنهاء التقييم.";
      }
      if (context === "assessment-age") {
        return "عمر الطفل الحالي خارج النطاق المدعوم للتقييم (من سنتين إلى خمس سنوات).";
      }
      return "تعذر إتمام الطلب بسبب بيانات غير صحيحة. يرجى مراجعة الحقول والمحاولة مرة أخرى.";
    case 401:
      if (context === "login") {
        return "البريد الإلكتروني أو كلمة المرور غير صحيحة.";
      }
      return "انتهت صلاحية الجلسة. يرجى تسجيل الدخول مرة أخرى.";
    case 403:
      return "لا تملك صلاحية الوصول إلى هذا المحتوى.";
    case 404:
      return "لم يتم العثور على العنصر المطلوب. ربما تم حذفه أو أنه غير متاح.";
    case 409:
      if (context === "register") {
        return "هذا البريد الإلكتروني مستخدم بالفعل. يمكنك تسجيل الدخول بدلاً من ذلك.";
      }
      return "تعذر إتمام الطلب بسبب تعارض في البيانات الحالية.";
    case 422:
      return "بعض البيانات المدخلة غير صالحة. يرجى مراجعة الحقول والمحاولة مرة أخرى.";
    case 429:
      return "عدد المحاولات كبير جدًا. يرجى الانتظار قليلًا ثم المحاولة مرة أخرى.";
    case 500:
      return "حدث خطأ في الخادم. يرجى المحاولة مرة أخرى لاحقًا.";
    case 503:
      return "الخدمة غير متاحة حاليًا. يرجى المحاولة مرة أخرى لاحقًا.";
    default:
      return "حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.";
  }
}

export function getMissingQuestionCount(error: unknown): number | null {
  if (!(error instanceof ApiError)) return null;
  const details = error.details as { missing_question_ids?: unknown } | undefined;
  if (details && Array.isArray(details.missing_question_ids)) {
    return details.missing_question_ids.length;
  }
  return null;
}
