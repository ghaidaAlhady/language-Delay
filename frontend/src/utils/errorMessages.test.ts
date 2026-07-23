import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, NetworkError, TimeoutError } from "@/api/ApiError";
import { getArabicErrorMessage, getMissingQuestionCount } from "@/utils/errorMessages";

describe("getArabicErrorMessage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns an Arabic message in Arabic script for every status code the app must handle", () => {
    const statuses = [400, 401, 403, 404, 409, 422, 429, 500, 503];
    for (const status of statuses) {
      const message = getArabicErrorMessage(new ApiError(status, "code", "English message"));
      expect(message).toMatch(/[؀-ۿ]/);
      expect(message).not.toContain("English message");
    }
  });

  it("distinguishes login 401 (wrong credentials) from a generic 401 (expired session)", () => {
    const error = new ApiError(401, "unauthorized", "Invalid email or password.");
    expect(getArabicErrorMessage(error, "login")).toContain("البريد الإلكتروني أو كلمة المرور");
    expect(getArabicErrorMessage(error, "generic")).toContain("انتهت صلاحية الجلسة");
  });

  it("distinguishes register 409 (duplicate email) from a generic 409", () => {
    const error = new ApiError(409, "conflict", "exists");
    expect(getArabicErrorMessage(error, "register")).toContain("مستخدم بالفعل");
    expect(getArabicErrorMessage(error, "generic")).not.toContain("مستخدم بالفعل");
  });

  it("gives a specific message for an incomplete assessment (400 + assessment-complete context)", () => {
    const error = new ApiError(400, "bad_request", "incomplete");
    expect(getArabicErrorMessage(error, "assessment-complete")).toContain("جميع الأسئلة");
  });

  it("reports offline state distinctly from a generic network error", () => {
    vi.stubGlobal("navigator", { onLine: false });
    expect(getArabicErrorMessage(new NetworkError())).toContain("غير متصل بالإنترنت");
  });

  it("reports a generic connection failure when online but unreachable", () => {
    vi.stubGlobal("navigator", { onLine: true });
    expect(getArabicErrorMessage(new NetworkError())).toContain("تعذر الاتصال بالخادم");
  });

  it("reports a timeout distinctly", () => {
    expect(getArabicErrorMessage(new TimeoutError())).toContain("استغرق الطلب وقتًا أطول");
  });

  it("reports offline (not a generic timeout) when a timeout happens while offline", () => {
    // Some browsers/network stacks leave an offline fetch hanging instead of
    // rejecting immediately, so it surfaces as our client-side TimeoutError
    // rather than NetworkError — the offline message should still win.
    vi.stubGlobal("navigator", { onLine: false });
    expect(getArabicErrorMessage(new TimeoutError())).toContain("غير متصل بالإنترنت");
  });

  it("falls back to a generic message for an unrecognized error shape", () => {
    expect(getArabicErrorMessage(new Error("boom"))).toBe("حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.");
  });
});

describe("getMissingQuestionCount", () => {
  it("extracts the missing-question count from a 400 error's details", () => {
    const error = new ApiError(400, "bad_request", "incomplete", {
      missing_question_ids: ["Q001", "Q002"],
    });
    expect(getMissingQuestionCount(error)).toBe(2);
  });

  it("returns null when details has no missing_question_ids", () => {
    expect(getMissingQuestionCount(new ApiError(400, "bad_request", "x"))).toBeNull();
  });

  it("returns null for a non-ApiError", () => {
    expect(getMissingQuestionCount(new Error("boom"))).toBeNull();
  });
});
