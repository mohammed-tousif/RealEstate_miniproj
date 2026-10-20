import { expect, test } from "@playwright/test";

// The specification's final demonstration, steps 1–15, end to end on the real stack.
test("demo scenario: advisor → details → estimate → compare → assistant explains ranking and documents", async ({ page }) => {
  await page.goto("/"); // 1
  await expect(page.locator('a[href^="/properties/"]').first()).toBeVisible();

  await page.goto("/advisor"); // 2–6
  await page.getByRole("button", { name: /Try the demo/ }).click();
  const cards = page.getByRole("article", { name: /Recommendation \d+/ });
  await expect(cards.first()).toBeVisible();
  await cards.nth(0).getByRole("button", { name: "Add to compare" }).click();
  await cards.nth(1).getByRole("button", { name: "Add to compare" }).click();

  await cards.nth(0).locator('a[href^="/properties/"]').first().click(); // 7–10
  await expect(page.getByText(/not a valuation/i).first()).toBeVisible();

  await page.goto("/compare"); // 11
  await expect(page.getByRole("row").filter({ hasText: "Match for your preferences" })).toBeVisible();

  await page.getByRole("link", { name: "Ask the assistant why one ranks higher" }).click(); // 12–13
  const answer = page.getByTestId("assistant-message").first();
  await expect(answer.getByText(/Ranking using the buyer's saved Advisor preferences/)).toBeVisible();
  await expect(answer.getByText(/The first ranks higher by/)).toBeVisible();
  await answer.locator('a[href^="/properties/"]').first().click();

  await page.getByRole("link", { name: "Ask whether its documents are verified" }).click(); // 14–15
  const docs = page.getByTestId("assistant-message").first();
  await expect(docs.getByText(/Stored document status for/)).toBeVisible();
  await expect(docs.getByText(/independently|None of these documents is verified/).first()).toBeVisible();
});
