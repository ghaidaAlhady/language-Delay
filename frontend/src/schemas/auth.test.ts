import { describe, expect, it } from "vitest";

import { loginSchema, registerSchema } from "@/schemas/auth";

describe("registerSchema", () => {
  const valid = {
    email: "parent@example.com",
    password: "supersecret1",
    confirmPassword: "supersecret1",
    displayName: "ولي الأمر",
  };

  it("accepts valid input", () => {
    expect(registerSchema.safeParse(valid).success).toBe(true);
  });

  it("rejects an invalid email", () => {
    const result = registerSchema.safeParse({ ...valid, email: "not-an-email" });
    expect(result.success).toBe(false);
  });

  it("rejects a password shorter than 8 characters", () => {
    const result = registerSchema.safeParse({ ...valid, password: "short1", confirmPassword: "short1" });
    expect(result.success).toBe(false);
  });

  it("rejects a password longer than 128 characters", () => {
    const long = "a".repeat(129);
    const result = registerSchema.safeParse({ ...valid, password: long, confirmPassword: long });
    expect(result.success).toBe(false);
  });

  it("rejects mismatched password confirmation", () => {
    const result = registerSchema.safeParse({ ...valid, confirmPassword: "different1" });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0]?.path).toEqual(["confirmPassword"]);
    }
  });

  it("rejects an empty display name", () => {
    const result = registerSchema.safeParse({ ...valid, displayName: "" });
    expect(result.success).toBe(false);
  });
});

describe("loginSchema", () => {
  it("accepts valid input", () => {
    expect(loginSchema.safeParse({ email: "a@b.com", password: "x" }).success).toBe(true);
  });

  it("rejects a missing password", () => {
    expect(loginSchema.safeParse({ email: "a@b.com", password: "" }).success).toBe(false);
  });

  it("rejects a malformed email", () => {
    expect(loginSchema.safeParse({ email: "not-an-email", password: "x" }).success).toBe(false);
  });
});
