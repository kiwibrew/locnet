import logging
import math
from copy import deepcopy
import numpy_financial as npf
import numpy as np
import pandas as pd
from fastapi import HTTPException
from library.helpers import (get_tech_data, get_backhaul, get_midhaul,
                             demand_curve, build_keyed_row, get_country_ids)
from library.bpo import (get_pl_lab_cos_by_year,
                         get_pl_oth_sys_op_cos_by_year,
                         get_pl_bh_pow_op_cos_by_year, get_pl_spec_fee_by_year,
                         get_pl_maint_cos_by_year, get_pl_tot_op_cos_by_year,
                         get_pl_op_prof_by_year, get_pl_dep_by_year,
                         get_pl_ebit_by_year, get_pl_int_by_year,
                         get_pl_ebt_by_year, get_pl_tax_by_year,
                         get_pl_prof_by_year, get_pl_sub_by_year,
                         get_pl_cli_rev_by_year, get_pl_tot_rev_by_year,
                         get_cf_cash_in_by_year, get_cf_cash_out_by_year,
                         get_cf_net_by_year, get_cf_cum_by_year,
                         build_inv_row)
from library.supply import assign_users, apply_cpe_costs, power_model
from library.display import get_net_summary_table, get_dc_points, get_dcba_table
from library.classes import BuilderInput, ModelerOutput, PowerModelInput
from library.geospatial import (
    CoverageService,
    GeospatialClient,
    calculate_coverage_population,
)
from math import pi, ceil


NETWORK_BOM_ROW_COLUMNS = [
    "location_name",
    "technology_type",
    "technology",
    "cost_each",
    "quantity",
    "cpe_quantity",
    "cpe_cost",
    "network_capex",
]


def calculate_access_users_supported(
    *,
    technology_family: str,
    population_covered: float,
    ue_per_sector: float,
    sectors: int,
    household_size: float,
    sector_mbps: float,
    user_final_year_peak_mbps: float,
) -> float:
    """Apply the population, equipment, and throughput capacity limits."""
    if technology_family not in {"Mobile", "FWA", "GPON"}:
        raise ValueError(
            f"Unsupported access technology family: {technology_family}"
        )
    if user_final_year_peak_mbps <= 0:
        raise ValueError("Final-year peak traffic per user must be greater than zero")

    users_per_ue = 1 if technology_family == "Mobile" else household_size
    return min(
        population_covered,
        ue_per_sector * sectors * users_per_ue,
        (sector_mbps * sectors) / user_final_year_peak_mbps,
    )


def build_network_bom_dataframe(
    ldf: pd.DataFrame, mdf: pd.DataFrame, bdf: pd.DataFrame
) -> pd.DataFrame:
    """Build the network equipment bill of materials from modeled equipment."""
    empty_bom = pd.DataFrame(columns=NETWORK_BOM_ROW_COLUMNS)

    access_bom = ldf[
        [
            "location_name",
            "network_type",
            "capex_per_sector",
            "sectors",
            "assigned_ue",
            "cpe_cost",
        ]
    ].copy()
    access_bom = access_bom.rename(
        columns={
            "network_type": "technology",
            "capex_per_sector": "cost_each",
            "sectors": "quantity",
        }
    )
    access_bom["technology_type"] = "Access Network"
    access_bom["cpe_quantity"] = np.where(
        access_bom["cpe_cost"].notna() & access_bom["cpe_cost"].ne(0),
        access_bom["assigned_ue"],
        0,
    )
    access_bom = access_bom[NETWORK_BOM_ROW_COLUMNS[:-1]]

    def build_link_bom(
        link_df: pd.DataFrame,
        technology_type: str,
        technology_column: str,
        cost_column: str,
    ) -> pd.DataFrame:
        if link_df.empty:
            return empty_bom.copy()

        link_bom = (
            link_df.groupby(
                ["location_name", technology_column], as_index=False, sort=False
            )
            .agg(
                cost_each=(cost_column, "first"),
                quantity=(technology_column, "size"),
            )
            .rename(columns={technology_column: "technology"})
        )
        link_bom["technology_type"] = technology_type
        link_bom["cpe_quantity"] = 0
        link_bom["cpe_cost"] = 0
        return link_bom[NETWORK_BOM_ROW_COLUMNS[:-1]]

    midhaul_bom = build_link_bom(
        mdf,
        "Midhaul Network",
        "network_link_type",
        "network_link_cost",
    )
    backhaul_bom = build_link_bom(
        bdf,
        "Backhaul Network",
        "backhaul_link_type",
        "backhaul_link_capex",
    )

    bom_df = pd.concat([access_bom, midhaul_bom, backhaul_bom], ignore_index=True)
    for column in ["cost_each", "quantity", "cpe_quantity", "cpe_cost"]:
        bom_df[column] = pd.to_numeric(bom_df[column], errors="coerce").fillna(0)
    # CPE costs are per assigned user for technologies that require CPE.
    bom_df["network_capex"] = (
        bom_df["cost_each"] * bom_df["quantity"]
        + bom_df["cpe_quantity"] * bom_df["cpe_cost"]
    ).round(2)
    bom_df = bom_df.sort_values(
        by=["location_name", "technology_type", "technology"],
        kind="stable",
    ).reset_index(drop=True)

    return bom_df[NETWORK_BOM_ROW_COLUMNS]


async def modeler(
    input_data: BuilderInput,
    geospatial_client: CoverageService | None = None,
) -> ModelerOutput:
    if geospatial_client is None:
        async with GeospatialClient.from_config() as configured_client:
            return await modeler(input_data, configured_client)

    # Log the received data
    logging.info(f'Received input: {input_data.model_dump_json()}')

    # Read technology and link data from the model database
    iso_3, iso_2, iso_code, country_name = get_country_ids(input_data.iso_3)  # numeric ISO code
    tech_data = get_tech_data()
    backhaul_data = get_backhaul()
    midhaul_data = get_midhaul()

    # Set some empty variables that will be filled latter
    data_rows = []
    midhaul_rows = []
    backhaul_rows = []
    power_rows = []
    coverage_maps = []
    tower_costs = []
    location_population_estimates = []
    tech_use = []  # A list that will store all technology types in use
    paf_facilities = 0
    paf_seats = 0
    paf_seat_cost = 0
    user_final_year_peak_mbps = False  # The peak hour data rate per user in the final year of network operation

    # Get some model inputs that will remain constant through the calculations
    hh_size = input_data.hh_size or input_data.users_per_household
    area_sqkm = sum(pi * location.radius ** 2 for location in input_data.locations)
    year_1_traffic = int(input_data.year_1_traffic)
    traffic_growth = round(float(input_data.traffic_growth),2)
    traffic_growth_pct = traffic_growth / 100  # Defaults and user entries are for percent so we divide by 100
    system_life = int(input_data.system_life)
    pop_growth_rate_input = input_data.pop_growth_rate if input_data.pop_growth_rate is not None else 0
    pop_growth_rate = pop_growth_rate_input / 100  # User Interface C11
    # Get the number of service providers and their users from user input
    service_providers = int(input_data.service_providers) if input_data.service_providers is not None else 0
    sp_users_avg = input_data.service_provider_users
    sp_users = int(service_providers * sp_users_avg) if sp_users_avg is not None else 0
    if sp_users == 0:
        service_providers = 0
    logging.info(f"Service Provider Users is {sp_users}")
    # Get the number of businesses and their users from user input
    businesses = int(input_data.businesses) if input_data.businesses is not None else 0
    bus_users_avg = input_data.business_users
    bus_users = int(businesses * bus_users_avg) if bus_users_avg is not None else 0
    if bus_users == 0:
        businesses = 0
    logging.info(f"Business Users is {bus_users}")

    labour_cost = input_data.labour_cost
    labour_monthly = labour_cost * 40 * 4.3

    # PAF parameters for use in supply model
    paf_hours_month_seat = 129  # Supply model considers 50% availability of 10 hours day, 6 days per week.
    paf_sub_use = input_data.paf_sub_use if input_data.paf_sub_use is not None else 0
    paf_non_sub_use = input_data.paf_non_sub_use if input_data.paf_non_sub_use is not None else 0
    paf_deterred_use = input_data.paf_deterred_use if input_data.paf_deterred_use is not None else 0
    paf_gb_hour = input_data.paf_gb_hour  # User Interface C69
    paf_usd_hour = input_data.paf_usd_hour
    paf_use_pp = max(paf_sub_use, paf_non_sub_use, paf_deterred_use)

    if paf_use_pp > 0:
        paf_users_per_seat = paf_hours_month_seat / paf_use_pp
    else:
        paf_users_per_seat = 0
    logging.info(f"use pp is {paf_use_pp} and users per seat is {round(paf_users_per_seat)}")

    # Get model power variable inputs for passing through to the power model:
    solar_cost_watt = input_data.solar_cost_watt
    solar_derating = input_data.solar_derating
    solar_efficiency = input_data.solar_efficiency
    mains_power_cost_kwh = input_data.mains_power_cost_kwh
    mains_power_installation_cost = input_data.mains_power_installation_cost
    battery_age_derating = input_data.battery_age_derating
    battery_cost_watt_hour = input_data.battery_cost_watt_hour
    battery_dod = input_data.battery_dod
    charger_inverter_base = input_data.charger_inverter_base
    charger_inverter_variable = input_data.charger_inverter_variable
    power_hybrid_hours = input_data.power_hybrid_hours
    power_intermittent_hours = input_data.power_intermittent_hours
    power_reliable_hours = input_data.power_reliable_hours
    power_capex = 0  # Power CapEx will be added to for each location
    power_opex = 0  # Power OpEx will be added to for each location

    # Process each location received
    for location in input_data.locations:
        logging.info(f'Processing location {location}')
        if location.tower_height is None or location.tower_opex is None:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Tower height and tower operating expense are required at "
                    f"{location.location_name}."
                ),
            )
        tower_costs.append(location.tower_cost or 0)
        power_type = location.power_type
        location_watts = 0 # Start a counter for all power use per location
        location_population_estimate = 0.0
        location_coverage_features = []
        location_area_sqkm = pi * location.radius ** 2
        logging.info(f"power type for this location is {power_type}")
        latitude = location.latitude
        longitude = location.longitude
        # Process network types and sectors (nt = network type) for each location
        # The zip function allows to read multiple lists in parallel
        # On a per-lcation basis, find the power type

        for nt, sectors in zip(location.network_type, location.sectors):
            access_capex = sector_power_use = users_sector = downlink_mbps = sector_mbps = cost_per_sector = sector_coverage = 0
            logging.info(f'Processing technology {nt}')
            tech = next((item for item in tech_data if item["network_type"] == nt), None)

            if not tech:
                raise HTTPException(status_code=400, detail=f"Invalid network type at {location.location_name}")
            # Add the technology to our list of techs in use
            tech_use.append(tech["technology"])
            spectrum_mhz = tech["spectrum_mhz"]
            ue_per_sector = tech["ue_per_sector"]

            coverage = await calculate_coverage_population(
                location=location,
                technology=tech,
                iso_3=iso_3,
                household_size=hh_size,
                service=geospatial_client,
            )
            cell_radius = coverage.cell_radius_km
            sector_coverage = coverage.sector_coverage_sqkm
            vegetation_factor = coverage.vegetation_factor
            vegetation_loss = coverage.vegetation_loss
            pop_covered = coverage.population_covered
            location_population_estimate = max(
                location_population_estimate,
                pop_covered,
            )
            coverage_feature = deepcopy(coverage.geojson)
            properties = coverage_feature.get("properties")
            if not isinstance(properties, dict):
                properties = {}
            coverage_feature["properties"] = {
                **properties,
                "network_type": nt,
                "technology": tech["technology"],
            }
            location_coverage_features.append(coverage_feature)

            # Calculate the number of end users supported per UE
            if tech["technology"] in ["Mobile", "PAF"]:
                users_per_ue = 1
            # GPON and FWA connections are assumed to be used by all household members
            else:
                users_per_ue = hh_size

            coverage_area = min((sector_coverage * sectors), location_area_sqkm)

            # Find the power requirement of the technology
            watts_sector = tech["power_consumption"]
            watts = sectors * watts_sector
            location_watts += watts

            # Capacity Calculations
            efficiency_bits_hz = tech["efficiency_bits_hz"]
            # Capacity per sector
            sector_mbps = spectrum_mhz * efficiency_bits_hz
            # Capacity of all sectors of this type at a location
            downlink_mbps = sectors * sector_mbps
            # Calculate the peak hour capacity required
            user_monthly_traffic = (year_1_traffic * (1 + traffic_growth_pct) ** (system_life + 1))
            user_final_year_peak_mbps = user_monthly_traffic / 30 * 0.085

            # Determine the population covered, users and households supported
            if tech["technology"] == "PAF":
                loc_paf_seats = sectors
                paf_seats += loc_paf_seats
                users_sector = paf_users_per_seat
                users_supported = users_sector * sectors
                # Re-set downlink mbps to reflect peak hour demand in final year times number of seats
                downlink_mbps = round((user_final_year_peak_mbps * loc_paf_seats),2)
            else:
                users_supported = calculate_access_users_supported(
                    technology_family=tech["technology"],
                    population_covered=pop_covered,
                    ue_per_sector=ue_per_sector,
                    sectors=sectors,
                    household_size=hh_size,
                    sector_mbps=sector_mbps,
                    user_final_year_peak_mbps=user_final_year_peak_mbps,
                )
                users_sector = users_supported / sectors if sectors else 0
            households_sector = users_sector / hh_size
            households_supported = users_supported / hh_size

            # Set the user's maximal information rate (MIR)
            if tech["technology"] == "PAF":
                user_mir = sector_mbps  # To 100% of desk capacity for a PAF
            elif tech["technology"] == "Mobile":
                logging.info("MIR for Mobile")
                active_fraction = 0.05
                active_users = users_sector * active_fraction
                active_users = max(active_users, 1)
                user_mir_calc = sector_mbps / active_users
                user_mir = round(min(user_mir_calc, sector_mbps), 1)
            elif tech["technology"] == "GPON":
                logging.info("MIR for GPON")
                active_fraction = 0.05
                active_users = max(users_sector * active_fraction, 1)
                user_mir = max((sector_mbps / active_users), 1000)
                logging.info(f"MIR for GPON calculated as {user_mir}")
            else:
                logging.info("MIR for FWA")
                user_mir = sector_mbps / 8  # To 12.5% of sector capacity for multi-access technologies

            # Determine the cost per sector
            tech_lifespan = tech["lifespan"]
            tech_refresh = ceil(system_life / tech_lifespan)
            logging.info(f"tech_refresh: {tech_refresh}")
            cpe_cost = 0
            if tech["cpe_cost"]:
                cpe_cost = tech["cpe_cost"]
            if tech["technology"] == "GPON":  # In the case of GPON the major inputs are cost of labour and area
                gpon_base = tech["cost_per_sector"]
                capex_per_sector = gpon_base + (
                    households_supported
                    * ((labour_cost * 8) + 50)
                    * location.radius
                )
                logging.info(f'capex per sector: {capex_per_sector}')
            else:  # In the case of Mobile and FWA we take the cost per sector from the technologies table
                capex_per_sector = tech["cost_per_sector"]
            capex_per_sector = capex_per_sector * tech_refresh
            access_capex = sectors * capex_per_sector
            logging.info(f'access capex: {access_capex}')

            # load on the cost of power use over the lifetime of the access considering power type available
            if power_type == "power_solar":
                sector_power_use = 0
            elif power_type == "power_hybrid":
                # Assume mains will only be used 25% of the time and solar will cover the rest
                sector_power_use = (watts_sector / 1000) * system_life * 87600 * mains_power_cost_kwh * 0.25
            else:
                sector_power_use = (watts_sector/1000) * system_life * 87600 * mains_power_cost_kwh
            logging.info(f'sector power use: {sector_power_use} from watts {watts} * {mains_power_cost_kwh} ')
            cost_per_sector = capex_per_sector + sector_power_use
            logging.info(f'cost per sector after power use added: {cost_per_sector}')

            # Determine the cost per pass
            if cpe_cost > 0:  # presence of a CPE assumes we're covering a household so add on CPE costs
                cost_per_sector += (cpe_cost * households_sector)
            cost_per_pass = cost_per_sector / users_sector if users_sector else 0
            logging.info(f"cost per pass calculated at {cost_per_pass}")

            # Determine quality of service measurements
            if tech["technology"] == "PAF":
                user_cir = user_mir
            else:
                user_cir = (
                    sector_mbps / (users_supported / sectors)
                    if users_supported and sectors
                    else 0
                )
            # Correct CIR in low capacity situations
            if user_cir > user_mir:
                user_cir = user_mir
            user_contention = user_mir / user_cir if user_cir else 0

            # For Public Access Facilities, reset irrelevant data and assign cost per seat
            if tech["technology"] == "PAF":
                spectrum_mhz = 0
                vegetation_loss = 0
                efficiency_bits_hz = 0
                paf_seat_cost = tech["cost_per_sector"]

            data_rows.append({
                "location_name": location.location_name,
                "network_type": nt,
                "capex_per_sector": capex_per_sector,
                "sectors": sectors,  # Number of sectors of the technology at this location
                "network_capex": access_capex,
                "vegetation_loss": vegetation_loss,
                "vegetation_factor": vegetation_factor,
                "spectrum_mhz": spectrum_mhz,  # the amount of spectrum per sector
                "ue_per_sector": ue_per_sector,  # maximum users supported by the technology
                "users_per_ue": users_per_ue,  # changed to household size from static FWA figure
                "cell_radius": round(cell_radius, 2),
                "coverage_area": round(coverage_area, 2),
                "population_covered": round(pop_covered),
                "efficiency_bits_hz": efficiency_bits_hz,
                "downlink_mbps": downlink_mbps,
                "user_mir": user_mir,
                "user_cir": round(user_cir, 2),
                "user_contention": round(user_contention, 1),
                "user_final_year_peak_mbps": round(user_final_year_peak_mbps, 2),
                "users_supported": round(users_supported),
                "cpe_cost": cpe_cost,
                "access_capex": float(round(access_capex)),
                "cost_per_sector": cost_per_sector,
                "cost_per_passing": round(cost_per_pass),
                "watts": watts,
                "sector_power_use": sector_power_use,
                "user_monthly_traffic": round(user_monthly_traffic)

            })

        coverage_maps.append(
            {
                "location_name": location.location_name,
                "latitude": location.latitude,
                "longitude": location.longitude,
                "geojson": {
                    "type": "FeatureCollection",
                    "features": location_coverage_features,
                },
            }
        )

        location_population_estimates.append(
            {
                "population": location_population_estimate,
                "households": location.households,
            }
        )

        # For each location process midhaul links (network_links)
        for link in location.network_links:
            # logging.info(f'Processing midhaul {link}')
            midhaul = next((item for item in midhaul_data if item["name"] == link), None)
            if not midhaul:
                raise HTTPException(status_code=400, detail="Invalid network link type")

            network_link_speed = midhaul["speed_mbps"]
            network_link_cost = midhaul["capital_cost_usd"]
            network_link_watts = midhaul["power_watts"]

            midhaul_rows.append({
                "location_name": location.location_name,
                "network_link_type": link,
                "network_link_speed": network_link_speed,
                "network_link_cost": network_link_cost,
                "network_link_watts": network_link_watts
            })
            location_watts += network_link_watts

        # For each location process backhaul links
        for link, cost_base, cost_mbps in zip(location.backhaul_links,
                                              location.backhaul_cost_base,
                                              location.backhaul_cost_mbps):

            # logging.info(f'Processing backhaul {link}')
            backhaul = next((item for item in backhaul_data if item["name"] == link), None)
            if not backhaul:
                raise HTTPException(status_code=400, detail="Invalid backhaul link type")

            backhaul_link_speed = backhaul["speed_mbps"]
            backhaul_link_capex = backhaul["capital_cost_usd"]
            backhaul_link_watts = backhaul["power_watts"]

            # Calculate the number of users the backhaul supports
            user_capacity = round(backhaul_link_speed / user_final_year_peak_mbps)
            # Calculate the cost of backhaul traffic based on peak hour demand
            backhaul_cost_mbps = float(cost_mbps)
            backhaul_monthly_base_opex = float(cost_base)
            # Assume the year 1 traffic is present from the first month and grow from there
            current_user_traffic = year_1_traffic / 30 * 0.085
            # Calculate the montly growh rate for traffic
            monthly_growth = (1 + traffic_growth_pct) ** (1 / 12) - 1
            # Set up an empty list for annual monthly variable bandwidth charges per user
            annual_monthly_variable_per_user = []
            # Iterate over the years of the system life
            for year in range(int(system_life)):
                monthly_charges = []
                # Iterate over the months in each year
                for month in range(12):
                    # calculate monthly per user backhaul charge
                    user_monthly_charge = current_user_traffic * backhaul_cost_mbps
                    # append the charge to the monthly list
                    monthly_charges.append(user_monthly_charge)
                    # grow the traffic for next month
                    current_user_traffic *= (1 + monthly_growth)
                full_year_avg_annual_charge = round(sum(monthly_charges) / 12, 2)
                annual_monthly_variable_per_user.append(full_year_avg_annual_charge)
            avg_monthly_variable_per_user = sum(annual_monthly_variable_per_user) / system_life

            backhaul_rows.append({
                "location_name": location.location_name,
                "backhaul_link_type": link,
                "backhaul_link_speed": backhaul_link_speed,
                "backhaul_link_capex": backhaul_link_capex,
                "backhaul_link_watts": backhaul_link_watts,
                "user_capacity": user_capacity,
                "backhaul_monthly_base_opex": backhaul_monthly_base_opex,
                "monthly_charges_per_user": annual_monthly_variable_per_user,
                "avg_monthly_variable_per_user": avg_monthly_variable_per_user
            })
            location_watts += backhaul_link_watts

        # For each location process power system required
        logging.info(f"Location {location} has a power system of {location.power_type} consumption of {location_watts}")

        # Power Model setup
        # region Power Model
        logging.info("Creating PowerModelInput and logging")
        power_model_input = PowerModelInput(
            location=location,
            latitude=latitude,
            longitude=longitude,
            power_required=location_watts,
            system_life=system_life,
            solar_cost_watt=solar_cost_watt,
            solar_derating=solar_derating,
            solar_efficiency=solar_efficiency,
            battery_age_derating=battery_age_derating,
            battery_cost_watt_hour=battery_cost_watt_hour,
            battery_dod=battery_dod,
            charger_inverter_base=charger_inverter_base,
            charger_inverter_variable=charger_inverter_variable,
            mains_power_cost_kwh=mains_power_cost_kwh,
            mains_power_installation_cost=mains_power_installation_cost,
            power_hybrid_hours=power_hybrid_hours,
            power_intermittent_hours=power_intermittent_hours,
            power_reliable_hours=power_reliable_hours,
            system_type=location.power_type
        )
        power_results = power_model(input_data=power_model_input)
        power_row = power_results.power_row.model_dump()
        power_row["structure_cost"] = location.tower_cost
        power_row["structure_annual_opex"] = location.tower_opex
        power_row["structure_height_m"] = location.tower_height
        power_rows.append(power_row)

        location_power_capex = power_results.power_capex
        power_capex += location_power_capex
        location_power_opex = power_results.power_opex
        power_opex += location_power_opex
        # endregion

    modeled_population = sum(
        estimate["population"] for estimate in location_population_estimates
    )
    submitted_population = input_data.total_potential_users or 0
    base_population = submitted_population or modeled_population
    total_potential_users_all_types = int(
        round(base_population * ((1 + pop_growth_rate) ** 3))
    )

    base_households = sum(
        estimate["households"]
        if estimate["households"] is not None
        else estimate["population"] / hh_size
        for estimate in location_population_estimates
    )
    households = int(round(base_households * ((1 + pop_growth_rate) ** 3)))

    # Avoid double-counting community members who receive service through a
    # business or service-provider connection.
    potential_household_users = total_potential_users_all_types - sp_users - bus_users
    if potential_household_users <= 0:
        raise HTTPException(
            status_code=422,
            detail=(
                "The modeled community cannot support the number of service "
                "providers and/or businesses entered."
            ),
        )
    logging.info(f"Potential Household Users is {potential_household_users}")

    paf_seat_demand_seats = (
        paf_use_pp * potential_household_users / paf_hours_month_seat
        if paf_use_pp > 0
        else 0
    )
    logging.info(f"demand for paf seats is {round(paf_seat_demand_seats)}")

    # Summarise Power CapEx and OpEx across all locations
    power_capex = round(power_capex, 2)
    power_opex = round(power_opex, 2)
    logging.info(f"Power CapEx is {power_capex} and OpEx is {power_opex}")

    # Deduplicate the tech_use list
    tech_use = list(set(tech_use))

    if not data_rows or not backhaul_rows:
        raise HTTPException(status_code=400, detail="No valid results")

    # Create DataFrames
    # region Builder Summary Stats
    # ldf is the per location data frame
    ldf = pd.DataFrame(data_rows)
    # mdf is the midhaul data frame, and we create a blank one if no midhaul data has been provided
    mdf = pd.DataFrame(midhaul_rows) if midhaul_rows else pd.DataFrame(
        columns=["network_link_speed", "network_link_cost", "network_link_watts"])
    # bdf is the backhaul data frame
    bdf = pd.DataFrame(backhaul_rows)
    # podf is the per location power data frame
    podf = pd.DataFrame(power_rows)

    # Logging the created data frames to check what they're producing
    logging.info(f'Technology per Location Data: \n{ldf.to_string(index=False)}')
    if not mdf.empty:
        logging.info(f'Midhaul link data table (mdf): \n{mdf.to_string(index=False)}')
    logging.info(f'Backhaul link data table (bdf): \n{bdf.to_string(index=False)}')
    if not podf.empty:
        logging.info(f'Power sizing table (podf): \n{podf.to_string(index=False)}')

    pbom_table_columns = [
        {"title": "Location", "data": "location_name"},
        {"title": "Structure Cost", "data": "structure_cost"},
        {"title": "Structure Annual OpEx", "data": "structure_annual_opex"},
        {"title": "Structure Height (m)", "data": "structure_height_m"},
        {"title": "Power Use (W)", "data": "power_required"},
        {"title": "Mains Installation", "data": "mains_power_installation_cost"},
        {"title": "Charger Cost", "data": "charger_cost"},
        {"title": "Battery Required (Wh)", "data": "battery_required"},
        {"title": "Battery Cost", "data": "battery_cost"},
        {"title": "PV Panels Needed (m2)", "data": "panels_need_m2"},
        {"title": "Solar Cost", "data": "solar_cost"},
        {"title": "Power CapEx", "data": "power_capex"},
    ]
    if not podf.empty:
        pbom_table_rows = (
            podf[
                [
                    "location_name",
                    "structure_cost",
                    "structure_annual_opex",
                    "structure_height_m",
                    "power_required",
                    "mains_power_installation_cost",
                    "charger_cost",
                    "battery_required",
                    "battery_cost",
                    "panels_need_m2",
                    "solar_cost",
                    "power_capex",
                ]
            ]
            .replace({np.nan: None})
            .to_dict(orient="records")
        )
    else:
        pbom_table_rows = []

    # Assign users to technologies
    logging.info("Assigning users to technologies...")
    logging.info(f"Total potential users: {total_potential_users_all_types}")
    ldf = assign_users(ldf, total_potential_users_all_types)

    logging.info("Assigning UE costs to the build")
    # Assign UE costs to the build
    ldf = apply_cpe_costs(ldf)

    # Debug print to see users assigned and CapEx costs with CPE included
    logging.info(f'Technologies with Users Assigned: \n{ldf.to_string(index=False)}')

    # Calculate summary metrics on coverage and users
    total_coverage_area = float(ldf.groupby('location_name')['coverage_area'].max().sum())
    total_population_covered = int(ldf.groupby('location_name')['population_covered'].max().sum().round())

    logging.info(f"PAF seats supported by the solution: {paf_seats}")
    paf_mask = ldf['network_type'].eq('Public Access Facility')
    cn_supported_users = int(ldf.loc[~paf_mask, 'users_supported'].sum().round())
    paf_supported_users = int(ldf.loc[paf_mask, 'users_supported'].sum().round())
    solution_supported_users = cn_supported_users + paf_supported_users
    if solution_supported_users < 1:
        raise ValueError("The supplied network configuration does not cover any users")
    logging.info(
        f"The solution supports {solution_supported_users} users across {len(ldf)} locations "
        f"({cn_supported_users} Community Network, {paf_supported_users} PAF)."
    )
    # Ensure total users supported doesn't exceed coverage or total potential users
    solution_supported_users = min(solution_supported_users, total_population_covered, total_potential_users_all_types)
    # PAF users are not relevant for backhaul calcs, only the number of seats in use.
    backhaul_required = int(round(user_final_year_peak_mbps * (cn_supported_users + paf_seats)))

    # Find the total power required by all access, midhaul, and backhaul equipment
    total_power_required = int((
            ldf['watts'].sum() + mdf['network_link_watts'].sum() + bdf['backhaul_link_watts'].sum()
    ).round())

    # Find CapEx costs for network elements
    total_tower_cost = sum(tower_costs)
    tower_capex = sum(tower_costs)
    access_capex = int(round(ldf['access_capex'].sum()))
    midhaul_capex = int(round(mdf['network_link_cost'].sum()))
    # Useful stats for users of the model to see what they've built
    total_midhaul_available = (mdf['network_link_speed'].sum() / 2).round() if not mdf.empty else 0
    # endregion

    # Backhaul Cost Calculations
    # region Backhaul
    # Find details of the lowest cost backhaul the user has provisioned
    lc_backhaul_row = bdf.loc[bdf["avg_monthly_variable_per_user"].idxmin()]
    lc_backhaul_type = lc_backhaul_row["backhaul_link_type"]
    lc_backhaul_user_support = lc_backhaul_row["user_capacity"]
    # Find the number of users the aggregate backhaul methods support
    bh_aggregate_users_supported = int(round(bdf['user_capacity'].sum()))
    # Check to see if backhaul is underprovisioned
    if bh_aggregate_users_supported < solution_supported_users:
        logging.info("Backhaul was underprovisioned")
        # If it's underprovisioned, find out by how much
        underprovision = solution_supported_users - bh_aggregate_users_supported
        # Find  how many new instances of the lowest cost backhaul we'd need to make up the difference
        new_bh_instances = ceil(underprovision / lc_backhaul_user_support)
        logging.info(f'{new_bh_instances} more instances of {lc_backhaul_type} will be added.')
        # Fix the underprovision by adding more instances of the lowest cost backhaul
        # First convert our lowest cost row to its own temporary data frame
        tdf = pd.DataFrame([lc_backhaul_row])
        # Then concatenate it to our backhaul data frame as many times as we need
        bdf = pd.concat([bdf] + [tdf] * new_bh_instances, ignore_index=True)
        logging.info("Backhaul data table has been updated to:")
        logging.info(f'Data table (bdf): \n {bdf.to_string(index=False)}')
        # Now find the updated number of users the aggregate backhaul methods support
        bh_aggregate_users_supported = int(round(bdf['user_capacity'].sum()))
    else:
        logging.info("Backhaul was adequtely provisioned")
    # Now we have adjusted the backhaul to support the network, find how much is available
    total_backhaul_available = int(bdf['backhaul_link_speed'].sum().round())
    # Also update the CapEx figure for backhaul in case we've added more links
    backhaul_capex = int(bdf['backhaul_link_capex'].sum().round())

    bom_table_columns = [
        {"title": "Location", "data": "location_name"},
        {"title": "Technology Type", "data": "technology_type"},
        {"title": "Technology", "data": "technology"},
        {"title": "Cost Each", "data": "cost_each"},
        {"title": "Quantity", "data": "quantity"},
        {"title": "CPE Quantity", "data": "cpe_quantity"},
        {"title": "CPE Cost", "data": "cpe_cost"},
        {"title": "Network CapEx", "data": "network_capex"},
    ]
    bom_df = build_network_bom_dataframe(ldf, mdf, bdf)
    logging.info(
        "Network equipment bill of materials (bom_df):\n%s",
        bom_df.to_string(index=False),
    )
    bom_table_rows = bom_df.replace({np.nan: None}).to_dict(orient="records")

    # Add a column to the backhaul data frame proportioning the backhaul use by its capacity
    bdf["bh_proportion"] = bdf["user_capacity"] / bh_aggregate_users_supported
    # Show us the new dataframe
    logging.info(f'Data table (bdf): \n{bdf.to_string(index=False)}')
    # Find the base OpEx of backhaul methods
    bh_aggregate_monthly_fixed = int(round(bdf['backhaul_monthly_base_opex'].sum()))
    # Calculate the weighted average monthly charge per user
    weighted_avg_bh_charge = (bdf["avg_monthly_variable_per_user"] * bdf["bh_proportion"]).sum()
    logging.info(f'Weighted average per user backhaul charge is {weighted_avg_bh_charge}.')
    # Calculate the average monthly backhaul charge by adding fixed plus variable charges
    backhaul_avg_monthly_opex = round(bh_aggregate_monthly_fixed + (weighted_avg_bh_charge * solution_supported_users), 2)
    logging.info(f'Average monthly backhaul charge is {backhaul_avg_monthly_opex}')
    # Calculate the annual weighted average monthly charge
    annual_weighted_bh_charges = []
    for i in range(system_life):
        weighted_avg = (bdf["bh_proportion"] * bdf["monthly_charges_per_user"].apply(lambda x: x[i])).sum()
        charge = round(bh_aggregate_monthly_fixed + (weighted_avg * solution_supported_users), 2)
        annual_weighted_bh_charges.append(charge)
    annual_weighted_bh_charges = [float(val) for val in annual_weighted_bh_charges]
    logging.info(f'Annual weighted backhaul charges are {annual_weighted_bh_charges}')
    # Calculate backhaul Opex
    backhaul_opex = int(round(backhaul_avg_monthly_opex * system_life * 12))
    backhaul_annual_opex = [int(round(val * 12)) for val in annual_weighted_bh_charges]

    # Backhaul cost provided by the model including CapEx, monthly fixed, and monthly variable charges
    backhaul_cost = int(round(backhaul_capex + backhaul_opex))
    # endregion

    # Entire system cost includes connectivity, power system, and backhaul

    connectivity_capex = access_capex + backhaul_capex + midhaul_capex
    system_capex = connectivity_capex + power_capex
    system_opex = backhaul_opex + power_opex

    logging.info(f"Total system CapEx is {system_capex}")
    system_cost = round((system_capex + system_opex),2)
    logging.info(f"Overall system cost before maintenance and labour is {system_cost}")

    # Network Summary Table
    # region NET SUM Table
    logging.info("Network Details Summary Table")

    net_summary_table_rows, net_summary_table_columns = get_net_summary_table(
        country_name=country_name, system_life=system_life,
        year_1_traffic=year_1_traffic, traffic_growth=traffic_growth,
        backhaul_required=backhaul_required, total_backhaul_available=total_backhaul_available,
        total_power_required=total_power_required, system_capex=system_capex,
        access_capex=access_capex, tower_capex=tower_capex, backhaul_capex=backhaul_capex,
        midhaul_capex=midhaul_capex, power_capex=power_capex
    )

    # endregion

    # Demand Modelling work

    # region demand model abbreviations
    """
    Abbreviations for Variables
    capsub = capex subsidy
    cba = Community Benefit Analysis
    cc = connectivity capex
    ccpdm = connectivity capex per decision maker
    cpdmpa = per annum capex per decision maker
    cocd = community capex discount
    cp = Corporate
    dc = demand curve
    dm = Decision Maker
    gbm = gigabytes per month
    hha = Households above median income
    hhb = Households below median income
    hdm = household decision makers
    inf = inflation
    mcec = Monthly CapEx Economic Cost (including power and after subsidy)
    ndm = number of decision makers
    pa = per annum
    paf = public access facilities
    pr = penetration rate
    ps = power system
    sp = Service Provider
    y3gb = year 3 gigabytes per month
    """
    # endregion

    # Variable Assignments
    # region CBA Variables
    # Imports from the User Interface
    # Calculate CapEx Subsidy as a percentage of total build cost
    capex_cash_subsidy = input_data.capex_subsidy
    capsub = min(capex_cash_subsidy / system_capex, 1.0)  # User Interface C20
    logging.info(f"CapEx Cash Subsidy: {capex_cash_subsidy}")
    logging.info(f"System CapEx: {system_capex}")
    logging.info(f"capsub percent: {capsub}")
    opsub = input_data.opex_subsidy / 100
    maint_opex = input_data.maintenance_opex / 100  # User Interface C27
    opex_ftes_fixed = input_data.staff_opex_fixed  # User Interface C31
    opex_ftes_variable = input_data.staff_opex_variable  # User Interface C31
    opex_other = input_data.other_opex / 100  # User Interface C33
    debt_amount = max(system_capex - capex_cash_subsidy, 0)
    debt_prop = debt_amount / system_capex if system_capex > 0 else 0
    fin_cos = input_data.finance_cost / 100  # Interest Rate or Finance Cost User Interface C34
    tax_rate = input_data.corp_tax / 100  # Corporate tax rate User Interface C36
    oc_margin = input_data.oc_margin / 100 # Margin on Operating Cost User Interface C37
    hh_income_week = input_data.hh_income_week
    spectrum_fee = input_data.spectrum_licence_fee
    ue_subsidy = input_data.ue_subsidy / 100
    ue_cost = input_data.ue_cost
    ue_exist_hha = input_data.existing_ue_above_med / 100
    ue_exist_hhb = input_data.existing_ue_below_med / 100
    # endregion

    # Demand Curve
    # region DC

    # Demand Curve Parameters
    # Add a function here later to get different curve parameters from the db based on the model required
    # In the db these parameters exist as model=default, parameters a, b, and c.
    dc_parameter_a = 0.0335842563942767  # Demand Modelling B27
    dc_parameter_b = 0.0158100053635772  # Demand Modelling B28
    dc_parameter_c = 0.000001  # Demand Modelling B29
    # Create Demand Curve Points for rendering as a table
    dc_points = get_dc_points(dc_parameter_a, dc_parameter_b)
    # endregion

    # Public Access Facilities Calculations
    # region PAF

    # Determine if this is a PAF only model by examining the list of technologies in use
    paf_only = (len(tech_use) == 1 and tech_use[0] == "PAF")
    paf_present = "PAF" in tech_use

    if paf_present:

        # Terminals / Proportion of Users (b64)
        seats_users_ratio = paf_seats / potential_household_users
        logging.info(f"Seats to Users Ratio: {seats_users_ratio}")

        # Percentage of non-subscribers who might use PAF (B50)
        paf_non_sub_pct = min(-0.097 * seats_users_ratio ** 3 + 1.6 * seats_users_ratio ** 2 - 0.6 * seats_users_ratio + 0.45, 0.70)
        logging.info(f"Pct of non-subscribers using paf: {paf_non_sub_pct}")

        # Percent of subscribers who might use PAF (B49)
        paf_sub_pct = paf_non_sub_pct / 2
        logging.info(f"Pct of subscribers using paf: {paf_sub_pct}")

        # Percentage of Deterred users who might use PAF (B51)
        paf_deterred_pct = min(paf_non_sub_pct * 2, 1.00)
        logging.info(f"Pct of deterred using paf: {paf_deterred_pct}")

    else:
        # Imports from the User Interface
        paf_sub_use = 0
        paf_non_sub_use = 0
        paf_deterred_use = 0
        paf_gb_hour = 0
        paf_usd_hour = 0
        seats_users = 0
        paf_non_sub_pct = 0
        paf_sub_pct = 0
        paf_deterred_pct = 0

    if paf_only:
        paf_deterred_use = 0
        paf_sub_use = 0


    # endregion

    # Find the Connectivity CapEx
    # region Connectivity CapEx
    cc = connectivity_capex
    # Get the Community CapEx discount from user input
    cocd = float(input_data.community_capex_discount) / 100  # User interface C38
    # Get the WACC from interface input
    # Weighted Average Cost of Capital
    wacc = float(input_data.wacc) / 100  # User interface C34
    # Get the inflation rate from user input
    inf = float(input_data.inflation) / 100  # User interface C28
    # Calculate the construction spend for BPO
    cons_spd = (system_capex * (1 - cocd)) / 1_000_000
    # Determine the real interest rate
    rate = (1 + wacc) / (1 + inf) - 1
    # endregion


    # Characteristics of Service and Community Benefit Analysis Calculations CBA General Demand Modelling B7-B10
    # region CBA GENERAL
    # Number of decision makers is the sum of service providers, businesses, and household decision makers
    # logging.info("Region CBA General")
    # logging.info("Limiting number of decision makers based on coverage provided")
    # logging.info(f"Total number of users supported by the system is {solution_supported_users}")
    # logging.info(f"Unadjusted households is {households} and size is {hh_size}")
    # logging.info(f"Unadjusted number of service providers proposed is {service_providers} with {sp_users_avg}")
    # logging.info(f"Unadjusted number of businesses is {businesses} with {bus_users_avg} users each")
    # logging.info(f"Unadjusted Business users are {bus_users} and total users are {total_potential_users_all_types}")

    # Priority 1: Service Provider Users
    # sp_users are first in line. We take the minimum of total supported or total SP users.
    logging.info(f"The network solution excluding PAF supports {cn_supported_users} users")
    supported_sp_users = min(cn_supported_users, sp_users)
    logging.info(f"Supported Service Provider Users is {supported_sp_users}")
    if supported_sp_users == 0:
        supported_service_providers = 0
    else:
        supported_service_providers = math.floor(supported_sp_users/sp_users_avg)
    sp_users = supported_sp_users
    logging.info(f"Adjusted Supported Service Providers is {supported_service_providers}")
    logging.info(f"Adjusted Service Provider users is {sp_users}")

    # Remaining capacity for Business and Household users
    remaining_capacity = cn_supported_users - supported_sp_users
    logging.info(f"Remaining Capacity after assigning Service Provider Users is {remaining_capacity}")

    # Priority 2: Business Users
    # bus_users are second in line. We take the minimum of total supported or total BUS users.

    if remaining_capacity > 0 and (bus_users + potential_household_users) > 0:
        supported_bus_users = min(remaining_capacity,bus_users)
        logging.info(f"Supported Business Users is {supported_bus_users}")
        remaining_capacity = remaining_capacity - supported_bus_users
        logging.info(f"Remaining Capacity after assigning Business Users is {remaining_capacity}")
        supported_household_users = remaining_capacity
        # logging.info(f"Adjusted household users is {supported_household_users}")

    else:
        logging.info("No capacity was left or no users were available, zeroing out household and business users ")
        supported_bus_users = 0
        supported_household_users = 0
    bus_users = supported_bus_users

    # Divide supported_household_users by users per household to get
    supported_households = min(math.floor(supported_household_users/hh_size), households)
    hdm = supported_households
    logging.info(f"Adjusted household decision makers is {hdm}")
    # Households above median
    hha = hdm // 2
    # Households below median
    hhb = hha

    # Divide supported_bus_users by number of businesses to get bdm
    if supported_bus_users == 0:
        supported_businesses = 0
    else:
        supported_businesses = math.floor(supported_bus_users/bus_users_avg)

    # logging.info(f"Adjusted businesses decision makers is {supported_businesses}")

    ndm = supported_service_providers + supported_businesses + supported_households  # Demand Modelling B20
    logging.info(f"Number of decision makers is {ndm}")

    # Connectivity capex per decision maker (Demand Modelling B7)
    ccpdm = cc * (1 - cocd) / ndm
    # Solution capex per decision maker (Demand Modelling B7)
    scpdm = system_capex * (1 - cocd) / ndm

    # Connectivity capex per annum per decision maker (Demand Modelling B8)
    pa_capex_per_decision_maker = (ccpdm * rate / (1 - (1 + rate) ** -system_life))

    # Power system capex per annum per decision maker (Demand Modelling B9)
    pa_ps_capex_per_decision_maker = npf.pmt(((1 + wacc)/(1 + inf)-1), system_life, (-power_capex/ndm*0.8))

    # (Demand Modelling O36)
    logging.info(f"CapEx including Power: {system_capex}")
    logging.info(f"rate: {rate}")
    logging.info(f"system_life: {system_life}")
    o36 = (system_capex * rate / (1 - (1 + rate) ** -system_life))

    # endregion

    # logging.info(f'CBA General Complete')
    # Year three Demand and CBA Assessment

    # Number of decision makers for the CBA model ndm (Demand Modelling B14-B20)
    # region CBA NDM
    # logging.info("Region CBA NDM")
    cba_ndm_oo = ndm  # Demand Modelling B20
    cba_ndm_sp = supported_service_providers  # Demand Modelling B14
    cba_ndm_bus = supported_businesses  # Demand Modelling B15
    cba_ndm_hha = hha  # Demand Modelling B16
    cba_ndm_hhb = hhb  # Demand Modelling B17
    # endregion
    logging.info(f'CBA SP: {cba_ndm_sp}, BUS: {cba_ndm_bus}, HHA: {cba_ndm_hha}, HHB: {cba_ndm_hhb} ')

    # Number of users for the CBA model nu (Demand Modelling C14-C20)
    # region CBA NU
    cba_nu_sp = sp_users  # Demand Modelling C14
    cba_nu_bus = bus_users  # Demand Modelling C15
    cba_nu_hha = cba_ndm_hha * hh_size  # Demand Modelling C16
    cba_nu_hhb = cba_ndm_hhb * hh_size  # Demand Modelling C17
    cba_nu_sub = cba_nu_sp + cba_nu_bus + cba_nu_hha + cba_nu_hhb  # Demand Modelling C18
    cba_nu_oo = cba_nu_sub
    # endregion
    logging.info(f'CBA NU Complete')

    # Total GB per month for the CBA Model gbm (Demand Modelling D14-D18)
    # region CBA GBM
    # Year 3 monthly traffic per user in GB
    y3gb = (year_1_traffic * (1 + traffic_growth_pct) ** 3)
    cba_gbm_sp = cba_nu_sp * y3gb  # Demand Modelling D14
    cba_gbm_bus = cba_nu_bus * y3gb  # Demand Modelling D15
    cba_gbm_hha = cba_nu_hha * y3gb  # Demand Modelling D16
    cba_gbm_hhb = cba_nu_hhb * y3gb  # Demand Modelling D17
    cba_gbm_sub = cba_gbm_sp + cba_gbm_bus + cba_gbm_hha + cba_gbm_hhb  # Demand Modelling D18
    # endregion
    # logging.info(f'CBA GBM Complete')

    # Operating cost, Charging Base occb (Demand Modelling P26-Q33)
    # region CBA OCCB
    # A set of costs per decision maker
    monthly_rate = wacc / 12
    months = system_life * 12
    inflation_adjustment = (1 + inf) ** 3

    # Maintenance Cost Monthly occb_maint_cost_m (Demand Modelling P26)
    occb_maint_cost_m = (pa_capex_per_decision_maker + pa_ps_capex_per_decision_maker) * maint_opex / 12
    # Maintenance Cost Annual occb_maint_cost_a (Demand Modelling Q26)
    occb_maint_cost_a = occb_maint_cost_m * 12
    # Fixed Labour Monthly occb_labour_fixed_m (Demand Modelling P27)
    occb_labour_fixed_m = (opex_ftes_fixed * labour_monthly) / cba_ndm_oo
    # Fixed Labour Annual occb_labour_fixed_a (Demand Modelling Q27)
    occb_labour_fixed_a = occb_labour_fixed_m * 12
    # Variable Labour Monthly occb_labour_var_m (Demand Modelling P28)
    # Monthly variable labour cost per decision maker based on FTEs per 100 users
    occb_labour_var_m = ((cba_nu_sub / 100) * opex_ftes_variable * labour_monthly) / ndm
    # Variable Labour Annual occb_labour_var_a (Demand Modelling Q28)
    occb_labour_var_a = occb_labour_var_m * 12
    # Other OCCB Monthly occb_other_m (Demand Modelling P29)
    # Office costs and other overheads, a percent of fixed and variable labour charges
    occb_other_m = (occb_labour_fixed_m + occb_labour_var_m) * opex_other
    # Other OCCB Annual occb_other_a (Demand Modelling Q29)
    occb_other_a = occb_other_m * 12
    # Spectrum OCCB Monthly occb_spectrum_m (Demand Modelling P30)
    monthly_payment = npf.pmt(monthly_rate, months, - spectrum_fee)
    occb_spectrum_m = monthly_payment / ndm
    # Spectrum OCCB Annual occb_spectrum_a (Demand Modelling Q30)
    occb_spectrum_a = occb_spectrum_m * 12
    # Backhaul OCCB Monthly occb_backhaul_m (Demand Modelling P31)
    # =PMT('User interface'!$C$35/12,system_life*12,-Builder_results_api!B8)*(1+'User interface'!C28)^3/$B$18
    # pmt(wacc/12, months, -backhaul_opex) * (1 +
    monthly_payment = npf.pmt(monthly_rate, months, -backhaul_opex)
    occb_backhaul_m = monthly_payment * ((inflation_adjustment) / ndm)
    # logging.info("occb_backhaul debug:")
    # logging.info(f"wacc: {wacc}")
    # logging.info(f"backhaul_opex: {backhaul_opex}")
    # logging.info(f"monthly_payment: {monthly_payment}")

    # Backhaul OCCB Annual occb_backhaul_m (Demand Modelling Q31)
    occb_backhaul_a = occb_backhaul_m * 12
    # Power OCCB Monthly occb_power_m (Demand Modelling P32)
    monthly_payment = npf.pmt(monthly_rate, months, -power_opex)
    occb_power_m = (monthly_payment * (1 + inf) ** 3) / ndm
    # Power OCCB Annual occb_power_a (Demand Modelling Q32)
    occb_power_a = occb_power_m * 12
    # OCCB Monthly (Demand Modelling P33)
    # Total Monthly Operating Cost per Decision Maker
    occb_total_m = (
            occb_maint_cost_m +
            occb_labour_fixed_m +
            occb_labour_var_m +
            occb_other_m +
            occb_spectrum_m +
            occb_backhaul_m +
            occb_power_m
    )
    # logging.info(f"occb_maint_cost_m: {occb_maint_cost_m}")
    # logging.info(f"occb_labour_fixed_m: {occb_labour_fixed_m}")
    # logging.info(f"occb_labour_var_m: {occb_labour_var_m}")
    # logging.info(f"occb_other_m: {occb_other_m}")
    # logging.info(f"occb_spectrum_m: {occb_spectrum_m}")
    # logging.info(f"occb_backhaul_m: {occb_backhaul_m}")
    # logging.info(f"occb_power_m: {occb_power_m}")

    # OCCB Annual (Demand Modelling Q33)
    occb_total_a = occb_total_m * 12
    # endregion
    # logging.info(f'CBA OCCB Complete')

    # Montly Operating Economic Cost
    # region CBA MOEC
    # logging.info("==== Calculating CBA MOEC ====")

    # Overall MOEC cba_moec_oo (Demand Modelling F20)
    # logging.info(f"paf_only: {paf_only}")
    # logging.info(f"o36: {o36}")
    # logging.info(f"occb_total_m: {occb_total_m}")
    # logging.info(f"opsub: {opsub}")
    # logging.info(f"inf: {inf}")

    if paf_only:
        cba_mcec_paf = o36 / 12
        # logging.info(f"cba_mcec_paf (copied from E19): {cba_mcec_paf}")
        cba_moec_oo = cba_mcec_paf * 0.2
        # logging.info(f"cba_moec_oo (PAF only): {cba_moec_oo}")
    else:
        cba_moec_oo = occb_total_m * (1 - opsub) * (1 + oc_margin)
        # logging.info(f"cba_moec_oo (full calc): {cba_moec_oo}")

    # SP MOEC (F14)
    # logging.info(f"service_providers: {service_providers}")
    if service_providers == 0:
        cba_moec_sp = 0
        # logging.info("No SPs: cba_moec_sp = 0")
    else:
        cba_moec_sp = cba_moec_oo * 2
        # logging.info(f"cba_moec_sp: {cba_moec_sp}")

    # Business MOEC (F15)
    # logging.info(f"businesses: {businesses}")
    if businesses == 0:
        cba_moec_bus = 0
        # logging.info("No businesses: cba_moec_bus = 0")
    else:
        cba_moec_bus = cba_moec_oo * 1.5
        # logging.info(f"cba_moec_bus: {cba_moec_bus}")

    # HHA MOEC (F16)
    if hha == 0:
        cba_moec_hha = 0
        # logging.info("No HHA: cba_moec_hha = 0")
    else:
        # logging.info(f"cba_moec_oo: {cba_moec_oo}, ndm: {ndm}")
        # logging.info(f"cba_ndm_sp: {cba_ndm_sp}, cba_moec_sp: {cba_moec_sp}")
        # logging.info(f"cba_ndm_bus: {cba_ndm_bus}, cba_moec_bus: {cba_moec_bus}")
        # logging.info(f"hha: {hha}, hhb: {hhb}")

        numerator = cba_moec_oo * ndm - (cba_ndm_sp * cba_moec_sp - cba_ndm_bus * cba_moec_bus)
        denominator = cba_ndm_hha + cba_ndm_hhb

        # logging.info(f"numerator: {numerator}")
        # logging.info(f"denominator: {denominator}")

        cba_moec_hha = numerator / denominator
        # logging.info(f"cba_moec_hha: {cba_moec_hha}")

    # HHB MOEC (F17)
    cba_moec_hhb = cba_moec_hha
    # logging.info(f"cba_moec_hhb (same as HHA): {cba_moec_hhb}")

    # Blended MOEC (F18)
    # logging.info(f"ndm: {ndm}")
    if ndm == 0:
        cba_moec_sub = 0
        # logging.info("No DMs: cba_moec_sub = 0")
    else:
        # Average monthly economic cost per decision maker
        cba_moec_sub = (((cba_moec_sp * cba_ndm_sp) + (cba_moec_bus * cba_ndm_bus) + (cba_moec_hha * cba_ndm_hha) + (
                    cba_moec_hhb * cba_ndm_hhb)) / (cba_ndm_sp + cba_ndm_bus + cba_ndm_hha + cba_ndm_hhb))

    # logging.info("==== CBA MOEC Complete ====")
    # endregion

    # Penetration Rate cba_pen (Demand Modelling I14-I18)
    # region CBA PEN
    # Model of declining adoption as service becomes less affordable or less accessible due to PAF crowding

    # Service Providers Penetration cba_pen_sp (Demand Modelling I14)
    if paf_only:
        cba_pen_sp = 0
    else:
        cba_pen_sp = 1
    # logging.info(f'CBA Penetration Rate SP Complete')

    # Households Above Median Penetration cba_pen_hha (Demand Modelling I16)
    # Business Penetration cba_pen_bus (Demand Modelling I15)
    # Includes cost as a proportion of income, a crowding factor for PFAS, and demand curve parameters
    # =IF('User interface'!C64="Yes",0,MIN(EXP((H16/('User interface'!C10*4*1.5*IF(users_public_facility=0,1,MAX(EXP(-0.004*users_public_facility),0.7)))-B$27)/(-B$28)),0.95))

    # logging.info("==== Calculating cba_pen_hha ====")
    # logging.info(f"paf_only: {paf_only}")
    # logging.info(f"paf_seats: {paf_seats}")
    # logging.info(f"hh_income_week: {hh_income_week}")
    # logging.info(f"cba_moec_hha: {cba_moec_hha}")
    # logging.info(f"dc_parameter_a: {dc_parameter_a}")
    # logging.info(f"dc_parameter_b: {dc_parameter_b}")

    if paf_only:
        cba_pen_hha = 0
        cba_pen_bus = 0
        # logging.info("PAF only connectivity: setting cba_pen_hha and cba_bus_hha = 0")
    else:
        if paf_seats == 0:
            crowding_factor = 1
        else:
            crowding_factor = max(math.exp(-0.004 * paf_seats), 0.7)

        # logging.info(f"Crowding factor: {crowding_factor}")

        affordability_denom = hh_income_week * 4 * 1.5 * crowding_factor
        # logging.info(f"Affordability denominator: {affordability_denom}")

        hha_adoption_score = (cba_moec_hha / affordability_denom - dc_parameter_a) / -dc_parameter_b
        # logging.info(f"Adoption score hha (raw): {hha_adoption_score}")

        bus_adoption_score = (cba_moec_bus / affordability_denom - dc_parameter_a) / -dc_parameter_b
        # logging.info(f"Adoption score Business (raw): {bus_adoption_score}")

        # Avoid math range errors
        MAX_EXP_INPUT = 700
        hha_safe_score = min(hha_adoption_score, MAX_EXP_INPUT)
        bus_safe_score = min(bus_adoption_score, MAX_EXP_INPUT)
        # logging.info(f"Adoption score (capped to safe max): {hha_safe_score}")
        # logging.info(f"Adoption score (capped to safe max): {bus_safe_score}")

        hha_exp_result = math.exp(hha_safe_score)
        # logging.info(f"exp(adoption_score): {hha_exp_result}")
        bus_exp_result = math.exp(bus_safe_score)
        # logging.info(f"exp(adoption_score): {bus_exp_result}")

        cba_pen_hha = min(hha_exp_result, 0.95)
        # logging.info(f"Final cba_pen_hha: {cba_pen_hha}")
        cba_pen_bus = min(bus_exp_result, 0.95)
        # logging.info(f"Final cba_pen_bus: {cba_pen_bus}")


    # logging.info(f'CBA Penetration Rate hha and Bus Complete')

    # Households Below Median Penetration cba_pen_hhb (Demand Modelling I17)
    # Includes cost as a proportion of income, a crowding factor for PFAS, and demand curve parameters
    # Compared to HHA, has a lower income allocation multiplier, tighter crowding penalty, different cost input
    # logging.info("==== Calculating cba_pen_hhb ====")
    # logging.info(f"paf_only: {paf_only}")
    # logging.info(f"paf_seats: {paf_seats}")
    # logging.info(f"hh_income_week: {hh_income_week}")
    # logging.info(f"cba_moec_hhb: {cba_moec_hhb}")
    # logging.info(f"dc_parameter_a: {dc_parameter_a}")
    # logging.info(f"dc_parameter_b: {dc_parameter_b}")
    if paf_only:
        cba_pen_hhb = 0
    else:
        if paf_seats == 0:
            crowding_factor = 1
        else:
            crowding_factor = max(math.exp(-0.006 * paf_seats), 0.6)

        # logging.info(f"Crowding factor hha: {crowding_factor}")

        affordability_denom = hh_income_week * 4 * 0.75 * crowding_factor
        # logging.info(f"Affordability denominator: {affordability_denom}")
        adoption_score = (cba_moec_hhb / affordability_denom - dc_parameter_a) / -dc_parameter_b
        # logging.info(f"Adoption score (capped to safe max): {safe_score}")

        cba_pen_hhb = min(math.exp(adoption_score), 0.95)
        # logging.info(f"Final cba_pen_hha: {cba_pen_hha}")

    # logging.info(f'CBA Penetration Rate HHB Complete')

    # Penetration Subtotal cba_pen_sub (Demand Modelling I18)
    # Blended adoption rate across all decision maker groups with weightings

    if paf_only:
        cba_pen_sub = 0
    else:
        cba_pen_wt_sp = cba_pen_sp * cba_ndm_sp
        cba_pen_wt_bus = cba_pen_bus * cba_ndm_bus
        cba_pen_wt_hha = cba_pen_hha * cba_ndm_hha
        cba_pen_wt_hhb = cba_pen_hhb * cba_ndm_hhb
        # logging.info(
        #     f"Weighted CBA values: cba_pen_wt_sp = {cba_pen_wt_sp:.4f}, cba_pen_wt_bus = {cba_pen_wt_bus:.4f}, "
        #     f"cba_pen_wt_hha = {cba_pen_wt_hha:.4f}, cba_pen_wt_hhb = {cba_pen_wt_hhb:.4f}"
        # )

        total_weighted_penetration = (
                cba_pen_wt_sp + cba_pen_wt_bus + cba_pen_wt_hha + cba_pen_wt_hhb
        )
        total_weight = cba_ndm_sp + cba_ndm_bus + cba_ndm_hha + cba_ndm_hhb
        cba_pen_sub = total_weighted_penetration / total_weight
        # logging.info(f'total weighted pen: {total_weighted_penetration}, ndm: {ndm}')
    # endregion

    # Monthly capex economic cost per decision maker mcec (Demand Modelling E14-E20)
    # region CBA MCEC
    # A monthly equivalent of annualised CAPEX including power capex and after subsidy
    # discounted to reflect delayed or deferred benefits (3-year delay)

    # Overall MCEC cba_mcec_oo (Demand Modelling E20)
    if paf_only:
        cba_mcec_oo = o36  # from E19
    else:
        annualised_total_capex = pa_capex_per_decision_maker + pa_ps_capex_per_decision_maker
        discounted = (annualised_total_capex / 12) / ((1 + inf) ** 3)
        cba_mcec_oo = discounted * (1 - capsub)

    # Service Providers MCEC cba_mcec_sp (Demand Modelling E14)
    """
    In contract negotiations, while there are more users within in a service provider, they are only using it for work purposes etc and a such there is just a negotiated outcome that decision makers will be prepared to pay more than an average household, but not significantly more – it is just an assumption of double based on the fact that it is more mission critical and there are multiple users).  Similar for corporate users it is 1.5 times. It is a simple approach but there is no real basis for complicating and already complicated model further in the opinion of economist Barry Burgan
    """
    if service_providers == 0:
        cba_mcec_sp = 0
    else:
        cba_mcec_sp = cba_mcec_oo * 2

    # Business MCEC cba_mcec_bus (Demand Modelling E15)

    if businesses == 0:
        cba_mcec_bus = 0
    else:
        cba_mcec_bus = cba_mcec_oo * 1.5

    # Household Above Median MCEC cba_mcec_hha (Demand Modelling E16)
    # Residual monthly capex economic cost per decision maker for Households above the median
    # After accounting for other groups' benefits and shared infrastructure costs.

    if hha == 0 or paf_only:
        cba_mcec_hha = 0
    else:
        total_value = cba_mcec_oo * ndm
        shared_paf_cost = pa_capex_per_decision_maker + pa_ps_capex_per_decision_maker
        shared_paf_cost = shared_paf_cost * 0.5 * paf_seats / system_life
        opportunity_cost = cba_ndm_sp * cba_mcec_sp - cba_ndm_bus * cba_mcec_bus
        cba_mcec_hha = (total_value - shared_paf_cost - opportunity_cost) / (hha + hhb)

    # Household Below Median MCEC cba_mcec_hhb (Demand Modelling E17)
    # Average monthly capex economic cost per decision maker, weighted across all user groups
    # Essentially a blended MCEC

    cba_mcec_hhb = cba_mcec_hha

    # Sub-total MCEC cba_mcec_sub (Demand Modelling E18)

    if ndm == 0:
        cba_mcec_sub = 0
    else:
        weighted_sum = (
                cba_ndm_sp * cba_mcec_sp +
                cba_ndm_bus * cba_mcec_bus +
                hha * cba_mcec_hha +
                hhb * cba_mcec_hhb
        )
        cba_mcec_sub = weighted_sum / ndm

    # PAF MCEC cba_mcec_paf (Demand Modelling E19)
    # logging.info(f'Entering PAF MCEC Demand Modelling E19')

    # X26–X29: Penetration inputs
    cvac_a_pen = 1
    cvac_hha_pen = min(math.exp((cba_moec_hha / (hh_income_week * 4 * 1.5) - dc_parameter_a) / -dc_parameter_b),
                       0.95)  # X28
    cvac_hhb_pen = min(math.exp((cba_moec_hhb / (hh_income_week * 4 * 0.75) - dc_parameter_a) / -dc_parameter_b),
                       0.95)  # x29

    # Additional PAF calculations
    # region ADDITIONAL PAF

    community_network_available = (not paf_only) and cn_supported_users > 0

    # Reduced Contracted Users (paf_deterred) (B43)
    if community_network_available:
        base_demand = hha * cba_pen_hha + hhb * cba_pen_hhb
        adjusted_demand = hha * cvac_hha_pen + hhb * cvac_hhb_pen
        paf_deterred_users = max(base_demand - adjusted_demand, 0)
    else:
        paf_deterred_users = 0

    # Remaining Contracted Users (paf_sub_users) (B44)
    # Weighted sum of adoption probabilities * number of users in each group
    paf_sub_users = hha * cvac_hha_pen + hhb * cvac_hhb_pen if community_network_available else 0

    # Non Contracted persons (paf_non_sub_users) (B45)
    # The overall number of users minus Deterred and Contracted Users
    paf_non_sub_users = max(potential_household_users - paf_deterred_users - paf_sub_users, 0)

    # PAF monthly capacity hours (B61)
    paf_monthly_capacity = paf_seats * paf_hours_month_seat

    deterred_hours_per_user = paf_deterred_pct * paf_deterred_use
    sub_hours_per_user = paf_sub_pct * paf_sub_use
    non_sub_hours_per_user = paf_non_sub_pct * paf_non_sub_use

    requested_paf_monthly_use = (
        paf_deterred_users * deterred_hours_per_user +
        paf_sub_users * sub_hours_per_user +
        paf_non_sub_users * non_sub_hours_per_user
    )

    if requested_paf_monthly_use > 0 and paf_monthly_capacity >= 0:
        paf_capacity_scale = min(paf_monthly_capacity / requested_paf_monthly_use, 1)
    else:
        paf_capacity_scale = 0 if paf_monthly_capacity <= 0 else 1

    paf_deterred_users *= paf_capacity_scale
    paf_sub_users *= paf_capacity_scale
    paf_non_sub_users *= paf_capacity_scale

    # PAF Non Contracted Users (B48)
    paf_noncon_users = paf_non_sub_users * paf_non_sub_pct + paf_deterred_users
    logging.info(f"Actual users of the PAF {paf_noncon_users}")

    # PAF use in Hours Subscribers (Subscriber Use) (B56)
    paf_sub_hours = paf_sub_users * sub_hours_per_user

    # PAF use in Hours Non-Subscribers (Non Subscriber Use) (B57)
    paf_non_sub_hours = paf_non_sub_users * non_sub_hours_per_user

    # PAF use in Hours Deferred Users (Deferred User Use) (B58)
    paf_deterred_hours = paf_deterred_users * deterred_hours_per_user

    # PAF use per month (B59)
    paf_monthly_use = paf_sub_hours + paf_non_sub_hours + paf_deterred_hours

    # Congestion Rate (B62)
    paf_congest_rate = False
    if paf_present and paf_monthly_capacity > 0:
        paf_congest_rate = paf_monthly_use / paf_monthly_capacity

    # PAF Annual Revenue (B46)
    paf_revenue = paf_hours_month_seat * paf_seats * paf_usd_hour * 12
    # PAF Margin compared to Internet Provider (B47)
    paf_margin = 0.5

    if paf_only:
        cba_mcec_paf = o36 / 12  # full annual connectivity capex divided monthly
    elif paf_seats == 0:
        cba_mcec_paf = 0
    else:
        revenue_per_seat_per_month = (paf_revenue / 12) * paf_margin / paf_seats
        public_share = cba_mcec_oo / (cba_moec_oo + cba_mcec_oo)
        cba_mcec_paf = revenue_per_seat_per_month * public_share
    # endregion

    # region Additional PAF
    # PAF MOEC (F19)
    logging.info("Entering PAF MOEC")
    if paf_only:
        cba_moec_paf = cba_mcec_paf * 0.2
    else:
        if paf_seats == 0:
            cba_moec_paf = 0
        else:
            base_value = (paf_revenue / 12 * paf_margin) / paf_seats
            scaling_factor = cba_moec_oo / (cba_moec_oo + cba_mcec_oo)
            cba_moec_paf = base_value * scaling_factor
    # endregion

    # Other monthly spend per decision maker omsdm (Demand Modelling G14-G20)
    # region CBA OMSDM

    # Other monthly spend per pervice provider omsdm_sp (Demand Modelling G14)
    # Monthly amortised cost of purchasing mobile devices for all users supported by service providers,
    # then distributes that cost across the number of SP decision makers.
    if cba_ndm_sp == 0:
        cba_omsdm_sp = 0
    else:
        total_ue_cost = cba_nu_sp * ue_cost
        monthly_payment = npf.pmt(wacc / 12, system_life * 12, -total_ue_cost)
        cba_omsdm_sp = (monthly_payment / cba_ndm_sp) * (1 - ue_subsidy)

    # logging.info(f"cba_ndm_sp: {cba_ndm_sp}")
    # logging.info(f"cba_nu_sp: {cba_nu_sp}")
    # logging.info(f"total_ue_cost: {total_ue_cost}")
    # logging.info(f"monthly_payment: {monthly_payment}")
    # logging.info(f"cba_omsdm_sp: {cba_omsdm_sp}")

    # Other monthly spend per service business omsdm_sp (Demand Modelling G15
    # Monthly amortised cost of purchasing mobile devices for all users supported by businesses
    # then distributes that cost across the number of business decision makers.
    if cba_ndm_bus == 0:
        cba_omsdm_bus = 0
    else:
        total_ue_cost = cba_nu_bus * ue_cost
        monthly_payment = npf.pmt(wacc / 12, system_life * 12, -total_ue_cost)
        cba_omsdm_bus = (monthly_payment / cba_ndm_bus) * (1 - ue_subsidy)

    # logging.info(f"cba_ndm_bus: {cba_ndm_bus}")
    # logging.info(f"cba_nu_bus: {cba_nu_bus}")
    # logging.info(f"total_ue_cost: {total_ue_cost}")
    # logging.info(f"monthly_payment: {monthly_payment}")
    # logging.info(f"cba_omsdm_bus: {cba_omsdm_bus}")

    # Other monthly cost per Household omsdm_hha (Demand Modelling G16)
    # Monthly device cost for household group A
    if hha == 0:
        cba_omsdm_hha = 0
    else:
        total_ue_cost = cba_nu_hha * ue_cost
        monthly_payment = npf.pmt(wacc / 12, system_life * 12, -total_ue_cost)
        cba_omsdm_hha = (monthly_payment / hha) * (1 - ue_exist_hha) * (1 - ue_subsidy)

    # logging.info(f"cba_ndm_hha: {cba_ndm_hha}")
    # logging.info(f"cba_nu_hha: {cba_nu_hha}")
    # logging.info(f"total_ue_cost: {total_ue_cost}")
    # logging.info(f"wacc: {wacc}")
    # logging.info(f"system_life: {system_life}")
    # logging.info(f"hha: {hha}")
    # logging.info(f"ue_exist_hha: {ue_exist_hha}")
    # logging.info(f"ue_subsidy: {ue_subsidy}")
    # logging.info(f"monthly_payment: {monthly_payment}")
    # logging.info(f"cba_omsdm_hha: {cba_omsdm_hha}")

    # Other monthly cost per Household omsdm_hhb (Demand Modelling G17)
    # Monthly device cost for household group B
    if hhb == 0:
        cba_omsdm_hhb = 0
    else:
        total_ue_cost = cba_nu_hhb * ue_cost
        monthly_payment = npf.pmt(wacc / 12, system_life * 12, -total_ue_cost)
        cba_omsdm_hhb = (monthly_payment / hhb) * (1 - ue_exist_hhb) * (1 - ue_subsidy)

    # logging.info(f"cba_ndm_hhb: {cba_ndm_hhb}")
    # logging.info(f"cba_nu_hhb: {cba_nu_hhb}")
    # logging.info(f"total_ue_cost: {total_ue_cost}")
    # logging.info(f"monthly_payment: {monthly_payment}")
    # logging.info(f"cba_omsdm_hhb: {cba_omsdm_hhb}")

    # Other monthly cost per Service Provider Decision Maker Subtotal cba_omsdm_sub (Demand Modelling G18)
    # Weighted average of monthly mobile device costs across all decision maker groups
    if cba_ndm_sp == 0:
        cba_omsdm_sub = 0
    else:
        total_weighted_cost = (
                cba_omsdm_sp * cba_ndm_sp +
                cba_omsdm_bus * cba_ndm_bus +
                cba_omsdm_hha * hha +
                cba_omsdm_hhb * hhb
        )
        cba_omsdm_sub = total_weighted_cost / ndm
    logging.info(f"cba_omsdm_sub: {cba_omsdm_sub}")

    # Other monthly cost per PAF decision maker cba_omsdm_sub (Demand Modelling G19)

    total_equipment_cost = paf_seats * paf_seat_cost
    annual_payment = npf.pmt(wacc, system_life, -total_equipment_cost)
    cba_omsdm_paf = annual_payment / 12
    logging.info(f"cba_omsdm_paf: {cba_omsdm_paf}")

    # endregion

    # Total system economic cost per month per decision maker tsec (Demand Modelling H14-H19)
    # region CBA TSEC
    cba_tsec_sp = cba_mcec_sp + cba_moec_sp + cba_omsdm_sp
    cba_tsec_bus = cba_mcec_bus + cba_moec_bus + cba_omsdm_bus
    cba_tsec_hha = cba_mcec_hha + cba_moec_hha + cba_omsdm_hha
    cba_tsec_hhb = cba_mcec_hhb + cba_moec_hhb + cba_omsdm_hhb
    cba_tsec_sub = cba_mcec_sub + cba_moec_sub + cba_omsdm_sub
    cba_tsec_paf = cba_mcec_paf + cba_omsdm_paf
    # endregion
    # logging.info(f'CBA TSEC Complete')

    # Calculation Variables for Area Under Curve
    # region CVAC

    # T28, T29: Income proportion
    cvac_hha_income_part = cba_tsec_hha / (hh_income_week * 4 * 1.5)
    cvac_hhb_income_part = cba_tsec_hhb / (hh_income_week * 4 * 0.75)
    # logging.info(f'T28: {cvac_hha_income_part}')
    # logging.info(f'T29: {cvac_hhb_income_part}')

    if paf_only:
        cvac_hha_area = 0  # U28
        cvac_hhb_area = 0  # U29
        cvac_hha_cost = 0  # V28
        cvac_hhb_cost = 0  # V29
        cvac_hha_ratio = 0  # W28
        cvac_hhb_ratio = 0  # W29
        cvac_hha_pen = 0  # X28
        cvac_hhb_pen = 0  # X29

    else:

        # logging.info(f'U28 variables required: cba_pen_hha: {cba_pen_hha}')
        # logging.info(f'U28 variables required: dc_parameter_c: {dc_parameter_c}')

        # U28, U29: Area under the demand curve
        cvac_hha_area = (
                dc_parameter_a * (cba_pen_hha - dc_parameter_c) -
                dc_parameter_b * (
                        cba_pen_hha * math.log(cba_pen_hha) - cba_pen_hha -
                        dc_parameter_c * math.log(dc_parameter_c) + dc_parameter_c
                )
        )
        # logging.info(f'U28: {cvac_hha_area}')

        cvac_hhb_area = (
                dc_parameter_a * (cba_pen_hhb - dc_parameter_c) -
                dc_parameter_b * (
                        cba_pen_hhb * math.log(cba_pen_hhb) - cba_pen_hhb -
                        dc_parameter_c * math.log(dc_parameter_c) + dc_parameter_c
                )
        )

        # logging.info(f'U29: {cvac_hhb_area}')


        # V28, V29: Cost area (height × base)
        cvac_hha_cost = cba_pen_hha * cvac_hha_income_part
        cvac_hhb_cost = cba_pen_hhb * cvac_hhb_income_part
        # logging.info(f'V28: {cvac_hha_cost}')
        # logging.info(f'V29: {cvac_hhb_cost}')


        # W28, W29: Area/cost ratio

        if cvac_hha_cost == 0:
            cvac_hha_ratio = 0
        else:
            cvac_hha_ratio = cvac_hha_area / cvac_hha_cost
        if cvac_hhb_cost == 0:
            cvac_hhb_ratio = 0
        else:
            cvac_hhb_ratio = cvac_hhb_area / cvac_hhb_cost
        # logging.info(f'W28: {cvac_hha_ratio}')
        # logging.info(f'W29: {cvac_hhb_ratio}')

        # # X26–X29: Penetration inputs unused by current version of the application
        # cvac_a_pen = 1
        # cvac_hha_pen = min(math.exp((cba_moec_hha / (hh_income_week * 4 * 1.5) - dc_parameter_a) / -dc_parameter_b),
        #                    0.95)  # X28
        # cvac_hhb_pen = min(math.exp((cba_moec_hhb / (hh_income_week * 4 * 0.75) - dc_parameter_a) / -dc_parameter_b),
        #                    0.95)  # x29


    # endregion

    # logging.info(f'CVAC Complete')

    # Log individual components
    # logging.info(f"paf_deterred_users: {paf_deterred_users}")
    # logging.info(f"paf_deterred_use: {paf_deterred_use}")
    # logging.info(f"paf_sub_users: {paf_sub_users}")
    # logging.info(f"paf_sub_pct: {paf_sub_pct}")
    # logging.info(f"paf_sub_use: {paf_sub_use}")
    # logging.info(f"paf_non_sub_users: {paf_non_sub_users}")
    # logging.info(f"paf_non_sub_pct: {paf_non_sub_pct}")
    # logging.info(f"paf_non_sub_use: {paf_non_sub_use}")
    # logging.info(f"paf_usd_hour: {paf_usd_hour}")

    # Log intermediate calculations
    logging.info(f"community_network_available: {community_network_available}")
    logging.info(f"requested_paf_monthly_use: {requested_paf_monthly_use}")
    logging.info(f"paf_monthly_capacity: {paf_monthly_capacity}")
    logging.info(f"paf_capacity_scale: {paf_capacity_scale}")

    deterred_component = paf_deterred_hours
    # logging.info(f"deterred_component (paf_deterred_hours): {deterred_component}")

    sub_component = paf_sub_hours
    # logging.info(f"sub_component (paf_sub_hours): {sub_component}")

    non_sub_component = paf_non_sub_hours
    # logging.info(f"non_sub_component (paf_non_sub_hours): {non_sub_component}")

    sum_component = paf_monthly_use
    # logging.info(f"sum_component (paf_monthly_use): {sum_component}")

    # Log final calculation
    # logging.info(f"paf_revenue B46: {paf_revenue}")

    # endregion

    # Monthly capex economic cost per decision maker mcec (Demand Modelling E14-E20)
    # region CBA MCEC
    # A monthly equivalent of annualised CAPEX including power capex and after subsidy
    # discounted to reflect delayed or deferred benefits (3-year delay)

    # Overall MCEC cba_mcec_oo (Demand Modelling E20)
    if paf_only:
        cba_mcec_oo = o36  # from E19
    else:
        annualised_total_capex = pa_capex_per_decision_maker + pa_ps_capex_per_decision_maker
        discounted = (annualised_total_capex / 12) / ((1 + inf) ** 3)
        cba_mcec_oo = discounted * (1 - capsub)

    # Service Providers MCEC cba_mcec_sp (Demand Modelling E14)
    """
    In contract negotiations, while there are more users within in a service provider, they are only using it for work purposes etc and a such there is just a negotiated outcome that decision makers will be prepared to pay more than an average household, but not significantly more – it is just an assumption of double based on the fact that it is more mission critical and there are multiple users).  Similar for corporate users it is 1.5 times. It is a simple approach but there is no real basis for complicating and already complicated model further in the opinion of economist Barry Burgan
    """
    if service_providers == 0:
        cba_mcec_sp = 0
    else:
        cba_mcec_sp = cba_mcec_oo * 2

    # Business MCEC cba_mcec_bus (Demand Modelling E15)

    if businesses == 0:
        cba_mcec_bus = 0
    else:
        cba_mcec_bus = cba_mcec_oo * 1.5

    # Household Above Median MCEC cba_mcec_hha (Demand Modelling E16)
    # Residual monthly capex economic cost per decision maker for Households above the median
    # After accounting for other groups' benefits and shared infrastructure costs.

    if hha == 0 or paf_only:
        cba_mcec_hha = 0
    else:
        total_value = cba_mcec_oo * ndm
        shared_paf_cost = pa_capex_per_decision_maker + pa_ps_capex_per_decision_maker
        shared_paf_cost = shared_paf_cost * 0.5 * paf_seats / system_life
        opportunity_cost = cba_ndm_sp * cba_mcec_sp - cba_ndm_bus * cba_mcec_bus

        cba_mcec_hha = (total_value - shared_paf_cost - opportunity_cost) / (hha + hhb)

    # Household Below Median MCEC cba_mcec_hhb (Demand Modelling E17)
    # Average monthly capex economic cost per decision maker, weighted across all user groups
    # Essentially a blended MCEC

    cba_mcec_hhb = cba_mcec_hha

    # Sub-total MCEC cba_mcec_sub (Demand Modelling E18)

    if ndm == 0:
        cba_mcec_sub = 0
    else:
        weighted_sum = (
                cba_ndm_sp * cba_mcec_sp +
                cba_ndm_bus * cba_mcec_bus +
                hha * cba_mcec_hha +
                hhb * cba_mcec_hhb
        )
        cba_mcec_sub = weighted_sum / ndm

    # PAF MCEC cba_mcec_paf (Demand Modellng E19)
    if paf_only:
        cba_mcec_paf = o36 / 12  # full annual connectivity capex divided monthly
    elif paf_seats == 0:
        cba_mcec_paf = 0
    else:
        revenue_per_seat_per_month = (paf_revenue / 12) * paf_margin / paf_seats
        public_share = cba_mcec_oo / (cba_moec_oo + cba_mcec_oo)
        cba_mcec_paf = revenue_per_seat_per_month * public_share
    # endregion

    # region Additional PAF
    # PAF MOEC (F19)
    if paf_only:
        cba_moec_paf = cba_mcec_paf * 0.2
    else:
        if paf_seats == 0:
            cba_moec_paf = 0
        else:
            base_value = (paf_revenue / 12 * paf_margin) / paf_seats
            scaling_factor = cba_moec_oo / (cba_moec_oo + cba_mcec_oo)
            cba_moec_paf = base_value * scaling_factor
    # endregion

    # Other monthly spend per decision maker omsdm (Demand Modelling G14-G20)
    # region CBA OMSDM

    # Other monthly spend per pervice provider omsdm_sp (Demand Modelling G14)
    # Monthly amortised cost of purchasing mobile devices for all users supported by service providers,
    # then distributes that cost across the number of SP decision makers.
    if cba_ndm_sp == 0:
        cba_omsdm_sp = 0
    else:
        total_ue_cost = cba_nu_sp * ue_cost
        monthly_payment = npf.pmt(wacc / 12, system_life * 12, -total_ue_cost)
        cba_omsdm_sp = (monthly_payment / cba_ndm_sp) * (1 - ue_subsidy)

    # Other monthly spend per service provider omsdm_sp (Demand Modelling G14)
    # Monthly amortised cost of purchasing mobile devices for all users supported by businesses
    # then distributes that cost across the number of business decision makers.
    if cba_ndm_bus == 0:
        cba_omsdm_bus = 0
    else:
        total_ue_cost = cba_nu_bus * ue_cost
        monthly_payment = npf.pmt(wacc / 12, system_life * 12, -total_ue_cost)
        cba_omsdm_bus = (monthly_payment / cba_ndm_bus) * (1 - ue_subsidy)
    # Other monthly cost per Household omsdm_hha (Demand Modelling G15)
    # Monthly device cost for household group A
    if hha == 0:
        cba_omsdm_hha = 0
    else:
        total_ue_cost = cba_nu_hha * ue_cost
        monthly_payment = npf.pmt(wacc / 12, system_life * 12, -total_ue_cost)
        cba_omsdm_hha = (monthly_payment / hha) * (1 - ue_exist_hha) * (1 - ue_subsidy)

    # Other monthly cost per Household omsdm_hhb (Demand Modelling G16)
    # Monthly device cost for household group B
    if hhb == 0:
        cba_omsdm_hhb = 0
    else:
        total_ue_cost = cba_nu_hhb * ue_cost
        monthly_payment = npf.pmt(wacc / 12, system_life * 12, -total_ue_cost)
        cba_omsdm_hhb = (monthly_payment / hhb) * (1 - ue_exist_hhb) * (1 - ue_subsidy)

    # Other monthly cost per Household Decision Maker Subtotal cba_omsdm_sub (Demand Modelling G17)
    # Weighted average of monthly mobile device costs across all decision maker groups
    if cba_ndm_sp == 0:
        cba_omsdm_sub = 0
    else:
        total_weighted_cost = (
                cba_omsdm_sp * cba_ndm_sp +
                cba_omsdm_bus * cba_ndm_bus +
                cba_omsdm_hha * hha +
                cba_omsdm_hhb * hhb
        )
        cba_omsdm_sub = total_weighted_cost / ndm

    # Other monthly cost per PAF decision maker cba_omsdm_sub (Demand Modelling G19)

    total_equipment_cost = paf_seats * paf_seat_cost
    annual_payment = npf.pmt(wacc, system_life, -total_equipment_cost)
    cba_omsdm_paf = annual_payment / 12

    # endregion

    # Total system economic cost per month per decision maker tsec (Demand Modelling H14-H19)
    # region CBA TSEC
    cba_tsec_sp = cba_mcec_sp + cba_moec_sp + cba_omsdm_sp
    cba_tsec_bus = cba_mcec_bus + cba_moec_bus + cba_omsdm_bus
    cba_tsec_hha = cba_mcec_hha + cba_moec_hha + cba_omsdm_hha
    cba_tsec_hhb = cba_mcec_hhb + cba_moec_hhb + cba_omsdm_hhb
    cba_tsec_sub = cba_mcec_sub + cba_moec_sub + cba_omsdm_sub
    cba_tsec_paf = cba_mcec_paf + cba_omsdm_paf
    # endregion
    # logging.info(f'CBA TSEC Complete')

    # User Demand cba_dem (was Number of actual users) (Demand Modelling J14-J20)
    # region CBA DEM
    cba_dem_sp = round(cba_nu_sp * cba_pen_sp)
    cba_dem_bus = round(cba_nu_bus * cba_pen_bus)
    cba_dem_hha = round(cba_nu_hha * cba_pen_hha)
    cba_dem_hhb = round(cba_nu_hhb * cba_pen_hhb)

    logging.info(f"cba_dem_sp = {cba_dem_sp}")
    logging.info(f"cba_dem_bus = {cba_dem_bus}")
    logging.info(f"cba_dem_hha = {cba_dem_hha}")
    logging.info(f"cba_dem_hhb = {cba_dem_hhb}")

    cba_dem_hh = round(cba_dem_hha + cba_dem_hhb)
    cba_dem_sub = round(cba_dem_sp + cba_dem_bus + cba_dem_hha + cba_dem_hhb)
    cba_dem_paf = round(paf_noncon_users)
    cba_dem_oo = round((cba_dem_sub + cba_dem_paf))
    # endregion
    # logging.info(f'CBA Demand Complete')

    # Traffic Demand in GB per Month (was GB per month demand (actual)) (Demand Modelling K14-K20)
    # region CBA DGBM
    # Demand weighted elasticity values for each

    if cba_dem_sp > 0:
        cba_dgbm_sp = cba_gbm_sp * cba_pen_sp
    else:
        cba_dgbm_sp = 0

    if cba_dem_bus > 0:
        cba_dgbm_bus = cba_gbm_bus * cba_pen_bus
    else:
        cba_dgbm_bus = 0

    if cba_dem_hha > 0:
        cba_dgbm_hha = cba_gbm_hha * cba_pen_hha
    else:
        cba_dgbm_hha = 0

    if cba_dem_hhb > 0:
        cba_dgbm_hhb = cba_gbm_hhb * cba_pen_hhb
    else:
        cba_dgbm_hhb = 0

    cba_dgbm_sub = cba_gbm_sub * cba_pen_sub
    cba_dgbm_paf = (
            min((paf_deterred_users * paf_deterred_use * paf_gb_hour +
            paf_sub_users * paf_sub_pct * paf_sub_use * paf_gb_hour +
            paf_non_sub_users * paf_non_sub_pct * paf_non_sub_use * paf_gb_hour),
                paf_hours_month_seat * paf_seats * paf_gb_hour)
    )
    cba_dgbm_oo = cba_dgbm_sub + cba_dgbm_paf
    # endregion

    # Annual user payments to network provider (Demand Modelling L14-L20)
    # region CBA AUP
    # logging.info("=== CBA AUP debug start ===")

    # logging.info("L14 inputs for cba_aup_sp")
    # logging.info(f"cba_ndm_sp = {cba_ndm_sp}")
    # logging.info(f"cba_pen_sp = {cba_pen_sp}")
    # logging.info(f"cba_mcec_sp = {cba_mcec_sp}")
    # logging.info(f"cba_moec_sp = {cba_moec_sp}")
    # logging.info(f"(cba_mcec_sp + cba_moec_sp) = {cba_mcec_sp + cba_moec_sp}")

    # logging.info("L15 inputs for cba_aup_bus")
    # logging.info(f"cba_ndm_bus = {cba_ndm_bus}")
    # logging.info(f"cba_pen_bus = {cba_pen_bus}")
    # logging.info(f"cba_mcec_bus = {cba_mcec_bus}")
    # logging.info(f"cba_moec_bus = {cba_moec_bus}")
    # logging.info(f"(cba_mcec_bus + cba_moec_bus) = {cba_mcec_bus + cba_moec_bus}")

    # logging.info("L16 inputs for cba_aup_hha")
    # logging.info(f"cba_ndm_hha = {cba_ndm_hha}")
    # logging.info(f"cba_pen_hha = {cba_pen_hha}")
    # logging.info(f"cba_mcec_hha = {cba_mcec_hha}")
    # logging.info(f"cba_moec_hha = {cba_moec_hha}")
    # logging.info(f"(cba_mcec_hha + cba_moec_hha) = {cba_mcec_hha + cba_moec_hha}")

    # logging.info("L17 inputs for cba_aup_hhb")
    # logging.info(f"cba_ndm_hhb = {cba_ndm_hhb}")
    # logging.info(f"cba_pen_hhb = {cba_pen_hhb}")
    # logging.info(f"cba_mcec_hhb = {cba_mcec_hhb}")
    # logging.info(f"cba_moec_hhb = {cba_moec_hhb}")
    # logging.info(f"(cba_mcec_hhb + cba_moec_hhb) = {cba_mcec_hhb + cba_moec_hhb}")
    #
    # logging.info("L19 inputs for cba_aup_paf")
    # logging.info(f"paf_revenue = {paf_revenue}")
    # logging.info(f"paf_margin = {paf_margin}")
    #
    # logging.info("=== CBA AUP debug end ===")

    if cba_dem_sp > 0:
        cba_aup_sp = cba_ndm_sp * cba_pen_sp * (cba_mcec_sp + cba_moec_sp) * 12  # L14
    else:
        cba_aup_sp = 0
    if cba_dem_bus > 0:
        cba_aup_bus = cba_ndm_bus * cba_pen_bus * (cba_mcec_bus + cba_moec_bus) * 12  # L15
    else:
        cba_aup_bus = 0
    if cba_dem_hha > 0:
        cba_aup_hha = cba_ndm_hha * cba_pen_hha * (cba_mcec_hha + cba_moec_hha) * 12  # L16
    else:
        cba_aup_hha = 0
    if cba_dem_hhb > 0:
        cba_aup_hhb = cba_ndm_hhb * cba_pen_hhb * (cba_mcec_hhb + cba_moec_hhb) * 12  # L17
    else:
        cba_aup_hhb = 0

    cba_aup_sub = cba_aup_sp + cba_aup_bus + cba_aup_hha + cba_aup_hhb  # L18
    cba_aup_paf = paf_revenue * paf_margin  # L19
    cba_aup_oo = cba_aup_sub + cba_aup_paf  # L20
    logging.info(f'cba_aup_oo: {cba_aup_oo}')
    # endregion

    # Consumer Surplus Ratio (Demand Modelling M14-M20)
    # region CBA SUR RATIO
    if paf_only:
        cba_sur_ratio_sp = 0
        cba_sur_ratio_bus = 0
        cba_sur_ratio_hha = 0
        cba_sur_ratio_hhb = 0
        cba_sur_ratio_paf = 2.5
    else:
        cba_sur_ratio_hha = max(cvac_hha_ratio, 0)
        cba_sur_ratio_hhb = max(cvac_hhb_ratio, 0)
        cba_sur_ratio_sp = cba_sur_ratio_hha * 1.5
        cba_sur_ratio_bus = cba_sur_ratio_hha
        cba_sur_ratio_paf = 0 if cba_aup_paf == 0 else cba_sur_ratio_hhb

    cba_sur_ratio_oo = (
        (cba_sur_ratio_bus * cba_aup_bus +
         cba_sur_ratio_hha * cba_aup_hha +
         cba_sur_ratio_hhb * cba_aup_hhb) / cba_aup_oo
        if not paf_only else 0
    )
    # endregion
    # logging.info(f'CBA Surplus Ratio Complete')

    # Consumer Surplus CBA SUR (Demand Modelling N14-N20)
    # region CBA SUR
    cba_sur_sp = (cba_aup_sp + (cba_omsdm_sp * 12)) * cba_sur_ratio_sp  # N14
    cba_sur_bus = (cba_aup_bus + (cba_omsdm_bus * 12)) * cba_sur_ratio_bus  # N15
    cba_sur_hha = (cba_aup_hha + (cba_omsdm_hha * 12)) * cba_sur_ratio_hha  # N16
    cba_sur_hhb = (cba_aup_hhb + (cba_omsdm_hhb * 12)) * cba_sur_ratio_hhb  # N17

    cba_sur_sub = cba_sur_sp + cba_sur_bus + cba_sur_hha + cba_sur_hhb  # N18
    cba_sur_paf = paf_revenue * cba_sur_ratio_paf  # N19
    cba_sur_oo = cba_sur_sub + cba_sur_paf  # N20
    # endregion

    # Social to Private Benefit Ratio cba_soc_priv_rat (Demand Modelling O14-O19)
    # region CBA SOC PRIV RATIO
    cba_soc_priv_rat_sp = 2
    cba_soc_priv_rat_bus = 2
    cba_soc_priv_rat_hha = 1
    cba_soc_priv_rat_hhb = 1
    cba_soc_priv_rat_paf = 0.5
    # endregion

    # Total Annual Community Benefit tcab (Demand Modelling P14-P20)
    # region CBA TACB
    cba_tacb_sp = cba_sur_sp * (1 + cba_soc_priv_rat_sp)
    cba_tacb_bus = cba_sur_bus * (1 + cba_soc_priv_rat_bus)
    cba_tacb_hha = cba_sur_hha * (1 + cba_soc_priv_rat_hha)
    cba_tacb_hhb = cba_sur_hhb * (1 + cba_soc_priv_rat_hhb)

    cba_tacb_sub = cba_tacb_sp + cba_tacb_bus + cba_tacb_hha + cba_tacb_hhb
    cba_tacb_paf = cba_sur_paf * (1 + cba_soc_priv_rat_paf)
    cba_tacb_oo = cba_tacb_sub + cba_tacb_paf
    # endregion

    # Demand and CBA Assessment, Year 3 (2024 Dollars) Table Assembly
    # region DCBA Table
    dcba_table_rows, dcba_table_columns = get_dcba_table(
        ndm=ndm,
        cba_ndm_sp=cba_ndm_sp, cba_nu_sp=cba_nu_sp, cba_gbm_sp=cba_gbm_sp, cba_mcec_sp=cba_mcec_sp,
        cba_moec_sp=cba_moec_sp, cba_omsdm_sp=cba_omsdm_sp, cba_tsec_sp=cba_tsec_sp, cba_pen_sp=cba_pen_sp,
        cba_dem_sp=cba_dem_sp, cba_dgbm_sp=cba_dgbm_sp, cba_aup_sp=cba_aup_sp, cba_sur_ratio_sp=cba_sur_ratio_sp,
        cba_sur_sp=cba_sur_sp, cba_soc_priv_rat_sp=cba_soc_priv_rat_sp, cba_tacb_sp=cba_tacb_sp,
        cba_ndm_bus=cba_ndm_bus, cba_nu_bus=cba_nu_bus, cba_gbm_bus=cba_gbm_bus, cba_mcec_bus=cba_mcec_bus,
        cba_moec_bus=cba_moec_bus, cba_omsdm_bus=cba_omsdm_bus, cba_tsec_bus=cba_tsec_bus, cba_pen_bus=cba_pen_bus,
        cba_dem_bus=cba_dem_bus, cba_dgbm_bus=cba_dgbm_bus, cba_aup_bus=cba_aup_bus, cba_sur_ratio_bus=cba_sur_ratio_bus,
        cba_sur_bus=cba_sur_bus, cba_soc_priv_rat_bus=cba_soc_priv_rat_bus, cba_tacb_bus=cba_tacb_bus,
        cba_ndm_hha=cba_ndm_hha, cba_nu_hha=cba_nu_hha, cba_gbm_hha=cba_gbm_hha, cba_mcec_hha=cba_mcec_hha,
        cba_moec_hha=cba_moec_hha, cba_omsdm_hha=cba_omsdm_hha, cba_tsec_hha=cba_tsec_hha, cba_pen_hha=cba_pen_hha,
        cba_dem_hha=cba_dem_hha, cba_dgbm_hha=cba_dgbm_hha, cba_aup_hha=cba_aup_hha, cba_sur_ratio_hha=cba_sur_ratio_hha,
        cba_sur_hha=cba_sur_hha, cba_soc_priv_rat_hha=cba_soc_priv_rat_hha, cba_tacb_hha=cba_tacb_hha,
        cba_ndm_hhb=cba_ndm_hhb, cba_nu_hhb=cba_nu_hhb, cba_gbm_hhb=cba_gbm_hhb, cba_mcec_hhb=cba_mcec_hhb,
        cba_moec_hhb=cba_moec_hhb, cba_omsdm_hhb=cba_omsdm_hhb, cba_tsec_hhb=cba_tsec_hhb, cba_pen_hhb=cba_pen_hhb,
        cba_dem_hhb=cba_dem_hhb, cba_dgbm_hhb=cba_dgbm_hhb, cba_aup_hhb=cba_aup_hhb, cba_sur_ratio_hhb=cba_sur_ratio_hhb,
        cba_sur_hhb=cba_sur_hhb, cba_soc_priv_rat_hhb=cba_soc_priv_rat_hhb, cba_tacb_hhb=cba_tacb_hhb,
        cba_nu_sub=cba_nu_sub, cba_gbm_sub=cba_gbm_sub, cba_mcec_sub=cba_mcec_sub, cba_moec_sub=cba_moec_sub,
        cba_omsdm_sub=cba_omsdm_sub, cba_tsec_sub=cba_tsec_sub, cba_pen_sub=cba_pen_sub, cba_dem_sub=cba_dem_sub,
        cba_dgbm_sub=cba_dgbm_sub, cba_aup_sub=cba_aup_sub, cba_sur_sub=cba_sur_sub, cba_tacb_sub=cba_tacb_sub,
        cba_mcec_paf=cba_mcec_paf, cba_moec_paf=cba_moec_paf, cba_omsdm_paf=cba_omsdm_paf, cba_tsec_paf=cba_tsec_paf,
        cba_dem_paf=cba_dem_paf, cba_dgbm_paf=cba_dgbm_paf, cba_aup_paf=cba_aup_paf, cba_sur_ratio_paf=cba_sur_ratio_paf,
        cba_sur_paf=cba_sur_paf, cba_soc_priv_rat_paf=cba_soc_priv_rat_paf, cba_tacb_paf=cba_tacb_paf,
        cba_nu_oo=cba_nu_oo, cba_mcec_oo=cba_mcec_oo, cba_moec_oo=cba_moec_oo, cba_dem_oo=cba_dem_oo,
        cba_dgbm_oo=cba_dgbm_oo, cba_aup_oo=cba_aup_oo, cba_sur_ratio_oo=cba_sur_ratio_oo,
        cba_sur_oo=cba_sur_oo, cba_tacb_oo=cba_tacb_oo
    )
    # endregion

    # Starting the Business Planning Outcomes work
    # Starting the Business Planning Outcomes work
    # Starting the Business Planning Outcomes work

    # region BP PL General and Imports
    cli_rev_y3 = cba_aup_oo / 1000000  # Business Planning E3
    # logging.info(f'cli_rev_y3: {cli_rev_y3}')

    # Define take-up rates across years 1–10
    # Note the hard-coded assumption of 0.75 in the first year
    tu_rates = {
        1: 0.75,
        2: 0.9,
    }

    # Fill years 4–10 with 1
    for year in range(3, 11):
        tu_rates[year] = 1

    # logging.info(f"Take-up rates per year: {tu_rates}")

    # endregion

    # Client Revenues
    # region BP PL CLI REV
    logging.info("Client Revenues Debug")
    logging.info(f"system_life: {system_life}")
    logging.info(f"inf: {inf}")
    logging.info(f"pop_growth_rate: {pop_growth_rate}")
    logging.info(f"tu_rates: {tu_rates}")
    logging.info(f"cli_rev_y3: {cli_rev_y3}")

    pl_cli_rev_by_year = get_pl_cli_rev_by_year(
        system_life, inf, pop_growth_rate, tu_rates, cli_rev_y3)

    revenues = list(pl_cli_rev_by_year.values())
    logging.info(f"cli_rev_list = {revenues}")
    pl_cli_rev_avg = sum(revenues) / len(revenues)
    # logging.info(f"avg client revenues: {pl_cli_rev_avg * 1_000_000}")
    # endregion

    # Labour Costs per year
    # region BP PL LAB COS
    # Fixed labour headcount + variable labour headcount * wage cost per employee / 1m

    pl_lab_cos_by_year = get_pl_lab_cos_by_year(
        system_life, opex_ftes_fixed, opex_ftes_variable, solution_supported_users, cba_pen_sub, pop_growth_rate,
        labour_cost, inf, tu_rates
    )
    # logging.info(f"pl_lab_cos_by_year = {pl_lab_cos_by_year}")
    # endregion

    # Other System operating Costs
    # region BP PL OTH SYS OP COS
    pl_oth_sys_op_cos_by_year = get_pl_oth_sys_op_cos_by_year(
        pl_lab_cos_by_year=pl_lab_cos_by_year,
        opex_other=opex_other,
        system_life=system_life
    )
    # logging.info(f"pl_oth_sys_op_cos_by_year = {pl_oth_sys_op_cos_by_year}")
    # endregion

    # Backhaul and Power Operating costs
    # region BP PL BH POW COS
    # Takes Backhaul and power opex from builder results
    # Divides evenly over the system's lifetime
    # Scales by inflation
    pl_bh_pow_op_cos_by_year = get_pl_bh_pow_op_cos_by_year(
        system_life, backhaul_opex, power_opex, inf
    )
    # endregion

    # Spectrum Licence Fee Costs
    # region BP PL SPEC LIC FEE
    # Calculates the per-annum spectrum cost using a payment function

    pl_spec_fee_by_year = get_pl_spec_fee_by_year(
        system_life, wacc, spectrum_fee
    )
    # logging.info(f"pl_spec_fee_by_year = {pl_spec_fee_by_year}")
    # endregion

    # Maintenance Cost
    # region BP PL Maint COS
    # Calculates the maintenance cost per year
    pl_maint_cos_by_year = get_pl_maint_cos_by_year(
        system_life, cons_spd, maint_opex, inf
    )
    # endregion

    # Total Operating Costs
    # region BP PL TOT OP COS
    # Sums the operating costs
    pl_tot_op_cos_by_year = get_pl_tot_op_cos_by_year(
        pl_lab_cos_by_year, pl_oth_sys_op_cos_by_year, pl_bh_pow_op_cos_by_year,
        pl_spec_fee_by_year, pl_maint_cos_by_year
    )
    totals = list(pl_tot_op_cos_by_year.values())
    pl_tot_op_cos_avg = sum(totals) / len(totals)
    # logging.info(f"pl_tot_op_cos_by_year = {pl_tot_op_cos_by_year}")

    # endregion

    # Subsidies
    # region BP PL SUB
    pl_sub_by_year = get_pl_sub_by_year(
        cons_spd, capsub, opsub, system_life, pl_tot_op_cos_by_year
    )
    subsidies = list(pl_sub_by_year.values())
    # logging.info(f"subsidies = {subsidies}")
    pl_cli_sub_avg = sum(subsidies) / len(subsidies)
    # logging.info(f"pl_cli_sub_avg = {pl_cli_sub_avg}")
    # endregion

    # Total Revenues
    # region BP PL TOT REV
    pl_tot_rev_by_year = get_pl_tot_rev_by_year(
        pl_cli_rev_by_year, pl_sub_by_year
    )
    # logging.info(f"pl_tot_rev_by_year = {pl_tot_rev_by_year}")
    # endregion

    # Operating Profit
    # region BP PL OP PROF
    # Subtracts operating costs from total revenues
    pl_op_prof_by_year = get_pl_op_prof_by_year(
        pl_tot_rev_by_year, pl_tot_op_cos_by_year
    )
    ebitdas = list(pl_op_prof_by_year.values())
    # logging.info(f"pl_op_prof_by_year = {pl_op_prof_by_year}")
    pl_op_profit_avg = sum(ebitdas)/len(ebitdas)
    # logging.info(f"pl_op_profit_avg = {pl_op_profit_avg}")

    # endregion

    # BP PL Depreciation
    # region BP PL Dep
    pl_dep_by_year = get_pl_dep_by_year(
        system_life, cons_spd
    )
    # logging.info(f"pl_dep_by_year = {pl_dep_by_year}")
    # endregion

    # BP PL EBIT
    # region BP PL EBIT
    # Subtraction of depreciation from operating profit
    pl_ebit_by_year = get_pl_ebit_by_year(
        pl_op_prof_by_year, pl_dep_by_year
    )
    # logging.info(f"pl_ebit_by_year = {pl_ebit_by_year}")
    # endregion

    # BP Interest Payments
    # region BP PL INT PAY
    # logging.info("Region BP PL INT PAY")
    pl_int_by_year = get_pl_int_by_year(
        system_life, cons_spd, debt_prop, fin_cos
    )
    # logging.info(f"pl_int_by_year = {pl_int_by_year}")
    # endregion

    # BP Earnings Before Tax
    # region BP PL EBT
    # logging.info("Region BP PL EBT")
    pl_ebt_by_year = get_pl_ebt_by_year(
        pl_ebit_by_year, pl_int_by_year
    )
    ebits = list(pl_ebt_by_year.values())
    pl_ebt_avg = sum(ebits) / len(ebits)
    # logging.info(f"pl_ebt_by_year = {pl_ebt_by_year}")
    # endregion

    # BP Tax
    # region BP PL Tax
    # logging.info("Region BP PL Tax")
    pl_tax_by_year = get_pl_tax_by_year(
        pl_ebt_by_year, tax_rate
    )
    # logging.info(f"pl_tax_by_year = {pl_tax_by_year}")
    # endregion

    # BP Profit
    # region BP Profit
    # logging.info("Region BP Profit")
    pl_prof_by_year = get_pl_prof_by_year(pl_ebt_by_year, pl_tax_by_year)
    # endregion

    # Profit and Loss Table
    # region BP PL Table
    # logging.info("Region BP PL Table")
    pl_table_columns = [
                           {"title": "Line Item", "data": "label"},
                       ] + [
                           {"title": f"Year {year}", "data": f"y{year}"} for year in range(1, 11)
                       ]

    pl_table_rows = [
        build_keyed_row("Client Revenues", "cli_rev", pl_cli_rev_by_year),
        build_keyed_row("Subsidies", "pl_sub", pl_sub_by_year),
        build_keyed_row("Total Revenues", "pl_tot_rev", pl_tot_rev_by_year),
        build_keyed_row("Labour Costs", "pl_lab_cos", pl_lab_cos_by_year),
        build_keyed_row("Other System OpEx", "pl_oth_sys_op_cos", pl_oth_sys_op_cos_by_year),
        build_keyed_row("Backhaul & Power OpEx", "pl_bh_pow_op_cos", pl_bh_pow_op_cos_by_year),
        build_keyed_row("Spectrum Fees", "pl_spec_fee", pl_spec_fee_by_year),
        build_keyed_row("Maintenance Costs", "pl_maint_cos", pl_maint_cos_by_year),
        build_keyed_row("Total Operating Costs", "pl_tot_op_cos", pl_tot_op_cos_by_year),
        build_keyed_row("Operating Profit", "pl_op_prof", pl_op_prof_by_year),
        build_keyed_row("Depreciation", "pl_dep", pl_dep_by_year),
        build_keyed_row("EBIT", "pl_ebit", pl_ebit_by_year),
        build_keyed_row("Interest Payments", "pl_int", pl_int_by_year),
        build_keyed_row("Earnings Before Tax (EBT)", "pl_ebt", pl_ebt_by_year),
        build_keyed_row("Tax", "pl_tax", pl_tax_by_year),
        build_keyed_row("Profit", "pl_prof", pl_prof_by_year),
    ]

    # endregion

    # Investment and Operating Cash Flow Statement
    # Investment and Operating Cash Flow Statement
    # Investment and Operating Cash Flow Statement

    # BP CF Cash In
    # region BP CF CAS IN

    cf_cash_in_by_year = get_cf_cash_in_by_year (
     pl_cli_rev_by_year, pl_sub_by_year
    )
    # endregion

    # BP CF Cash Out
    # region BP CF CAS OUT

    cf_cash_out_by_year = get_cf_cash_out_by_year (
        pl_lab_cos_by_year, pl_oth_sys_op_cos_by_year, pl_bh_pow_op_cos_by_year, pl_spec_fee_by_year, pl_maint_cos_by_year, pl_tax_by_year
    )
    # endregion

    # BP CF Net Cashflow
    # region BP CF NET CAS
    cf_net_by_year = get_cf_net_by_year(
        cf_cash_in_by_year, cf_cash_out_by_year
    )

    cf_nets_all = list(cf_net_by_year.values())  # all nets 1-10
    cf_y0 = cons_spd * -1
    cf_nets_all.insert(0, cf_y0)
    # logging.info(f"cf_nets_all: {cf_nets_all}")
    cf_nets_y1_y10 = cf_nets_all[1:]  # only get years 1 through 10

    # endregion

    # BP CF Cumulative Cashflow
    # region BP CF CUM CAS
    cf_cum_by_year = get_cf_cum_by_year(
      cf_net_by_year, cons_spd
    )
    # logging.info(f"cf_cum_by_year: {cf_cum_by_year}")
    # endregion

    # BP CF Net Present Value
    # region BP CF NPV
    cf_npv = npf.npv(wacc,cf_nets_y1_y10) - cons_spd
    cf_irr = npf.irr(cf_nets_all)
    if np.isnan(cf_irr):
        cf_irr = 0
    # logging.info(f"cf_irr: {cf_irr}")

    # endregion

    # Outcomes Individual Perspective
    # region Outcomes Individual
    # logging.info("region Outcomes Individual")
    # logging.info("=== ARPU divide-by-zero debug ===")
    # logging.info(f"cba_aup_sp = {cba_aup_sp}")
    # logging.info(f"cba_dem_sp = {cba_dem_sp}")
    # logging.info(f"cba_dem_sp == 0 -> {cba_dem_sp == 0}")
    #
    # logging.info(f"cba_aup_bus = {cba_aup_bus}")
    # logging.info(f"cba_dem_bus = {cba_dem_bus}")
    # logging.info(f"cba_dem_bus == 0 -> {cba_dem_bus == 0}")
    #
    # logging.info(f"cba_aup_hha = {cba_aup_hha}")
    # logging.info(f"cba_aup_hhb = {cba_aup_hhb}")
    # logging.info(f"cba_dem_hha = {cba_dem_hha}")
    # logging.info(f"cba_dem_hhb = {cba_dem_hhb}")
    # logging.info(f"(cba_dem_hha + cba_dem_hhb) = {cba_dem_hha + cba_dem_hhb}")
    # logging.info(f"(cba_dem_hha + cba_dem_hhb) == 0 -> {(cba_dem_hha + cba_dem_hhb) == 0}")
    #
    # logging.info(f"hh_size = {hh_size}")

    arpu_sp = 0 if cba_dem_sp == 0 else (cba_aup_sp / 12) / cba_dem_sp
    arpu_bus = 0 if cba_dem_bus == 0 else (cba_aup_bus / 12) / cba_dem_bus

    household_demand = cba_dem_hha + cba_dem_hhb
    arpu_id = 0 if household_demand == 0 else ((cba_aup_hha + cba_aup_hhb) / 12) / household_demand

    arpu_hh = round(arpu_id * hh_size, 2)


    # endregion

    # BP CF Investment and Operating Cash Flow Statement Table
    # region BP CF Table
    logging.info("region BP CF Table")
    inv_table_columns = [{"title": "Line Item", "data": "label"}] + [
        {"title": f"Year {year}", "data": f"y{year}"} for year in range(0, 11)
    ]

    inv_table_rows = [
        build_inv_row("Client Revenues", "cli_rev", pl_cli_rev_by_year),
        build_inv_row("Subsidies", "pl_sub", pl_sub_by_year),
        build_inv_row("Total Cash In", "cf_cash_in", cf_cash_in_by_year, year0_value=0.0),
        {"label": "Construction Spend", "y0": float(cons_spd), **{f"y{year}": "" for year in range(1, 11)}},
        build_inv_row("Labour Costs", "pl_lab_cos", pl_lab_cos_by_year),
        build_inv_row("Other System Operating Costs", "pl_oth_sys_op_cos", pl_oth_sys_op_cos_by_year),
        build_inv_row("Backhaul & Power Operating Costs", "pl_bh_pow_op_cos", pl_bh_pow_op_cos_by_year),
        build_inv_row("Spectrum Licence Fees", "pl_spec_fee", pl_spec_fee_by_year),
        build_inv_row("Maintenance Cost", "pl_maint_cos", pl_maint_cos_by_year),
        build_inv_row("Tax Payable", "pl_tax", pl_tax_by_year),
        build_inv_row("Total Cash Out", "cf_cash_out", cf_cash_out_by_year, year0_value=float(cons_spd)),
        build_inv_row("Net Cash Flow", "cf_net", cf_net_by_year, year0_value=-1 * float(cons_spd)),
        build_inv_row("Cumulative Cash Flow", "cf_cum", cf_cum_by_year, year0_value=-1 * float(cons_spd)),
    ]

    # endregion

    # Outcomes Summary Table
    # region OUT SUM Table
    logging.info("Outcomes Summary Table")

    outcomes_table_columns = [
        {"title": "Outcome", "data": "label"},
        {"title": "Value", "data": "Value"}
    ]
    outcomes_table_rows = []

    if not paf_only:
        pa_cba_moec_sub = cba_moec_sub * 12
        avg_cost_dm_m =  (pa_capex_per_decision_maker + pa_ps_capex_per_decision_maker + pa_cba_moec_sub)/12
        outcomes_table_rows.extend([
            {"label": "Solution Capex per potential decision maker (ex PAF)", "Value": f"${scpdm:,.2f}"},
            {"label": "Annual Operating cost per decision maker (ex PAF)", "Value": f"${pa_cba_moec_sub:,.2f}"},
            {"label": "Monthly average cost of service per decision maker", "Value": f"${avg_cost_dm_m:,.2f}"}
        ])
    pl_cli_rev_avg = pl_cli_rev_avg * 1_000_000
    pl_cli_sub_avg = pl_cli_sub_avg * 1_000_000
    pl_tot_op_cos_avg = pl_tot_op_cos_avg * 1_000_000
    pl_ebt_avg = pl_ebt_avg * 1_000_000
    pl_op_profit_avg = pl_op_profit_avg * 1_000_000
    soc_ben_avg = pl_cli_rev_avg * (cba_tacb_oo / cba_aup_oo)
    if solution_supported_users >= total_potential_users_all_types:
        users_supported_prop = 1
    else:
        users_supported_prop = solution_supported_users / total_potential_users_all_types

    outcomes_table_rows.extend([
        {"label": "Additional private costs per decision maker", "Value": f"${cba_omsdm_sub:,.2f}"},
        {"label": "Average Annual operator revenue (US$)", "Value": f"${pl_cli_rev_avg:,.0f}"},
        {"label": "Average Annual costs (US$)", "Value": f"${pl_tot_op_cos_avg:,.0f}"},
        {"label": "Average Annual operating profit (EBITDA) (US$)", "Value": f"${pl_op_profit_avg:,.0f}"},
        {"label": "Average Annual EBT (US$)", "Value": f"${pl_ebt_avg:,.0f}"},
        {"label": "Financial Return on Investment (IRR of CashFlows)", "Value": f"{cf_irr:.2%}"},
        {"label": "Average annual social benefit (US$)", "Value": f"${soc_ben_avg:,.0f}"},
        {"label": "Population geographic coverage", "Value": f"{total_potential_users_all_types:,}"},
        {"label": "Users supported by the solution", "Value": f"{solution_supported_users:,}"},
        {"label": "Home users taking up the solution", "Value": f"{cba_dem_hh:,}"},
        {"label": "Business users taking up the solution", "Value": f"{round(cba_dem_bus):,}"},
        {"label": "Service provider users taking up the solution", "Value": f"{cba_dem_sp:,}"},
        {"label": "Predicted Users of Public Access Facilities", "Value": f"{cba_dem_paf:,}"},
        {"label": "Proportion of total potential private users supported", "Value": f"{users_supported_prop:.2%}"},
        {"label": "Adoption level (% of possible subscribers)", "Value": f"{cba_pen_sub:.2%}"},
        {"label": "Average Revenue per Service Provider User", "Value": f"${arpu_sp:.2f}"},
        {"label": "Average Revenue per Business User", "Value": f"${arpu_bus:.2f}"},
        {"label": "Average Revenue per Household", "Value": f"${arpu_hh:.2f}"},
        {"label": "Average Revenue per Individual User", "Value": f"${arpu_id:.2f}"}
    ])
    # endregion

    output_data = {
        "access_cost": access_capex,
        "area_covered": total_coverage_area,
        "area_sqkm": area_sqkm,
        "backhaul_available": total_backhaul_available,
        "backhaul_cost": backhaul_cost,  # Sum of OpEx and CapEx over the life of the system
        "backhaul_capex": backhaul_capex,
        "backhaul_annual_opex": backhaul_annual_opex,
        "backhaul_opex": backhaul_opex,
        "backhaul_required": backhaul_required,
        "battery_age_derating": battery_age_derating,
        "battery_cost_watt_hour": battery_cost_watt_hour,
        "battery_dod": battery_dod,
        "charger_inverter_base": charger_inverter_base,
        "charger_inverter_variable": charger_inverter_variable,
        "connectivity_capex": int(round(cc)),
        "labour_cost": labour_cost,
        "lang": input_data.lang,
        "country_name": country_name,
        "mains_power_cost_kwh": mains_power_cost_kwh,
        "mains_power_installation_cost": mains_power_installation_cost,
        "midhaul_available": total_midhaul_available,
        "midhaul_cost": midhaul_capex,  # Midhaul doesn't have an OpEx component handled separately
        "population_covered": total_population_covered,
        "power_capex": int(round(power_capex)),
        "power_hybrid_hours": power_hybrid_hours,
        "power_intermittent_hours": power_intermittent_hours,
        "power_reliable_hours": power_reliable_hours,
        "power_opex": int(round(power_opex)),
        "power_required": total_power_required,
        "solar_cost_watt": solar_cost_watt,
        "solar_derating": solar_derating,
        "solar_efficiency": solar_efficiency,
        "system_life": system_life,
        "total_potential_users": total_potential_users_all_types,
        "system_capex": int(round(system_capex)),
        "total_system_cost": int(round(system_cost)),
        "towers_cost": int(round(total_tower_cost)),
        "traffic_growth": traffic_growth,
        "users_per_household": hh_size,
        "users_supported": solution_supported_users,
        "year_1_traffic": year_1_traffic,
        "demand_curve_points": dc_points,
        "dcba_table_rows": dcba_table_rows,
        "dcba_table_columns": dcba_table_columns,
        "pl_table_columns": pl_table_columns,
        "pl_table_rows": pl_table_rows,
        "inv_table_columns": inv_table_columns,
        "inv_table_rows": inv_table_rows,
        "outcomes_table_columns": outcomes_table_columns,
        "outcomes_table_rows": outcomes_table_rows,
        "detailed_results": ldf.to_dict(orient='records'),
        "bom_table_columns": bom_table_columns,
        "bom_table_rows": bom_table_rows,
        "pbom_table_columns": pbom_table_columns,
        "pbom_table_rows": pbom_table_rows,
        "coverage_maps": coverage_maps,
        "net_summary_table_columns": net_summary_table_columns,
        "net_summary_table_rows": net_summary_table_rows
    }

    return ModelerOutput(**output_data)
