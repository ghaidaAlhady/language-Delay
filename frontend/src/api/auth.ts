import { apiRequest } from "@/api/client";
import type { LoginRequest, RegisterRequest, TokenResponse, UserResponse } from "@/types/api";

export function register(payload: RegisterRequest): Promise<UserResponse> {
  return apiRequest<UserResponse>("/api/v1/auth/register", {
    method: "POST",
    body: payload,
    skipAuth: true,
  });
}

export function login(payload: LoginRequest): Promise<TokenResponse> {
  return apiRequest<TokenResponse>("/api/v1/auth/login", {
    method: "POST",
    body: payload,
    skipAuth: true,
  });
}

export function logout(refreshToken: string): Promise<void> {
  return apiRequest<void>("/api/v1/auth/logout", {
    method: "POST",
    body: { refresh_token: refreshToken },
  });
}

export function getMe(): Promise<UserResponse> {
  return apiRequest<UserResponse>("/api/v1/auth/me");
}

export function deleteAccount(): Promise<void> {
  return apiRequest<void>("/api/v1/auth/me", { method: "DELETE" });
}
