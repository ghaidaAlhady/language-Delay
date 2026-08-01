import { type ReactNode, useCallback, useEffect, useState } from "react";

import { Button } from "@/components/Button";
import { Logo } from "@/components/Logo";
import { Spinner } from "@/components/Spinner";
import {
  BACKEND_HEALTH_URL,
  BACKEND_PROBE_TIMEOUT_MS,
  BACKEND_WAKE_TIMEOUT_MS,
} from "@/config/runtime";

type BackendState = "checking" | "ready" | "error";

async function sleep(milliseconds: number): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, milliseconds));
}

async function probeBackend(signal: AbortSignal): Promise<boolean> {
  const response = await fetch(BACKEND_HEALTH_URL, {
    method: "GET",
    cache: "no-store",
    headers: { Accept: "application/json" },
    signal,
  });
  if (!response.ok) return false;
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) return false;
  const body = (await response.json()) as { status?: string };
  return body.status === "ok";
}

async function waitForBackend(signal: AbortSignal): Promise<boolean> {
  const deadline = Date.now() + BACKEND_WAKE_TIMEOUT_MS;
  while (!signal.aborted && Date.now() < deadline) {
    const remaining = deadline - Date.now();
    const probeController = new AbortController();
    const forwardAbort = () => probeController.abort();
    signal.addEventListener("abort", forwardAbort, { once: true });
    const timeoutId = setTimeout(
      () => probeController.abort(),
      Math.min(BACKEND_PROBE_TIMEOUT_MS, remaining),
    );
    try {
      if (await probeBackend(probeController.signal)) return true;
    } catch {
      // A sleeping or temporarily unavailable free backend is expected here.
    } finally {
      clearTimeout(timeoutId);
      signal.removeEventListener("abort", forwardAbort);
    }
    if (!signal.aborted && Date.now() < deadline) await sleep(2_500);
  }
  return false;
}

export function BackendAvailabilityGate({ children }: { children: ReactNode }) {
  const [state, setState] = useState<BackendState>("checking");
  const [attempt, setAttempt] = useState(0);

  const retry = useCallback(() => {
    setState("checking");
    setAttempt((value) => value + 1);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void waitForBackend(controller.signal).then((ready) => {
      if (!controller.signal.aborted) setState(ready ? "ready" : "error");
    });
    return () => controller.abort();
  }, [attempt]);

  if (state === "ready") return children;

  return (
    <main
      className="flex min-h-screen items-center justify-center bg-primary-50 px-4 text-center"
      dir="rtl"
    >
      <section className="w-full max-w-md rounded-3xl bg-white p-8 shadow-sm">
        <div className="mb-5 flex justify-center">
          <Logo />
        </div>
        {state === "checking" ? (
          <div role="status" aria-live="polite">
            <div className="mb-4 flex justify-center">
              <Spinner />
            </div>
            <h1 className="text-xl font-bold text-primary-900">جارٍ تشغيل الخادم...</h1>
            <p className="mt-3 text-gray-600">
              النسخة التجريبية المجانية قد تحتاج إلى نحو دقيقة بعد فترة من عدم الاستخدام.
              اتركي الصفحة مفتوحة وسنكمل تلقائيًا عند جاهزية الخدمة.
            </p>
          </div>
        ) : (
          <div role="alert">
            <h1 className="text-xl font-bold text-primary-900">تعذر الاتصال بالخادم</h1>
            <p className="mt-3 text-gray-600">
              تحققي من اتصال الإنترنت، ثم أعيدي المحاولة. لم تُفقد أي بيانات محفوظة.
            </p>
            <Button className="mt-5" onClick={retry}>
              إعادة المحاولة
            </Button>
          </div>
        )}
      </section>
    </main>
  );
}
