import { expect, test } from "@playwright/test";

test("landing page shows real listings and category counts", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /property research that explains itself/i })).toBeVisible();
  await expect(page.locator("article").first()).toBeVisible();
  await expect(page.getByText(/\d+ listings/).first()).toBeVisible();
  await expect(page.getByText("Synthetic demo listing").first()).toBeVisible();
});

test("search with budget, city and type filters, then open details", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("City").selectOption("Dharwad");
  await page.getByLabel("Property type").selectOption("residential_plot");
  await page.getByLabel("Maximum budget").fill("25 lakh");
  await page.getByRole("button", { name: "Search" }).click();
  await expect(page).toHaveURL(/city=Dharwad.*max_price=2500000/);
  await expect(page.getByText(/listings? match/)).toBeVisible();
  const prices = await page.locator("article p.text-lg").allTextContents();
  expect(prices.length).toBeGreaterThan(0);

  await page.getByLabel("Sort").selectOption("price_asc");
  await expect(page).toHaveURL(/sort=price_asc/);

  await page.locator("article a").nth(1).click();
  await expect(page.getByRole("heading", { name: "Documents" })).toBeVisible();
  await expect(page.getByRole("status").filter({ hasText: "This is a synthetic demonstration listing" })).toBeVisible();
  await expect(page.getByText("Provided – unverified").or(page.getByText("Not provided")).first()).toBeVisible();
  await expect(page.locator(".leaflet-container")).toBeVisible();
});

test("impossible filters show an empty state", async ({ page }) => {
  await page.goto("/properties?max_price=1000");
  await expect(page.getByText("No listings match these filters")).toBeVisible();
});

test("compare two listings", async ({ page }) => {
  await page.goto("/properties?property_type=residential_plot");
  const boxes = page.getByLabel("Compare");
  await boxes.nth(0).check();
  await boxes.nth(1).check();
  await page.getByRole("link", { name: /Compare/ }).first().click();
  await expect(page.getByRole("heading", { name: "Compare properties" })).toBeVisible();
  await expect(page.locator("table thead th")).toHaveCount(3);
  await expect(page.getByRole("rowheader", { name: "Price per sq ft" })).toBeVisible();
});

test("real listings can be filtered and show their source", async ({ page }) => {
  await page.goto("/properties?is_synthetic=false");
  await expect(page.getByText(/listings? match/)).toBeVisible();
  await expect(page.getByText("Real listing · unverified").first()).toBeVisible();
  await expect(page.getByText("Synthetic demo listing", { exact: true })).toHaveCount(0);
  await page.locator("article").filter({ hasText: "Real listing · unverified" }).first().locator("a").first().click();
  const alert = page.getByRole("status").filter({ hasText: "Real listing from a public website" });
  await expect(alert).toBeVisible();
  await expect(alert.getByRole("link", { name: "1acre.in" })).toHaveAttribute("href", /^https:\/\/1acre\.in\/lands-for-sale\//);
});
