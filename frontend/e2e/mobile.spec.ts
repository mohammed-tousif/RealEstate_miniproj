import { expect, test } from "@playwright/test";

test("listings page fits a phone screen", async ({ page }) => {
  await page.goto("/properties");
  await expect(page.locator("article").first()).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(1);
  await page.getByRole("button", { name: /Filters/ }).click();
  await expect(page.getByRole("form", { name: "Filters" })).toBeVisible();
  await page.getByRole("button", { name: "Menu" }).click();
  await expect(page.getByRole("link", { name: "Methodology" }).last()).toBeVisible();
});
