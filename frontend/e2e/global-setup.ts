import { request } from "@playwright/test";

import { SHARED_PARENT_EMAIL } from "./helpers";

const E2E_BACKEND_URL = "http://127.0.0.1:8001";

/**
 * Ensures the one shared parent account (see helpers.ts::SHARED_PARENT_EMAIL)
 * exists in the isolated E2E database. It uses a real HTTP request instead
 * of launching a browser only for setup: individual tests still exercise
 * login through the real UI, while setup avoids an unnecessary browser
 * process and a second rate-limited login.
 */
export default async function globalSetup(): Promise<void> {
  const api = await request.newContext({ baseURL: E2E_BACKEND_URL });
  try {
    const response = await api.post("/api/v1/auth/register", {
      data: {
        email: SHARED_PARENT_EMAIL,
        password: "supersecret1",
        display_name: "ولي أمر",
      },
    });
    if (response.status() !== 201 && response.status() !== 409) {
      throw new Error(
        `Unable to seed the shared E2E parent: ${response.status()} ${await response.text()}`,
      );
    }
  } finally {
    await api.dispose();
  }
}
