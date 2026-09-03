"""Pydantic schemas for the network model and lookup APIs."""

from math import pi
from pydantic import BaseModel, ConfigDict, RootModel, Field, model_validator
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


class BoundsResponse(BaseModel):
    iso_3: str
    centroid_lat: float
    centroid_long: float
    bbox_west: float
    bbox_south: float
    bbox_east: float
    bbox_north: float


# Define the input data model
class LocationData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    location_name: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    radius: float = Field(default=2.0, ge=0.05, le=50.0)
    households: Optional[int] = Field(default=None, ge=0)
    tower_cost: Optional[float] = Field(default=None, ge=0)
    tower_opex: Optional[float] = Field(default=None, ge=0)
    tower_height: Optional[float] = Field(default=None, gt=0)
    network_type: List[str]
    sectors: List[int]
    network_links: List[str]
    backhaul_links: List[str]
    backhaul_cost_base: List[float]
    backhaul_cost_mbps: List[float]
    power_type: str


class BuilderInput(BaseModel):
    model_config = ConfigDict(extra="ignore", protected_namespaces=())

    model_version: int = Field(default=2, ge=1)
    area_sqkm: Optional[float] = None
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
    total_potential_users: Optional[float] = Field(default=None, ge=0)
    traffic_growth: float
    users_per_household: float
    year_1_traffic: int

    # Expanded Economic Model Fields
    households_total: Optional[int] = Field(default=None, ge=0)
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

    @model_validator(mode="after")
    def derive_location_aggregates(self):
        """Legacy submitted aggregate values never override location data."""
        self.area_sqkm = round(
            sum(pi * location.radius ** 2 for location in self.locations), 2
        )
        self.households_total = sum(
            location.households or 0 for location in self.locations
        )
        return self


class LocationCoverageMap(BaseModel):
    location_name: str
    latitude: float
    longitude: float
    geojson: Dict[str, Any]


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
    total_potential_users: Optional[float] = None
    total_system_cost: int
    tower_cost: Optional[float] = None
    towers_cost: Optional[int] = None
    traffic_growth: Optional[float] = None
    users_per_household: Optional[float] = None
    users_supported: int
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
    power_opex: float
    power_required: int
    solar_cost_watt: Optional[float] = None
    solar_derating: Optional[float] = None
    solar_efficiency: Optional[int] = None
    system_capex: int
    system_life: int
    total_potential_users: Optional[float] = None
    total_system_cost: int
    tower_cost: Optional[float] = None
    towers_cost: Optional[int] = None
    traffic_growth: Optional[float] = None
    users_per_household: Optional[float] = None
    users_supported: int
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
    pbom_table_rows: Optional[List[Dict[str, Any]]] = None
    pbom_table_columns: Optional[List[Dict[str, str]]] = None
    bom_table_rows: Optional[List[Dict[str, Any]]] = None
    bom_table_columns: Optional[List[Dict[str, str]]] = None
    coverage_maps: List[LocationCoverageMap] = Field(default_factory=list)


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
    pbom_table_rows: Optional[List[Dict[str, Any]]] = None
    pbom_table_columns: Optional[List[Dict[str, str]]] = None
    bom_table_rows: Optional[List[Dict[str, Any]]] = None
    bom_table_columns: Optional[List[Dict[str, str]]] = None
    coverage_maps: List[LocationCoverageMap] = Field(default_factory=list)


# Power Model Input
class PowerModelInput(BaseModel):
    location: LocationData
    latitude: float
    longitude: float
    power_required: float
    system_life: int
    solar_cost_watt: float
    solar_derating: float
    solar_efficiency: int
    battery_age_derating: float
    battery_cost_watt_hour: float
    battery_dod: float
    charger_inverter_base: float
    charger_inverter_variable: float
    mains_power_cost_kwh: float
    mains_power_installation_cost: float
    power_hybrid_hours: float
    power_intermittent_hours: float
    power_reliable_hours: float
    system_type: str


class PowerModelRow(BaseModel):
    location_name: str
    system_type: str
    latitude: float
    longitude: float
    power_required: float
    system_life: int
    solar_cost_watt: float
    solar_derating: float
    solar_efficiency: int
    battery_age_derating: float
    battery_cost_watt_hour: float
    battery_dod: float
    charger_inverter_base: float
    charger_inverter_variable: float
    mains_power_cost_kwh: float
    mains_power_installation_cost: float
    power_hybrid_hours: float
    power_intermittent_hours: float
    power_reliable_hours: float
    min_daily_sun_wm2: float
    max_no_sun_days: float
    annual_no_sun_days: float
    min_temp_c: float
    adjusted_hours: float
    battery_required: float
    battery_cost: float
    charger_cost: float
    power_opex: float
    watts_day_m2: Optional[float] = None
    panels_need_m2: Optional[float] = None
    solar_cost: float = 0
    power_capex: float


class PowerModelResult(BaseModel):
    power_capex: float
    power_opex: float
    power_row: PowerModelRow
