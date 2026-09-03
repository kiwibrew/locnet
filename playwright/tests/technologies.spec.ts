import { test, expect } from "./fixtures";
// Only import types from the SPA, never code
import { type BuilderInput } from "../../spa/src/features/locnet/api-generated-client";
import { type LocNetModel } from "../../spa/src/features/locnet/model";
import { assertNever } from "./typescript";





test("can select technologies", async ({ page }) => {
  await page.goto("/app");
  const countrySelector = page.getByTestId("sel_country");
  await expect(countrySelector).toBeVisible();
  await expect(page.getByTestId("introduction")).toHaveCount(0);
  await countrySelector.selectOption("NZL");
});

test("requires a technology before adding a network location", async ({
  page,
}) => {
  await page.goto("/app");
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
  await expect(
    page.getByTestId("physical_characteristics"),
  ).toHaveCount(0);

  const useModelHouseholds = page.getByTestId(
    "location-0-model-households",
  );
  const householdOverride = page.getByTestId("location-0-households");
  await expect(useModelHouseholds).toBeChecked();
  await expect(householdOverride).toBeDisabled();
  await expect(householdOverride).toHaveValue("");
  await expect(page.getByTestId("location-0-towerOpex")).toHaveValue("0");
  await expect(page.getByTestId("location-0-towerHeight")).toHaveValue("6");

  await useModelHouseholds.uncheck();
  await expect(householdOverride).toBeEnabled();
});
