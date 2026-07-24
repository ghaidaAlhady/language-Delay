import { defineConfig, devices } from "@playwright/test";

// The backend E2E instance (see ../backend/run_e2e_server.sh) listens on a
// different port than the developer's normal dev backend (8000), and reads
// its own disposable SQLite file — never `backend/language_delay.db`.
const E2E_BACKEND_URL = "http://127.0.0.1:8001";

export default defineConfig({
  testDir: "./e2e",
  // Ensures one shared parent account exists for the whole run (see
  // global-setup.ts) so specs that just need "a logged-in parent" log in
  // (10/minute limit) instead of registering fresh (5/minute limit). Safe
  // to do fresh every run since the E2E database itself starts empty.
  globalSetup: "./e2e/global-setup.ts",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 1,
  // `POST /auth/login` is rate-limited to 10/minute, keyed by remote address
  // (see backend/app/core/rate_limit.py) — every worker's traffic hits the
  // *same* 127.0.0.1 bucket. With more than one worker, enough specs' login
  // calls can land in the same 60s window to trip that real limit, and a
  // fixed-window reset can take close to a minute to clear — too long to
  // paper over with an in-test retry/backoff without either fighting the
  // per-test timeout or masking the actual timing. Serializing here removes
  // the concurrent bursts at the source instead.
  workers: 1,
  reporter: "html",
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "on-first-retry",
  },
  projects: [
    { name: "desktop-chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "tablet", use: { ...devices["iPad (gen 7)"] } },
    { name: "mobile-chromium", use: { ...devices["Pixel 7"] } },
  ],
  // Both servers are started fresh for every E2E run (reuseExistingServer:
  // false, unconditionally) rather than reusing whatever a developer might
  // already have running on these ports. That's a deliberate isolation
  // guarantee, not an oversight: reusing a stray dev-pointed frontend would
  // silently point it at the dev backend/database instead of the isolated
  // E2E one. The tradeoff is a few extra seconds of startup per run.
  webServer: [
    {
      command: "bash ../backend/run_e2e_server.sh",
      url: `${E2E_BACKEND_URL}/health`,
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: "npm run dev",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: false,
      timeout: 30_000,
      env: { VITE_API_BASE_URL: E2E_BACKEND_URL },
    },
  ],
});
