import { test, expect } from "@playwright/test";
// Only import types from the SPA, never code
import { type BuilderInput } from "../../spa/src/features/locnet/api-generated-client";
import { type LocNetModel } from "../../spa/src/features/locnet/model";
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
  await page.getByTestId("physical_characteristics").click();
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
      case "terrain_type":
        await page.getByLabel("Terrain profile").selectOption(String(newValue));
        break;
      case "vegetation_type":
        await page
          .getByLabel("Vegetation profile")
          .selectOption(String(newValue));
        break;
      case "users_per_household":
      case "total_potential_users":
        // uneditable field
        break;
      case "area_sqkm":
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
      case "households_total":
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
      case "paf_usd_hour":
      case "ue_cost":
      case "inflation":
      case "power_offgrid_hours":
      case "provider_type":
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
      default:
        assertNever(key);
    }
  }

  for (let i = 0; i < locnetModel.locations.length; i++) {
    const networkElement = locnetModel.locations[i];
    await page.getByTestId("add_network_location").click();
    if (networkElement.name) {
      await page.getByTestId(`location-${i}-name`).fill(networkElement.name);
    }

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

  await page.waitForTimeout(2000);

  await expect(page.getByTestId("report")).toHaveText("Report");
});
