/**
 * MSW request handlers used only by tests (Vitest component tests). These
 * intercept requests to the same paths the real API client calls, so tests
 * exercise the real request/response mapping code without a live backend.
 * Never imported by application/production code.
 */
import { HttpResponse, http } from "msw";

import {
  fixtureAssessmentCompleted,
  fixtureChild,
  fixtureQuestions,
  fixtureReport,
  fixtureUser,
  fixtureWeeklyFollowupContext,
  fixtureWeeklyPlan,
} from "@/tests/fixtures";

const BASE = import.meta.env.VITE_API_BASE_URL;

export const handlers = [
  http.post(`${BASE}/api/v1/auth/refresh`, () =>
    HttpResponse.json({ access_token: "test-access", refresh_token: "test-refresh" }),
  ),
  http.get(`${BASE}/api/v1/auth/me`, () => HttpResponse.json(fixtureUser)),
  http.post(`${BASE}/api/v1/auth/register`, () => HttpResponse.json(fixtureUser, { status: 201 })),
  http.post(`${BASE}/api/v1/auth/login`, () =>
    HttpResponse.json({ access_token: "test-access", refresh_token: "test-refresh" }),
  ),
  http.post(`${BASE}/api/v1/auth/logout`, () => new HttpResponse(null, { status: 204 })),

  http.get(`${BASE}/api/v1/children`, () => HttpResponse.json([fixtureChild])),
  http.get(`${BASE}/api/v1/children/:childId`, () => HttpResponse.json(fixtureChild)),
  http.post(`${BASE}/api/v1/children`, () => HttpResponse.json(fixtureChild, { status: 201 })),

  http.get(`${BASE}/api/v1/children/:childId/assessments`, () =>
    HttpResponse.json([fixtureAssessmentCompleted]),
  ),
  http.get(`${BASE}/api/v1/assessments/:assessmentId`, () => HttpResponse.json(fixtureAssessmentCompleted)),
  http.get(`${BASE}/api/v1/assessments/:assessmentId/questions`, () => HttpResponse.json(fixtureQuestions)),

  http.get(`${BASE}/api/v1/children/:childId/reports`, () => HttpResponse.json([fixtureReport])),
  http.get(`${BASE}/api/v1/reports/:reportId`, () => HttpResponse.json(fixtureReport)),

  http.get(`${BASE}/api/v1/children/:childId/weekly-plan`, () => HttpResponse.json(fixtureWeeklyPlan)),
  http.get(`${BASE}/api/v1/weekly-plans/:planId/followup-questions`, () =>
    HttpResponse.json(fixtureWeeklyFollowupContext),
  ),
];
