from library.helpers import *
from library.classes import *
from fastapi import APIRouter, HTTPException
from fastapi.templating import Jinja2Templates
from typing import List
import logging
from fastapi import Body

router = APIRouter()
templates = Jinja2Templates(directory="templates/")
logging.basicConfig(level=logging.INFO)

@router.get(
    "/api/site_text",
    summary="Website text for a specific language",
    description="Returns a dictionary where the key is the UI element and the value is the text in the requested language.",
    tags=["API GET Endpoints"],
    response_model=SiteTextResponse,
    include_in_schema=False,
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                      "banner": "Community Network Builder",
                      "welcome": "<p>The Community Network Builder is an application that helps you estimate and understand the cost of building and operating a community network anywhere in the world. Users can select the frequencies available in their context or proceed with the default ISM bands of 2.4GHz and 5.8GHz, which are widely available globally.</p>\n<p>You can model a variety of network types, including mobile or Wi-Fi networks, fixed wireless, fibre-to-the- home, public access facilities, or any combination of these. The application guides users in describing terrain and vegetation conditions that may impact network deployment, particularly for radio frequency networks.</p>\n<p>After specifying the population and area to be covered, users can design the network step by step, adding locations and technologies incrementally. The application provides helpful hints throughout this process, including suggested costs for network elements and traffic, which can easily be adjusted.For more advanced control, the Expert Options menu allows users to fine-tune details such as labour costs and electricity prices for their specific market.</p>\n<p>The Community Network Builder Application was commissioned by the Association for Progressive Communication (APC) to Systems Knowledge Concepts (SKC) and Telco2. It was developed with the support of the Internet Society (ISOC), the Asia Pacific Network Information Centre (APNIC) Foundation, Hello World and the World Association for Christian Communication (WACC).</p>",
                      "language": "English",
                      "sel_lang": "Select your Language",
                      "sel_country": "Select your Country",
                      "build_network": "Build a Community Network in",
                      "sel_freq": "Select the frequencies you have access to",
                      "sel_tech": "Select the technologies you want to use",
                      "sel_terrain": "Select a terrain profile",
                      "sel_veg": "Select a vegetation profile",
                      "terrain": "Terrain Profile",
                      "vegetation": "Vegetation Profile",
                      "model_supports": "This version of the model supports either wireless or fibre technologies, but not both at the same time.",
                      "sel_freq_one": "Please select at least one frequency. In many countries 2.4 and 5.8 GHz are available without a license.",
                      "sel_tech_one": "Please select at least one technology.",
                      "selected_freq": "Selected Frequencies",
                      "selected_tech": "Selected Technologies",
                      "selected_terrain": "Selected Terrain Profile",
                      "selected_veg": "Selected Vegetation Profile",
                      "coverage_req": "Coverage Requirements",
                      "expert_opt": "Expert Options",
                      "show": "Show",
                      "hide": "Hide",
                      "add": "Add",
                      "remove": "Remove",
                      "coverage_pop_note": "Enter the total population of the community, which must be fewer than 100,000 people.",
                      "coverage_hh_note": "Enter the average number of people per household, which must between 1 and 10.",
                      "coverage_area_note": "Enter the area your population is distributed over, which must be between 0.1 and 10,000 square kilometres.",
                      "selected_options": "Selected Options",
                      "net_elements": "Network Elements",
                      "net_elements_desc": "Your network must have at least one tower location. A button at the bottom of the page allows you to add a new tower location, or delete a tower location you've added.",
                      "tower_location": "Location",
                      "tower_location_name": "Tower Location Name",
                      "net_types": "Network Types",
                      "net_type": "Network Type",
                      "net_types_desc": "In this section you pick a technology and a number of instances of the technology provided by this location. Wireless technologies may have between 1-6 sectors, depending on the technology. GPON installations need only one chassis. Public Access Facilities may have between 4-30 seats. Tower locations can support multiple technologies but please choose only one instance of each.",
                      "tower_connect": "Tower Connectivity",
                      "tower_connect_desc": "Every tower location must have at least one network link or one backhaul link. If your tower location has only a network link, you must add another tower location that will have a backhaul link.",
                      "net_links": "Network Links",
                      "net_link": "Network Link",
                      "net_links_desc": "A network link, or midhaul, connects this location to another location. If you choose to add a network link at this location, you must add the same type of network link at another location.",
                      "backhaul_links": "Backhaul Links",
                      "backhaul_link": "Backhaul Link",
                      "backhaul_links_desc": "A backhaul is a connection to the Internet. Every network needs at least one backhaul, but not every tower location needs a backhaul. Correct the suggested costs if you have better information for your application.",
                      "next": "Next",
                      "back": "Back",
                      "terrain_profile_desc": "Terrain profile is a coarse control for model users to estimate how terrain may block signals from a tower location to end users. In the event hills or mountains prevent half of users in a normal coverage area from line of sight to a tower location, “Very High Variation” can be selected and coverage area will be reduced by 50%.",
                      "veg_profile_desc": "The vegetation profile represents how much vegetation (in meters) is between an end user and the nearest communication tower. The more vegetation there is, the more it blocks or weakens the radio signal, limiting coverage. Vegetation absorbs and scatters the signal, and the effect is greater at higher frequencies. You can select from various options, ranging from no vegetation (0 meters) to very high vegetation (100 meters), to account for the impact on your wireless coverage. This helps the model estimate how signal strength will be affected in your environment.",
                      "sectors": "Sectors",
                      "tower_type": "Tower Type",
                      "tower_type_desc": "Towers can be as simple as antennas mounted on a rooftop or as complex as an engineered structure with guy wires. For this model, the important data is cost. Correct the supplied cost if you have better information for your application.",
                      "cost": "Cost",
                      "capacity": "Capacity",
                      "cost_to_install": "installation Cost",
                      "cost_per_mbps": "Cost of traffic",
                      "fixed_monthly_charge": "Fixed Monthly Charge",
                      "alert_add_one_location": "Please add at least one location.",
                      "alert_name_locations": "Please enter a name for all locations.",
                      "alert_enter_population": "Please enter a number between 1 and 100,000 for Population.",
                      "alert_enter_household_size": "Please enter a number between 1 and 10 for Household Size.",
                      "alert_enter_coverage_area": "Please enter a number between 0.1 and 10,000 for Coverage Area.",
                      "alert_enter_backhaul": "At least one backhaul link must be selected across all locations",
                      "alert_enter_midhaul": "If more than one location is being submitted, at least two Network Links (Midhaul) must be selected.",
                      "calculate_network": "Run the Model",
                      "toggle": "Toggle",
                      "network_cover_cost": "Network Details",
                      "number_between_vals": "Please enter a number between the values",
                      "and": "and",
                      "veg_very_high": "Very High Vegetation",
                      "veg_high": "High Vegetation",
                      "veg_med": "Medium Vegetation",
                      "veg_low": "Low Vegetation",
                      "veg_very_low": "Very Low Vegetation",
                      "veg_none": "No Vegetation",
                      "veg_very_high_desc": "100 meters of vegetation is present between the user and the tower.",
                      "veg_high_desc": "50 meters of vegetation is present between the user and the tower.",
                      "veg_med_desc": "25 meters of vegetation is present between the user and the tower.",
                      "veg_low_desc": "10 meters of vegetation is present between the user and the tower.",
                      "veg_very_low_desc": "5 meters of vegetation is present between the user and the tower.",
                      "veg_none_desc": "There is no vegetation is present between the user and the tower.",
                      "tower_roof_top": "Use of a building rooftop to mount antennas instead of a freestanding tower.",
                      "tower_5_m": "A five metre tall tower, mast, or utility pole.",
                      "tower_10_m": "A ten metre tall tower, mast, or utility pole.",
                      "tower_15_m": "A fifteen metre tall tower, which could be freestanding or supported by guy wires.",
                      "tower_20_m": "A twenty metre tall tower, which could be freestanding or supported by guy wires.",
                      "tower_25_m": "A twenty-five metre tall tower, which could be freestanding or supported by guy wires.",
                      "tower_30_m": "A thirty metre tall tower, which could be freestanding or supported by guy wires.",
                      "terrain_very_high": "50% reduction in coverage",
                      "terrain_high": "40% reduction in coverage",
                      "terrain_med": "30% reduction in coverage",
                      "terrain_low": "20% reduction in coverage",
                      "terrain_very_low": "10% reduction in coverage",
                      "terrain_none": "No reduction in coverage",
                      "tech_none": "None",
                      "tech_fwa": "Fixed Wireless to the Home/Premises",
                      "tech_mobile": "Mobile, and/or Public WiFi hotspot(s)",
                      "tech_gpon": "Fibre to the Home/Premises",
                      "tech_paf": "Public Access Facility",
                      "midhaul_none": "No network present",
                      "midhaul_fibre_1g": "Fibre to a network termination unit (NTU)",
                      "midhaul_fibre_10g": "Fibre to a network termination unit (NTU)",
                      "midhaul_ism_fwa_100": "ISM Fixed Wireless 100 Mbps",
                      "midhaul_ism_fwa_200": "ISM Fixed Wireless 200 Mbps",
                      "midhaul_ism_fwa_500": "ISM Fixed Wireless 500 Mbps",
                      "midhaul_microwave_500": "Licensed Microwave 2048 QAM, 6-18 GHz",
                      "midhaul_microwave_1000": "Licensed Microwave 2048 QAM, 6-18 GHz",
                      "system_life": "System Life",
                      "year_1_traffic": "Year 1 Traffic",
                      "traffic_growth": "Traffic Growth",
                      "tower_cost": "Tower Cost",
                      "building_cost": "Building Cost",
                      "labour_cost": "Labour Cost",
                      "mains_power_installation_cost": "Mains Power Installation Cost",
                      "mains_power_cost_kwh": "Mains Power Cost per kWh",
                      "solar_cost_watt": "Solar Cost per Watt",
                      "battery_cost_watt_hour": "Battery Cost per Watt Hour",
                      "battery_dod": "Battery Depth of Discharge",
                      "charger_inverter_base": "Charger Inverter Base Cost",
                      "charger_inverter_variable": "Charger Inverter Variable Cost",
                      "solar_efficiency": "Solar Efficiency",
                      "solar_derating": "Solar Derating",
                      "battery_age_derating": "Battery Age Derating",
                      "power_reliable_hours": "Reliable Power Hours",
                      "power_intermittent_hours": "Intermittent Power Hours",
                      "power_offgrid_hours": "Offgrid Power Hours",
                      "power_hybrid_hours": "Hybrid Power Hours",
                      "system_life_desc": "The expected life of the system in years. This version of the model uses a sinlge lifespan for the tower, access and backhaul equipment, and the power system.",
                      "year_1_traffic_desc": "Expected traffic consumption per person in the first year of the system's use.",
                      "traffic_growth_desc": "Expected annual growth in traffic consumption. In underdeveloped markets this is typically 30%.",
                      "tower_cost_desc": "Cost of building a free-standing tower to host cellular or wireless transmission equipment.",
                      "building_cost_desc": "Cost of preparing the rooftop of a building to host cellular or wireless transmission equipment.",
                      "labour_cost_desc": "Cost of labour in the local market, per hour.",
                      "mains_power_installation_cost_desc": "Cost of installing mains power to a site.",
                      "mains_power_cost_kwh_desc": "Cost of energy per Kilowatt hour.",
                      "solar_cost_watt_desc": "Cost of solar systems, per Watt, including installation to a frame or roof. Will be higher in remote and island locations.",
                      "battery_cost_watt_hour_desc": "Cost of battery power per Watt hour of storage.",
                      "battery_dod_desc": "The degree to which a battery is allowed to discharge. Lead acid systems in particular have longer lifespans when discharge depth is limited.",
                      "charger_inverter_base_desc": "The base cost for a generic Maximum Power Point Tracking (MPPT) solar charge controller.",
                      "charger_inverter_variable_desc": "Additional cost per watt for MPPT solar charge controllers. Systems above 1kW are assumed to have a built-in inverter.",
                      "solar_efficiency_desc": "Solar panel efficiency. New modules are typically 18-21% efficient. Changing efficiency changes physical area required for panels, not system price.",
                      "solar_derating_desc": "Percent of solar capacity lost every year due to loss of efficency as panels age.",
                      "battery_age_derating_desc": "Percent of battery capacity lost every year due to loss of efficency as batteries age.",
                      "power_reliable_hours_desc": "Hours of standby power to provision for a system with reliable grid power.",
                      "power_intermittent_hours_desc": "Hours of standby power to provision for a system with intermittent power. This covers countries where load-shedding is common.",
                      "power_offgrid_hours_desc": "Hours of standby power to provision for an offgrid system. This figure will be automatically adjusted depending on the location of the system.",
                      "power_hybrid_hours_desc": "Hours of standby power to provision for a dual solar and grid system. A higher figure may be appropriate where power losses are common in winter or rainy seasons.",
                      "backhaul_none": "No backhaul",
                      "backhaul_gpon": "Gigabit Passive Optical Network (GPON) 1 Gbps",
                      "backhaul_fibre_1g": "Fibre Optic 1 Gbps",
                      "backhaul_fibre_10g": "Fibre Optic 10 Gbps",
                      "backhaul_hts_vsat": "High throughput satellite 100 Mbps",
                      "backhaul_ism_fwa_100": "ISM Fixed Wireless 100 Mbps",
                      "backhaul_ism_fwa_200": "ISM Fixed Wireless 200 Mbps",
                      "backhaul_ism_fwa_500": "ISM Fixed Wireless 500 Mbps",
                      "backhaul_microwave": "Microwave 1,000 Mbps",
                      "backhaul_leo": "Low Earth Orbit Satellite",
                      "introduction": "Introduction",
                      "years": "Years",
                      "hours": "Hours",
                      "percent": "Percent",
                      "gigabytes": "Gigabytes",
                      "USD": "USD",
                      "country": "Country",
                      "location": "Location",
                      "area_covered": "Area Covered",
                      "pop_covered": "Population Covered",
                      "users_supported": "Users Supported",
                      "backhaul_required": "Backhaul Required",
                      "backhaul_available": "Backhaul Available",
                      "available": "Available",
                      "total_power_req": "Total Power Required",
                      "system_lifetime_cost": "Lifetime System Cost",
                      "towers": "Towers",
                      "access_network": "Access Network",
                      "midhaul": "Intermediate Links",
                      "backhaul": "Backhaul",
                      "power_system": "Power System",
                      "power_system_type": "Power System Type",
                      "per_user": "per user",
                      "per_annum": "per_annum",
                      "spectrum": "Spectrum",
                      "spectral_efficiency": "Spectral Efficiency",
                      "coverage_details": "Coverage Details",
                      "user_equipment": "User Equipment",
                      "per": "per",
                      "sector": "Sector",
                      "users_per_ue": "Users per User Equipment",
                      "veg_loss": "Vegetation Loss",
                      "terrain_loss": "Terrain Loss",
                      "cell_radius": "Cell Radius",
                      "coverage_area": "Community Area (sq km)",
                      "pop_density": "Population Density",
                      "system_capacity": "System Capacity",
                      "monthly_gb_user": "Monthly Traffic per User",
                      "est_mir": "Estimated MIR (Maximum or Peak Information Rate)",
                      "est_cir": "Estimated CIR (Committed Information Rate)",
                      "contention_ratio": "Contention Ratio",
                      "peak_hour_capacity_per_user": "Peak Hour Capacity per User",
                      "cost_per_passing": "Lifetime Cost per Passing inc Power use & Refresh",
                      "power_consumption": "Power Consumption",
                      "next_warning": "Changing Frequency, Technology, Terrain, and Vegetation parameters will re-set the model.",
                      "community_characteristics": "Community Characteristics",
                      "freq_tech_terrain_veg": "Frequencies, Technologies, Terrain, and Vegetation",
                      "option": "Option",
                      "value": "Value",
                      "description": "Description",
                      "user_types": "User Types",
                      "service_providers": "Service Providers",
                      "sp_users": "Average number of individual users per service provider",
                      "businesses": "Businesses",
                      "bus_users": "Average number of individual users per business",
                      "internet_cafes": "Internet Cafés",
                      "households_total": "Total number of Households",
                      "pop_in_scope": "In-Scope Population",
                      "non_users_pct": "Percent of non-users per household",
                      "hh_income_week": "Weekly Household Income (USD)",
                      "pop_growth_rate": "Population Growth Rate",
                      "staff_opex_fixed": "Customer Service OpEx (Fixed)",
                      "fte": "FTE",
                      "maintenance_opex": "Maintenance OpEx",
                      "capex_subsidy": "CapEx subsidy ",
                      "opex_subsidy": "OpEx subsidy as % of OpEx",
                      "ue_subsidy": "User Equipment Subsidy",
                      "ue_cost": "Cost of User Equipment",
                      "finance_cost": "Cost of Finance",
                      "debt_proportion": "Proportion of capital funded by debt",
                      "wacc": "Weighted Average Cost of Capital",
                      "inflation": "Expected Inflation",
                      "corp_tax": "Corporate Tax Rate",
                      "staff_opex_variable": "Customer Service Opex (Variable)",
                      "paf_deterred_use": "Public Access Facilities use by a deterred user",
                      "paf_sub_use": "Public Access Facilities use by a subscriber",
                      "paf_non_sub_use": "Public Access Facilities use by a non-subscriber",
                      "paf_gb_hour": "Use of Internet traffic per hour",
                      "paf_facilities_charge": "Charge for Public Access Facilities use",
                      "general_cat": "General Options",
                      "business_cat": "Business Options",
                      "power_cat": "Power Options",
                      "paf_cat": "Public Access Facility Options",
                      "spectrum_licence_fee": "Initial Spectrum Licence Fee",
                      "spectrum_licence_fee_desc": "Any spectrum fees associated with the solution for the life of the solution are entered here.",
                      "capex_subsidy_desc": "The dollar value of Capex funded by subsidies (assumed to be paid at the end of the first year).",
                      "opex_subsidy_desc": "The percentage of Operational Expenditure funded each year for the life of the solution",
                      "ue_subsidy_desc": "Percentage of the total cost of personal equipment for end users subsidised.",
                      "ue_cost_desc": "The cost of handsets or other individual based equipment such as tablets, per user.",
                      "debt_proportion_desc": "The proportion of Capital Expenditure that is funded by debt.",
                      "maintenance_opex_desc": "An estimate of maintenance topics expressed as a percentage of total network and power equipment capital cost.",
                      "inflation_desc": "Annual expected inflation expressed as a percentage price increase.",
                      "other_opex": "Other Operational Expenses",
                      "other_opex_desc": "Other operational costs, for example office costs and overheads. This is expressed as a percentage of labour costs. Community provision may have a lower value than corporate provision because of voluntary contribution of labour by community members.",
                      "wacc_desc": "The required return on the project, or target Weighted Average Cost of Capital. The required rate may be lower for community provision than for commercial provision.",
                      "corp_tax_desc": "It may be that there is no corporate tax or a lower corporate tax rate for community provision.",
                      "oc_margin": "Margin on Operating Cost",
                      "oc_margin_desc": "This allows any differences in required margin on operating costs between commercial and community provision to be accommodated in the model. Note that this margin is on opex only.",
                      "community_capex_discount": "Cost Discount for Community Operators",
                      "community_capex_discount_desc": "For a variety of reasons, the cost of capital equipment may be lower for community provision than for commercial provision. The discount of the cost of capital equipment for community provision compared to commercial is expressed here as a percentage discount. If, for example, the type and cost of capital used for community provision was exactly the same as for commercial provision, this discount would be set to zero.",
                      "staff_opex_fixed_desc": "The fixed operating expenditure for customer service (the expenditure that does not vary by the number of system users) specified by the number of full-time employees required. Community provision may have a lower value than corporate provision because of voluntary contribution of labour by community members.",
                      "staff_opex_variable_desc": "The customer service operating expenditure that varies with the number of  users and  is expressed as the number of full-time employees per  100 users. Community provision may have a lower value than corporate provision because of voluntary contribution of labour by community members.",
                      "paf_deterred_use_desc": "A 'deterred user' is one who would have become a subscriber but decides not to because of the availability of Public Access Facilities. The average number of hours per month per deterred user is set here. ",
                      "paf_facilities_charge_desc": "Charge for use based on a percentage of weekly household income per hour.",
                      "paf_gb_hour_desc": "The traffic in gigabytes per hour generated by the average user of the PAF",
                      "paf_non_sub_use_desc": "A ‘non-subscriber’ is a community member who would not have subscribed (at current parameter values). The average number of hours per month that ‘non-subscribers’ use the PAFs is entered here.",
                      "paf_sub_use_desc": "An estimate of the number of hours that subscribers to alternative Technical solutions will use the Public Access Facility.",
                      "area_sqkm": "Area in km²",
                      "users_per_household": "Users per household",
                      "total_potential_users": "Total potential users",
                      "business_users": "Business Users",
                      "service_provider_users": "Service Provider Users",
                      "area_sqkm_desc": "The total area in square kilometers targeted for coverage.",
                      "households_total_desc": "The total number of households in the target coverage area.",
                      "users_per_household_desc": "Household occupants between the ages of 10-79 years old are assumed to be users of the service.",
                      "non_users_pct_desc": "Household occupants younger than ten years or older than 80 years are not considered to be users of the service.",
                      "total_potential_users_desc": "The number of users times the number of households.",
                      "pop_growth_rate_desc": "Default value via World Bank SP.POP.GROW Population growth (annual %)",
                      "hh_income_week_desc": "An estimate derived from GDP per Capita multiplied by Household Size, divided by 100.",
                      "businesses_desc": "This subscriber type is intended to be used to include the many small community based businesses  with (probably only a few) employees, some of who use connectivity solution. Essentially this subscriber type is a less intensive use-case with lower QOS requirements.",
                      "business_users_desc": "The number of connectivity users in the business.",
                      "service_providers_desc": "This is a subscriber type that is intended to reflect the characteristics of government or private organisations, such as health (rural clinics) or education (schools), NGOs, churches, etc, with potentially many intensive users in the same premises. ",
                      "service_provider_users_desc": "The number of connectivity users in the service provider.",
                      "community_cat": "General Options",
                      "user_cat": "Additional User Types",
                      "hh_above_med_inc": "Households above median income",
                      "hh_below_med_inc": "Households below median income",
                      "subtotal": "Subtotal",
                      "decision_makers_quantity": "Number of decision makers",
                      "hh_size": "Household Size",
                      "people": "People",
                      "hh_size_desc": "Default value sourced from UNDESA PD 2022",
                      "sqkm": "km²",
                      "provider_commercial": "Commercial Operator",
                      "provider_type_desc": "Please choose whether the network will be operated by a commercial provider or a community provider. This option impacts a set of default cost and financial parameters reflect the characteristics of each type of provision. Commercial provisioning implies ROI/profit targets, while community provisioning would imply a cost-recovery / non-profit model.",
                      "provider_type": "Organisation Type",
                      "provider_community": "Community Operator",
                      "paf_usd_hour": "Charge for Public Access Facilities use",
                      "paf_usd_hour_desc": "Charge for use based on a percentage of weekly household income per hour.",
                      "existing_ue_above_med": "Users Above Median Income with Internet-Capable Phones",
                      "existing_ue_below_med": "Users Below Median Income with Internet-Capable Phones",
                      "existing_ue_above_med_desc": "Proportion of users living in households with income above the national median who already own mobile phones capable of browsing the Internet.",
                      "existing_ue_below_med_desc": "Proportion of users living in households with income below the national median who already own mobile phones capable of browsing the Internet.",
                      "demand_curve": "Demand Curve",
                      "model_parameters": "Model Parameters",
                      "dev_notice": "This application is under active development and may change or be unavailable at any time.",
                      "location_error": "Your network must have at least one tower location.",
                      "system_capex": "System CapEx",
                      "physical_characteristics": "Physical Characteristics",
                      "sel": "Select",
                      "power_hybrid": "Hybrid Power",
                      "power_hybrid_desc": "A location that may have reliable or intermittent mains power, but could use solar panels to lower long-term operational costs.",
                      "power_mains_int": "Intermittent Mains Power",
                      "power_mains_int_desc": "Mains power that's subject to regular interruptions.",
                      "power_mains_rel": "Reliable Mains Power",
                      "power_mains_rel_desc": "Mains power that's usually available throughout the day and night all year round.",
                      "power_solar": "Solar Power",
                      "power_solar_desc": "A site that doesn't have mains power but is capable of hosting solar panels.",
                      "power_system_desc": "What type of power is available at this site? Is there room to install solar panels? In most cases a hybrid mains and solar power system will have the lowest long-term cost."
                    }
                }
            }
        },
        400: {
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid language code. Use a two-letter ISO code (e.g. 'en')."}
                }
            }
        },
        500: {
            "content": {
                "application/json": {
                    "example": {"description": "Internal server error"}
                }
            }
        },
    },
)
async def get_site_text_by_lang(lang: str):
    try:
        if not isinstance(lang, str) or len(lang.strip()) != 2 or not lang.strip().isalpha():
            raise HTTPException(status_code=400, detail="Invalid language code. Use a two-letter ISO code (e.g. 'en').")
        data = get_site_text_by_language(lang)
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/defaults", summary="Default model parameters",
            description="Provides a JSON structure with default model settings. Most of these can be changed in the "
                        "user interface by enabling Expert Mode. The returned structure contains the variable name, "
                        "its default value, the minimum and maximum allowed values, and the step allowed. It's "
                        "up to the user interface to enforce minimums, maximums, and steps, because the model will "
                        "fail if vaules outside the minimum and maximum, or with too much precision are submitted.",
            tags=["API GET Endpoints"],
            response_model=List[DefaultsDetail],
            include_in_schema=True,
            responses={
                200: {
                    "content": {
                        "application/json": {
                            "example": {
                                "variable": "system_life",
                                "value": 10.0,
                                "min": 5.0,
                                "max": 15.0,
                                "step": 1.0,
                                "description": "The expected life of the system in years. This version of the"
                                               " model uses a sinlge lifespan for the tower, access and backhaul"
                                               " equipment, and the power system."
                            }
                        }
                    }
                },
                500: {
                    "content": {
                        "application/json": {
                            "example": {"description": "Internal server error"}
                        }
                    }
                }

            })
async def get_defaults_data():
    try:
        data = get_defaults()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/characteristics", summary="Country Specific Characteristics",
             description="Supply an ISO3 country code and get the default model settings for that country. "
                         "This is done by fetching the default model settings and then modifying them with "
                         "country-specific data from the World Bank, ITU, etc.",
             response_model=List[DefaultsDetail],
             tags=["API POST Endpoints"],
             include_in_schema=False,
             responses={
                 200: {
                     "content": {
                         "application/json": {
                             "example": [
                                 {
                                     "variable": "hh_size",
                                     "value": 5.1,
                                     "min": 1,
                                     "max": 10,
                                     "step": 0.1,
                                     "element": "hh_size",
                                     "unit": "people"
                                 }
                             ]
                         }
                     }
                 },
                 500: {
                     "content": {
                         "application/json": {
                             "example": {"description": "Internal server error"}
                         }
                     }
                 }
             })
async def get_characteristics(request: CharacteristicsRequest):
    try:
        iso_3 = request.iso_3.upper()
        defaults_data = calculate_characteristics(iso_3)

        if defaults_data is None:
            raise HTTPException(status_code=404, detail=f"Country with ISO3 '{iso_3}' not found.")

        return defaults_data

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in get_characteristics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

