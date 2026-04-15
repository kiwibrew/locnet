import logging
from library.helpers import fetch_grist_data
from library.classes import SolarModelInput
import numpy as np
import pandas as pd


def assign_users(df, total_potential_users):
    df = df.copy()
    df["assigned_users"] = 0
    df["_row_order"] = np.arange(len(df))

    # Sort by cost, then original order
    df = df.sort_values(["cost_per_passing", "_row_order"])

    remaining = total_potential_users

    for cost, grp in df.groupby("cost_per_passing", sort=False):
        idx = grp.index
        capacities = grp["users_supported"].to_numpy()
        tier_capacity = capacities.sum()

        if remaining <= 0:
            break

        # Case 1: fill entire tier
        if remaining >= tier_capacity:
            df.loc[idx, "assigned_users"] = capacities
            remaining -= tier_capacity
            continue

        # Case 2: partial fill of this tier
        n = len(grp)

        # Sub-case A: equal capacities
        if np.all(capacities == capacities[0]):
            base = remaining // n
            rem = remaining % n
            alloc = np.full(n, base)
            alloc[:rem] += 1

        # Sub-case B: proportional allocation
        else:
            alloc = np.floor(
                remaining * capacities / tier_capacity
            ).astype(int)

            shortfall = remaining - alloc.sum()
            if shortfall > 0:
                alloc[:shortfall] += 1

        # Cap allocations
        alloc = np.minimum(alloc, capacities)

        df.loc[idx, "assigned_users"] = alloc
        remaining -= alloc.sum()
        break  # bin exhausted

    return (
        df
        .drop(columns="_row_order")
        .sort_index()
    )


def apply_cpe_costs(df):
    df = df.copy()
    if "access_capex" in df.columns:
        df["access_capex"] = df["access_capex"].astype(float)
    mask = (df["cpe_cost"] != 0) & (df["assigned_users"] != 0)
    if "users_per_ue" in df.columns:
        df.loc[mask, "access_capex"] += round(df.loc[mask, "cpe_cost"] * (df.loc[mask, "assigned_users"] / df.loc[mask, "users_per_ue"]), 2)
    else:
        df.loc[mask, "access_capex"] += round(df.loc[mask, "cpe_cost"] * df.loc[mask, "assigned_users"], 2)
    return df


def solar_model(input_data: SolarModelInput):
    logging.info(f'Entered the solar model')

    # Get variables from the input data
    latitude = input_data.latitude
    longitude = input_data.longitude
    logging.info(f"lat & long: {latitude}, {longitude}")
    power_reliable_hours = input_data.power_reliable_hours
    power_required = input_data.power_required
    system_life = input_data.system_life
    battery_cost_watt_hour = input_data.battery_cost_watt_hour
    charger_inverter_base = input_data.charger_inverter_base
    charger_inverter_variable = input_data.charger_inverter_variable
    mains_power_cost_kwh = input_data.mains_power_cost_kwh
    mains_power_installation_cost = input_data.mains_power_installation_cost
    solar_cost_watt = input_data.solar_cost_watt
    power_intermittent_hours = input_data.power_intermittent_hours
    power_hybrid_hours = input_data.power_hybrid_hours
    system_type = input_data.system_type
    power_capex = 0
    power_opex = 0

    query_name = "solarstats_query"
    sql_query = """
        SELECT
        location, iso_2, latitude, longitude, min_sun, max_no_sun_days, annual_no_sun_days, avg_temp, min_temp, max_temp
        FROM solarstats
        where latitude = {}
        and longitude = {}
        """.format(latitude, longitude)

    # Fetch Data
    logging.info(f'running the db query')
    try:
        data = fetch_grist_data(sql_query)
    except Exception as e:
        logging.info(f"Failed to load {query_name} data: {str(e)}")
        return False

    min_sun = float(data[0]['min_sun'])
    max_no_sun_days = float(data[0]['max_no_sun_days'])
    annual_no_sun_days = float(data[0]['annual_no_sun_days'])
    min_temp = float(data[0]['min_temp'])
    solar_efficiency = input_data.solar_efficiency / 100
    solar_derating = input_data.solar_derating / 100
    battery_age_derating = input_data.battery_age_derating / 100
    battery_dod = input_data.battery_dod / 100
    logging.info(f'extracted results from the db query')

    # Cold derating calculation
    def calculate_cold_derating(_min_temp):
        if _min_temp <= -20:
            return 65
        elif -20 < _min_temp <= -10:
            return 1.5 * _min_temp + 95
        elif -10 < _min_temp <= 0:
            return _min_temp + 90
        elif 0 < _min_temp <= 10:
            return 0.7 * _min_temp + 90
        elif 10 < _min_temp <= 20:
            return 0.3 * _min_temp + 94
        else:
            return 100

    # # Creating a data frame to store the calculations for later comparison
    # podf = pd.DataFrame()
    #
    # def add_to_podf(podf_system_type,
    #                 podf_power_required,
    #                 podf_adjusted_hours,
    #                 podf_battery_required,
    #                 podf_battery_cost,
    #                 podf_charger_cost,
    #                 podf_power_opex,
    #                 podf_min_sun,
    #                 podf_collection_w_day_m2,
    #                 podf_panels_needed_m2,
    #                 podf_solar_cost_watt,
    #                 podf_solar_cost,
    #                 podf_power_system_capex,
    #                 podf_total_cost):
    #     row = pd.DataFrame([{
    #         "system_type": podf_system_type,
    #         "power_required": podf_power_required,
    #         "adjusted_hours": podf_adjusted_hours,
    #         "battery_required": podf_battery_required,
    #         "battery_cost": podf_battery_cost,
    #         "charger_cost": podf_charger_cost,
    #         "power_opex": podf_power_opex,
    #         "min_daily_sun_wm2": podf_min_sun,
    #         "watts_day_m2": podf_collection_w_day_m2,
    #         "panels_need_m2": podf_panels_needed_m2,
    #         "solar_cost_pw": podf_solar_cost_watt,
    #         "solar_cost": podf_solar_cost,
    #         "power_system_capex": podf_power_system_capex,
    #         "total_cost": podf_total_cost
    #     }])
    #     return pd.concat([podf, row], ignore_index=True)

    # Populating blank variables to be used for Reilable and Hybrid systems
    collection_w_day_m2 = ""
    panels_needed_m2 = ""
    solar_cost = ""

    if system_type == "power_mains_rel":
        # Calculations for Reliable
        adjusted_hours = power_reliable_hours
        base_battery = power_required * adjusted_hours * battery_dod
        aged_battery = base_battery / ((1 - battery_age_derating) ** system_life)
        cold_derating = calculate_cold_derating(min_temp)
        battery_required = aged_battery / (cold_derating / 100)
        battery_cost = round(battery_required * battery_cost_watt_hour)
        charger_cost = round(charger_inverter_base + (power_required * 1.5))
        power_opex = round((mains_power_cost_kwh / 1000) * power_required * 24 * 365 * system_life)
        power_capex = round(battery_cost + charger_cost + mains_power_installation_cost)
        # system_total_cost = power_system_capex + power_opex

    # # Add to DataFrame using pd.concat
    # podf = add_to_podf(system_type, power_required, adjusted_hours, battery_required, battery_cost, charger_cost,
    #                    power_opex, min_sun, collection_w_day_m2, panels_needed_m2, solar_cost_watt, solar_cost,
    #                    power_system_capex,
    #                    system_total_cost)

    elif system_type == "power_mains_int":
        # Calculations for Intermittent
        adjusted_hours = power_intermittent_hours
        base_battery = power_required * adjusted_hours * battery_dod
        aged_battery = base_battery / ((1 - battery_age_derating) ** system_life)
        cold_derating = calculate_cold_derating(min_temp)
        battery_required = aged_battery / (cold_derating / 100)
        battery_cost = battery_required * battery_cost_watt_hour
        charger_cost = charger_inverter_base + (power_required * 1.5)
        power_opex = (mains_power_cost_kwh / 1000) * power_required * 24 * 365 * system_life
        power_capex = battery_cost + charger_cost + mains_power_installation_cost
        # system_total_cost = power_system_capex + power_opex

    # # Add to DataFrame using pd.concat
    # podf = add_to_podf(system_type, power_required, adjusted_hours, battery_required, battery_cost, charger_cost,
    #                    power_opex, min_sun, collection_w_day_m2, panels_needed_m2, solar_cost_watt, solar_cost,
    #                    power_system_capex,
    #                    system_total_cost)

    elif system_type == "power_hybrid":
        # Calculations for Hybrid
        adjusted_hours = power_hybrid_hours
        base_battery = power_required * adjusted_hours * battery_dod
        aged_battery = base_battery / ((1 - battery_age_derating) ** system_life)
        cold_derating = calculate_cold_derating(min_temp)
        battery_required = aged_battery / (cold_derating / 100)
        solar_watts_needed = power_required * adjusted_hours
        irradiance_w_day_m2 = min_sun * 1000
        collection_w_day_m2 = irradiance_w_day_m2 * (solar_efficiency * ((1 - solar_derating) ** system_life))
        panels_needed_m2 = solar_watts_needed / collection_w_day_m2
        panel_watts_per_m2 = solar_efficiency * 1350
        panel_watts_needed = panels_needed_m2 * panel_watts_per_m2
        panel_cost = panel_watts_per_m2 * solar_cost_watt
        solar_cost = panels_needed_m2 * panel_cost
        battery_cost = battery_required * battery_cost_watt_hour
        charger_cost = charger_inverter_base + (panel_watts_needed * charger_inverter_variable)
        power_opex = (mains_power_cost_kwh / 1000) * power_required * 24 * annual_no_sun_days * system_life
        power_capex = battery_cost + charger_cost + mains_power_installation_cost
        # system_total_cost = power_system_capex + power_opex + solar_cost

    # # Add to DataFrame using pd.concat
    # podf = add_to_podf(system_type, power_required, adjusted_hours, battery_required, battery_cost, charger_cost,
    #                    power_opex, min_sun, collection_w_day_m2, panels_needed_m2, solar_cost_watt, solar_cost,
    #                    power_system_capex,
    #                    system_total_cost)

    elif system_type == "power_solar":
        # Calculations for Off Grid
        power_opex = 0  # Set to zero for off-grid sites
        adjusted_hours = max_no_sun_days * 24
        base_battery = power_required * adjusted_hours * battery_dod
        aged_battery = base_battery / ((1 - battery_age_derating) ** system_life)
        cold_derating = calculate_cold_derating(min_temp)
        battery_required = aged_battery / (cold_derating / 100)
        solar_watts_needed = power_required * adjusted_hours
        irradiance_w_day_m2 = min_sun * 1000
        collection_w_day_m2 = irradiance_w_day_m2 * (solar_efficiency * ((1 - solar_derating) ** system_life))
        panels_needed_m2 = solar_watts_needed / collection_w_day_m2
        panel_watts_per_m2 = solar_efficiency * 1350
        panel_watts_needed = panels_needed_m2 * panel_watts_per_m2
        panel_cost = panel_watts_per_m2 * solar_cost_watt
        solar_cost = panels_needed_m2 * panel_cost
        battery_cost = battery_required * battery_cost_watt_hour
        charger_cost = charger_inverter_base + (panel_watts_needed * charger_inverter_variable)
        power_capex = battery_cost + charger_cost + solar_cost
        # system_total_cost = power_system_capex

    # # Add to DataFrame using pd.concat
    # podf = add_to_podf(system_type, power_required, adjusted_hours, battery_required, battery_cost, charger_cost,
    #                    power_opex, min_sun, collection_w_day_m2, panels_needed_m2, solar_cost_watt, solar_cost,
    #                    power_system_capex,
    #                    system_total_cost)
    #
    # logging.info("Power system comparison table (podf)")
    # logging.info(podf.to_string(index=False))

    # # Find particular rows
    # lowest_system_row = podf.loc[podf["total_cost"].idxmin()]
    # off_grid_row = podf.loc[podf["system_type"] == "Off Grid"]
    # reliable_row = podf.loc[podf["system_type"] == "Reliable"]
    # intermittent_row = podf.loc[podf["system_type"] == "Intermittent"]
    # hybrid_row = podf.loc[podf["system_type"] == "Hybrid"]

    # # Extract the 'System' and 'Total Cost' from that row
    # lowest_cost_system_type = lowest_system_row["system_type"]
    # lowest_system_cost = lowest_system_row["total_cost"]
    # power_opex = lowest_system_row["power_opex"]
    # power_capex = lowest_system_row["power_system_capex"]
    # logging.info(f'Lowest Cost System is {lowest_cost_system_type} at {lowest_system_cost} USD with CapEx {power_system_capex}.')
    # off_grid_cost = off_grid_row["power_system_capex"].values[0]
    # logging.info(f'Power System Cost for Off Grid system: {off_grid_cost}')

    return {
        "power_capex": round(power_capex),
        "power_opex": round(power_opex),
        "lowest_cost_system_type": "na",
        "off_grid_cost": 0
    }