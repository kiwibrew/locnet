import { test, expect } from "@playwright/test";
// Only import types from the SPA, never runtime code.
import { type BuilderInput } from "../../spa/src/features/locnet/api-generated-client";
import { type LocNetModel } from "../../spa/src/features/locnet/model";
import { sampleData } from "./sampleData";
import { assertNever } from "./typescript";

declare global {
  interface Window {
    locnetBuilderInputToModel: (input: BuilderInput) => LocNetModel;
  }
}

test("has title", async ({ page }) => {
  await page.goto("");

  // Expect a title "to contain" a substring.
  await expect(page).toHaveTitle(/Community Network Builder/);
});

const builderInput: BuilderInput = sampleData;

test("can load sample data and generate output", async ({ page }) => {
  await page.goto("");

  const locnetModel = await page.evaluate(async (builderInput) => {
    // The page has a global on `window` to facilitate the conversion
    // it needs JSON from the page to do this, that's why it needs to
    // done in the browser rather than in Node
    return window.locnetBuilderInputToModel(builderInput);
  }, builderInput);

  console.log(locnetModel);

  await page.getByTestId("sel_country").selectOption(locnetModel.iso_3);

  await page.waitForTimeout(1000);

  await page.getByTestId("community_characteristics").click();

  // Select all technologies to reveal all parts of form
  await page.getByTestId("sel_tech").click();
  await page.locator('input[value="FWA"]').click();
  await page.locator('input[value="GPON"]').click();
  await page.locator('input[value="Mobile"]').click();
  await page.locator('input[value="PAF"]').click();

  // Open all disclosures
  await page.getByTestId("sel_freq").click();
  await page.getByTestId("tech_paf").click();
  await page.getByTestId("provider_type").click();
  await page.getByTestId("expert_opt").click();
  await page.getByTestId("net_elements").click();

  const locnetEntries = Object.entries(locnetModel);

  for (let i = 0; i < locnetEntries.length; i++) {
    const [_key, newValue] = locnetEntries[i];
    const key = _key as keyof LocNetModel;

    switch (key) {
      case "locations":
      case "iso_3":
        // already set these, above
        // although this 'case' code does nothing we're putting the key
        // in the switch/case to allow assertNever() below to work
        // and assert that we've handled ALL keys
        break;
      case "model_version":
      case "area_sqkm":
      case "households_total":
      case "users_per_household":
      case "total_potential_users":
      case "paf_usd_hour":
        // uneditable field
        break;
      case "battery_age_derating":
      case "battery_cost_watt_hour":
      case "battery_dod":
      case "charger_inverter_base":
      case "charger_inverter_variable":
      case "labour_cost":
      case "lang":
      case "mains_power_cost_kwh":
      case "mains_power_installation_cost":
      case "power_hybrid_hours":
      case "power_intermittent_hours":
      case "power_reliable_hours":
      case "solar_cost_watt":
      case "solar_derating":
      case "solar_efficiency":
      case "system_life":
      case "traffic_growth":
      case "year_1_traffic":
      case "hh_size":
      case "pop_growth_rate":
      case "hh_income_week":
      case "businesses":
      case "business_users":
      case "service_providers":
      case "service_provider_users":
      case "staff_opex_fixed":
      case "staff_opex_variable":
      case "maintenance_opex":
      case "capex_subsidy":
      case "opex_subsidy":
      case "ue_subsidy":
      case "finance_cost":
      case "debt_proportion":
      case "wacc":
      case "corp_tax":
      case "spectrum_licence_fee":
      case "other_opex":
      case "oc_margin":
      case "community_capex_discount":
      case "paf_deterred_use":
      case "paf_sub_use":
      case "paf_non_sub_use":
      case "paf_gb_hour":
      case "paf_facilities_charge":
      case "ue_cost":
      case "inflation":
      case "power_offgrid_hours":
      case "existing_ue_above_med":
      case "existing_ue_below_med":
        if (typeof newValue === "string" || typeof newValue === "number") {
          await page.getByTestId(key).fill(String(newValue));
        } else {
          console.error({ key, newValue });
          throw Error(
            `Couldn't set ${JSON.stringify(key)} because value wasn't string, was typeof=${typeof newValue}`,
          );
        }
        break;
      case "provider_type": {
        const providerCommercial = page.locator(
          'input[name="provider_type"][value="provider_commercial"]',
        );
        const providerCommunity = page.locator(
          'input[name="provider_type"][value="provider_community"]',
        );

        await providerCommercial.check({ force: true });
        await expect(providerCommercial).toBeChecked();

        await providerCommunity.check({ force: true });
        await expect(providerCommunity).toBeChecked();
        break;
      }
      default:
        assertNever(key);
    }
  }

  const pafUsdHourField = page.getByTestId("paf_usd_hour");
  await expect(pafUsdHourField).toHaveAttribute("readonly", "");

  const pafUsdHourValue = await pafUsdHourField.inputValue();
  expect(pafUsdHourValue).toMatch(/^\d+(\.\d{1,2})?$/);
  expect(Number(pafUsdHourValue)).toBeGreaterThan(0);

  for (let i = 0; i < locnetModel.locations.length; i++) {
    const networkElement = locnetModel.locations[i];
    await page.getByTestId("add_network_location").click();
    if (networkElement.location_name) {
      await page
        .getByTestId(`location-${i}-name`)
        .fill(networkElement.location_name);
    }

    // Keep this browser test independent from the external population service.
    await page.getByTestId(`location-${i}-model-households`).uncheck();
    await page.getByTestId(`location-${i}-households`).fill("100");

    for (let y = 0; y < networkElement.networkTypes.length; y++) {
      const networkType = networkElement.networkTypes[y];
      await page.getByTestId(`location-${i}-add-network-type`).click();
      await page
        .getByTestId(`location-${i}-networktype-${y}-type`)
        .selectOption(networkType.type);
      await page
        .getByTestId(`location-${i}-networktype-${y}-unitCount`)
        .fill(networkType.unitCount);
    }

    if (networkElement.power_type) {
      await page
        .getByTestId(`location-${i}-power_type`)
        .selectOption(networkElement.power_type);
    }

    if (networkElement.towerType) {
      await page
        .getByTestId(`location-${i}-towerType`)
        .selectOption(networkElement.towerType.name);
      await page
        .getByTestId(`location-${i}-towerTypeCost_USD`)
        .fill(networkElement.towerType.cost_USD);
      await page
        .getByTestId(`location-${i}-towerOpex`)
        .fill(networkElement.towerType.opex_USD);
      await page
        .getByTestId(`location-${i}-towerHeight`)
        .fill(networkElement.towerType.height_m);
    }

    for (let y = 0; y < networkElement.midhaulLink.length; y++) {
      const midhaulLink = networkElement.midhaulLink[y];
      await page.getByTestId(`location-${i}-add_midhaul`).click();
      await page.waitForTimeout(100);
      console.log(
        "set",
        `location-${i}-networklink-${y}-type`,
        `[${midhaulLink.type}]`,
      );
      await page
        .getByTestId(`location-${i}-networklink-${y}-type`)
        .selectOption(midhaulLink.type);
    }

    for (let y = 0; y < networkElement.backhaulLinks.length; y++) {
      const backhaulLink = networkElement.backhaulLinks[y];
      await page.getByTestId(`location-${i}-add_backhaul`).click();
      await page.waitForTimeout(100);
      await page
        .getByTestId(`location-${i}-backhaulLink-${y}-type`)
        .selectOption(backhaulLink.type);
      await page
        .getByTestId(`location-${i}-backhaulLink-${y}-monthlyCharge`)
        .fill(backhaulLink.monthlyCharge);
      await page
        .getByTestId(`location-${i}-backhaulLink-${y}-trafficCost_USD`)
        .fill(backhaulLink.trafficCost_USD);
    }
  }

  await page.waitForTimeout(500);

  await page.getByTestId("calculate_network").click();

  await expect(page.getByTestId("report")).toHaveText("Report", {
    timeout: 120_000,
  });

  const coverageMaps = page.getByTestId("coverage-maps");
  await expect(coverageMaps).toBeVisible();
  await expect(coverageMaps.getByTestId(/^coverage-map-/)).toHaveCount(
    locnetModel.locations.length,
  );
  await expect(
    coverageMaps.locator('[data-pdf-map-status="ready"]'),
  ).toHaveCount(locnetModel.locations.length, { timeout: 30_000 });
  // Spreadsheet serializers only include explicitly marked data sheets.
  await expect(coverageMaps.locator("[data-sheet]")).toHaveCount(0);

  const expectedDownloads = [
    ["Download CSV", /\.csv$/],
    ["Download Excel", /\.xlsx$/],
    ["Download PDF", /\.pdf$/],
  ] as const;

  for (const [buttonName, extension] of expectedDownloads) {
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      page.getByRole("button", { name: buttonName }).click(),
    ]);
    expect(download.suggestedFilename()).toMatch(extension);

    if (buttonName === "Download CSV" || buttonName === "Download PDF") {
      const stream = await download.createReadStream();
      const chunks: Buffer[] = [];
      for await (const chunk of stream) chunks.push(Buffer.from(chunk));
      const contents = Buffer.concat(chunks);
      if (buttonName === "Download CSV") {
        expect(contents.toString("utf8")).not.toContain(
          "Location Coverage Maps",
        );
      } else {
        // MapLibre canvases are replaced with PNG snapshots for PDF export.
        expect(contents.toString("latin1")).toContain("/Subtype /Image");
      }
    }
  }
});
