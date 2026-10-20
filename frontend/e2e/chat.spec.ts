import { expect, test } from "@playwright/test";

test("assistant answers a search in Basic search mode with listing cards", async ({ page }) => {
  await page.goto("/chat");
  await expect(page.getByRole("heading", { name: "Property assistant" })).toBeVisible();
  await page.getByRole("button", { name: "Residential plots in Dharwad under 25 lakh" }).click();
  const answer = page.getByTestId("assistant-message").first();
  await expect(answer).toBeVisible();
  await expect(answer.getByText(/Basic search mode|AI assistant/).first()).toBeVisible();
  await expect(answer.getByText(/listing\(s\) match residential plot in Dharwad/)).toBeVisible();
  await expect(answer.getByText(/synthetic/i).first()).toBeVisible();
  const link = answer.locator('a[href^="/properties/"]').first();
  await link.click();
  await expect(page).toHaveURL(/\/properties\/[0-9a-f-]{36}$/);
});

test("assistant explains a document term with the official portal link", async ({ page }) => {
  await page.goto("/chat");
  await page.getByLabel("Your question").fill("What is an encumbrance certificate?");
  await page.getByRole("button", { name: "Send" }).click();
  const answer = page.getByTestId("assistant-message").first();
  await expect(answer.getByText("Encumbrance Certificate (EC)")).toBeVisible();
  await expect(answer.getByRole("link", { name: "https://kaveri.karnataka.gov.in" })).toBeVisible();
});

test("listing details show risk flags and link to the assistant", async ({ page }) => {
  await page.goto("/properties?property_type=agricultural_land");
  await page.locator('a[href^="/properties/"]').first().click();
  await expect(page.getByTestId("risk-flags")).toBeVisible();
  await page.getByRole("link", { name: "Ask the assistant about this listing" }).click();
  const answer = page.getByTestId("assistant-message").first();
  await expect(answer.getByText("Things to check:")).toBeVisible();
});
