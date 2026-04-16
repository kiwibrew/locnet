import { test, expect } from "@playwright/test";
import { type BuilderInput } from "../../spa/src/features/locnet/api-generated-client";
import { type LocNetModel } from "../../spa/src/features/locnet/model";

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

// Sample data value from API docs
const builderInput: BuilderInput = {
  area_sqkm: 100,
  battery_age_derating: 0.5,
  battery_cost_watt_hour: 0.42,
  charger_inverter_base: 50,
  charger_inverter_variable: 0.35,
  iso_3: "PER",
  labour_cost: 25,
  locations: [
    {
      location_name: "Location 1",
      tower_cost: 1000,
      network_type: ["ISM Wi-Fi 2.4 GHz", "ISM FWA 5.8 GHz"],
      sectors: [2, 2],
      network_links: ["ISM FWA 500"],
      backhaul_links: [],
      backhaul_cost_base: [],
      backhaul_cost_mbps: [],
      power_type: "power_mains_rel",
    },
    {
      location_name: "Location 2",
      tower_cost: 2000,
      network_type: ["ISM Wi-Fi 2.4 GHz", "ISM FWA 5.8 GHz"],
      sectors: [2, 2],
      network_links: ["ISM FWA 500", "ISM FWA 500"],
      backhaul_links: ["LEO Satellite"],
      backhaul_cost_base: [100],
      backhaul_cost_mbps: [5],
      power_type: "power_mains_int",
    },
    {
      location_name: "Location 3",
      tower_cost: 6000,
      network_type: ["ISM Wi-Fi 2.4 GHz", "ISM FWA 5.8 GHz"],
      sectors: [3, 1],
      network_links: ["ISM FWA 500"],
      backhaul_links: ["Fibre 1G", "HTS VSAT"],
      backhaul_cost_base: [200, 50],
      backhaul_cost_mbps: [0.5, 20],
      power_type: "power_solar",
    },
  ],
  mains_power_cost_kwh: 0.65,
  mains_power_installation_cost: 2000,
  solar_cost_watt: 0.6,
  solar_derating: 0.1,
  solar_efficiency: 20,
  system_life: 10,
  terrain_type: "None",
  total_potential_users: 500,
  traffic_growth: 30,
  users_per_household: 4,
  vegetation_type: "None",
  year_1_traffic: 10,
};

test("can load sample data and generate output", async ({ page }) => {
  await page.goto("http://localhost:8000");

  const locnetModel = await page.evaluate(async (builderInput) => {
    // The page has a global on `window` to facilitate the conversion
    // it needs JSON from the page to do this, that's why it needs to 
    // done in the browser rather than in Node
    return window.locnetBuilderInputToModel(builderInput);
  }, builderInput);

  console.log(locnetModel);

  await page.getByTestId("sel_country").selectOption(locnetModel.iso_3);

  await page.waitForTimeout(1000);

  await expect(page.getByTestId("community_characteristics")).toBeVisible({
    timeout: 1000,
  });
});
