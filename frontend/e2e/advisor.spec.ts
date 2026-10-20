import { expect, test } from "@playwright/test";

test("advisor demo: ₹25 lakh residential plot in Hubballi–Dharwad for long-term investment", async ({ page }) => {
  await page.goto("/advisor");
  await expect(page.getByRole("heading", { name: "Property advisor" })).toBeVisible();
  await page.getByRole("button", { name: /Try the demo/ }).click();

  const first = page.getByRole("article", { name: "Recommendation 1", exact: true });
  await expect(first).toBeVisible();
  await expect(page.locator("#adv-max")).toHaveValue("25 lakh");
  await expect(page.getByText(/approved listings meet your strict requirements/)).toBeVisible();
  await expect(page.getByText(/Excluded: .*over your maximum budget/i)).toBeVisible();
  await expect(page.getByText(/not a probability of investment success/)).toBeVisible();
  await expect(first.getByText("Suitability score")).toBeVisible();
  await expect(first.getByRole("list", { name: "Score breakdown" }).getByText("Budget fit")).toBeVisible();

  // Every shown result respects the strict budget and type.
  const cards = page.getByRole("article", { name: /Recommendation \d+/ });
  expect(await cards.count()).toBeGreaterThan(0);
  for (const t of await cards.allInnerTexts()) expect(t).toContain("Residential plot");

  // Preferences persist after reload.
  await page.reload();
  await expect(page.locator("#adv-max")).toHaveValue("25 lakh");
  await expect(page.locator("#adv-objective")).toHaveValue("long_term_investment");
  await page.getByRole("button", { name: "Find matches" }).click();
  await expect(first).toBeVisible();

  // Compare the top two with match scores.
  await cards.nth(0).getByRole("button", { name: "Add to compare" }).click();
  await cards.nth(1).getByRole("button", { name: "Add to compare" }).click();
  await page.goto("/compare");
  const row = page.getByRole("row").filter({ hasText: "Match for your preferences" });
  await expect(row).toBeVisible();
  await expect(row.getByText("#1 of 2")).toBeVisible();
  await expect(row.getByText("#2 of 2")).toBeVisible();
  await expect(page.getByText(/Match scores use your last Advisor preferences/)).toBeVisible();
});

test("advisor validates input and explains an empty result", async ({ page }) => {
  await page.goto("/advisor");
  await page.locator("#adv-max").fill("lots");
  await page.getByRole("button", { name: "Find matches" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Budget not understood" })).toBeVisible();

  await page.locator("#adv-max").fill("1 lakh");
  await page.getByRole("button", { name: "Find matches" }).click();
  await expect(page.getByText("No listings meet all of your strict requirements")).toBeVisible();
});

test("property page shows KNN similar listings and the about page shows the scoring method", async ({ page }) => {
  await page.goto("/properties");
  await page.locator('a[href^="/properties/"]').first().click();
  await expect(page.getByRole("heading", { name: "Similar listings" })).toBeVisible();
  await expect(page.getByText(/^Similar: /).first()).toBeVisible();

  await page.goto("/about");
  await expect(page.getByText(/Default weights/)).toBeVisible();
  await expect(page.getByText(/Purpose base scores by property type/)).toBeVisible();
});
