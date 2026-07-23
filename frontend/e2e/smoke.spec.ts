import { expect, test } from "@playwright/test";

test("visual smoke: landing page renders RTL with no console errors", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (err) => errors.push(err.message));
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(msg.text());
  });

  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page.getByRole("heading", { name: "المرشد الذكي للتأخر اللغوي لدى الأطفال" })).toBeVisible();

  await page.screenshot({ path: "e2e/__screenshots__/landing.png", fullPage: true });

  expect(errors, `console/page errors: ${errors.join("\n")}`).toEqual([]);
});
