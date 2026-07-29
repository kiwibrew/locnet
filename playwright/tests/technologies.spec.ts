import { test, expect } from "@playwright/test";
// Only import types from the SPA, never code
import { type BuilderInput } from "../../spa/src/features/locnet/api-generated-client";
import { type LocNetModel } from "../../spa/src/features/locnet/model";
import { assertNever } from "./typescript";





test("can select technologies", async ({ page }) => {
  await page.goto("");
  await page.getByTestId("sel_country").selectOption("NZL");

  await expect(page.getByTestId("introduction")).toHaveText("Introduction");
});

test("requires a technology before adding a network location", async ({
  page,
}) => {
  await page.goto("");
  await page.getByTestId("sel_country").selectOption("NZL");
  await page.getByTestId("net_elements").click();

  const addLocation = page.getByTestId("add_network_location");
  const technologiesDisclosure = page.getByTestId("sel_tech");
  const firstTechnology = page
    .locator(
      '[data-form-node="technologies"] input[type="checkbox"]:not(:disabled)',
    )
    .first();

  await expect(addLocation).toHaveAttribute("aria-disabled", "true");
  await addLocation.click({ force: true });

  await expect(page.getByTestId("location-0")).toHaveCount(0);
  await expect(technologiesDisclosure).toHaveAttribute("aria-pressed", "true");
  await expect(firstTechnology).toBeFocused();
  await expect(firstTechnology).toHaveJSProperty(
    "validationMessage",
    "Please select at least one technology.",
  );

  await firstTechnology.check();
  await expect(addLocation).toHaveAttribute("aria-disabled", "false");
  await expect(firstTechnology).toHaveJSProperty("validationMessage", "");

  await addLocation.click();
  await expect(page.getByTestId("location-0")).toBeVisible();
});
