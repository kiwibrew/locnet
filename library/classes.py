from pydantic import BaseModel, RootModel, Field
from typing import List, Optional, Dict, Any


class LanguagesResponse(RootModel):
    root: Dict[str, str]


class CountriesResponse(RootModel):
    root: Dict[str, str]


class PowerItem(BaseModel):
    element: str
    description: str


class PowerResponse(RootModel):
    root: List[PowerItem]


class SiteTextResponse(RootModel):
    root: Dict[str, str]


class BackhaulDetail(BaseModel):
    name: str
    type: str
    speed_mbps: int
    power_watts: int
    capital_cost_usd: float
    cost_base: float
    cost_mbps: float
    element: str


class DefaultsDetail(BaseModel):
    variable: str
    value: float
    min: float
    max: float
    step: float
    element: str
    unit: str
    alt: float
    category: str
    seq: int
    no_default: Optional[bool] = Field(default=None, alias="noDefault")

class InputData(BaseModel):
    x: float
    y: float


class FrequencyDetail(BaseModel):
    frequency: int
    frequency_name: str


class FrequencyData(BaseModel):
    frequencies: List[int]
    technologies: Optional[List[str]] = None  # Allows for multiple technologies


class CharacteristicsRequest(BaseModel):
    iso_3: str


class MidhaulDetail(BaseModel):
    name: str
    speed_mbps: int
    capital_cost_usd: float
    power_watts: float
    element: str


class FrequencyResponse(BaseModel):
    frequency: int
    network_types: List[str]  # A list of strings to hold all matches


class TechnologyDetail(BaseModel):
    technology: str
    technology_name: str


# Define the input data model
class LocationData(BaseModel):
    location_name: str
    tower_cost: Optional[float]
    network_type: List[str]
    sectors: List[int]
    network_links: List[str]
    backhaul_links: List[str]
    backhaul_cost_base: List[float]
    backhaul_cost_mbps: List[float]
    power_type: str


class BuilderInput(BaseModel):
    area_sqkm: float
    battery_age_derating: float
    battery_cost_watt_hour: float
    battery_dod: float
    charger_inverter_base: float
    charger_inverter_variable: float
    iso_3: str
    labour_cost: float
    lang: Optional[str] = Field(default="en")  # Optional language with default "en"
    locations: List['LocationData']
    mains_power_cost_kwh: float
    mains_power_installation_cost: float
    power_hybrid_hours: int
    power_intermittent_hours: int
    power_reliable_hours: int
    solar_cost_watt: float
    solar_derating: float
    solar_efficiency: int
    system_life: int
    terrain_type: Optional[str] = Field(default="none")
    total_potential_users: float
    traffic_growth: float
    users_per_household: float
    vegetation_type: Optional[str] = Field(default="none")
    year_1_traffic: int

    # Expanded Economic Model Fields
    households_total: Optional[int] = Field(default=100)
    hh_size: Optional[float] = Field(default=3)
    pop_growth_rate: Optional[float] = Field(default=0.3)
    hh_income_week: float
    businesses: Optional[int] = Field(default=1)
    business_users: Optional[float] = Field(default=2)
    service_providers: Optional[int] = Field(default=1)
    service_provider_users: Optional[float] = Field(default=2)
    staff_opex_fixed: float
    staff_opex_variable: float
    maintenance_opex: Optional[float] = Field(default=2)
    capex_subsidy: Optional[float] = Field(default=20)
    opex_subsidy: Optional[float] = Field(default=20)
    ue_subsidy: Optional[float] = Field(default=0)
    finance_cost: Optional[float] = Field(default=5)
    debt_proportion: Optional[float] = Field(default=50)
    wacc: float
    corp_tax: Optional[float] = Field(default=0)
    spectrum_licence_fee: float
    other_opex: Optional[float] = Field(default=7.5)
    oc_margin: Optional[float] = Field(default=15)
    community_capex_discount: float
    paf_deterred_use: Optional[float] = Field(default=0)
    paf_sub_use: Optional[float] = Field(default=0)
    paf_non_sub_use: Optional[float] = Field(default=0)
    paf_gb_hour: Optional[float] = Field(default=0.5)
    paf_facilities_charge: Optional[float] = Field(default=0.5)
    paf_usd_hour: Optional[float] = Field(default=2.128)
    ue_cost: Optional[float] = Field(default=100)
    inflation: float
    power_offgrid_hours: Optional[float] = Field(default=96)
    provider_type: Optional[str] = Field(default="provider_community")
    existing_ue_above_med: Optional[float] = Field(default=.30)
    existing_ue_below_med: Optional[float] = Field(default=.1)


# Define the output data model
class BuilderOutput(BaseModel):
    access_cost: Optional[int] = None
    area_covered: float
    area_sqkm: Optional[float] = None
    backhaul_available: int
    backhaul_cost: int
    backhaul_capex: int
    backhaul_opex: int
    backhaul_annual_opex: list
    backhaul_required: int
    battery_age_derating: Optional[float] = None
    battery_cost_watt_hour: Optional[float] = None
    battery_dod: Optional[float] = None
    charger_inverter_base: Optional[float] = None
    charger_inverter_variable: Optional[float] = None
    connectivity_cost: Optional[int] = None
    labour_cost: Optional[float] = None
    lang: Optional[str] = Field(default="en")
    location: str
    lowest_power_system_type: Optional[str] = None
    mains_power_cost_kwh: Optional[float] = None
    mains_power_installation_cost: Optional[float] = None
    midhaul_available: Optional[int] = None
    midhaul_cost: Optional[int] = None
    off_grid_system_cost: Optional[int] = None
    population_covered: Optional[int] = None
    power_capex: int
    power_intermittent_hours: Optional[int] = None
    power_hybrid_hours: Optional[int] = None
    power_reliable_hours: Optional[int] = None
    power_opex: int
    power_required: int
    solar_cost_watt: Optional[float] = None
    solar_derating: Optional[float] = None
    solar_efficiency: Optional[int] = None
    system_life: int
    terrain_type: str
    total_potential_users: Optional[float] = None
    total_system_cost: int
    tower_cost: Optional[float] = None
    towers_cost: Optional[int] = None
    traffic_growth: Optional[float] = None
    users_per_household: Optional[float] = None
    users_supported: int
    vegetation_type: Optional[str] = None
    year_1_traffic: Optional[int] = None
    detailed_results: List[Dict[str, Any]]


# Define the output data model
class ModelerOutput(BaseModel):
    access_cost: Optional[int] = None
    area_covered: float
    area_sqkm: Optional[float] = None
    backhaul_available: int
    backhaul_cost: int
    backhaul_capex: int
    backhaul_opex: int
    backhaul_annual_opex: list
    backhaul_required: int
    battery_age_derating: Optional[float] = None
    battery_cost_watt_hour: Optional[float] = None
    battery_dod: Optional[float] = None
    charger_inverter_base: Optional[float] = None
    charger_inverter_variable: Optional[float] = None
    connectivity_cost: Optional[int] = None
    labour_cost: Optional[float] = None
    lang: Optional[str] = Field(default="en")
    country_name: str
    lowest_power_system_type: Optional[str] = None
    mains_power_cost_kwh: Optional[float] = None
    mains_power_installation_cost: Optional[float] = None
    midhaul_available: Optional[int] = None
    midhaul_cost: Optional[int] = None
    off_grid_system_cost: Optional[int] = None
    population_covered: Optional[int] = None
    power_capex: int
    power_intermittent_hours: Optional[int] = None
    power_hybrid_hours: Optional[int] = None
    power_reliable_hours: Optional[int] = None
    power_opex: int
    power_required: int
    solar_cost_watt: Optional[float] = None
    solar_derating: Optional[float] = None
    solar_efficiency: Optional[int] = None
    system_capex: int
    system_life: int
    terrain_type: str
    total_potential_users: Optional[float] = None
    total_system_cost: int
    tower_cost: Optional[float] = None
    towers_cost: Optional[int] = None
    traffic_growth: Optional[float] = None
    users_per_household: Optional[float] = None
    users_supported: int
    vegetation_type: Optional[str] = None
    year_1_traffic: Optional[int] = None
    detailed_results: List[Dict[str, Any]]
    demand_curve_points: List[Dict[str, float]] = Field(default_factory=list)
    dcba_table_rows: Optional[List[Dict[str, Any]]] = None
    dcba_table_columns: Optional[List[Dict[str, str]]] = None
    pl_table_rows: Optional[List[Dict[str, Any]]] = None
    pl_table_columns: Optional[List[Dict[str, str]]] = None
    inv_table_rows: Optional[List[Dict[str, Any]]] = None
    inv_table_columns: Optional[List[Dict[str, str]]] = None
    outcomes_table_rows: Optional[List[Dict[str, Any]]] = None
    outcomes_table_columns: Optional[List[Dict[str, str]]] = None
    net_summary_table_rows: Optional[List[Dict[str, Any]]] = None
    net_summary_table_columns: Optional[List[Dict[str, str]]] = None

class ModelerAPIOutput(BaseModel):
    detailed_results: List[Dict[str, Any]]
    demand_curve_points: List[Dict[str, float]] = Field(default_factory=list)
    dcba_table_rows: Optional[List[Dict[str, Any]]] = None
    dcba_table_columns: Optional[List[Dict[str, str]]] = None
    pl_table_rows: Optional[List[Dict[str, Any]]] = None
    pl_table_columns: Optional[List[Dict[str, str]]] = None
    inv_table_rows: Optional[List[Dict[str, Any]]] = None
    inv_table_columns: Optional[List[Dict[str, str]]] = None
    outcomes_table_rows: Optional[List[Dict[str, Any]]] = None
    outcomes_table_columns: Optional[List[Dict[str, str]]] = None
    net_summary_table_rows: Optional[List[Dict[str, Any]]] = None
    net_summary_table_columns: Optional[List[Dict[str, str]]] = None

# Solar Model Input
class SolarModelInput:
    def __init__(self,
                 battery_age_derating: float,
                 battery_cost_watt_hour: float,
                 battery_dod: float,
                 charger_inverter_base: float,
                 charger_inverter_variable: float,
                 latitude: float,
                 longitude: float,
                 mains_power_installation_cost: float,
                 mains_power_cost_kwh: float,
                 power_hybrid_hours: float,
                 power_intermittent_hours: float,
                 power_reliable_hours: float,
                 power_required: int,
                 system_life: int,
                 system_type: str,
                 solar_cost_watt: float,
                 solar_derating: float,
                 solar_efficiency: int):
        self.battery_age_derating = battery_age_derating
        self.battery_cost_watt_hour = battery_cost_watt_hour
        self.battery_dod = battery_dod
        self.charger_inverter_base = charger_inverter_base
        self.charger_inverter_variable = charger_inverter_variable
        self.latitude = latitude
        self.longitude = longitude
        self.mains_power_installation_cost = mains_power_installation_cost
        self.mains_power_cost_kwh = mains_power_cost_kwh
        self.power_hybrid_hours = power_hybrid_hours
        self.power_intermittent_hours = power_intermittent_hours
        self.power_reliable_hours = power_reliable_hours
        self.power_required = power_required
        self.system_life = system_life
        self.system_type = system_type
        self.solar_cost_watt = solar_cost_watt
        self.solar_derating = solar_derating
        self.solar_efficiency = solar_efficiency
