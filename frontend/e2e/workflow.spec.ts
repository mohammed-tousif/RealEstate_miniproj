import { expect, test } from "@playwright/test";

const PASSWORD = process.env.SEED_DEMO_PASSWORD ?? "DemoPass123";

test("seller submits a listing, admin approves it, guest finds it", async ({ page, browser }) => {
  const title = `E2E plot ${Date.now()}`;

  await page.goto("/login");
  await page.getByLabel("Email").fill("seller1@demo.propwise.example");
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "My listings" })).toBeVisible();

  await page.getByRole("link", { name: "Add a listing" }).click();
  await page.locator("#title").fill(title);
  await page.locator("#price").fill("19.5 lakh");
  await page.locator("#locality").selectOption({ label: "Saptapur (Dharwad)" });
  await page.locator("#area").fill("1200");
  await page.locator("#road").selectOption("paved_internal");
  await page.getByLabel("rtc_pahani availability").selectOption("provided");
  await page.getByRole("checkbox", { name: /I consent/ }).check();
  await page.getByRole("button", { name: "Submit for review" }).click();
  await expect(page.getByText("Listing submitted")).toBeVisible();
  await expect(page.getByText("pending", { exact: true })).toBeVisible();

  // Not visible to guests yet.
  const guest = await browser.newPage();
  await guest.goto(`/properties?q=${encodeURIComponent(title)}`);
  await expect(guest.getByText("No listings match these filters")).toBeVisible();

  // Admin approves.
  await page.getByRole("button", { name: /Sign out/ }).click();
  await page.goto("/login");
  await page.getByLabel("Email").fill("admin@demo.propwise.example");
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Admin dashboard" })).toBeVisible();
  const row = page.locator("tr", { hasText: title });
  await row.getByRole("button", { name: "Approve" }).click();
  await expect(row).toHaveCount(0);

  await guest.goto(`/properties?q=${encodeURIComponent(title)}`);
  await expect(guest.getByText(title)).toBeVisible();
});
