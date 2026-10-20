import { expect, test } from "@playwright/test";

test("price estimate from entered details, with quoted-price comparison and comparables", async ({ page }) => {
  await page.goto("/estimate");
  await expect(page.getByRole("heading", { name: "Indicative price estimate" })).toBeVisible();
  await page.getByRole("button", { name: "Estimate price" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Choose a locality." })).toBeVisible();

  await page.locator("#locality").selectOption({ label: "Saptapur (Dharwad)" });
  await page.locator("#area").fill("1200");
  await page.locator("#conversion").selectOption("converted_claimed");
  await page.locator("#layout").selectOption("approved_layout_claimed");
  await page.locator("#road").selectOption("paved_internal");
  await page.locator("#quoted").fill("60 lakh");
  await page.getByRole("button", { name: "Estimate price" }).click();

  const result = page.getByTestId("estimate-result");
  await expect(result).toBeVisible();
  await expect(result.getByText(/Indicative range ₹/)).toBeVisible();
  await expect(result.getByText(/Quoted ₹60 lakh is .* above the estimate/)).toBeVisible();
  await expect(result.getByText("Trained on synthetic data", { exact: true })).toBeVisible();
  await expect(result.getByText("Comparable listings (asking prices)")).toBeVisible();
  await expect(result.getByText(/not a valuation/i).first()).toBeVisible();
});

test("farmland in acres switches unit and gives an estimate", async ({ page }) => {
  await page.goto("/estimate");
  await page.locator("#locality").selectOption({ label: "Garag (Dharwad)" });
  await page.locator("#ptype").selectOption("agricultural_land");
  await expect(page.getByLabel("Area unit")).toHaveValue("acre");
  await page.locator("#area").fill("2.25");
  await expect(page.getByText("= 98,010 sq ft")).toBeVisible();
  await page.getByRole("button", { name: "Estimate price" }).click();
  await expect(page.getByTestId("estimate-result").getByText(/Indicative range ₹/)).toBeVisible();
});

test("listing detail shows the model estimate next to the asking price", async ({ page }) => {
  await page.goto("/properties?property_type=residential_plot");
  await page.locator("article a").first().click();
  const card = page.getByTestId("estimate-result");
  await expect(card).toBeVisible();
  await expect(card.getByText(/Quoted ₹.* the estimate/)).toBeVisible();
  await expect(card.getByText("Trained on synthetic data", { exact: true })).toBeVisible();
});

test("methodology page reports measured model results", async ({ page }) => {
  await page.goto("/about");
  await expect(page.getByText("Test listings (n = ", { exact: false })).toBeVisible();
  await expect(page.getByText("Baseline: overall median price").first()).toBeVisible();
  await expect(page.getByText(/Trained on \d+ synthetic rows \(a documented formula\) plus \d+ real asking prices/)).toBeVisible();
});
