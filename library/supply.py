import asyncio
import logging
import math
from typing import Any

import requests
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.repositories import DataRepository
from library.classes import PowerModelInput, PowerModelResult, PowerModelRow
import numpy as np
import pandas as pd


NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/climatology/point"
NASA_POWER_ERROR_DETAIL = "The NSAS POWER service returned incomplete or invalid data."
SOLAR_CACHE_TABLE = "Solar_cache"
SOLAR_CACHE_DATA_COLUMNS = (
    "min_sun",
    "max_no_sun_days",
    "annual_no_sun_days",
    "avg_temp",
    "min_temp",
    "max_temp",
)
MONTHS = (
    "JAN",
    "FEB",
    "MAR",
    "APR",
    "MAY",
    "JUN",
    "JUL",
    "AUG",
    "SEP",
    "OCT",
    "NOV",
    "DEC",
)


def _nasa_power_error() -> HTTPException:
    return HTTPException(status_code=502, detail=NASA_POWER_ERROR_DETAIL)


def _as_valid_nasa_value(value: Any) -> float | None:
    """Return a finite NASA value, treating its -999 fill value as invalid."""
    if isinstance(value, bool):
        return None

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(number) or number == -999:
        return None
    return number


def _is_nasa_fill_value(value: Any) -> bool:
    if isinstance(value, bool):
        return False

    try:
        return float(value) == -999
    except (TypeError, ValueError):
        return False


def _valid_monthly_values(parameter: Any) -> list[float]:
    if not isinstance(parameter, dict):
        return []

    values = []
    for month in MONTHS:
        value = _as_valid_nasa_value(parameter.get(month))
        if value is not None:
            values.append(value)
    return values


def _complete_valid_monthly_values(parameter: Any) -> list[float] | None:
    """Return all twelve monthly values, or None when a month is missing/invalid."""
    if not isinstance(parameter, dict):
        return None

    values = []
    for month in MONTHS:
        value = _as_valid_nasa_value(parameter.get(month))
        if value is None:
            return None
        values.append(value)
    return values


def _parse_solar_cache_record(record: Any) -> dict[str, float] | None:
    """Accept a cache record only when every calculated statistic is usable."""
    if not isinstance(record, dict):
        return None

    solar_stats = {}
    for column in SOLAR_CACHE_DATA_COLUMNS:
        value = _as_valid_nasa_value(record.get(column))
        if value is None:
            return None
        solar_stats[column] = value
    return solar_stats


async def _get_cached_solar_stats(
    repository: DataRepository,
    latitude: float,
    longitude: float,
) -> dict[str, float] | None:
    columns = ", ".join(("latitude", "longitude", *SOLAR_CACHE_DATA_COLUMNS))
    sql_query = (
        f"SELECT {columns} FROM {SOLAR_CACHE_TABLE} "
        "WHERE latitude = :latitude AND longitude = :longitude"
    )

    records = await repository.fetch_all(
        sql_query,
        {"latitude": latitude, "longitude": longitude},
    )
    for record in records:
        solar_stats = _parse_solar_cache_record(record)
        if solar_stats is not None:
            return solar_stats
    return None


def _parse_nasa_solar_stats(payload: Any) -> dict[str, float]:
    """Extract the statistics needed by the power model from NASA POWER JSON."""
    if not isinstance(payload, dict):
        raise _nasa_power_error()

    properties = payload.get("properties")
    if not isinstance(properties, dict):
        raise _nasa_power_error()

    parameters = properties.get("parameter")
    if not isinstance(parameters, dict):
        raise _nasa_power_error()

    temperatures = parameters.get("T2M")
    irradiance = parameters.get("SI_TILTED_AVG_LATITUDE")
    no_sun_days = parameters.get("EQUIV_NO_SUN_CONSEC_07")
    if not all(isinstance(parameter, dict) for parameter in (temperatures, irradiance, no_sun_days)):
        raise _nasa_power_error()

    temperature_values = _valid_monthly_values(temperatures)
    if not temperature_values:
        raise _nasa_power_error()

    annual_temperature = _as_valid_nasa_value(temperatures.get("ANN"))
    if annual_temperature is not None:
        avg_temp = annual_temperature
    elif _is_nasa_fill_value(temperatures.get("ANN")) and len(temperature_values) >= 10:
        avg_temp = sum(temperature_values) / len(temperature_values)
    else:
        raise _nasa_power_error()

    sun_values = _valid_monthly_values(irradiance)
    if not sun_values:
        raise _nasa_power_error()

    no_sun_values = _complete_valid_monthly_values(no_sun_days)
    if no_sun_values is None:
        raise _nasa_power_error()

    return {
        "min_sun": round(min(sun_values),2),
        "max_no_sun_days": round(max(no_sun_values),2),
        "annual_no_sun_days": round(sum(value * 4.3 for value in no_sun_values),2),
        "avg_temp": avg_temp,
        "min_temp": min(temperature_values),
        "max_temp": max(temperature_values),
    }


def _get_nasa_solar_stats(latitude: float, longitude: float) -> dict[str, float]:
    url = (
        f"{NASA_POWER_URL}?parameters=SI_EF_TILTED_SURFACE,EQUIV_NO_SUN_CONSEC_07,T2M"
        f"&community=RE&longitude={longitude:.2f}&latitude={latitude:.2f}&format=JSON"
    )

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        logging.warning("NASA POWER request failed for %s, %s: %s", latitude, longitude, exc)
        raise _nasa_power_error() from exc

    return _parse_nasa_solar_stats(payload)


async def _store_solar_cache(
    repository: DataRepository,
    latitude: float,
    longitude: float,
    solar_stats: dict[str, float],
) -> None:
    """Persist a successful NASA response for future requests at these coordinates."""
    try:
        await repository.store_solar_cache(latitude, longitude, solar_stats)
    except SQLAlchemyError:
        # NASA provided valid data, so a cache write failure should not prevent a
        # user from receiving a power-model result. It will be retried next time.
        logging.exception("Failed to store solar statistics in Solar_cache")


async def get_solar_statistics(
    repository: DataRepository,
    latitude: float,
    longitude: float,
) -> dict[str, float]:
    """Return cached solar statistics, retrieving and caching them on a miss."""
    latitude = round(float(latitude), 2)
    longitude = round(float(longitude), 2)
    if not math.isfinite(latitude) or not math.isfinite(longitude):
        raise ValueError("Latitude and longitude must be finite numbers.")

    solar_stats = await _get_cached_solar_stats(repository, latitude, longitude)
    if solar_stats is not None:
        logging.info("Using cached solar statistics for %s, %s", latitude, longitude)
        return solar_stats

    logging.info("No complete solar-cache record for %s, %s; requesting NASA POWER", latitude, longitude)
    solar_stats = await asyncio.to_thread(_get_nasa_solar_stats, latitude, longitude)
    await _store_solar_cache(repository, latitude, longitude, solar_stats)
    return solar_stats


def assign_users(df, total_potential_users):
    df = df.copy()
    df["assigned_users"] = 0
    df["_row_order"] = np.arange(len(df))

    # Sort by cost, then original order
    df = df.sort_values(["cost_per_passing", "_row_order"])

    remaining = int(round(total_potential_users))

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
            rem = int(remaining % n)
            alloc = np.full(n, int(base))
            alloc[:rem] += 1

        # Sub-case B: proportional allocation
        else:
            alloc = np.floor(
                remaining * capacities / tier_capacity
            ).astype(int)

            shortfall = int(remaining - alloc.sum())
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
        df["assigned_ue"] = 0
        df.loc[mask, "assigned_ue"] = (
            df.loc[mask, "assigned_users"] / df.loc[mask, "users_per_ue"]
        ).round().astype(int)
        df.loc[mask, "access_capex"] += (df.loc[mask, "cpe_cost"] * round((df.loc[mask, "assigned_users"] / df.loc[mask, "users_per_ue"])))
    else:
        df.loc[mask, "access_capex"] += round(df.loc[mask, "cpe_cost"] * df.loc[mask, "assigned_users"], 2)
    return df


async def power_model(
    repository: DataRepository,
    input_data: PowerModelInput,
) -> PowerModelResult:
    logging.info("Entered the power model")

    # Get variables from the input data
    location = input_data.location
    latitude = round(float(input_data.latitude), 2)
    longitude = round(float(input_data.longitude), 2)
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
    collection_w_day_m2 = None
    panels_needed_m2 = None
    solar_cost = 0.0
    power_capex = 0
    power_opex = 0

    solar_stats = await get_solar_statistics(repository, latitude, longitude)
    min_sun = solar_stats["min_sun"]
    max_no_sun_days = solar_stats["max_no_sun_days"]
    annual_no_sun_days = solar_stats["annual_no_sun_days"]
    min_temp = solar_stats["min_temp"]
    solar_efficiency = input_data.solar_efficiency / 100
    solar_derating = input_data.solar_derating / 100
    battery_age_derating = input_data.battery_age_derating / 100
    battery_dod = input_data.battery_dod / 100
    logging.info("Extracted solar statistics")

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

    if system_type == "power_mains_rel":
        adjusted_hours = power_reliable_hours
        base_battery = power_required * adjusted_hours * battery_dod
        aged_battery = base_battery / ((1 - battery_age_derating) ** system_life)
        cold_derating = calculate_cold_derating(min_temp)
        battery_required = aged_battery / (cold_derating / 100)
        battery_cost = battery_required * battery_cost_watt_hour
        charger_cost = charger_inverter_base + (power_required * charger_inverter_variable)
        power_opex = (mains_power_cost_kwh / 1000) * power_required * 24 * 365 * system_life
        power_capex = battery_cost + charger_cost + mains_power_installation_cost

    elif system_type == "power_mains_int":
        adjusted_hours = power_intermittent_hours
        base_battery = power_required * adjusted_hours * battery_dod
        aged_battery = base_battery / ((1 - battery_age_derating) ** system_life)
        cold_derating = calculate_cold_derating(min_temp)
        battery_required = aged_battery / (cold_derating / 100)
        battery_cost = battery_required * battery_cost_watt_hour
        charger_cost = charger_inverter_base + (power_required * charger_inverter_variable)
        power_opex = (mains_power_cost_kwh / 1000) * power_required * 24 * 365 * system_life
        power_capex = battery_cost + charger_cost + mains_power_installation_cost

    elif system_type == "power_hybrid":
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

    elif system_type == "power_solar":
        power_opex = 0
        mains_power_installation_cost = 0
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
    else:
        raise ValueError(f"Unsupported power system type: {system_type}")

    power_row = PowerModelRow(
        location_name=location.location_name,
        system_type=system_type,
        latitude=latitude,
        longitude=longitude,
        power_required=round(float(power_required), 2),
        system_life=system_life,
        solar_cost_watt=solar_cost_watt,
        solar_derating=input_data.solar_derating,
        solar_efficiency=input_data.solar_efficiency,
        battery_age_derating=input_data.battery_age_derating,
        battery_cost_watt_hour=battery_cost_watt_hour,
        battery_dod=input_data.battery_dod,
        charger_inverter_base=charger_inverter_base,
        charger_inverter_variable=charger_inverter_variable,
        mains_power_cost_kwh=mains_power_cost_kwh,
        mains_power_installation_cost=mains_power_installation_cost,
        power_hybrid_hours=power_hybrid_hours,
        power_intermittent_hours=power_intermittent_hours,
        power_reliable_hours=power_reliable_hours,
        min_daily_sun_wm2=round(min_sun, 2),
        max_no_sun_days=round(max_no_sun_days, 2),
        annual_no_sun_days=round(annual_no_sun_days, 2),
        min_temp_c=round(min_temp, 2),
        adjusted_hours=round(float(adjusted_hours), 2),
        battery_required=round(float(battery_required), 2),
        battery_cost=round(float(battery_cost), 2),
        charger_cost=round(float(charger_cost), 2),
        power_opex=round(float(power_opex), 2),
        watts_day_m2=round(float(collection_w_day_m2), 2) if collection_w_day_m2 is not None else None,
        panels_need_m2=round(float(panels_needed_m2), 2) if panels_needed_m2 is not None else None,
        solar_cost=round(float(solar_cost), 2),
        power_capex=round(float(power_capex), 2),
    )

    logging.info("Power model result row: %s", power_row.model_dump())

    return PowerModelResult(
        power_capex=round(float(power_capex), 2),
        power_opex=round(float(power_opex), 2),
        power_row=power_row,
    )
