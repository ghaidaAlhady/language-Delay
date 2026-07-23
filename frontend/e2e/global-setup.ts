import { chromium, type FullConfig } from "@playwright/test";

import { loginExistingParent, registerNewParent, SHARED_PARENT_EMAIL } from "./helpers";

/**
 * Ensures the one shared parent account (see helpers.ts::SHARED_PARENT_EMAIL)
 * exists, registering it if this is the first run against this dev
 * database. Re-running the suite against a dev database where the account
 * already exists is expected (registration then 409s) — that's fine, we
 * just confirm login still works.
 */
export default async function globalSetup(config: FullConfig): Promise<void> {
  const baseURL = config.projects[0]?.use.baseURL ?? "http://127.0.0.1:5173";
  const browser = await chromium.launch();
  const context = await browser.newContext({ baseURL });
  const page = await context.newPage();

  try {
    await registerNewParent(page, { email: SHARED_PARENT_EMAIL });
  } catch {
    await loginExistingParent(page, SHARED_PARENT_EMAIL);
  }

  await browser.close();
}
